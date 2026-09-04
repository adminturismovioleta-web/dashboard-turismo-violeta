from __future__ import annotations

import io
import json
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Iterable
from urllib.parse import urljoin, urlsplit

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

APP_VERSION = "v21.0 panel administrativo integral y filtros"

st.set_page_config(
    page_title="Dashboard Turismo Violeta",
    page_icon="📊",
    layout="wide",
)

# Configuración común para evitar zoom, barra de herramientas o interacción accidental en gráficos.
CHART_CONFIG = {"displayModeBar": False, "staticPlot": True, "scrollZoom": False, "responsive": True}

# Metadatos reconstruidos desde el XLSForm recibido el 10/07.
# Incluye los 7 principios WEPs, 13 objetivos y 48 indicadores en el orden lógico del formulario.
PRINCIPLES = [{'id': 1,
  'title': 'Promover la igualdad de género desde la dirección al más alto nivel',
  'objectives': [3],
  'documents': 'Principios WEPS; complementar con Acuerdo MDT-2025-102 cuando existan brechas laborales.',
  'reading': 'Reforzar compromiso de alta dirección, gobernanza, Comité de Igualdad, políticas institucionales y '
             'seguimiento del plan.',
  'score_field': 'score_wep_1_pct',
  'level_field': 'nivel_wep_1',
  'reading_field': 'inf_wep_01_lectura_plan'},
 {'id': 2,
  'title': 'Trato equitativo, derechos humanos y no discriminación en el trabajo',
  'objectives': [1, 2],
  'documents': 'Principios WEPS, Acuerdo MDT-2025-102, Protocolo Turismo Violeta y Tool Kit.',
  'reading': 'Priorizar trato equitativo, no discriminación, igualdad en selección, promoción, formación, remuneración '
             'y condiciones laborales.',
  'score_field': 'score_wep_2_pct',
  'level_field': 'nivel_wep_2',
  'reading_field': 'inf_wep_02_lectura_plan'},
 {'id': 3,
  'title': 'Salud, seguridad, bienestar y vida libre de violencia',
  'objectives': [4, 5],
  'documents': 'Protocolo Turismo Violeta, Tool Kit, Acuerdo MDT-2025-102 y Manual ESNNA.',
  'reading': 'Fortalecer seguridad, salud, bienestar, prevención de violencia y acoso, rutas de atención, derivación y '
             'protección.',
  'score_field': 'score_wep_3_pct',
  'level_field': 'nivel_wep_3',
  'reading_field': 'inf_wep_03_lectura_plan'},
 {'id': 4,
  'title': 'Educación, formación y desarrollo profesional de mujeres y grupos subrepresentados',
  'objectives': [6, 7],
  'documents': 'Principios WEPS y Tool Kit para capacitación y fortalecimiento de capacidades.',
  'reading': 'Consolidar educación, formación, desarrollo profesional y participación de mujeres y grupos '
             'subrepresentados.',
  'score_field': 'score_wep_4_pct',
  'level_field': 'nivel_wep_4',
  'reading_field': 'inf_wep_04_lectura_plan'},
 {'id': 5,
  'title': 'Desarrollo empresarial, cadena de suministro y marketing a favor del empoderamiento de las mujeres',
  'objectives': [8, 9],
  'documents': 'Principios WEPS y Tool Kit para marketing, proveedores y cadena de valor.',
  'reading': 'Ajustar prácticas empresariales, marketing responsable, cadena de suministro, proveedores y compras con '
             'enfoque de igualdad.',
  'score_field': 'score_wep_5_pct',
  'level_field': 'nivel_wep_5',
  'reading_field': 'inf_wep_05_lectura_plan'},
 {'id': 6,
  'title': 'Igualdad mediante iniciativas comunitarias y participación territorial',
  'objectives': [10, 11],
  'documents': 'Principios WEPS, Plan Integral de Seguridad Turística y Protocolo Turismo Violeta.',
  'reading': 'Fortalecer iniciativas comunitarias, participación territorial, pagos transparentes, alianzas locales y '
             'saberes ancestrales.',
  'score_field': 'score_wep_6_pct',
  'level_field': 'nivel_wep_6',
  'reading_field': 'inf_wep_06_lectura_plan'},
 {'id': 7,
  'title': 'Evaluar y difundir los progresos realizados a favor de la igualdad de género',
  'objectives': [12, 13],
  'documents': 'Principios WEPS, Protocolo Turismo Violeta y Tool Kit para seguimiento, evidencias y comunicación de '
               'avances.',
  'reading': 'Institucionalizar monitoreo, indicadores, informes, comunicación de avances, rendición de cuentas y '
             'mejora continua.',
  'score_field': 'score_wep_7_pct',
  'level_field': 'nivel_wep_7',
  'reading_field': 'inf_wep_07_lectura_plan'}]

OBJECTIVES = {1: {'id': 1,
     'title': 'Equidad de género en selección, promoción, formación, liderazgo y remuneración',
     'linked': 'Principios relacionados: WEPS 1 y 2',
     'score_field': 'inf_obj_01_pct',
     'level_field': 'inf_obj_01_nivel',
     'reading_field': 'inf_obj_01_lectura_plan',
     'reading': 'Priorizar los indicadores con score menor a 76%, especialmente políticas, datos desagregados, brecha '
                'salarial y participación equilibrada.',
     'indicators': [1, 2, 3, 4, 5, 6, 7]},
 2: {'id': 2,
     'title': 'Participación de mujeres en nivel operativo, liderazgo y espacios de planificación local',
     'linked': 'Principios relacionados: WEPS 1, 2 y 6',
     'score_field': 'inf_obj_02_pct',
     'level_field': 'inf_obj_02_nivel',
     'reading_field': 'inf_obj_02_lectura_plan',
     'reading': 'Fortalecer participación de mujeres en áreas operativas y espacios externos de '
                'articulación/planificación.',
     'indicators': [39]},
 3: {'id': 3,
     'title': 'Comité de Igualdad y gobernanza del plan',
     'linked': 'Principio relacionado: WEPS 1',
     'score_field': 'inf_obj_03_pct',
     'level_field': 'inf_obj_03_nivel',
     'reading_field': 'inf_obj_03_lectura_plan',
     'reading': 'Formalizar el comité, generar actas, capacitar integrantes y establecer seguimiento periódico.',
     'indicators': [8, 9, 20, 21, 22]},
 4: {'id': 4,
     'title': 'Gestión de riesgos sobre trata, tráfico y explotación sexual en turismo',
     'linked': 'Principio relacionado: WEPS 3',
     'score_field': 'inf_obj_04_pct',
     'level_field': 'inf_obj_04_nivel',
     'reading_field': 'inf_obj_04_lectura_plan',
     'reading': 'Implementar rutas, protocolos, reportes y evidencias de coordinación con autoridades.',
     'indicators': [18, 19, 36]},
 5: {'id': 5,
     'title': 'Lugar de trabajo seguro, libre de acoso, violencia, discriminación y con rutas de atención',
     'linked': 'Principios relacionados: WEPS 2 y 3',
     'score_field': 'inf_obj_05_pct',
     'level_field': 'inf_obj_05_nivel',
     'reading_field': 'inf_obj_05_lectura_plan',
     'reading': 'Cerrar brechas en registro, atención, derivación, sanción, prevención, protocolos y rutas '
                'internas/externas.',
     'indicators': [10, 11, 12, 13, 14, 15, 16, 17]},
 6: {'id': 6,
     'title': 'Desarrollo profesional de mujeres y grupos subrepresentados',
     'linked': 'Principio relacionado: WEPS 4',
     'score_field': 'inf_obj_06_pct',
     'level_field': 'inf_obj_06_nivel',
     'reading_field': 'inf_obj_06_lectura_plan',
     'reading': 'Consolidar plan de capacitación, cobertura, participación desagregada y evidencias por tema.',
     'indicators': [23, 24, 25, 26, 27, 28]},
 7: {'id': 7,
     'title': 'Capacitación y sensibilización en igualdad, prevención y cero tolerancia',
     'linked': 'Principios relacionados: WEPS 3 y 4',
     'score_field': 'inf_obj_07_pct',
     'level_field': 'inf_obj_07_nivel',
     'reading_field': 'inf_obj_07_lectura_plan',
     'reading': 'Priorizar capacitación anual, cobertura alta del personal y registro desagregado de participantes.',
     'indicators': [29, 30, 31, 32, 33, 34]},
 8: {'id': 8,
     'title': 'Comunicación y marketing responsable sin estereotipos ni discriminación',
     'linked': 'Principio relacionado: WEPS 5',
     'score_field': 'inf_obj_08_pct',
     'level_field': 'inf_obj_08_nivel',
     'reading_field': 'inf_obj_08_lectura_plan',
     'reading': 'Implementar revisión periódica de contenidos y criterios de marketing responsable.',
     'indicators': [35]},
 9: {'id': 9,
     'title': 'Proveedores, cadena de valor y compras responsables con enfoque de igualdad',
     'linked': 'Principio relacionado: WEPS 5',
     'score_field': 'inf_obj_09_pct',
     'level_field': 'inf_obj_09_nivel',
     'reading_field': 'inf_obj_09_lectura_plan',
     'reading': 'Incorporar lineamientos de igualdad en proveedores, priorización de compras y desagregación de datos '
                'de la cadena de valor.',
     'indicators': [37, 38, 40, 41, 42]},
 10: {'id': 10,
      'title': 'Vinculación comunitaria, participación territorial y pagos con enfoque de igualdad',
      'linked': 'Principio relacionado: WEPS 6',
      'score_field': 'inf_obj_10_pct',
      'level_field': 'inf_obj_10_nivel',
      'reading_field': 'inf_obj_10_lectura_plan',
      'reading': 'Fortalecer participación con gad/actores locales, transparencia de pagos y participación de mujeres '
                 'en servicios comunitarios.',
      'indicators': [43]},
 11: {'id': 11,
      'title': 'Difusión de saberes ancestrales y patrimonio cultural con participación de mujeres',
      'linked': 'Principio relacionado: WEPS 6',
      'score_field': 'inf_obj_11_pct',
      'level_field': 'inf_obj_11_nivel',
      'reading_field': 'inf_obj_11_lectura_plan',
      'reading': 'Documentar actividades, participantes y mecanismos para visibilizar saberes de mujeres y '
                 'comunidades.',
      'indicators': [44, 45]},
 12: {'id': 12,
      'title': 'Monitoreo, evaluación y seguimiento del plan',
      'linked': 'Principio relacionado: WEPS 7',
      'score_field': 'inf_obj_12_pct',
      'level_field': 'inf_obj_12_nivel',
      'reading_field': 'inf_obj_12_lectura_plan',
      'reading': 'Establecer informes periódicos, ejecución planificada y tablero de seguimiento.',
      'indicators': [46, 47]},
 13: {'id': 13,
      'title': 'Comunicación de buenas prácticas, informe anual y reconocimiento público',
      'linked': 'Principio relacionado: WEPS 7',
      'score_field': 'inf_obj_13_pct',
      'level_field': 'inf_obj_13_nivel',
      'reading_field': 'inf_obj_13_lectura_plan',
      'reading': 'Preparar informe anual, comunicar resultados y postular avances verificables a reconocimientos o '
                 'buenas prácticas.',
      'indicators': [48]}}

INDICATORS = {1: {'id': 1,
     'title': 'Número de mujeres / Número de hombres por área.',
     'score_field': 'inf_ind_001_score',
     'level_field': 'inf_ind_001_nivel',
     'ref': 'WEPS: 1, 2 | TV: 1, 2 | #: 1',
     'method': 'Metodología: se toma la información agregada de nómina por sexo registrada en la pregunta 17. Cuando exista detalle por '
               'área, debe complementarse en las notas de seguimiento.'},
 2: {'id': 2,
     'title': 'Número de mujeres / Número de hombres por cargo.',
     'score_field': 'inf_ind_002_score',
     'level_field': 'inf_ind_002_nivel',
     'ref': 'WEPS: 1, 2 | TV: 1, 2 | #: 1',
     'method': 'Metodología: usa la medición estructurada de liderazgo y nivel operativo como aproximación a cargos/niveles. Si existen '
               'más cargos, debe registrarse el detalle en las notas.'},
 3: {'id': 3,
     'title': 'Número de mujeres / Número de hombres en procesos de selección.',
     'score_field': 'inf_ind_003_score',
     'level_field': 'inf_ind_003_nivel',
     'ref': 'WEPS: 1, 2 | TV: 1, 2 | #: 1',
     'method': 'Metodología: calcula total y participación de mujeres en procesos de selección. El puntaje valora equilibrio de '
               'participación: 40%-60% = avanzado; 30%-70% = parcial; fuera de ese rango = inicial.'},
 4: {'id': 4,
     'title': 'Número de mujeres / Número de hombres en procesos de promoción/ascensos.',
     'score_field': 'inf_ind_004_score',
     'level_field': 'inf_ind_004_nivel',
     'ref': 'WEPS: 1,2 | TV: 1,2 | #: 2',
     'method': 'Metodología: calcula la participación de mujeres en procesos de promoción o ascenso y mide equilibrio relativo.'},
 5: {'id': 5,
     'title': 'Número de mujeres / Número de hombres en procesos de formación.',
     'score_field': 'inf_ind_005_score',
     'level_field': 'inf_ind_005_nivel',
     'ref': 'WEPS: 1,2 | TV: 1,2 | #: 3',
     'method': 'Metodología: calcula la participación de mujeres en procesos de formación/capacitación y mide equilibrio relativo.'},
 6: {'id': 6,
     'title': 'Remuneración promedio de mujeres por cargo / remuneración promedio de hombres por cargo.',
     'score_field': 'inf_ind_006_score',
     'level_field': 'inf_ind_006_nivel',
     'ref': 'WEPS: 1,2 | TV: 1,2 | #: 4',
     'method': 'Metodología: compara remuneraciones promedio de mujeres y hombres en cargos directivos, medios y operativos. El puntaje se '
               'reduce cuando existe brecha salarial a favor de hombres.'},
 7: {'id': 7,
     'title': 'Número de mujeres / Número de hombres en puesto de liderazgo.',
     'score_field': 'inf_ind_007_score',
     'level_field': 'inf_ind_007_nivel',
     'ref': 'WEPS: 1,2 | TV: 1,2 | #: 5',
     'method': 'Metodología: mide la participación de mujeres en puestos de liderazgo o decisión.'},
 39: {'id': 39,
      'title': 'Número de espacios de participación con Ejecutivo / GAD u otros actores en procesos que empoderen a las mujeres.',
      'score_field': 'inf_ind_039_score',
      'level_field': 'inf_ind_039_nivel',
      'ref': 'WEPS: 6 | TV: 6 | #: 23',
      'method': 'Metodología: verifica participación en espacios de articulación o planificación local vinculados al empoderamiento de '
                'mujeres en turismo.'},
 8: {'id': 8,
     'title': 'Número de mujeres / Número de hombres que conforman el Comité.',
     'score_field': 'inf_ind_008_score',
     'level_field': 'inf_ind_008_nivel',
     'ref': 'WEPS: 1,2 | TV: 1,2 | #: 6',
     'method': 'Metodología: mide composición del Comité de Igualdad y equilibrio de participación.'},
 9: {'id': 9,
     'title': 'Nro. de Actas de reunión del Comité de Igualdad.',
     'score_field': 'inf_ind_009_score',
     'level_field': 'inf_ind_009_nivel',
     'ref': 'WEPS: 1,2 | TV: 1,2 | #: 6',
     'method': 'Metodología: verifica si existen actas o registros formales de reunión del Comité durante el último año.'},
 20: {'id': 20,
      'title': 'Número de mujeres / Número de hombres que conforman el Comité.',
      'score_field': 'inf_ind_020_score',
      'level_field': 'inf_ind_020_nivel',
      'ref': 'WEPS: 3 | TV: 3 | #: 15',
      'method': 'Metodología: usa la composición del Comité de Igualdad como base de gobernanza para prevención y seguimiento.'},
 21: {'id': 21,
      'title': 'Nro. de Actas de reunión del Comité de Igualdad.',
      'score_field': 'inf_ind_021_score',
      'level_field': 'inf_ind_021_nivel',
      'ref': 'WEPS: 3 | TV: 3 | #: 15',
      'method': 'Metodología: verifica si el Comité cuenta con actas/registros de reunión.'},
 22: {'id': 22,
      'title': 'Nro. de procesos de capacitación en los que han participado los integrantes del Comité de SSO.',
      'score_field': 'inf_ind_022_score',
      'level_field': 'inf_ind_022_nivel',
      'ref': 'WEPS: 3 | TV: 3 | #: 15',
      'method': 'Metodología: calcula porcentaje de personas delegadas para SSO/atención de riesgos capacitadas en prevención, '
                'identificación y respuesta.'},
 18: {'id': 18,
      'title': 'Número de activaciones del protocolo ante situaciones de trata y tráfico de personas, desagregado por sexo y edad.',
      'score_field': 'inf_ind_018_score',
      'level_field': 'inf_ind_018_nivel',
      'ref': 'WEPS: 3 | TV: 3 | #: 14',
      'method': 'Metodología: registra activaciones del protocolo de trata/tráfico. El puntaje mide capacidad de registro y desagregación, '
                'no la ocurrencia de casos.'},
 19: {'id': 19,
      'title': 'Número de reportes realizados a autoridades locales por presunción de trata o tráfico de personas, desagregado por sexo.',
      'score_field': 'inf_ind_019_score',
      'level_field': 'inf_ind_019_nivel',
      'ref': 'WEPS: 3 | TV: 3 | #: 14',
      'method': 'Metodología: si existen activaciones, verifica reportes a autoridades. Si no existen activaciones y sí existe registro, '
                'no se penaliza el indicador.'},
 36: {'id': 36,
      'title': 'Número de reportes realizados a autoridades locales por presunción de trata o tráfico de personas, desagregado por sexo.',
      'score_field': 'inf_ind_036_score',
      'level_field': 'inf_ind_036_nivel',
      'ref': 'WEPS: 5 | TV: 5 | #: 21',
      'method': 'Metodología: usa el mismo registro de reportes a autoridades por presunción de trata/tráfico.'},
 10: {'id': 10,
      'title': 'Número de casos de violencia, acoso, discriminación reportados internamente, desagregados por sexo.',
      'score_field': 'inf_ind_010_score',
      'level_field': 'inf_ind_010_nivel',
      'ref': 'WEPS: 2,3 | TV: 2,3 | #: 7',
      'method': 'Metodología: mide si existe registro consolidado, anonimizado y desagregado. El puntaje se basa en la capacidad de '
                'registro, no en la existencia de casos.'},
 11: {'id': 11,
      'title': 'Número de casos resueltos dentro de los plazos establecidos.',
      'score_field': 'inf_ind_011_score',
      'level_field': 'inf_ind_011_nivel',
      'ref': 'WEPS: 2,3 | TV: 2,3 | #: 8',
      'method': 'Metodología: calcula el porcentaje de casos resueltos dentro de plazo sobre el total de casos reportados.'},
 12: {'id': 12,
      'title': 'Número de casos resueltos dentro de los plazos establecidos.',
      'score_field': 'inf_ind_012_score',
      'level_field': 'inf_ind_012_nivel',
      'ref': 'WEPS: 3 | TV: 3 | #: 9',
      'method': 'Metodología: mantiene la trazabilidad del indicador duplicado de la matriz original. Usa la misma base de cálculo de '
                'resolución dentro de plazo.'},
 13: {'id': 13,
      'title': 'Número y grado de sanciones ejecutadas desagregado por sexo.',
      'score_field': 'inf_ind_013_score',
      'level_field': 'inf_ind_013_nivel',
      'ref': 'WEPS: 3 | TV: 3 | #: 10',
      'method': 'Metodología: registra sanciones ejecutadas de manera agregada. Si no existen casos reportados y sí existe registro, no se '
                'penaliza el indicador; si hay casos pero no sanciones/seguimiento, queda como avance inicial.'},
 14: {'id': 14,
      'title': 'Número de programas de prevención de violencia contra las mujeres desarrollados.',
      'score_field': 'inf_ind_014_score',
      'level_field': 'inf_ind_014_nivel',
      'ref': 'WEPS: 3 | TV: 3 | #: 12',
      'method': 'Metodología: verifica existencia de programas de prevención desarrollados.'},
 15: {'id': 15,
      'title': 'Número de mujeres / Número de hombres beneficiados de los programas de prevención de violencia contra las mujeres.',
      'score_field': 'inf_ind_015_score',
      'level_field': 'inf_ind_015_nivel',
      'ref': 'WEPS: 3 | TV: 3 | #: 12',
      'method': 'Metodología: calcula beneficiarios de programas de prevención y cobertura estimada frente al total de personal.'},
 16: {'id': 16,
      'title': 'Número de mujeres / Número de hombres que recibieron atención interna.',
      'score_field': 'inf_ind_016_score',
      'level_field': 'inf_ind_016_nivel',
      'ref': 'WEPS: 3 | TV: 3 | #: 13',
      'method': 'Metodología: registra atención interna de forma agregada. Si no existen casos y sí existe registro, no se penaliza el '
                'indicador.'},
 17: {'id': 17,
      'title': 'Número de mujeres / Número de hombres derivados a servicios externos.',
      'score_field': 'inf_ind_017_score',
      'level_field': 'inf_ind_017_nivel',
      'ref': 'WEPS: 3 | TV: 3 | #: 13',
      'method': 'Metodología: registra derivaciones externas. Si no existen casos y sí existe registro, no se penaliza el indicador.'},
 23: {'id': 23,
      'title': 'Número de capacitaciones realizadas a todo el personal.',
      'score_field': 'inf_ind_023_score',
      'level_field': 'inf_ind_023_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 16',
      'method': 'Metodología: registra capacitaciones realizadas para todo el personal en igualdad, prevención de violencia, acoso, '
                'discriminación o temas relacionados. Si hay más de un tema, detalle en notas.'},
 24: {'id': 24,
      'title': '% de participación del personal.',
      'score_field': 'inf_ind_024_score',
      'level_field': 'inf_ind_024_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 16',
      'method': 'Metodología: calcula cobertura de participación sobre el total de personal.'},
 25: {'id': 25,
      'title': 'Número de mujeres / Número de hombres capacitados.',
      'score_field': 'inf_ind_025_score',
      'level_field': 'inf_ind_025_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 16',
      'method': 'Metodología: registra personas capacitadas desagregadas por sexo/género.'},
 26: {'id': 26,
      'title': 'Número de capacitaciones realizadas a todo el personal.',
      'score_field': 'inf_ind_026_score',
      'level_field': 'inf_ind_026_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 17',
      'method': 'Metodología: registra capacitaciones realizadas para todo el personal en igualdad, prevención de violencia, acoso, '
                'discriminación o temas relacionados. Si hay más de un tema, detalle en notas.'},
 27: {'id': 27,
      'title': '% de participación del personal.',
      'score_field': 'inf_ind_027_score',
      'level_field': 'inf_ind_027_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 17',
      'method': 'Metodología: calcula cobertura de participación sobre el total de personal.'},
 28: {'id': 28,
      'title': 'Número de mujeres / Número de hombres capacitados.',
      'score_field': 'inf_ind_028_score',
      'level_field': 'inf_ind_028_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 17',
      'method': 'Metodología: registra personas capacitadas desagregadas por sexo/género.'},
 29: {'id': 29,
      'title': 'Número de capacitaciones realizadas a todo el personal.',
      'score_field': 'inf_ind_029_score',
      'level_field': 'inf_ind_029_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 18',
      'method': 'Metodología: registra capacitaciones realizadas para todo el personal en igualdad, prevención de violencia, acoso, '
                'discriminación o temas relacionados. Si hay más de un tema, detalle en notas.'},
 30: {'id': 30,
      'title': '% de participación del personal.',
      'score_field': 'inf_ind_030_score',
      'level_field': 'inf_ind_030_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 18',
      'method': 'Metodología: calcula cobertura de participación sobre el total de personal.'},
 31: {'id': 31,
      'title': 'Número de mujeres / Número de hombres capacitados.',
      'score_field': 'inf_ind_031_score',
      'level_field': 'inf_ind_031_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 18',
      'method': 'Metodología: registra personas capacitadas desagregadas por sexo/género.'},
 32: {'id': 32,
      'title': 'Número de capacitaciones realizadas a todo el personal.',
      'score_field': 'inf_ind_032_score',
      'level_field': 'inf_ind_032_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 19',
      'method': 'Metodología: registra capacitaciones realizadas para todo el personal en igualdad, prevención de violencia, acoso, '
                'discriminación o temas relacionados. Si hay más de un tema, detalle en notas.'},
 33: {'id': 33,
      'title': '% de participación del personal.',
      'score_field': 'inf_ind_033_score',
      'level_field': 'inf_ind_033_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 19',
      'method': 'Metodología: calcula cobertura de participación sobre el total de personal.'},
 34: {'id': 34,
      'title': 'Número de mujeres / Número de hombres capacitados.',
      'score_field': 'inf_ind_034_score',
      'level_field': 'inf_ind_034_nivel',
      'ref': 'WEPS: 4 | TV: 4 | #: 19',
      'method': 'Metodología: registra personas capacitadas desagregadas por sexo/género.'},
 35: {'id': 35,
      'title': 'Nro. de monitoreo de contenidos de productos comunicacionales.',
      'score_field': 'inf_ind_035_score',
      'level_field': 'inf_ind_035_nivel',
      'ref': 'WEPS: 5 | TV: 5 | #: 20',
      'method': 'Metodología: verifica si se monitorean contenidos comunicacionales para evitar estereotipos, sexualización, '
                'discriminación o mensajes contrarios a igualdad.'},
 37: {'id': 37,
      'title': 'Número de proveedores identificados que incorporan lineamientos claros respecto a violencia, discriminación, tráfico y '
               'trata.',
      'score_field': 'inf_ind_037_score',
      'level_field': 'inf_ind_037_nivel',
      'ref': 'WEPS: 5 | TV: 5 | #: 22',
      'method': 'Metodología: calcula porcentaje de proveedores/actores de cadena de valor con lineamientos claros.'},
 38: {'id': 38,
      'title': 'Valor de compras realizadas a proveedores priorizados / valor de compras realizadas a todos los proveedores.',
      'score_field': 'inf_ind_038_score',
      'level_field': 'inf_ind_038_nivel',
      'ref': 'WEPS: 5 | TV: 5 | #: 22',
      'method': 'Metodología: calcula la participación del valor de compras priorizadas con enfoque de igualdad sobre el total de '
                'compras.'},
 40: {'id': 40,
      'title': 'Número de organizaciones de mujeres que forman parte de la cadena de valor de la organización.',
      'score_field': 'inf_ind_040_score',
      'level_field': 'inf_ind_040_nivel',
      'ref': 'WEPS: 6 | TV: 6 | #: 23',
      'method': 'Metodología: calcula presencia de organizaciones/comunidades lideradas por mujeres dentro de la cadena de valor.'},
 41: {'id': 41,
      'title': 'Número de mujeres / Número de hombres de las organizaciones que forman parte de la cadena de valor.',
      'score_field': 'inf_ind_041_score',
      'level_field': 'inf_ind_041_nivel',
      'ref': 'WEPS: 6 | TV: 6 | #: 23',
      'method': 'Metodología: calcula composición por sexo/género de personas vinculadas a organizaciones de la cadena de valor.'},
 42: {'id': 42,
      'title': 'Número de mujeres / Número de hombres que ocupan cargos directivos en organizaciones de la cadena de valor.',
      'score_field': 'inf_ind_042_score',
      'level_field': 'inf_ind_042_nivel',
      'ref': 'WEPS: 6 | TV: 6 | #: 23',
      'method': 'Metodología: calcula composición de cargos directivos en organizaciones vinculadas a la cadena de valor.'},
 43: {'id': 43,
      'title': 'Número de mujeres / Número de hombres que recibieron pago por servicios brindados en la comunidad.',
      'score_field': 'inf_ind_043_score',
      'level_field': 'inf_ind_043_nivel',
      'ref': 'WEPS: 6 | TV: 6 | #: 24',
      'method': 'Metodología: calcula participación de mujeres tanto en número de personas pagadas como en valor de pagos comunitarios.'},
 44: {'id': 44,
      'title': 'Número de mujeres / Número de hombres involucrados en la difusión de saberes ancestrales.',
      'score_field': 'inf_ind_044_score',
      'level_field': 'inf_ind_044_nivel',
      'ref': 'WEPS: 6 | TV: 6 | #: 25',
      'method': 'Metodología: registra personas involucradas en difusión de saberes ancestrales/patrimonio cultural y mide presencia de '
                'mujeres.'},
 45: {'id': 45,
      'title': 'Número de actividades de difusión de saberes ancestrales.',
      'score_field': 'inf_ind_045_score',
      'level_field': 'inf_ind_045_nivel',
      'ref': 'WEPS: 6 | TV: 6 | #: 25',
      'method': 'Metodología: verifica número de actividades o documentos de difusión de saberes ancestrales/patrimonio cultural.'},
 46: {'id': 46,
      'title': 'Número de informes presentados que recojan evidencia e indicadores de las acciones realizadas.',
      'score_field': 'inf_ind_046_score',
      'level_field': 'inf_ind_046_nivel',
      'ref': 'WEPS: 7 | TV: 7 | #: 26',
      'method': 'Metodología: verifica existencia de informes con evidencia e indicadores del plan o acciones de igualdad.'},
 47: {'id': 47,
      'title': '% de ejecución del plan, que compara lo ejecutado versus lo planificado.',
      'score_field': 'inf_ind_047_score',
      'level_field': 'inf_ind_047_nivel',
      'ref': 'WEPS: 7 | TV: 7 | #: 27',
      'method': 'Metodología: calcula porcentaje de acciones ejecutadas sobre acciones planificadas del Plan de Igualdad.'},
 48: {'id': 48,
      'title': 'Informe anual presentado, que incluya los indicadores planteados.',
      'score_field': 'inf_ind_048_score',
      'level_field': 'inf_ind_048_nivel',
      'ref': 'WEPS: 7 | TV: 7 | #: 28',
      'method': 'Metodología: verifica si la organización cuenta con informe anual/reporte de sostenibilidad que incluya indicadores de '
                'igualdad.'}}

SCORE_WORDS = {
    "no tiene": 0,
    "no cuenta": 0,
    "no existe": 0,
    "ninguno": 0,
    "inexistente": 0,
    "inicial": 1,
    "idea": 1,
    "en diseno": 2,
    "en diseño": 2,
    "borrador": 2,
    "parcial": 2,
    "en construccion": 3,
    "en construcción": 3,
    "implementado parcialmente": 3,
    "aprobado": 4,
    "formalizado": 4,
    "difundido": 5,
    "implementado": 4,
    "evaluado": 5,
    "rendicion": 5,
    "rendición": 5,
    "seguimiento": 5,
    "rendicion de cuentas": 5,
    "rendición de cuentas": 5,
}


def norm_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()


def norm_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm_text(value))


def clean_col(col: Any) -> str:
    return re.sub(r"\s+", " ", str(col).replace("\n", " ")).strip()


def get_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default


def sanitize_kobo_token(raw_token: str) -> str:
    token = str(raw_token or "").strip().strip('"').strip("'").strip()
    if token.lower().startswith("token "):
        token = token.split(" ", 1)[1].strip()
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()
    match = re.search(r"[A-Fa-f0-9]{32,80}", token)
    if match:
        return match.group(0)
    return token


def _extract_kobo_asset_uid(url: str) -> tuple[str | None, str | None]:
    """Extrae host y asset UID de una URL v2 de KOBO cuando es posible."""
    raw = str(url or "").strip()
    if not raw:
        return None, None
    match = re.search(r"/api/v2/assets/([^/]+)/", raw)
    if not match:
        return None, None
    parsed = urlsplit(raw)
    if not parsed.scheme or not parsed.netloc:
        return None, None
    return f"{parsed.scheme}://{parsed.netloc}", match.group(1)


def _submission_access_code(record: dict[str, Any]) -> tuple[str | None, str | None]:
    """Obtiene la CLAVE de una respuesta JSON de KOBO.

    Prioriza el nombre XML actual ``CLAVE`` y después acepta nombres históricos
    o la etiqueta de la pregunta para respuestas creadas con versiones anteriores.
    """
    if not isinstance(record, dict):
        return None, None

    # 1) CLAVE exacta o como último segmento de una ruta de grupo.
    for key, value in record.items():
        parts = re.split(r"[/.:]", str(key))
        if norm_id(key) == "clave" or (parts and norm_id(parts[-1]) == "clave"):
            if value is not None and str(value).strip() != "":
                return str(value), str(key)

    # 2) Nombre XML histórico confirmado.
    historical = {
        norm_id("Cree_un_C_digo_de_ac_e_proceso_de_llenado"),
        norm_id("Cree_un_C_digo_de_acceso"),
        norm_id("codigo_acceso"),
        norm_id("codigo_de_acceso"),
        norm_id("clave_acceso"),
        norm_id("access_code"),
    }
    for key, value in record.items():
        kid = norm_id(key)
        if kid in historical or any(kid.endswith(h) for h in historical):
            if value is not None and str(value).strip() != "":
                return str(value), str(key)

    # 3) Respaldo semántico por encabezado/label.
    phrases = [
        "cree un codigo de acceso",
        "cree un código de acceso",
        "codigo de acceso para poder ingresar",
        "código de acceso para poder ingresar",
        "ingresar posteriormente",
    ]
    phrase_norm = [norm_text(p) for p in phrases]
    for key, value in record.items():
        ktext = norm_text(key)
        if any(p in ktext for p in phrase_norm):
            if value is not None and str(value).strip() != "":
                return str(value), str(key)

    return None, None


def _live_kobo_submissions(url: str, token: str) -> list[dict[str, Any]]:
    """Lee respuestas actuales directamente desde /api/v2/assets/{uid}/data/.

    Este respaldo evita que un export guardado omita una pregunta recién renombrada
    (por ejemplo CLAVE). Si no se puede derivar el asset UID, devuelve una lista vacía
    sin afectar el resto del dashboard.
    """
    base, asset_uid = _extract_kobo_asset_uid(url)
    if not base or not asset_uid:
        return []

    clean_token = sanitize_kobo_token(token)
    headers = {
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    if clean_token:
        headers["Authorization"] = f"Token {clean_token}"

    next_url = f"{base}/api/v2/assets/{asset_uid}/data/?limit=1000"
    rows: list[dict[str, Any]] = []
    pages = 0

    while next_url and pages < 50:
        pages += 1
        try:
            response = requests.get(next_url, headers=headers, timeout=90)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return rows

        if isinstance(payload, dict):
            results = payload.get("results", [])
            if isinstance(results, list):
                rows.extend([r for r in results if isinstance(r, dict)])
            nxt = payload.get("next")
            next_url = urljoin(next_url, str(nxt)) if nxt else None
        elif isinstance(payload, list):
            rows.extend([r for r in payload if isinstance(r, dict)])
            next_url = None
        else:
            next_url = None

    return rows


def _row_identity_values(row: Any) -> set[str]:
    """Devuelve identificadores comparables de una fila/registro KOBO."""
    values: set[str] = set()
    if isinstance(row, pd.Series):
        items = row.items()
    elif isinstance(row, dict):
        items = row.items()
    else:
        return values

    accepted = {
        "id", "uuid", "instanceid", "metainstanceid", "rootuuid",
        "submissionid", "index",
    }
    for key, value in items:
        kid = norm_id(key)
        if kid in accepted or any(kid.endswith(x) for x in ["instanceid", "rootuuid"]):
            if value is None or (isinstance(value, float) and np.isnan(value)):
                continue
            val = str(value).strip().strip('{}').casefold()
            if val:
                values.add(val)
    return values


def _augment_export_with_live_clave(df: pd.DataFrame, url: str, token: str) -> pd.DataFrame:
    """Completa/actualiza la columna CLAVE usando el endpoint JSON en vivo de KOBO.

    Se usa únicamente para la credencial de acceso. El resto de datos continúa
    proviniendo de la exportación XLSX/CSV para preservar hojas repeat y cálculos.
    """
    if df.empty:
        return df

    live_rows = _live_kobo_submissions(url, token)
    if not live_rows:
        return df

    out = df.copy()

    # Localiza una CLAVE ya existente en el export; si no existe, crea una columna canónica.
    clave_col = None
    for col in out.columns:
        parts = re.split(r"[/.:]", str(col))
        if norm_id(col) == "clave" or (parts and norm_id(parts[-1]) == "clave"):
            clave_col = col
            break
    if clave_col is None:
        clave_col = "CLAVE"
        out[clave_col] = pd.NA

    live_entries: list[dict[str, Any]] = []
    for record in live_rows:
        code, source_key = _submission_access_code(record)
        if code is None:
            continue
        live_entries.append(
            {
                "code": code,
                "source_key": source_key,
                "ids": _row_identity_values(record),
                "record": record,
            }
        )

    if not live_entries:
        return out

    # Caso habitual actual: una sola respuesta. Evita depender del nombre exportado.
    if len(out) == 1 and len(live_entries) == 1:
        out.at[out.index[0], clave_col] = live_entries[0]["code"]
        return out

    # Primero relaciona por _id/_uuid/instanceID/root_uuid.
    for idx, row in out.iterrows():
        current = row.get(clave_col)
        if current is not None and not pd.isna(current) and str(current).strip():
            continue

        row_ids = _row_identity_values(row)
        if not row_ids:
            continue

        candidates = [entry for entry in live_entries if row_ids.intersection(entry["ids"])]
        if len(candidates) == 1:
            out.at[idx, clave_col] = candidates[0]["code"]

    # Respaldo por nombre legal de organización cuando sea inequívoco.
    company_col = None
    for col in out.columns:
        ctext = norm_text(col)
        if "nombre legal de la organizacion" in ctext or "nombre legal de la organización" in ctext:
            company_col = col
            break

    if company_col:
        live_by_company: dict[str, list[str]] = {}
        for entry in live_entries:
            record = entry["record"]
            company_value = None
            for key, value in record.items():
                ktext = norm_text(key)
                if "nombre legal de la organizacion" in ktext or "nombre legal de la organización" in ktext:
                    company_value = value
                    break
            if company_value is not None and str(company_value).strip():
                live_by_company.setdefault(normalize_company(company_value), []).append(entry["code"])

        for idx, row in out.iterrows():
            current = row.get(clave_col)
            if current is not None and not pd.isna(current) and str(current).strip():
                continue
            comp = normalize_company(row.get(company_col))
            codes = list(dict.fromkeys(live_by_company.get(comp, [])))
            if len(codes) == 1:
                out.at[idx, clave_col] = codes[0]

    return out


@st.cache_data(ttl=300, show_spinner=False)
def load_data_from_source(url: str, token: str) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Carga la exportación XLSX/CSV guardada de KOBO.

    Configuración recomendada para la URL usada por Streamlit:
    - XLS
    - Valores y encabezados XML
    - Incluir grupos en encabezados: Sí
    - Incluir campos de todas las versiones: No
    - Guardar la configuración de exportación y usar su ``data_url_xlsx``.

    Se leen todas las hojas para conservar los grupos repetibles.
    """
    if not url:
        return pd.DataFrame(), {}

    clean_token = sanitize_kobo_token(token)
    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
    if clean_token:
        headers["Authorization"] = f"Token {clean_token}"

    response = requests.get(url, headers=headers, timeout=90)

    if response.status_code == 401:
        raise RuntimeError(
            "KOBO rechazó la autenticación (401 Unauthorized). Revise KOBO_TOKEN y los permisos sobre el proyecto."
        )
    if response.status_code == 403:
        raise RuntimeError(
            "KOBO respondió 403 Forbidden. El token no tiene permisos suficientes sobre esta exportación."
        )

    response.raise_for_status()
    content = response.content
    lower_url = url.lower()
    content_type = str(response.headers.get("Content-Type", "")).lower()

    if lower_url.endswith(".csv") or "data.csv" in lower_url or "text/csv" in content_type:
        df = pd.read_csv(io.BytesIO(content), dtype=str)
        df.columns = [clean_col(c) for c in df.columns]
        df = df.dropna(how="all")
        return df, {}

    try:
        workbook = pd.read_excel(io.BytesIO(content), sheet_name=None, dtype=str)
    except Exception:
        try:
            df = pd.read_csv(io.BytesIO(content), dtype=str)
            df.columns = [clean_col(c) for c in df.columns]
            df = df.dropna(how="all")
            return df, {}
        except Exception as exc:
            raise RuntimeError("No se pudo interpretar la exportación de KOBO como XLSX ni CSV.") from exc

    cleaned_sheets: dict[str, pd.DataFrame] = {}
    for sheet_name, sheet_df in workbook.items():
        cleaned = sheet_df.copy()
        cleaned.columns = [clean_col(c) for c in cleaned.columns]
        cleaned = cleaned.dropna(how="all")
        cleaned_sheets[str(sheet_name)] = cleaned

    if not cleaned_sheets:
        return pd.DataFrame(), {}

    main_sheet_name = next(iter(cleaned_sheets))
    main_df = cleaned_sheets[main_sheet_name]
    repeat_sheets = {name: sheet for name, sheet in cleaned_sheets.items() if name != main_sheet_name}
    return main_df, repeat_sheets

def find_column(df: pd.DataFrame, preferred: str, candidates: Iterable[str]) -> str | None:
    if df.empty:
        return None
    columns = list(df.columns)
    if preferred and preferred in columns:
        return preferred
    preferred_norm = norm_text(preferred)
    if preferred_norm:
        for col in columns:
            if norm_text(col) == preferred_norm:
                return col
    candidate_norms = [norm_text(c) for c in candidates]
    for col in columns:
        col_norm = norm_text(col)
        if any(c and c in col_norm for c in candidate_norms):
            return col
    return None


def find_field_column(df: pd.DataFrame, field_name: str) -> str | None:
    """Busca columnas exportadas por KOBO aunque vengan con prefijo de grupo o etiqueta larga."""
    if df.empty or not field_name:
        return None

    wanted = norm_id(field_name)
    columns = list(df.columns)

    # Coincidencia exacta por nombre o por último segmento de rutas tipo group/name.
    for col in columns:
        parts = re.split(r"[/.:]", str(col))
        if norm_id(col) == wanted or (parts and norm_id(parts[-1]) == wanted):
            return col

    # Coincidencia por final de columna. Evita perder campos dentro de grupos anidados.
    for col in columns:
        col_id = norm_id(col)
        if col_id.endswith(wanted):
            return col

    # Coincidencia contenida, solo como respaldo.
    for col in columns:
        col_id = norm_id(col)
        if wanted and wanted in col_id:
            return col

    return None


def get_field_value(row: pd.Series, df: pd.DataFrame, field_name: str) -> Any:
    col = find_field_column(df, field_name)
    if not col:
        return None
    return row.get(col)



def detect_company_column(df: pd.DataFrame) -> str | None:
    """Detecta el nombre legal de la organización en exportaciones XML o con etiquetas.

    Para el flujo actual de Streamlit se recomienda usar "Valores y encabezados XML".
    En ese formato KOBO exporta el campo como ``diagnostico/.../nombre_legal``.
    """
    if df.empty:
        return None

    preferred = get_secret("COMPANY_COLUMN", "")
    if preferred:
        found = find_field_column(df, preferred) or find_column(df, preferred, [])
        if found:
            return found

    # Nombre XML actual del formulario.
    for field_name in ["nombre_legal", "nombre_organizacion", "nombre_organización"]:
        found = find_field_column(df, field_name)
        if found:
            return found

    # Compatibilidad con exportaciones que usen etiquetas.
    return find_column(
        df,
        "",
        [
            "nombre legal de la organizacion",
            "nombre legal de la organización",
            "nombre de empresa",
            "empresa",
            "organizacion",
            "organización",
        ],
    )

def detect_access_code_column(df: pd.DataFrame) -> str | None:
    """Devuelve la columna usada como credencial de acceso.

    Desde esta versión el campo canónico es ``CLAVE``. Se mantiene compatibilidad
    con nombres históricos únicamente para respuestas anteriores del formulario.
    Nunca se usan _id, UUID, instanceID u otros identificadores técnicos de KOBO.
    """
    columns = detect_access_code_columns(df)
    return columns[0] if columns else None


def detect_access_code_columns(df: pd.DataFrame) -> list[str]:
    """Detecta el campo CLAVE y, después, alias históricos del código de acceso.

    KOBO puede exportar el nombre XML directamente (``CLAVE``), una ruta de grupo
    como ``grupo/CLAVE`` o la etiqueta larga de la pregunta. La prioridad absoluta
    es el campo CLAVE configurado actualmente en el formulario.
    """
    if df.empty:
        return []

    ordered: list[str] = []

    technical_ids = {
        "id", "_id", "uuid", "_uuid", "instanceid", "instance_id",
        "meta/instanceid", "meta_instanceid", "index", "_index",
        "submission_id", "submissionid", "formhub/uuid", "formhubuuid",
        "xform_id_string", "xformidstring",
    }
    technical_norm = {norm_id(x) for x in technical_ids}

    def is_technical(col: str) -> bool:
        cid = norm_id(col)
        if cid in technical_norm:
            return True
        return any(cid.endswith(x) for x in ["instanceid", "submissionid", "formhubuuid"])

    def add(col: str | None) -> None:
        if col and col in df.columns and not is_technical(str(col)) and col not in ordered:
            ordered.append(col)

    # 0) Si se configuró explícitamente en Secrets, se respeta antes que nada.
    preferred = get_secret("ACCESS_CODE_COLUMN", "")
    if preferred:
        add(find_column(df, preferred, []))
        add(find_field_column(df, preferred))

    # 1) Campo CANÓNICO actual del formulario: CLAVE.
    # find_field_column también encuentra rutas como grupo/CLAVE.
    for field_name in ["CLAVE", "clave"]:
        add(find_field_column(df, field_name))

    # Refuerzo para encabezados cuyo último segmento sea exactamente CLAVE.
    for col in df.columns:
        if is_technical(str(col)):
            continue
        parts = re.split(r"[/.:]", str(col))
        if norm_id(str(col)) == "clave" or (parts and norm_id(parts[-1]) == "clave"):
            add(str(col))

    # 2) Nombre XML utilizado en versiones anteriores del XLSForm.
    historical_names = [
        "Cree_un_C_digo_de_ac_e_proceso_de_llenado",
        "cree_un_c_digo_de_ac_e_proceso_de_llenado",
        "codigo_acceso",
        "codigo_de_acceso",
        "codigo_ingreso",
        "codigo_consulta",
        "clave_acceso",
        "access_code",
        "Cree_un_codigo_de_acceso",
        "Cree_un_C_digo_de_acceso",
    ]
    for field_name in historical_names:
        add(find_field_column(df, field_name))

    # 3) Exportaciones que usan la etiqueta completa de la pregunta.
    strong_phrases = [
        "cree un codigo de acceso",
        "cree un código de acceso",
        "codigo de acceso para poder ingresar",
        "código de acceso para poder ingresar",
        "ingresar posteriormente",
        "conserve este codigo al finalizar",
        "conserve este código al finalizar",
        "codigo acceso",
        "código acceso",
        "clave de acceso",
    ]
    strong_norm = [norm_text(x) for x in strong_phrases]

    for col in df.columns:
        if is_technical(str(col)):
            continue
        col_norm = norm_text(col)
        col_id = norm_id(col)

        if any(term and term in col_norm for term in strong_norm):
            add(str(col))
            continue

        if (
            ("codigo" in col_id or "cdigo" in col_id or "clave" in col_id)
            and ("acceso" in col_id or "ac_e" in str(col).lower() or "ingresar" in col_id or col_id == "clave")
        ):
            add(str(col))

    return ordered

def normalize_access_code(value: Any, *, casefold: bool = False) -> str:
    """Normaliza la credencial sin confundirla con identificadores de KOBO.

    Corrige espacios invisibles y representaciones numéricas de Excel. Por
    defecto preserva mayúsculas/minúsculas; el modo ``casefold=True`` se usa
    únicamente como respaldo de compatibilidad para respuestas históricas.
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""

    text = str(value)
    text = unicodedata.normalize("NFKC", text)
    text = (
        text.replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
        .replace("\xa0", " ")
        .strip()
        .strip('"')
        .strip("'")
        .strip()
    )
    # Elimina espacios accidentales incluso si se pegaron en medio del código.
    text = re.sub(r"\s+", "", text)

    # Excel/KOBO puede serializar códigos numéricos como 793682208.0 o notación E.
    numeric_like = text.replace(",", ".")
    if re.fullmatch(r"\d+\.0+", numeric_like):
        numeric_like = numeric_like.split(".", 1)[0]
    elif re.fullmatch(r"\d+(?:\.\d+)?[eE][+\-]?\d+", numeric_like):
        try:
            numeric_like = str(int(float(numeric_like)))
        except Exception:
            pass

    return numeric_like.casefold() if casefold else numeric_like


def _code_mask(series: pd.Series, typed_code: str) -> pd.Series:
    """Comparación exacta primero y tolerante a mayúsculas como respaldo."""
    typed_exact = normalize_access_code(typed_code)
    if not typed_exact:
        return pd.Series(False, index=series.index)

    exact = series.apply(normalize_access_code) == typed_exact
    if exact.any():
        return exact

    typed_folded = normalize_access_code(typed_code, casefold=True)
    folded = series.apply(lambda v: normalize_access_code(v, casefold=True))
    return folded == typed_folded


def find_valid_records_by_code(
    records: pd.DataFrame,
    code_columns: list[str],
    typed_code: str,
) -> tuple[pd.DataFrame, str | None]:
    """Busca el código en cualquiera de las columnas válidas de acceso."""
    if not normalize_access_code(typed_code):
        return records.iloc[0:0], None

    for col in code_columns:
        if col not in records.columns:
            continue
        mask = _code_mask(records[col], typed_code)
        if mask.any():
            return records.loc[mask].copy(), col

    return records.iloc[0:0], None


def find_global_records_by_code(
    df: pd.DataFrame,
    code_columns: list[str],
    typed_code: str,
) -> tuple[pd.DataFrame, str | None]:
    """Respaldo: localiza la credencial en toda la exportación.

    Esto resuelve respuestas históricas en las que el nombre de la empresa cambió
    levemente entre versiones, sin usar nunca _id/UUID como contraseña.
    """
    return find_valid_records_by_code(df, code_columns, typed_code)


def _is_forbidden_access_column(col: Any) -> bool:
    """Excluye identificadores técnicos y campos que nunca deben actuar como clave."""
    cid = norm_id(col)
    technical = {
        "id", "uuid", "instanceid", "instance_id", "metainstanceid",
        "submissionid", "submission_id", "formhubuuid", "index",
        "xformidstring", "xform_id_string",
    }
    if cid in {norm_id(x) for x in technical}:
        return True
    if any(cid.endswith(x) for x in ["instanceid", "submissionid", "formhubuuid"]):
        return True
    return False


def _access_column_score(col: Any) -> int:
    """Puntúa qué tan plausible es que una columna sea la credencial de acceso."""
    if _is_forbidden_access_column(col):
        return -10000

    raw = str(col)
    ntext = norm_text(raw)
    nid = norm_id(raw)
    parts = re.split(r"[/.:]", raw)
    last_id = norm_id(parts[-1]) if parts else nid
    score = 0

    # Campo canónico actual: prioridad absoluta.
    if nid == "clave" or last_id == "clave":
        score += 2500

    exact_current = norm_id("Cree_un_C_digo_de_ac_e_proceso_de_llenado")
    if nid == exact_current or nid.endswith(exact_current):
        score += 1000

    phrases = [
        "cree un codigo de acceso",
        "cree un código de acceso",
        "codigo de acceso para poder ingresar",
        "código de acceso para poder ingresar",
        "ingresar posteriormente",
        "conserve este codigo",
        "conserve este código",
    ]
    if any(norm_text(p) in ntext for p in phrases):
        score += 700

    if "codigo" in nid or "cdigo" in nid or "clave" in nid or "accesscode" in nid:
        score += 250
    if "acceso" in nid or "ingresar" in nid or "llenado" in nid or "aceproceso" in nid:
        score += 180

    if any(k in nid for k in [
        "score", "nivel", "porcentaje", "percent", "total", "fecha",
        "latitude", "longitude", "geopoint", "geopunto", "telefono", "cedula",
    ]):
        score -= 300

    return score

def find_access_records_autodetect(
    records: pd.DataFrame,
    typed_code: str,
    preferred_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, str | None, list[str]]:
    """Encuentra el código aunque KOBO haya cambiado el encabezado exportado.

    Primero prueba las columnas detectadas por nombre. Si no encuentra coincidencia,
    revisa dinámicamente todas las columnas no técnicas del DataFrame buscando el
    valor escrito. Así se evita depender de cómo KOBO nombre o prefije el campo en
    cada versión/exportación, sin volver a aceptar _id, UUID o instanceID.
    """
    if records.empty or not normalize_access_code(typed_code):
        return records.iloc[0:0], None, []

    preferred_columns = [
        c for c in (preferred_columns or [])
        if c in records.columns and not _is_forbidden_access_column(c)
    ]

    # 1) Ruta normal: campo de código conocido/detectado.
    direct, direct_col = find_valid_records_by_code(records, preferred_columns, typed_code)
    if not direct.empty:
        return direct, direct_col, [direct_col] if direct_col else []

    # 2) Autodetección por valor.
    matches: list[tuple[int, str, pd.Series]] = []
    for col in records.columns:
        if col in preferred_columns or _is_forbidden_access_column(col):
            continue
        try:
            mask = _code_mask(records[col], typed_code)
        except Exception:
            continue
        if bool(mask.any()):
            matches.append((_access_column_score(col), str(col), mask))

    if not matches:
        return records.iloc[0:0], None, []

    matches.sort(key=lambda item: item[0], reverse=True)
    matched_names = [m[1] for m in matches]
    best_score, best_col, best_mask = matches[0]

    # Si existe una columna semánticamente plausible, se prioriza siempre.
    if best_score > 0:
        return records.loc[best_mask].copy(), best_col, matched_names

    # Si solo una columna no técnica contiene el valor, es razonable asumir que es
    # la credencial aunque KOBO haya exportado un encabezado totalmente inesperado.
    if len(matches) == 1:
        return records.loc[best_mask].copy(), best_col, matched_names

    # Si varias columnas contienen el mismo valor pero conducen exactamente al mismo
    # registro, se acepta el registro sin convertir IDs técnicos en contraseña.
    index_sets = [set(records.index[m[2]]) for m in matches]
    common = set.intersection(*index_sets) if index_sets else set()
    if common:
        return records.loc[sorted(common)].copy(), best_col, matched_names

    return records.iloc[0:0], None, matched_names

def normalize_company(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).replace("\xa0", " ").strip()
    return re.sub(r"\s+", " ", text).casefold()


def parse_date(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Sin fecha"
    text = str(value).strip()
    if not text:
        return "Sin fecha"
    try:
        number = float(text)
        if 20000 <= number <= 60000:
            date = datetime(1899, 12, 30) + timedelta(days=number)
            return date.strftime("%d/%m/%Y")
    except Exception:
        pass
    try:
        date = pd.to_datetime(text, errors="coerce")
        if pd.notna(date):
            return date.strftime("%d/%m/%Y")
    except Exception:
        pass
    return text[:30]


def parse_score(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    raw = str(value).strip()
    if raw == "":
        return None
    lowered = norm_text(raw)

    percent_match = re.search(r"(-?\d+(?:[\.,]\d+)?)\s*%", raw)
    if percent_match:
        try:
            return max(0.0, min(100.0, float(percent_match.group(1).replace(",", "."))))
        except Exception:
            pass

    numeric = re.findall(r"-?\d+(?:[\.,]\d+)?", raw)
    if numeric:
        try:
            n = float(numeric[0].replace(",", "."))
            if 0 <= n <= 100:
                return n
            if 0 <= n <= 5:
                return n * 20.0
        except Exception:
            pass

    for phrase, score_0_5 in SCORE_WORDS.items():
        if phrase in lowered:
            return score_0_5 * 20.0
    return None


def parse_level(value: Any, fallback_score: float | None = None) -> str:
    if value is not None and not pd.isna(value):
        text = str(value).strip()
        if text:
            # Respeta niveles calculados por KOBO, pero simplifica etiqueta crítica.
            if norm_text(text) == "brecha critica":
                return "Crítico"
            return text
    return level_from_score(fallback_score)


def level_from_score(score: float | None) -> str:
    if score is None or np.isnan(score):
        return "Sin cálculo"
    if score < 25:
        return "Crítico"
    if score < 50:
        return "Inicial"
    if score < 75:
        return "En construcción"
    return "Avanzado"


def color_from_score(score: float | None) -> str:
    if score is None or np.isnan(score):
        return "#9ca3af"
    if score < 25:
        return "#dc2626"
    if score < 50:
        return "#ea580c"
    if score < 75:
        return "#7c3aed"
    return "#16a34a"


def score_display(score: float | None) -> str:
    if score is None or np.isnan(score):
        return "Sin cálculo"
    return f"{score:.1f}%"


def donut(score: float | None, title: str, height: int = 210) -> go.Figure:
    value = 0 if score is None or np.isnan(score) else float(max(0, min(100, score)))
    fig = go.Figure(
        data=[
            go.Pie(
                values=[value, 100 - value],
                hole=0.72,
                sort=False,
                direction="clockwise",
                textinfo="none",
                marker=dict(colors=[color_from_score(value), "#eef2f7"], line=dict(width=0)),
            )
        ]
    )
    fig.update_layout(
        title=dict(text=title, x=0.5, y=0.96, font=dict(size=13)),
        showlegend=False,
        height=height,
        margin=dict(l=5, r=5, t=35, b=5),
        annotations=[
            dict(
                text=score_display(score),
                x=0.5,
                y=0.5,
                font=dict(size=22, color="#111827"),
                showarrow=False,
            )
        ],
    )
    return fig


def relevant_cols(df: pd.DataFrame, keywords: Iterable[str]) -> list[str]:
    if df.empty:
        return []
    kws = [norm_text(k) for k in keywords if norm_text(k)]
    if not kws:
        return []
    matches: list[str] = []
    for col in df.columns:
        col_norm = norm_text(col)
        if any(k in col_norm for k in kws):
            matches.append(col)
    return matches


def average_scores_from_cols(row: pd.Series, cols: list[str]) -> float | None:
    values = []
    for col in cols:
        score = parse_score(row.get(col))
        if score is not None:
            values.append(score)
    if not values:
        return None
    return float(np.mean(values))


def direct_score(row: pd.Series, df: pd.DataFrame, field_name: str) -> float | None:
    return parse_score(get_field_value(row, df, field_name))


def direct_level(row: pd.Series, df: pd.DataFrame, field_name: str, fallback_score: float | None = None) -> str:
    return parse_level(get_field_value(row, df, field_name), fallback_score)


def direct_text(row: pd.Series, df: pd.DataFrame, field_name: str, fallback: str = "") -> str:
    value = get_field_value(row, df, field_name)
    if value is None or pd.isna(value) or str(value).strip() == "":
        return fallback
    return str(value).strip()


def indicator_score(row: pd.Series, df: pd.DataFrame, indicator_id: int) -> float | None:
    meta = INDICATORS[indicator_id]
    score = direct_score(row, df, meta["score_field"])
    if score is not None:
        return score

    # Respaldo por número de indicador o etiqueta si el export no trae calculate.
    keys = [f"indicador {indicator_id}", f"inf_ind_{indicator_id:03d}", meta["title"][:70]]
    cols = relevant_cols(df, keys)
    return average_scores_from_cols(row, cols)


def objective_score(row: pd.Series, df: pd.DataFrame, objective_id: int) -> float | None:
    meta = OBJECTIVES[objective_id]
    score = direct_score(row, df, meta["score_field"])
    if score is not None:
        return score

    scores = [indicator_score(row, df, i) for i in meta["indicators"]]
    scores = [s for s in scores if s is not None]
    return float(np.mean(scores)) if scores else None


def principle_score(row: pd.Series, df: pd.DataFrame, principle_id: int, objective_scores: dict[int, float | None]) -> float | None:
    meta = next((p for p in PRINCIPLES if p["id"] == principle_id), None)
    if meta:
        score = direct_score(row, df, meta["score_field"])
        if score is not None:
            return score

    objective_ids = meta["objectives"] if meta else []
    scores = [objective_scores.get(i) for i in objective_ids if objective_scores.get(i) is not None]
    if scores:
        return float(np.mean(scores))
    return None


def overall_score(principle_scores: dict[int, float | None]) -> float | None:
    scores = [s for s in principle_scores.values() if s is not None]
    if not scores:
        return None
    return float(np.mean(scores))


def latest_row(group: pd.DataFrame) -> pd.Series:
    if group.empty:
        return pd.Series(dtype=object)
    date_candidates = [c for c in group.columns if any(k in norm_text(c) for k in ["fecha", "submission", "start", "end", "inicio", "fin"])]
    if date_candidates:
        col = date_candidates[0]
        tmp = group.copy()
        tmp["__date_sort"] = pd.to_datetime(tmp[col], errors="coerce")
        tmp = tmp.sort_values("__date_sort", na_position="first")
        return tmp.iloc[-1].drop(labels=["__date_sort"], errors="ignore")
    return group.iloc[-1]


def render_header() -> None:
    st.title("Dashboard empresarial | Turismo Violeta")
    st.caption(f"Versión: {APP_VERSION}")
    st.write(
        "Consulta pública de resultados agregados y acceso individual por empresa mediante código. "
        "La lectura se organiza por los 7 principios WEPs, 13 objetivos, 48 indicadores y acciones sugeridas para el plan."
    )



def render_company_view(df: pd.DataFrame, company_col: str | None, code_col: str | None) -> None:
    st.subheader("Acceso a resultados de empresa")

    if st.button(
        "Actualizar datos desde KOBO",
        help="Limpia el caché de Streamlit y vuelve a descargar la exportación guardada de KOBO.",
    ):
        st.cache_data.clear()
        st.rerun()

    if not company_col:
        st.error(
            "No se detectó la columna de nombre de empresa. "
            "La exportación recomendada debe incluir el campo XML 'nombre_legal'."
        )
        return

    # Campo de acceso canónico de la versión vigente del formulario.
    clave_col = find_field_column(df, "CLAVE")

    # Compatibilidad histórica solo si la exportación actual no contiene CLAVE.
    historical_columns = [
        c for c in detect_access_code_columns(df)
        if c != clave_col
    ]

    visible_by_norm: dict[str, str] = {}
    for value in df[company_col].dropna().astype(str):
        if value.strip():
            visible_by_norm.setdefault(normalize_company(value), value.strip())
    companies = sorted(visible_by_norm.values(), key=lambda x: x.casefold())

    if not companies:
        st.warning("No hay empresas disponibles en la fuente de datos.")
        return

    col1, col2 = st.columns([1.2, 1])
    with col1:
        selected_company = st.selectbox("Nombre de empresa", companies)
    with col2:
        typed_code = st.text_input("Código de acceso", type="password")

    selected_norm = normalize_company(selected_company)
    company_records = df[df[company_col].apply(normalize_company) == selected_norm].copy()

    if not typed_code:
        st.info("Seleccione la empresa y escriba la CLAVE creada en la encuesta.")
        with st.expander("Ayuda rápida"):
            st.write(f"Columna de empresa detectada: `{company_col}`")
            st.write(f"Columna CLAVE detectada: `{clave_col}`" if clave_col else "CLAVE no detectada.")
            if not clave_col:
                st.warning(
                    "La exportación que alimenta Streamlit no contiene CLAVE. "
                    "Use una exportación guardada de la última versión del formulario y actualice KOBO_DATA_URL."
                )
        return

    valid_records = company_records.iloc[0:0]
    matched_code_col: str | None = None

    # ------------------------------------------------------------
    # 1) Flujo vigente: empresa + CLAVE.
    # No se compara contra _id, UUID, cédulas ni ninguna otra columna.
    # ------------------------------------------------------------
    if clave_col and clave_col in company_records.columns:
        mask = _code_mask(company_records[clave_col], typed_code)
        if mask.any():
            valid_records = company_records.loc[mask].copy()
            matched_code_col = clave_col

    # ------------------------------------------------------------
    # 2) Compatibilidad histórica: solo si CLAVE no existe en el XLSX.
    # ------------------------------------------------------------
    elif historical_columns:
        valid_records, matched_code_col = find_valid_records_by_code(
            company_records,
            historical_columns,
            typed_code,
        )

    if valid_records.empty:
        st.error(
            "La CLAVE ingresada no coincide con la registrada en la exportación vigente de KOBO para esta empresa."
        )
        with st.expander("Ayuda rápida"):
            st.write(f"Empresa seleccionada: **{selected_company}**")
            st.write(f"Columna empresa: `{company_col}`")
            st.write(f"Columna CLAVE: `{clave_col or 'NO DETECTADA'}`")
            if clave_col and clave_col in company_records.columns:
                st.write(
                    "La aplicación está validando exclusivamente el campo CLAVE. "
                    "Presione **Actualizar datos desde KOBO** si acaba de editar el envío."
                )
            else:
                st.warning(
                    "La URL configurada en KOBO_DATA_URL parece apuntar a una exportación anterior "
                    "o a una configuración que no incluye la versión vigente."
                )

            admin_pw = st.text_input(
                "Clave de administrador para revisar qué está exportando KOBO",
                type="password",
                key="admin_code_debug",
            )
            if admin_pw == get_secret("ADMIN_PASSWORD", "TurismoVioleta2026"):
                debug_rows = []
                if clave_col and clave_col in company_records.columns:
                    values = company_records[clave_col].tolist()
                    for raw in values:
                        debug_rows.append({
                            "columna": clave_col,
                            "valor exportado": "(vacío)" if raw is None or pd.isna(raw) else str(raw),
                            "valor normalizado": normalize_access_code(raw),
                        })
                else:
                    for col in historical_columns:
                        if col not in company_records.columns:
                            continue
                        for raw in company_records[col].tolist():
                            debug_rows.append({
                                "columna": col,
                                "valor exportado": "(vacío)" if raw is None or pd.isna(raw) else str(raw),
                                "valor normalizado": normalize_access_code(raw),
                            })
                if debug_rows:
                    st.dataframe(pd.DataFrame(debug_rows), use_container_width=True, hide_index=True)
        return

    st.success("CLAVE validada. Mostrando los resultados de la empresa.")
    row = latest_row(valid_records)
    render_result(row, df, selected_company)

def render_indicator_table(row: pd.Series, df: pd.DataFrame, indicator_ids: list[int]) -> None:
    """Render indicators as responsive cards instead of a dataframe.

    Streamlit dataframes truncate long text and require manual column resizing or
    horizontal scrolling. These cards keep every field readable by wrapping the
    content vertically inside the page width.
    """
    if not indicator_ids:
        st.info("Este objetivo no tiene indicadores vinculados en la matriz cargada.")
        return

    for iid in indicator_ids:
        meta = INDICATORS[iid]
        score = indicator_score(row, df, iid)
        level = direct_level(row, df, meta["level_field"], score)
        score_value = 0 if score is None else int(max(0, min(100, round(float(score)))))

        with st.container(border=True):
            top1, top2, top3, top4 = st.columns([0.16, 0.22, 0.24, 0.38])
            top1.metric("Indicador", iid)
            top2.metric("Avance", score_display(score))
            top3.metric("Nivel", level)
            top4.write("**WEPS / TV / #**")
            top4.write(meta["ref"])

            st.progress(score_value)
            st.write("**Nombre del indicador**")
            st.write(meta["title"])

            st.write("**Metodología de cálculo / lectura**")
            st.caption(meta["method"])


def render_result(row: pd.Series, df: pd.DataFrame, company_name: str) -> None:
    objective_scores = {obj_id: objective_score(row, df, obj_id) for obj_id in OBJECTIVES}
    principle_scores = {p["id"]: principle_score(row, df, p["id"], objective_scores) for p in PRINCIPLES}
    total = overall_score(principle_scores)
    level = level_from_score(total)

    date_col = find_column(df, "", ["fecha de envio", "fecha de envío", "submission", "end", "fin"])
    date_text = parse_date(row.get(date_col)) if date_col else "Sin fecha"

    st.divider()
    st.subheader("Resultado general")
    c0, c1, c2, c3 = st.columns([1.2, 1, 1, 1])
    with c0:
        st.metric("Empresa", company_name)
    with c1:
        st.metric("Avance general", score_display(total))
    with c2:
        st.metric("Nivel", level)
    with c3:
        st.metric("Fecha de envío", date_text)

    left, right = st.columns([0.8, 1.4])
    with left:
        st.plotly_chart(donut(total, "Avance general", height=250), use_container_width=True, config=CHART_CONFIG, key="donut_avance_general")
    with right:
        p_data = pd.DataFrame(
            {
                "Principio": [f"WEPs {pid}" for pid in principle_scores],
                "Avance": [0 if score is None else score for score in principle_scores.values()],
            }
        )
        fig = go.Figure(
            go.Bar(
                x=p_data["Avance"],
                y=p_data["Principio"],
                orientation="h",
                marker_color=[color_from_score(v) for v in p_data["Avance"]],
                text=[f"{v:.1f}%" for v in p_data["Avance"]],
                textposition="auto",
                hoverinfo="skip",
            )
        )
        fig.update_layout(
            height=330,
            margin=dict(l=10, r=10, t=20, b=20),
            xaxis=dict(range=[0, 100], title="Avance (%)", fixedrange=True),
            yaxis=dict(autorange="reversed", fixedrange=True),
            showlegend=False,
            dragmode=False,
        )
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key="bar_principios_empresa")

    st.subheader("Principios, objetivos e indicadores para el plan")
    st.caption("Los indicadores se muestran en el orden lógico del XLSForm: 7 principios WEPs, 13 objetivos y 48 indicadores.")

    for p in PRINCIPLES:
        pid = p["id"]
        p_score = principle_scores.get(pid)
        with st.expander(f"» » E.1.{pid}. Principio WEPs {pid}: {p['title']}", expanded=True):
            col_a, col_b, col_c = st.columns([0.75, 1, 1.3])
            with col_a:
                st.plotly_chart(donut(p_score, "Avance del principio", height=210), use_container_width=True, config=CHART_CONFIG, key=f"donut_principio_{pid}")
            with col_b:
                st.metric("Avance calculado", score_display(p_score))
                st.metric("Nivel", direct_level(row, df, p["level_field"], p_score))
                st.progress(0 if p_score is None else int(max(0, min(100, p_score))))
            with col_c:
                st.write("Documentos de apoyo:")
                st.write(p["documents"])
                st.write("Lectura para plan:")
                st.info(direct_text(row, df, p["reading_field"], p["reading"]))

            for objective_id in p["objectives"]:
                meta = OBJECTIVES[objective_id]
                o_score = objective_scores.get(objective_id)
                with st.container(border=True):
                    oc1, oc2 = st.columns([0.22, 1])
                    with oc1:
                        st.plotly_chart(donut(o_score, "", height=150), use_container_width=True, config=CHART_CONFIG, key=f"donut_principio_{pid}_objetivo_{objective_id}")
                    with oc2:
                        st.markdown(f"### » » E.2.{objective_id}. Objetivo {objective_id}: {meta['title']}")
                        st.caption(meta.get("linked", ""))
                        cc1, cc2 = st.columns(2)
                        cc1.metric("Avance calculado", score_display(o_score))
                        cc2.metric("Nivel", direct_level(row, df, meta["level_field"], o_score))
                        st.write("Lectura para plan:")
                        st.success(direct_text(row, df, meta["reading_field"], meta["reading"]))
                        st.write("Indicadores que sustentan este objetivo:")
                        render_indicator_table(row, df, meta["indicators"])


# ============================================================
# RESUMEN PÚBLICO | TURISMO VIOLETA
# Dashboard agregado con cobertura territorial, resultados WEPs
# y distribución de empresas por nivel.
# ============================================================

PUBLIC_MAP_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "responsive": True,
}

# Coordenadas aproximadas de referencia provincial para el mapa agregado.
# Se utilizan únicamente cuando la fuente KOBO dispone de provincia pero no
# de coordenadas individuales válidas.
ECUADOR_PROVINCES = {
    "azuay": (-2.9001, -79.0059),
    "bolivar": (-1.5926, -79.0009),
    "canar": (-2.5589, -78.9388),
    "carchi": (0.8119, -77.7173),
    "chimborazo": (-1.6731, -78.6483),
    "cotopaxi": (-0.9333, -78.6167),
    "el oro": (-3.2581, -79.9554),
    "esmeraldas": (0.9682, -79.6517),
    "galapagos": (-0.9538, -90.9656),
    "guayas": (-2.1709, -79.9224),
    "imbabura": (0.3517, -78.1223),
    "loja": (-3.9931, -79.2042),
    "los rios": (-1.8022, -79.5344),
    "manabi": (-1.0546, -80.4545),
    "morona santiago": (-2.3087, -78.1114),
    "napo": (-0.9938, -77.8129),
    "orellana": (-0.4664, -76.9868),
    "pastaza": (-1.4924, -78.0026),
    "pichincha": (-0.1807, -78.4678),
    "santa elena": (-2.2267, -80.8587),
    "santo domingo de los tsachilas": (-0.2531, -79.1754),
    "sucumbios": (0.0860, -76.8890),
    "tungurahua": (-1.2491, -78.6168),
    "zamora chinchipe": (-4.0692, -78.9567),
}

PROVINCE_DISPLAY = {
    "azuay": "Azuay",
    "bolivar": "Bolívar",
    "canar": "Cañar",
    "carchi": "Carchi",
    "chimborazo": "Chimborazo",
    "cotopaxi": "Cotopaxi",
    "el oro": "El Oro",
    "esmeraldas": "Esmeraldas",
    "galapagos": "Galápagos",
    "guayas": "Guayas",
    "imbabura": "Imbabura",
    "loja": "Loja",
    "los rios": "Los Ríos",
    "manabi": "Manabí",
    "morona santiago": "Morona Santiago",
    "napo": "Napo",
    "orellana": "Orellana",
    "pastaza": "Pastaza",
    "pichincha": "Pichincha",
    "santa elena": "Santa Elena",
    "santo domingo de los tsachilas": "Santo Domingo de los Tsáchilas",
    "sucumbios": "Sucumbíos",
    "tungurahua": "Tungurahua",
    "zamora chinchipe": "Zamora Chinchipe",
}



# Etiquetas territoriales oficiales reconstruidas desde el XLSForm del proyecto.
# Permiten que el dashboard use encabezados/valores XML estables en KOBO y, al
# mismo tiempo, muestre nombres legibles de provincia, cantón, parroquia y localidad.
GEO_CHOICE_LABELS = {'can_0101': 'CUENCA',
 'can_0102': 'GIRÓN',
 'can_0103': 'GUALACEO',
 'can_0104': 'NABÓN',
 'can_0105': 'PAUTE',
 'can_0106': 'PUCARA',
 'can_0107': 'SAN FERNANDO',
 'can_0108': 'SANTA ISABEL',
 'can_0109': 'SÍGSIG',
 'can_0110': 'OÑA',
 'can_0111': 'CHORDELEG',
 'can_0112': 'EL PAN',
 'can_0113': 'SEVILLA DE ORO',
 'can_0114': 'GUACHAPALA',
 'can_0115': 'CAMILO PONCE ENRÍQUEZ',
 'can_0201': 'GUARANDA',
 'can_0202': 'CHILLANES',
 'can_0203': 'CHIMBO',
 'can_0204': 'ECHEANDÍA',
 'can_0205': 'SAN MIGUEL',
 'can_0206': 'CALUMA',
 'can_0207': 'LAS NAVES',
 'can_0301': 'AZOGUES',
 'can_0302': 'BIBLIÁN',
 'can_0303': 'CAÑAR',
 'can_0304': 'LA TRONCAL',
 'can_0305': 'EL TAMBO',
 'can_0306': 'DÉLEG',
 'can_0307': 'SUSCAL',
 'can_0401': 'TULCÁN',
 'can_0402': 'BOLÍVAR',
 'can_0403': 'ESPEJO',
 'can_0404': 'MIRA',
 'can_0405': 'MONTÚFAR',
 'can_0406': 'SAN PEDRO DE HUACA',
 'can_0501': 'LATACUNGA',
 'can_0502': 'LA MANÁ',
 'can_0503': 'PANGUA',
 'can_0504': 'PUJILI',
 'can_0505': 'SALCEDO',
 'can_0506': 'SAQUISILÍ',
 'can_0507': 'SIGCHOS',
 'can_0601': 'RIOBAMBA',
 'can_0602': 'ALAUSI',
 'can_0603': 'COLTA',
 'can_0604': 'CHAMBO',
 'can_0605': 'CHUNCHI',
 'can_0606': 'GUAMOTE',
 'can_0607': 'GUANO',
 'can_0608': 'PALLATANGA',
 'can_0609': 'PENIPE',
 'can_0610': 'CUMANDÁ',
 'can_0701': 'MACHALA',
 'can_0702': 'ARENILLAS',
 'can_0703': 'ATAHUALPA',
 'can_0704': 'BALSAS',
 'can_0705': 'CHILLA',
 'can_0706': 'EL GUABO',
 'can_0707': 'HUAQUILLAS',
 'can_0708': 'MARCABELÍ',
 'can_0709': 'PASAJE',
 'can_0710': 'PIÑAS',
 'can_0711': 'PORTOVELO',
 'can_0712': 'SANTA ROSA',
 'can_0713': 'ZARUMA',
 'can_0714': 'LAS LAJAS',
 'can_0801': 'ESMERALDAS',
 'can_0802': 'ELOY ALFARO',
 'can_0803': 'MUISNE',
 'can_0804': 'QUININDÉ',
 'can_0805': 'SAN LORENZO',
 'can_0806': 'ATACAMES',
 'can_0807': 'RÍOVERDE',
 'can_0808': 'LA CONCORDIA',
 'can_0901': 'GUAYAQUIL',
 'can_0902': 'ALFREDO BAQUERIZO MORENO',
 'can_0903': 'BALAO',
 'can_0904': 'BALZAR',
 'can_0905': 'COLIMES',
 'can_0906': 'DAULE',
 'can_0907': 'DURÁN',
 'can_0908': 'EL EMPALME',
 'can_0909': 'EL TRIUNFO',
 'can_0910': 'MILAGRO',
 'can_0911': 'NARANJAL',
 'can_0912': 'NARANJITO',
 'can_0913': 'PALESTINA',
 'can_0914': 'PEDRO CARBO',
 'can_0916': 'SAMBORONDÓN',
 'can_0918': 'SANTA LUCÍA',
 'can_0919': 'SALITRE',
 'can_0920': 'SAN JACINTO DE YAGUACHI',
 'can_0921': 'PLAYAS',
 'can_0922': 'SIMÓN BOLÍVAR',
 'can_0923': 'CORONEL MARCELINO MARIDUEÑA',
 'can_0924': 'LOMAS DE SARGENTILLO',
 'can_0925': 'NOBOL',
 'can_0927': 'GENERAL ANTONIO ELIZALDE',
 'can_0928': 'ISIDRO AYORA',
 'can_1001': 'IBARRA',
 'can_1002': 'ANTONIO ANTE',
 'can_1003': 'COTACACHI',
 'can_1004': 'OTAVALO',
 'can_1005': 'PIMAMPIRO',
 'can_1006': 'SAN MIGUEL DE URCUQUÍ',
 'can_1101': 'LOJA',
 'can_1102': 'CALVAS',
 'can_1103': 'CATAMAYO',
 'can_1104': 'CELICA',
 'can_1105': 'CHAGUARPAMBA',
 'can_1106': 'ESPÍNDOLA',
 'can_1107': 'GONZANAMÁ',
 'can_1108': 'MACARÁ',
 'can_1109': 'PALTAS',
 'can_1110': 'PUYANGO',
 'can_1111': 'SARAGURO',
 'can_1112': 'SOZORANGA',
 'can_1113': 'ZAPOTILLO',
 'can_1114': 'PINDAL',
 'can_1115': 'QUILANGA',
 'can_1116': 'OLMEDO',
 'can_1201': 'BABAHOYO',
 'can_1202': 'BABA',
 'can_1203': 'MONTALVO',
 'can_1204': 'PUEBLOVIEJO',
 'can_1205': 'QUEVEDO',
 'can_1206': 'URDANETA',
 'can_1207': 'VENTANAS',
 'can_1208': 'VINCES',
 'can_1209': 'PALENQUE',
 'can_1210': 'BUENA FÉ',
 'can_1211': 'VALENCIA',
 'can_1212': 'MOCACHE',
 'can_1213': 'QUINSALOMA',
 'can_1301': 'PORTOVIEJO',
 'can_1302': 'BOLÍVAR',
 'can_1303': 'CHONE',
 'can_1304': 'EL CARMEN',
 'can_1305': 'FLAVIO ALFARO',
 'can_1306': 'JIPIJAPA',
 'can_1307': 'JUNÍN',
 'can_1308': 'MANTA',
 'can_1309': 'MONTECRISTI',
 'can_1310': 'PAJÁN',
 'can_1311': 'PICHINCHA',
 'can_1312': 'ROCAFUERTE',
 'can_1313': 'SANTA ANA',
 'can_1314': 'SUCRE',
 'can_1315': 'TOSAGUA',
 'can_1316': '24 DE MAYO',
 'can_1317': 'PEDERNALES',
 'can_1318': 'OLMEDO',
 'can_1319': 'PUERTO LÓPEZ',
 'can_1320': 'JAMA',
 'can_1321': 'JARAMIJÓ',
 'can_1322': 'SAN VICENTE',
 'can_1401': 'MORONA',
 'can_1402': 'GUALAQUIZA',
 'can_1403': 'LIMÓN INDANZA',
 'can_1404': 'PALORA',
 'can_1405': 'SANTIAGO',
 'can_1406': 'SUCÚA',
 'can_1407': 'HUAMBOYA',
 'can_1408': 'SAN JUAN BOSCO',
 'can_1409': 'TAISHA',
 'can_1410': 'LOGROÑO',
 'can_1411': 'PABLO SEXTO',
 'can_1412': 'TIWINTZA',
 'can_1413': 'SEVILLA DON BOSCO',
 'can_1501': 'TENA',
 'can_1503': 'ARCHIDONA',
 'can_1504': 'EL CHACO',
 'can_1507': 'QUIJOS',
 'can_1509': 'CARLOS JULIO AROSEMENA TOLA',
 'can_1601': 'PASTAZA',
 'can_1602': 'MERA',
 'can_1603': 'SANTA CLARA',
 'can_1604': 'ARAJUNO',
 'can_1701': 'DISTRITO METROPOLITANO DE QUITO',
 'can_1702': 'CAYAMBE',
 'can_1703': 'MEJIA',
 'can_1704': 'PEDRO MONCAYO',
 'can_1705': 'RUMIÑAHUI',
 'can_1707': 'SAN MIGUEL DE LOS BANCOS',
 'can_1708': 'PEDRO VICENTE MALDONADO',
 'can_1709': 'PUERTO QUITO',
 'can_1801': 'AMBATO',
 'can_1802': 'BAÑOS DE AGUA SANTA',
 'can_1803': 'CEVALLOS',
 'can_1804': 'MOCHA',
 'can_1805': 'PATATE',
 'can_1806': 'QUERO',
 'can_1807': 'SAN PEDRO DE PELILEO',
 'can_1808': 'SANTIAGO DE PÍLLARO',
 'can_1809': 'TISALEO',
 'can_1901': 'ZAMORA',
 'can_1902': 'CHINCHIPE',
 'can_1903': 'NANGARITZA',
 'can_1904': 'YACUAMBI',
 'can_1905': 'YANTZAZA',
 'can_1906': 'EL PANGUI',
 'can_1907': 'CENTINELA DEL CÓNDOR',
 'can_1908': 'PALANDA',
 'can_1909': 'PAQUISHA',
 'can_2001': 'SAN CRISTÓBAL',
 'can_2002': 'ISABELA',
 'can_2003': 'SANTA CRUZ',
 'can_2101': 'LAGO AGRIO',
 'can_2102': 'GONZALO PIZARRO',
 'can_2103': 'PUTUMAYO',
 'can_2104': 'SHUSHUFINDI',
 'can_2105': 'SUCUMBÍOS',
 'can_2106': 'CASCALES',
 'can_2107': 'CUYABENO',
 'can_2201': 'FRANCISCO DE ORELLANA',
 'can_2202': 'AGUARICO',
 'can_2203': 'LA JOYA DE LOS SACHAS',
 'can_2204': 'LORETO',
 'can_2301': 'SANTO DOMINGO',
 'can_2302': 'LA CONCORDIA',
 'can_2401': 'SANTA ELENA',
 'can_2402': 'LA LIBERTAD',
 'can_2403': 'SALINAS',
 'ciu_010101': 'BELLAVISTA',
 'ciu_010102': 'CAÑARIBAMBA',
 'ciu_010103': 'EL BATÁN',
 'ciu_010104': 'EL SAGRARIO',
 'ciu_010105': 'EL VECINO',
 'ciu_010106': 'GIL RAMÍREZ DÁVALOS',
 'ciu_010107': 'HUAYNACÁPAC',
 'ciu_010108': 'MACHÁNGARA',
 'ciu_010109': 'MONAY',
 'ciu_010110': 'SAN BLAS',
 'ciu_010111': 'SAN SEBASTIÁN',
 'ciu_010112': 'SUCRE',
 'ciu_010113': 'TOTORACOCHA',
 'ciu_010114': 'YANUNCAY',
 'ciu_010115': 'HERMANO MIGUEL',
 'ciu_010150': 'CUENCA',
 'ciu_010250': 'GIRÓN',
 'ciu_010350': 'GUALACEO',
 'ciu_010450': 'NABÓN',
 'ciu_010550': 'PAUTE',
 'ciu_010650': 'PUCARÁ',
 'ciu_010750': 'SAN FERNANDO',
 'ciu_010850': 'SANTA ISABEL',
 'ciu_010950': 'SÍGSIG',
 'ciu_011050': 'SAN FELIPE DE OÑA',
 'ciu_011150': 'CHORDELEG',
 'ciu_011250': 'EL PAN',
 'ciu_011350': 'SEVILLA DE ORO',
 'ciu_011450': 'GUACHAPALA',
 'ciu_011550': 'CAMILO PONCE ENRÍQUEZ',
 'ciu_020101': 'ÁNGEL POLIBIO CHÁVES',
 'ciu_020102': 'GABRIEL IGNACIO VEINTIMILLA',
 'ciu_020103': 'GUANUJO',
 'ciu_020150': 'GUARANDA',
 'ciu_020250': 'CHILLANES',
 'ciu_020350': 'SAN JOSÉ DE CHIMBO',
 'ciu_020450': 'ECHEANDÍA',
 'ciu_020550': 'SAN MIGUEL',
 'ciu_020650': 'CALUMA',
 'ciu_020701': 'LAS MERCEDES',
 'ciu_020702': 'LAS NAVES [001]',
 'ciu_020750': 'LAS NAVES [002]',
 'ciu_030101': 'AURELIO BAYAS MARTÍNEZ',
 'ciu_030102': 'AZOGUES [001]',
 'ciu_030103': 'BORRERO',
 'ciu_030104': 'SAN FRANCISCO',
 'ciu_030150': 'AZOGUES [002]',
 'ciu_030250': 'BIBLIÁN',
 'ciu_030350': 'CAÑAR',
 'ciu_030450': 'LA TRONCAL',
 'ciu_030550': 'EL TAMBO',
 'ciu_030650': 'DÉLEG',
 'ciu_030750': 'SUSCAL',
 'ciu_040101': 'GONZÁLEZ SUÁREZ',
 'ciu_040102': 'TULCÁN [001]',
 'ciu_040150': 'TULCÁN [002]',
 'ciu_040250': 'BOLÍVAR',
 'ciu_040301': 'EL ÁNGEL [001]',
 'ciu_040302': '27 DE SEPTIEMBRE',
 'ciu_040350': 'EL ÁNGEL [002]',
 'ciu_040450': 'MIRA',
 'ciu_040501': 'GONZÁLEZ SUÁREZ',
 'ciu_040502': 'SAN JOSÉ',
 'ciu_040550': 'SAN GABRIEL',
 'ciu_040650': 'HUACA',
 'ciu_050101': 'ELOY ALFARO (SAN FELIPE)',
 'ciu_050102': 'IGNACIO FLORES (PARQUE FLORES)',
 'ciu_050103': 'JUAN MONTALVO (SAN SEBASTIÁN)',
 'ciu_050104': 'LA MATRIZ',
 'ciu_050105': 'SAN BUENAVENTURA',
 'ciu_050150': 'LATACUNGA',
 'ciu_050201': 'EL CARMEN',
 'ciu_050202': 'LA MANÁ [001]',
 'ciu_050203': 'EL TRIUNFO',
 'ciu_050250': 'LA MANÁ [002]',
 'ciu_050350': 'EL CORAZÓN',
 'ciu_050450': 'PUJILÍ',
 'ciu_050550': 'SAN MIGUEL',
 'ciu_050650': 'SAQUISILÍ',
 'ciu_050750': 'SIGCHOS',
 'ciu_060101': 'LIZARZABURU',
 'ciu_060102': 'MALDONADO',
 'ciu_060103': 'VELASCO',
 'ciu_060104': 'VELOZ',
 'ciu_060105': 'YARUQUÍES',
 'ciu_060150': 'RIOBAMBA',
 'ciu_060250': 'ALAUSÍ',
 'ciu_060301': 'CAJABAMBA',
 'ciu_060302': 'SICALPA',
 'ciu_060350': 'VILLA LA UNIÓN',
 'ciu_060450': 'CHAMBO',
 'ciu_060550': 'CHUNCHI',
 'ciu_060650': 'GUAMOTE',
 'ciu_060701': 'EL ROSARIO',
 'ciu_060702': 'LA MATRIZ',
 'ciu_060750': 'GUANO',
 'ciu_060850': 'PALLATANGA',
 'ciu_060950': 'PENIPE',
 'ciu_061050': 'CUMANDÁ',
 'ciu_070101': 'LA PROVIDENCIA',
 'ciu_070102': 'MACHALA [001]',
 'ciu_070103': 'PUERTO BOLÍVAR',
 'ciu_070104': 'NUEVE DE MAYO',
 'ciu_070105': 'EL CAMBIO',
 'ciu_070150': 'MACHALA [002]',
 'ciu_070250': 'ARENILLAS',
 'ciu_070350': 'PACCHA',
 'ciu_070450': 'BALSAS',
 'ciu_070550': 'CHILLA',
 'ciu_070650': 'EL GUABO',
 'ciu_070701': 'ECUADOR',
 'ciu_070702': 'EL PARAÍSO',
 'ciu_070703': 'HUALTACO',
 'ciu_070704': 'MILTON REYES',
 'ciu_070705': 'UNIÓN LOJANA',
 'ciu_070750': 'HUAQUILLAS',
 'ciu_070850': 'MARCABELÍ',
 'ciu_070901': 'BOLÍVAR',
 'ciu_070902': 'LOMA DE FRANCO',
 'ciu_070903': 'OCHOA LEÓN (MATRIZ)',
 'ciu_070904': 'TRES CERRITOS',
 'ciu_070950': 'PASAJE',
 'ciu_071001': 'LA MATRIZ',
 'ciu_071002': 'LA SUSAYA',
 'ciu_071003': 'PIÑAS GRANDE',
 'ciu_071050': 'PIÑAS',
 'ciu_071150': 'PORTOVELO',
 'ciu_071201': 'SANTA ROSA [001]',
 'ciu_071202': 'PUERTO JELÍ',
 'ciu_071203': 'BALNEARIO JAMBELÍ (SATÉLITE)',
 'ciu_071204': 'JUMÓN (SATÉLITE)',
 'ciu_071205': 'NUEVO SANTA ROSA',
 'ciu_071250': 'SANTA ROSA [002]',
 'ciu_071350': 'ZARUMA',
 'ciu_071401': 'LA VICTORIA [001]',
 'ciu_071402': 'PLATANILLOS',
 'ciu_071403': 'VALLE HERMOSO',
 'ciu_071450': 'LA VICTORIA [002]',
 'ciu_080101': 'BARTOLOMÉ RUIZ (CÉSAR FRANCO CARRIÓN)',
 'ciu_080102': '5 DE AGOSTO',
 'ciu_080103': 'ESMERALDAS [001]',
 'ciu_080104': 'LUIS TELLO (LAS PALMAS)',
 'ciu_080105': 'SIMÓN PLATA TORRES',
 'ciu_080150': 'ESMERALDAS [002]',
 'ciu_080250': 'VALDEZ (LIMONES)',
 'ciu_080350': 'MUISNE',
 'ciu_080450': 'ROSA ZÁRATE',
 'ciu_080550': 'SAN LORENZO',
 'ciu_080650': 'ATACAMES',
 'ciu_080750': 'RÍOVERDE',
 'ciu_080850': 'LA CONCORDIA',
 'ciu_090101': 'AYACUCHO',
 'ciu_090102': 'BOLÍVAR (SAGRARIO)',
 'ciu_090103': 'CARBO (CONCEPCIÓN)',
 'ciu_090104': 'FEBRES CORDERO',
 'ciu_090105': 'GARCÍA MORENO',
 'ciu_090106': 'LETAMENDI',
 'ciu_090107': 'NUEVE DE OCTUBRE',
 'ciu_090108': 'OLMEDO (SAN ALEJO)',
 'ciu_090109': 'ROCA',
 'ciu_090110': 'ROCAFUERTE',
 'ciu_090111': 'SUCRE',
 'ciu_090112': 'TARQUI',
 'ciu_090113': 'URDANETA',
 'ciu_090114': 'XIMENA',
 'ciu_090115': 'PASCUALES',
 'ciu_090150': 'GUAYAQUIL',
 'ciu_090250': 'ALFREDO BAQUERIZO MORENO (JUJÁN)',
 'ciu_090350': 'BALAO',
 'ciu_090450': 'BALZAR',
 'ciu_090550': 'COLIMES',
 'ciu_090601': 'DAULE [001]',
 'ciu_090602': 'LA AURORA (SATÉLITE)',
 'ciu_090603': 'BANIFE',
 'ciu_090604': 'EMILIANO CAICEDO MARCOS',
 'ciu_090605': 'MAGRO',
 'ciu_090606': 'PADRE JUAN BAUTISTA AGUIRRE',
 'ciu_090607': 'SANTA CLARA',
 'ciu_090608': 'VICENTE PIEDRAHITA',
 'ciu_090650': 'DAULE [002]',
 'ciu_090701': 'ELOY ALFARO (DURÁN)',
 'ciu_090702': 'EL RECREO',
 'ciu_090703': 'DIVINO NIÑO',
 'ciu_090750': 'ELOY ALFARO',
 'ciu_090850': 'VELASCO IBARRA',
 'ciu_090950': 'EL TRIUNFO',
 'ciu_091001': 'CAMILO ANDRADE',
 'ciu_091002': 'ELOY ALFARO',
 'ciu_091003': 'CHIRIJOS',
 'ciu_091004': 'CORONEL ENRIQUE VALDEZ',
 'ciu_091005': 'ROSA MARÍA',
 'ciu_091006': 'JOSÉ MARÍA VELASCO IBARRA',
 'ciu_091007': 'VICENTE ROCAFUERTE',
 'ciu_091008': 'ERNESTO SEMINARIO',
 'ciu_091009': 'LAS PIÑAS',
 'ciu_091050': 'MILAGRO',
 'ciu_091150': 'NARANJAL',
 'ciu_091250': 'NARANJITO',
 'ciu_091350': 'PALESTINA',
 'ciu_091450': 'PEDRO CARBO',
 'ciu_091601': 'SAMBORONDÓN [001]',
 'ciu_091602': 'LA PUNTILLA (SATÉLITE)',
 'ciu_091650': 'SAMBORONDÓN [002]',
 'ciu_091850': 'SANTA LUCÍA',
 'ciu_091901': 'BOCANA',
 'ciu_091902': 'CANDILEJOS',
 'ciu_091903': 'CENTRAL',
 'ciu_091904': 'PARAÍSO',
 'ciu_091905': 'SAN MATEO',
 'ciu_091950': 'EL SALITRE',
 'ciu_092050': 'SAN JACINTO DE YAGUACHI',
 'ciu_092150': 'GENERAL VILLAMIL',
 'ciu_092250': 'SIMÓN BOLÍVAR',
 'ciu_092350': 'CORONEL MARCELINO MARIDUEÑA',
 'ciu_092450': 'LOMAS DE SARGENTILLO',
 'ciu_092550': 'NARCISA DE JESÚS',
 'ciu_092750': 'GENERAL ANTONIO ELIZALDE',
 'ciu_092850': 'ISIDRO AYORA',
 'ciu_100101': 'CARANQUI',
 'ciu_100102': 'GUAYAQUIL DE ALPACHACA',
 'ciu_100103': 'SAGRARIO',
 'ciu_100104': 'SAN FRANCISCO',
 'ciu_100105': 'LA DOLOROSA DEL PRIORATO',
 'ciu_100150': 'SAN MIGUEL DE IBARRA',
 'ciu_100201': 'ANDRADE MARÍN (LOURDES)',
 'ciu_100202': 'ATUNTAQUI [001]',
 'ciu_100250': 'ATUNTAQUI [002]',
 'ciu_100301': 'SAGRARIO',
 'ciu_100302': 'SAN FRANCISCO',
 'ciu_100350': 'COTACACHI',
 'ciu_100401': 'JORDÁN',
 'ciu_100402': 'SAN LUIS',
 'ciu_100450': 'OTAVALO',
 'ciu_100550': 'PIMAMPIRO',
 'ciu_100650': 'URCUQUÍ CABECERA CANTONAL',
 'ciu_110101': 'EL SAGRARIO',
 'ciu_110102': 'SAN SEBASTIÁN',
 'ciu_110103': 'SUCRE',
 'ciu_110104': 'VALLE',
 'ciu_110105': 'CARIGÁN',
 'ciu_110106': 'PUNZARA',
 'ciu_110150': 'LOJA',
 'ciu_110201': 'CARIAMANGA [001]',
 'ciu_110202': 'CHILE',
 'ciu_110203': 'SAN VICENTE',
 'ciu_110250': 'CARIAMANGA [002]',
 'ciu_110301': 'CATAMAYO [001]',
 'ciu_110302': 'SAN JOSÉ',
 'ciu_110350': 'CATAMAYO [002]',
 'ciu_110450': 'CELICA',
 'ciu_110550': 'CHAGUARPAMBA',
 'ciu_110650': 'AMALUZA',
 'ciu_110750': 'GONZANAMÁ',
 'ciu_110801': 'GENERAL ELOY ALFARO (SAN SEBASTIÁN)',
 'ciu_110802': 'MACARÁ (MANUEL ENRIQUE RENGEL SUQUILANDA)',
 'ciu_110850': 'MACARÁ',
 'ciu_110901': 'CATACOCHA [001]',
 'ciu_110902': 'LOURDES',
 'ciu_110950': 'CATACOCHA [002]',
 'ciu_111050': 'ALAMOR',
 'ciu_111150': 'SARAGURO',
 'ciu_111250': 'SOZORANGA',
 'ciu_111350': 'ZAPOTILLO',
 'ciu_111450': 'PINDAL',
 'ciu_111550': 'QUILANGA',
 'ciu_111650': 'OLMEDO',
 'ciu_120101': 'CLEMENTE BAQUERIZO',
 'ciu_120102': 'DOCTOR CAMILO PONCE',
 'ciu_120103': 'BARREIRO',
 'ciu_120104': 'EL SALTO',
 'ciu_120150': 'BABAHOYO',
 'ciu_120250': 'BABA',
 'ciu_120350': 'MONTALVO',
 'ciu_120450': 'PUEBLOVIEJO',
 'ciu_120501': 'QUEVEDO [001]',
 'ciu_120502': 'SAN CAMILO',
 'ciu_120503': 'SAN JOSÉ',
 'ciu_120504': 'GUAYACÁN',
 'ciu_120505': 'NICOLÁS INFANTE DÍAZ',
 'ciu_120506': 'SAN CRISTÓBAL',
 'ciu_120507': 'SIETE DE OCTUBRE',
 'ciu_120508': '24 DE MAYO',
 'ciu_120509': 'VENUS DEL RÍO QUEVEDO',
 'ciu_120510': 'VIVA ALFARO',
 'ciu_120550': 'QUEVEDO [002]',
 'ciu_120650': 'CATARAMA',
 'ciu_120701': '10 DE NOVIEMBRE',
 'ciu_120702': 'VENTANAS [001]',
 'ciu_120750': 'VENTANAS [002]',
 'ciu_120801': 'BALZAR DE VINCES',
 'ciu_120802': 'VINCES CENTRAL',
 'ciu_120803': 'SAN LORENZO DE VINCES',
 'ciu_120850': 'VINCES',
 'ciu_120950': 'PALENQUE',
 'ciu_121001': 'SAN JACINTO DE BUENA FÉ [001]',
 'ciu_121002': '7 DE AGOSTO',
 'ciu_121003': '11 DE OCTUBRE',
 'ciu_121050': 'SAN JACINTO DE BUENA FÉ [002]',
 'ciu_121101': 'VALENCIA [001]',
 'ciu_121102': 'LA UNIÓN',
 'ciu_121103': 'LA NUEVA UNIÓN',
 'ciu_121150': 'VALENCIA [002]',
 'ciu_121250': 'MOCACHE',
 'ciu_121350': 'QUINSALOMA',
 'ciu_130101': 'PORTOVIEJO [001]',
 'ciu_130102': '12 DE MARZO',
 'ciu_130103': 'COLÓN',
 'ciu_130104': 'PICOAZÁ',
 'ciu_130105': 'SAN PABLO',
 'ciu_130106': 'ANDRÉS DE VERA',
 'ciu_130107': 'FRANCISCO PACHECO',
 'ciu_130108': '18 DE OCTUBRE',
 'ciu_130109': 'SIMÓN BOLÍVAR',
 'ciu_130150': 'PORTOVIEJO [002]',
 'ciu_130250': 'CALCETA',
 'ciu_130301': 'CHONE [001]',
 'ciu_130302': 'SANTA RITA',
 'ciu_130350': 'CHONE [002]',
 'ciu_130401': 'EL CARMEN [001]',
 'ciu_130402': '4 DE DICIEMBRE',
 'ciu_130450': 'EL CARMEN [002]',
 'ciu_130550': 'FLAVIO ALFARO',
 'ciu_130601': 'DOCTOR MIGUEL MORÁN LUCIO',
 'ciu_130602': 'MANUEL INOCENCIO PARRALES Y GUALE',
 'ciu_130603': 'SAN LORENZO DE JIPIJAPA',
 'ciu_130650': 'JIPIJAPA',
 'ciu_130750': 'JUNÍN',
 'ciu_130801': 'LOS ESTEROS',
 'ciu_130802': 'MANTA [001]',
 'ciu_130803': 'SAN MATEO',
 'ciu_130804': 'TARQUI',
 'ciu_130805': 'ELOY ALFARO',
 'ciu_130850': 'MANTA [002]',
 'ciu_130901': 'ANÍBAL SAN ANDRÉS',
 'ciu_130902': 'MONTECRISTI [001]',
 'ciu_130903': 'EL COLORADO',
 'ciu_130904': 'GENERAL ELOY ALFARO',
 'ciu_130905': 'LEONIDAS PROAÑO',
 'ciu_130906': 'ISABEL MUENTES',
 'ciu_130950': 'MONTECRISTI [002]',
 'ciu_131050': 'PAJÁN',
 'ciu_131150': 'PICHINCHA',
 'ciu_131250': 'ROCAFUERTE',
 'ciu_131301': 'SANTA ANA',
 'ciu_131302': 'LODANA',
 'ciu_131350': 'SANTA ANA DE VUELTA LARGA',
 'ciu_131401': 'BAHÍA DE CARÁQUEZ [001]',
 'ciu_131402': 'LEONIDAS PLAZA GUTIÉRREZ',
 'ciu_131450': 'BAHÍA DE CARÁQUEZ [002]',
 'ciu_131550': 'TOSAGUA',
 'ciu_131650': 'SUCRE',
 'ciu_131750': 'PEDERNALES',
 'ciu_131850': 'OLMEDO',
 'ciu_131950': 'PUERTO LÓPEZ',
 'ciu_132050': 'JAMA',
 'ciu_132150': 'JARAMIJÓ',
 'ciu_132250': 'SAN VICENTE',
 'ciu_140150': 'MACAS',
 'ciu_140201': 'GUALAQUIZA [001]',
 'ciu_140202': 'MERCEDES MOLINA',
 'ciu_140250': 'GUALAQUIZA [002]',
 'ciu_140350': 'GENERAL LEONIDAS PLAZA GUTIÉRREZ',
 'ciu_140450': 'PALORA (METZERA)',
 'ciu_140550': 'SANTIAGO DE MÉNDEZ',
 'ciu_140650': 'SUCÚA',
 'ciu_140750': 'HUAMBOYA',
 'ciu_140850': 'SAN JUAN BOSCO',
 'ciu_140950': 'TAISHA',
 'ciu_141050': 'LOGROÑO',
 'ciu_141150': 'PABLO SEXTO',
 'ciu_141250': 'SANTIAGO',
 'ciu_141350': 'SEVILLA DON BOSCO',
 'ciu_150150': 'TENA',
 'ciu_150350': 'ARCHIDONA',
 'ciu_150450': 'EL CHACO',
 'ciu_150750': 'BAEZA',
 'ciu_150950': 'CARLOS JULIO AROSEMENA TOLA',
 'ciu_160150': 'PUYO',
 'ciu_160250': 'MERA',
 'ciu_160350': 'SANTA CLARA',
 'ciu_160450': 'ARAJUNO',
 'ciu_170101': 'BELISARIO QUEVEDO',
 'ciu_170102': 'CARCELÉN',
 'ciu_170103': 'CENTRO HISTÓRICO',
 'ciu_170104': 'COCHAPAMBA',
 'ciu_170105': 'COMITÉ DEL PUEBLO',
 'ciu_170106': 'COTOCOLLAO',
 'ciu_170107': 'CHILIBULO',
 'ciu_170108': 'CHILLOGALLO',
 'ciu_170109': 'CHIMBACALLE',
 'ciu_170110': 'EL CONDADO',
 'ciu_170111': 'GUAMANÍ',
 'ciu_170112': 'IÑAQUITO',
 'ciu_170113': 'ITCHIMBÍA',
 'ciu_170114': 'JIPIJAPA',
 'ciu_170115': 'KENNEDY',
 'ciu_170116': 'LA ARGELIA',
 'ciu_170117': 'LA CONCEPCIÓN',
 'ciu_170118': 'LA ECUATORIANA',
 'ciu_170119': 'LA FERROVIARIA',
 'ciu_170120': 'LA LIBERTAD',
 'ciu_170121': 'LA MAGDALENA',
 'ciu_170122': 'LA MENA',
 'ciu_170123': 'MARISCAL SUCRE',
 'ciu_170124': 'PONCEANO',
 'ciu_170125': 'PUENGASÍ',
 'ciu_170126': 'QUITUMBE',
 'ciu_170127': 'RUMIPAMBA',
 'ciu_170128': 'SAN BARTOLO',
 'ciu_170129': 'SAN ISIDRO DEL INCA',
 'ciu_170130': 'SAN JUAN',
 'ciu_170131': 'SOLANDA',
 'ciu_170132': 'TURUBAMBA',
 'ciu_170150': 'QUITO',
 'ciu_170201': 'AYORA',
 'ciu_170202': 'CAYAMBE [001]',
 'ciu_170203': 'JUAN MONTALVO',
 'ciu_170250': 'CAYAMBE [002]',
 'ciu_170350': 'MACHACHI',
 'ciu_170450': 'TABACUNDO',
 'ciu_170501': 'SANGOLQUÍ [001]',
 'ciu_170502': 'SAN PEDRO DE TABOADA',
 'ciu_170503': 'SAN RAFAEL',
 'ciu_170504': 'FAJARDO',
 'ciu_170550': 'SANGOLQUÍ [002]',
 'ciu_170750': 'SAN MIGUEL DE LOS BANCOS',
 'ciu_170850': 'PEDRO VICENTE MALDONADO',
 'ciu_170950': 'PUERTO QUITO',
 'ciu_180101': 'ATOCHA – FICOA',
 'ciu_180102': 'CELIANO MONGE',
 'ciu_180103': 'HUACHI CHICO',
 'ciu_180104': 'HUACHI LORETO',
 'ciu_180105': 'LA MERCED',
 'ciu_180106': 'LA PENÍNSULA',
 'ciu_180107': 'MATRIZ',
 'ciu_180108': 'PISHILATA',
 'ciu_180109': 'SAN FRANCISCO',
 'ciu_180150': 'AMBATO',
 'ciu_180250': 'BAÑOS',
 'ciu_180350': 'CEVALLOS',
 'ciu_180450': 'MOCHA',
 'ciu_180550': 'PATATE',
 'ciu_180650': 'QUERO',
 'ciu_180701': 'PELILEO [001]',
 'ciu_180702': 'PELILEO GRANDE',
 'ciu_180750': 'PELILEO [002]',
 'ciu_180801': 'CIUDAD NUEVA',
 'ciu_180802': 'PÍLLARO [001]',
 'ciu_180850': 'PÍLLARO [002]',
 'ciu_180950': 'TISALEO',
 'ciu_190101': 'EL LIMÓN',
 'ciu_190102': 'ZAMORA [001]',
 'ciu_190150': 'ZAMORA [002]',
 'ciu_190250': 'ZUMBA',
 'ciu_190350': 'GUAYZIMI',
 'ciu_190450': '28 DE MAYO',
 'ciu_190550': 'YANTZAZA',
 'ciu_190650': 'EL PANGUI',
 'ciu_190750': 'ZUMBI',
 'ciu_190850': 'PALANDA',
 'ciu_190950': 'PAQUISHA',
 'ciu_200150': 'PUERTO BAQUERIZO MORENO',
 'ciu_200250': 'PUERTO VILLAMIL',
 'ciu_200350': 'PUERTO AYORA',
 'ciu_210150': 'NUEVA LOJA',
 'ciu_210250': 'LUMBAQUÍ',
 'ciu_210350': 'PUERTO EL CARMEN DEL PUTUMAYO',
 'ciu_210450': 'SHUSHUFINDI',
 'ciu_210550': 'LA BONITA',
 'ciu_210650': 'EL DORADO DE CASCALES',
 'ciu_210750': 'TARAPOA',
 'ciu_220150': 'EL COCA (PUERTO FRANCISCO DE ORELLANA)',
 'ciu_220201': 'NUEVO ROCAFUERTE [001]',
 'ciu_220202': 'TIPUTINI',
 'ciu_220250': 'NUEVO ROCAFUERTE [002]',
 'ciu_220350': 'LA JOYA DE LOS SACHAS',
 'ciu_220450': 'LORETO',
 'ciu_230101': 'ABRAHAM CALAZACÓN',
 'ciu_230102': 'BOMBOLÍ',
 'ciu_230103': 'CHIGUILPE',
 'ciu_230104': 'RÍO TOACHI',
 'ciu_230105': 'RÍO VERDE',
 'ciu_230106': 'SANTO DOMINGO DE LOS COLORADOS [001]',
 'ciu_230107': 'ZARACAY',
 'ciu_230150': 'SANTO DOMINGO DE LOS COLORADOS [002]',
 'ciu_230250': 'LA CONCORDIA',
 'ciu_240101': 'BALLENITA',
 'ciu_240102': 'SANTA ELENA [001]',
 'ciu_240150': 'SANTA ELENA [002]',
 'ciu_240250': 'LA LIBERTAD',
 'ciu_240301': 'CARLOS ESPINOZA LARREA',
 'ciu_240302': 'GENERAL ALBERTO ENRÍQUEZ GALLO',
 'ciu_240303': 'VICENTE ROCAFUERTE',
 'ciu_240304': 'SANTA ROSA',
 'ciu_240350': 'SALINAS',
 'par_010101': 'BELLAVISTA',
 'par_010102': 'CAÑARIBAMBA',
 'par_010103': 'EL BATÁN',
 'par_010104': 'EL SAGRARIO',
 'par_010105': 'EL VECINO',
 'par_010106': 'GIL RAMÍREZ DÁVALOS',
 'par_010107': 'HUAYNACÁPAC',
 'par_010108': 'MACHÁNGARA',
 'par_010109': 'MONAY',
 'par_010110': 'SAN BLAS',
 'par_010111': 'SAN SEBASTIÁN',
 'par_010112': 'SUCRE',
 'par_010113': 'TOTORACOCHA',
 'par_010114': 'YANUNCAY',
 'par_010115': 'HERMANO MIGUEL',
 'par_010150': 'CUENCA (cabecera cantonal y capital provincial)',
 'par_010151': 'BAÑOS',
 'par_010152': 'CUMBE',
 'par_010153': 'CHAUCHA',
 'par_010154': 'CHECA',
 'par_010155': 'CHIQUINTAD',
 'par_010156': 'LLACAO',
 'par_010157': 'MOLLETURO',
 'par_010158': 'NULTI',
 'par_010159': 'OCTAVIO CORDERO PALACIOS',
 'par_010160': 'PACCHA',
 'par_010161': 'QUINGEO',
 'par_010162': 'RICAURTE',
 'par_010163': 'SAN JOAQUÍN',
 'par_010164': 'SANTA ANA',
 'par_010165': 'SAYAUSÍ',
 'par_010166': 'SIDCAY',
 'par_010167': 'SININCAY',
 'par_010168': 'TARQUI',
 'par_010169': 'TURI',
 'par_010170': 'VALLE',
 'par_010171': 'VICTORIA DEL PORTETE (CAB. EN IRQUIS)',
 'par_010250': 'GIRÓN (cabecera cantonal)',
 'par_010251': 'LA ASUNCIÓN',
 'par_010252': 'SAN GERARDO (CAB. EN SAN GERARDO DE HUAHUALPATA)',
 'par_010350': 'GUALACEO (cabecera cantonal)',
 'par_010351': 'CHORDELEG',
 'par_010352': 'DANIEL CÓRDOVA TORAL',
 'par_010353': 'JADÁN',
 'par_010354': 'MARIANO MORENO',
 'par_010355': 'PRINCIPAL',
 'par_010356': 'REMIGIO CRESPO TORAL',
 'par_010357': 'SAN JUAN',
 'par_010358': 'ZHIDMAD',
 'par_010359': 'LUIS CORDERO VEGA (CAB. EN LAGUAN)',
 'par_010360': 'SIMÓN BOLÍVAR (CAB. EN GAÑAZOL)',
 'par_010450': 'NABÓN (cabecera cantonal)',
 'par_010451': 'COCHAPATA',
 'par_010452': 'EL PROGRESO (CAB. EN ZHOTA)',
 'par_010453': 'LAS NIEVES',
 'par_010454': 'OÑA',
 'par_010455': 'LA PAZ',
 'par_010550': 'PAUTE (cabecera cantonal)',
 'par_010551': 'AMALUZA',
 'par_010552': 'BULÁN',
 'par_010553': 'CHICÁN',
 'par_010554': 'EL CABO',
 'par_010555': 'GUACHAPALA',
 'par_010556': 'GUARAINAG',
 'par_010557': 'PALMAS',
 'par_010558': 'PAN',
 'par_010559': 'SAN CRISTÓBAL',
 'par_010560': 'SEVILLA DE ORO',
 'par_010561': 'TOMEBAMBA',
 'par_010562': 'DUG DUG (CAB. EN DUG - DUG)',
 'par_010650': 'PUCARÁ (cabecera cantonal)',
 'par_010651': 'CAMILO PONCE ENRÍQUEZ (CAB. EN RÍO 7 DE MOLLEPONGO)',
 'par_010652': 'SAN RAFAEL DE SHARUG',
 'par_010750': 'SAN FERNANDO (cabecera cantonal)',
 'par_010751': 'CHUMBLÍN',
 'par_010850': 'SANTA ISABEL (cabecera cantonal)',
 'par_010851': 'ABDÓN CALDERÓN',
 'par_010852': 'EL CARMEN DE PIJILÍ',
 'par_010853': 'SHAGLLI',
 'par_010854': 'SAN SALVADOR DE CAÑARIBAMBA',
 'par_010950': 'SÍGSIG (cabecera cantonal)',
 'par_010951': 'CUCHIL',
 'par_010952': 'JIMA',
 'par_010953': 'GÜEL',
 'par_010954': 'LUDO',
 'par_010955': 'SAN BARTOLOMÉ',
 'par_010956': 'SAN JOSÉ DE RARANGA',
 'par_011050': 'SAN FELIPE DE OÑA (cabecera cantonal)',
 'par_011051': 'SUSUDEL',
 'par_011150': 'CHORDELEG (cabecera cantonal)',
 'par_011151': 'PRINCIPAL',
 'par_011152': 'LA UNIÓN',
 'par_011153': 'LUIS GALARZA ORELLANA (CAB. EN DELEGSOL)',
 'par_011154': 'SAN MARTÍN DE PUZHIO',
 'par_011250': 'EL PAN (cabecera cantonal)',
 'par_011251': 'AMALUZA',
 'par_011252': 'PALMAS',
 'par_011253': 'SAN VICENTE',
 'par_011350': 'SEVILLA DE ORO (cabecera cantonal)',
 'par_011351': 'AMALUZA',
 'par_011352': 'PALMAS',
 'par_011450': 'GUACHAPALA (cabecera cantonal)',
 'par_011550': 'CAMILO PONCE ENRÍQUEZ (cabecera cantonal)',
 'par_011551': 'EL CARMEN DE PIJILÍ',
 'par_020101': 'ÁNGEL POLIBIO CHÁVES',
 'par_020102': 'GABRIEL IGNACIO VEINTIMILLA',
 'par_020103': 'GUANUJO [001]',
 'par_020150': 'GUARANDA (cabecera cantonal y capital provincial)',
 'par_020151': 'FACUNDO VELA',
 'par_020152': 'GUANUJO [002]',
 'par_020153': 'JULIO E. MORENO (CAB. EN CATANAGUAN - ESPINO)',
 'par_020154': 'LAS NAVES',
 'par_020155': 'SALINAS',
 'par_020156': 'SAN LORENZO',
 'par_020157': 'SAN SIMÓN',
 'par_020158': 'SANTA FE',
 'par_020159': 'SIMIÁTUG',
 'par_020160': 'SAN LUIS DE PAMBIL',
 'par_020250': 'CHILLANES (cabecera cantonal)',
 'par_020251': 'SAN JOSÉ DEL TAMBO (CAB. EN TAMBOPAMBA)',
 'par_020350': 'SAN JOSÉ DE CHIMBO (cabecera cantonal)',
 'par_020351': 'ASUNCIÓN',
 'par_020352': 'CALUMA',
 'par_020353': 'LA MAGDALENA',
 'par_020354': 'SAN SEBASTIÁN',
 'par_020355': 'TELIMBELA',
 'par_020450': 'ECHEANDÍA (cabecera cantonal)',
 'par_020550': 'SAN MIGUEL (cabecera cantonal)',
 'par_020551': 'BALSAPAMBA',
 'par_020552': 'BILOVÁN',
 'par_020553': 'RÉGULO DE MORA',
 'par_020554': 'SAN PABLO',
 'par_020555': 'SANTIAGO',
 'par_020556': 'SAN VICENTE',
 'par_020650': 'CALUMA (cabecera cantonal)',
 'par_020701': 'LAS MERCEDES',
 'par_020702': 'LAS NAVES',
 'par_020750': 'LAS NAVES (cabecera cantonal)',
 'par_030101': 'AURELIO BAYAS MARTÍNEZ',
 'par_030102': 'AZOGUES',
 'par_030103': 'BORRERO',
 'par_030104': 'SAN FRANCISCO',
 'par_030150': 'AZOGUES (cabecera cantonal y capital provincial)',
 'par_030151': 'COJITAMBO',
 'par_030152': 'DÉLEG',
 'par_030153': 'GUAPÁN',
 'par_030154': 'JAVIER LOYOLA',
 'par_030155': 'LUIS CORDERO',
 'par_030156': 'PINDILIG',
 'par_030157': 'RIVERA',
 'par_030158': 'SAN MIGUEL',
 'par_030159': 'SOLANO',
 'par_030160': 'TADAY',
 'par_030250': 'BIBLIÁN (cabecera cantonal)',
 'par_030251': 'NAZÓN (CAB. EN PAMPA DE DOMÍNGUEZ)',
 'par_030252': 'SAN FRANCISCO DE SAGEO',
 'par_030253': 'TURUPAMBA',
 'par_030254': 'JERUSALÉN',
 'par_030350': 'CAÑAR (cabecera cantonal)',
 'par_030351': 'CHONTAMARCA',
 'par_030352': 'CHOROCOPTE',
 'par_030353': 'GENERAL MORALES',
 'par_030354': 'GUALLETURO',
 'par_030355': 'HONORATO VÁSQUEZ',
 'par_030356': 'INGAPIRCA',
 'par_030357': 'JUNCAL',
 'par_030358': 'SAN ANTONIO',
 'par_030359': 'SUSCAL',
 'par_030360': 'TAMBO',
 'par_030361': 'ZHUD',
 'par_030362': 'VENTURA',
 'par_030363': 'DUCUR',
 'par_030450': 'LA TRONCAL (cabecera cantonal)',
 'par_030451': 'MANUEL J. CALLE',
 'par_030452': 'PANCHO NEGRO',
 'par_030550': 'EL TAMBO (cabecera cantonal)',
 'par_030650': 'DÉLEG (cabecera cantonal)',
 'par_030651': 'SOLANO',
 'par_030750': 'SUSCAL (cabecera cantonal)',
 'par_040101': 'GONZÁLEZ SUÁREZ',
 'par_040102': 'TULCÁN',
 'par_040150': 'TULCÁN (cabecera cantonal y capital provincial)',
 'par_040151': 'EL CARMELO',
 'par_040152': 'HUACA',
 'par_040153': 'JULIO ANDRADE',
 'par_040154': 'MALDONADO',
 'par_040155': 'PIOTER',
 'par_040156': 'TOBAR DONOSO (CAB. EN LA BOCANA DE CAMUMBÍ)',
 'par_040157': 'TUFIÑO',
 'par_040158': 'URBINA',
 'par_040159': 'EL CHICAL',
 'par_040160': 'MARISCAL SUCRE',
 'par_040161': 'SANTA MARTHA DE CUBA',
 'par_040250': 'BOLÍVAR (cabecera cantonal)',
 'par_040251': 'GARCÍA MORENO',
 'par_040252': 'LOS ANDES',
 'par_040253': 'MONTE OLIVO',
 'par_040254': 'SAN VICENTE DE PUSIR',
 'par_040255': 'SAN RAFAEL',
 'par_040301': 'EL ÁNGEL',
 'par_040302': '27 DE SEPTIEMBRE',
 'par_040350': 'EL ÁNGEL (cabecera cantonal)',
 'par_040351': 'EL GOALTAL',
 'par_040352': 'LA LIBERTAD',
 'par_040353': 'SAN ISIDRO',
 'par_040450': 'MIRA (cabecera cantonal)',
 'par_040451': 'CONCEPCIÓN',
 'par_040452': 'JIJÓN Y CAAMAÑO (CAB. EN RÍO BLANCO)',
 'par_040453': 'JUAN MONTALVO (CAB. EN SAN IGNACIO DE QUIL)',
 'par_040501': 'GONZÁLEZ SUÁREZ',
 'par_040502': 'SAN JOSÉ',
 'par_040550': 'SAN GABRIEL (cabecera cantonal)',
 'par_040551': 'CRISTÓBAL COLÓN',
 'par_040552': 'CHITÁN DE NAVARRETE',
 'par_040553': 'FERNÁNDEZ SALVADOR',
 'par_040554': 'LA PAZ',
 'par_040555': 'PIARTAL',
 'par_040650': 'HUACA (cabecera cantonal)',
 'par_040651': 'MARISCAL SUCRE',
 'par_050101': 'ELOY ALFARO (SAN FELIPE)',
 'par_050102': 'IGNACIO FLORES (PARQUE FLORES)',
 'par_050103': 'JUAN MONTALVO (SAN SEBASTIÁN)',
 'par_050104': 'LA MATRIZ',
 'par_050105': 'SAN BUENAVENTURA',
 'par_050150': 'LATACUNGA (cabecera cantonal y capital provincial)',
 'par_050151': 'ALÁQUEZ',
 'par_050152': 'BELISARIO QUEVEDO',
 'par_050153': 'GUAYTACAMA',
 'par_050154': 'JOSEGUANGO BAJO',
 'par_050155': 'LAS PAMPAS',
 'par_050156': 'MULALÓ',
 'par_050157': 'ONCE DE NOVIEMBRE',
 'par_050158': 'POALÓ',
 'par_050159': 'SAN JUAN DE PASTOCALLE',
 'par_050160': 'SIGCHOS',
 'par_050161': 'TANICUCHÍ',
 'par_050162': 'TOACASO',
 'par_050163': 'PALO QUEMADO',
 'par_050201': 'EL CARMEN',
 'par_050202': 'LA MANÁ',
 'par_050203': 'EL TRIUNFO',
 'par_050250': 'LA MANÁ (cabecera cantonal)',
 'par_050251': 'GUASAGANDA (CAB. EN GUASAGANDA CENTRO )',
 'par_050252': 'PUCAYACU',
 'par_050350': 'EL CORAZÓN (cabecera cantonal)',
 'par_050351': 'MORASPUNGO',
 'par_050352': 'PINLLOPATA',
 'par_050353': 'RAMÓN CAMPAÑA',
 'par_050450': 'PUJILÍ (cabecera cantonal)',
 'par_050451': 'ANGAMARCA',
 'par_050452': 'CHUCCHILÁN (CHUGCHILÁN)',
 'par_050453': 'GUANGAJE',
 'par_050454': 'ISINLIBÍ (ISINLIVÍ)',
 'par_050455': 'LA VICTORIA',
 'par_050456': 'PILALÓ',
 'par_050457': 'TINGO',
 'par_050458': 'ZUMBAHUA',
 'par_050550': 'SAN MIGUEL (cabecera cantonal)',
 'par_050551': 'ANTONIO JOSÉ HOLGUÍN',
 'par_050552': 'CUSUBAMBA',
 'par_050553': 'MULALILLO',
 'par_050554': 'MULLIQUINDIL',
 'par_050555': 'PANSALEO (CAB. EN PANZALEO )',
 'par_050650': 'SAQUISILÍ (cabecera cantonal)',
 'par_050651': 'CANCHAGUA',
 'par_050652': 'CHANTILÍN',
 'par_050653': 'COCHAPAMBA',
 'par_050750': 'SIGCHOS (cabecera cantonal)',
 'par_050751': 'CHUGCHILLÁN',
 'par_050752': 'ISINLIVI',
 'par_050753': 'LAS PAMPAS',
 'par_050754': 'PALO QUEMADO',
 'par_060101': 'LIZARZABURU',
 'par_060102': 'MALDONADO',
 'par_060103': 'VELASCO',
 'par_060104': 'VELOZ',
 'par_060105': 'YARUQUÍES',
 'par_060150': 'RIOBAMBA (cabecera cantonal y capital provincial)',
 'par_060151': 'CACHA',
 'par_060152': 'CALPI',
 'par_060153': 'CUBIJÍES',
 'par_060154': 'FLORES (CAB. EN LANLÁN)',
 'par_060155': 'LICÁN',
 'par_060156': 'LICTO',
 'par_060157': 'PUNGALÁ',
 'par_060158': 'PUNÍN',
 'par_060159': 'QUIMIAG',
 'par_060160': 'SAN JUAN',
 'par_060161': 'SAN LUIS',
 'par_060250': 'ALAUSÍ (cabecera cantonal)',
 'par_060251': 'ACHUPALLAS',
 'par_060252': 'CUMANDÁ',
 'par_060253': 'GUASUNTOS',
 'par_060254': 'HUIGRA',
 'par_060255': 'MULTITUD',
 'par_060256': 'PISTISHI',
 'par_060257': 'PUMALLACTA',
 'par_060258': 'SEVILLA',
 'par_060259': 'SIBAMBE',
 'par_060260': 'TIXÁN',
 'par_060301': 'CAJABAMBA',
 'par_060302': 'SICALPA',
 'par_060350': 'VILLA LA UNIÓN (cabecera cantonal)',
 'par_060351': 'CAÑI',
 'par_060352': 'COLUMBE',
 'par_060353': 'JUAN DE VELASCO',
 'par_060354': 'SANTIAGO DE QUITO (CAB. EN SAN ANTONIO',
 'par_060450': 'CHAMBO (cabecera cantonal)',
 'par_060550': 'CHUNCHI (cabecera cantonal)',
 'par_060551': 'CAPZOL',
 'par_060552': 'COMPUD',
 'par_060553': 'GONZOL',
 'par_060554': 'LLAGOS',
 'par_060650': 'GUAMOTE (cabecera cantonal)',
 'par_060651': 'CEBADAS',
 'par_060652': 'PALMIRA',
 'par_060701': 'EL ROSARIO',
 'par_060702': 'LA MATRIZ',
 'par_060750': 'GUANO (cabecera cantonal)',
 'par_060751': 'GUANANDO',
 'par_060752': 'ILAPO',
 'par_060753': 'LA PROVIDENCIA',
 'par_060754': 'SAN ANDRÉS',
 'par_060755': 'SAN GERARDO (CAB. EN SAN GERARDO DE PACAICAGUÁN)',
 'par_060756': 'SAN ISIDRO DE PATULÚ',
 'par_060757': 'SAN JOSÉ DEL CHAZO',
 'par_060758': 'SANTA FÉ DE GALÁN',
 'par_060759': 'VALPARAISO',
 'par_060850': 'PALLATANGA (cabecera cantonal)',
 'par_060950': 'PENIPE (cabecera cantonal)',
 'par_060951': 'EL ALTAR',
 'par_060952': 'MATUS',
 'par_060953': 'PUELA',
 'par_060954': 'SAN ANTONIO DE BAYUSHIG',
 'par_060955': 'LA CANDELARIA',
 'par_060956': 'BILBAO (CAB.EN QUILLUYACU)',
 'par_061050': 'CUMANDÁ (cabecera cantonal)',
 'par_070101': 'LA PROVIDENCIA',
 'par_070102': 'MACHALA',
 'par_070103': 'PUERTO BOLÍVAR',
 'par_070104': 'NUEVE DE MAYO',
 'par_070105': 'EL CAMBIO [001]',
 'par_070150': 'MACHALA (cabecera cantonal y capital provincial)',
 'par_070151': 'EL CAMBIO [002]',
 'par_070152': 'EL RETIRO',
 'par_070250': 'ARENILLAS (cabecera cantonal)',
 'par_070251': 'CHACRAS',
 'par_070252': 'LA LIBERTAD',
 'par_070253': 'LAS LAJAS (CAB. EN LA VICTORIA)',
 'par_070254': 'PALMALES',
 'par_070255': 'CARCABÓN',
 'par_070256': 'LA CUCA',
 'par_070350': 'PACCHA (cabecera cantonal)',
 'par_070351': 'AYAPAMBA',
 'par_070352': 'CORDONCILLO',
 'par_070353': 'MILAGRO',
 'par_070354': 'SAN JOSÉ',
 'par_070355': 'SAN JUAN DE CERRO AZUL',
 'par_070450': 'BALSAS (cabecera cantonal)',
 'par_070451': 'BELLAMARÍA',
 'par_070550': 'CHILLA (cabecera cantonal)',
 'par_070650': 'EL GUABO (cabecera cantonal)',
 'par_070651': 'BARBONES',
 'par_070652': 'LA IBERIA',
 'par_070653': 'TENDALES (CAB.EN PUERTO TENDALES)',
 'par_070654': 'RÍO BONITO',
 'par_070701': 'ECUADOR',
 'par_070702': 'EL PARAÍSO',
 'par_070703': 'HUALTACO',
 'par_070704': 'MILTON REYES',
 'par_070705': 'UNIÓN LOJANA',
 'par_070750': 'HUAQUILLAS (cabecera cantonal)',
 'par_070850': 'MARCABELÍ (cabecera cantonal)',
 'par_070851': 'EL INGENIO',
 'par_070901': 'BOLÍVAR',
 'par_070902': 'LOMA DE FRANCO',
 'par_070903': 'OCHOA LEÓN (MATRIZ)',
 'par_070904': 'TRES CERRITOS',
 'par_070950': 'PASAJE (cabecera cantonal)',
 'par_070951': 'BUENAVISTA',
 'par_070952': 'CASACAY',
 'par_070953': 'LA PEAÑA',
 'par_070954': 'PROGRESO',
 'par_070955': 'UZHCURRUMI',
 'par_070956': 'CAÑAQUEMADA',
 'par_071001': 'LA MATRIZ',
 'par_071002': 'LA SUSAYA',
 'par_071003': 'PIÑAS GRANDE',
 'par_071050': 'PIÑAS (cabecera cantonal)',
 'par_071051': 'CAPIRO (CAB. EN LA CAPILLA DE CAPIRO)',
 'par_071052': 'LA BOCANA',
 'par_071053': 'MOROMORO (CAB. EN EL VADO)',
 'par_071054': 'PIEDRAS',
 'par_071055': 'SAN ROQUE',
 'par_071056': 'SARACAY',
 'par_071150': 'PORTOVELO (cabecera cantonal)',
 'par_071151': 'CURTINCAPA',
 'par_071152': 'MORALES',
 'par_071153': 'SALATÍ',
 'par_071201': 'SANTA ROSA',
 'par_071202': 'PUERTO JELÍ',
 'par_071203': 'BALNEARIO JAMBELÍ (SATÉLITE)',
 'par_071204': 'JUMÓN (SATÉLITE)',
 'par_071205': 'NUEVO SANTA ROSA',
 'par_071250': 'SANTA ROSA (cabecera cantonal)',
 'par_071251': 'BELLAVISTA',
 'par_071252': 'JAMBELÍ',
 'par_071253': 'LA AVANZADA',
 'par_071254': 'SAN ANTONIO',
 'par_071255': 'TORATA',
 'par_071256': 'VICTORIA',
 'par_071257': 'BELLAMARÍA',
 'par_071350': 'ZARUMA (cabecera cantonal)',
 'par_071351': 'ABAÑÍN',
 'par_071352': 'ARCAPAMBA',
 'par_071353': 'GUANAZÁN',
 'par_071354': 'GUIZHAGUIÑA',
 'par_071355': 'HUERTAS',
 'par_071356': 'MALVAS',
 'par_071357': 'MULUNCAY GRANDE',
 'par_071358': 'SINSAO',
 'par_071359': 'SALVIAS',
 'par_071401': 'LA VICTORIA',
 'par_071402': 'PLATANILLOS',
 'par_071403': 'VALLE HERMOSO',
 'par_071450': 'LA VICTORIA (cabecera cantonal)',
 'par_071451': 'LA LIBERTAD',
 'par_071452': 'EL PARAÍSO',
 'par_071453': 'SAN ISIDRO',
 'par_080101': 'BARTOLOMÉ RUIZ (CÉSAR FRANCO CARRIÓN)',
 'par_080102': '5 DE AGOSTO',
 'par_080103': 'ESMERALDAS',
 'par_080104': 'LUIS TELLO (LAS PALMAS)',
 'par_080105': 'SIMÓN PLATA TORRES',
 'par_080150': 'ESMERALDAS (cabecera cantonal y capital provincial)',
 'par_080151': 'ATACAMES',
 'par_080152': 'CAMARONES (CAB. EN SAN VICENTE)',
 'par_080153': 'CORONEL CARLOS CONCHA TORRES (CAB.EN HUELE)',
 'par_080154': 'CHINCA',
 'par_080155': 'CHONTADURO',
 'par_080156': 'CHUMUNDÉ',
 'par_080157': 'LAGARTO',
 'par_080158': 'LA UNIÓN',
 'par_080159': 'MAJUA',
 'par_080160': 'MONTALVO (CAB. EN HORQUETA)',
 'par_080161': 'RÍO VERDE',
 'par_080162': 'ROCAFUERTE',
 'par_080163': 'SAN MATEO',
 'par_080164': 'SÚA (CAB. EN LA BOCANA)',
 'par_080165': 'TABIAZO',
 'par_080166': 'TACHINA',
 'par_080167': 'TONCHIGÜE',
 'par_080168': 'VUELTA LARGA',
 'par_080250': 'VALDEZ (LIMONES) (cabecera cantonal)',
 'par_080251': 'ANCHAYACU',
 'par_080252': 'ATAHUALPA (CAB. EN CAMARONES)',
 'par_080253': 'BORBÓN',
 'par_080254': 'LA TOLA',
 'par_080255': 'LUIS VARGAS TORRES (CAB. EN PLAYA DE ORO)',
 'par_080256': 'MALDONADO',
 'par_080257': 'PAMPANAL DE BOLÍVAR',
 'par_080258': 'SAN FRANCISCO DE ONZOLE',
 'par_080259': 'SANTO DOMINGO DE ONZOLE',
 'par_080260': 'SELVA ALEGRE',
 'par_080261': 'TELEMBÍ',
 'par_080262': 'COLÓN ELOY DEL MARÍA (CAB. EN COLÓN ELOY)',
 'par_080263': 'SAN JOSÉ DE CAYAPAS',
 'par_080264': 'TIMBIRÉ',
 'par_080265': 'SANTA LUCÍA DE LAS PEÑAS',
 'par_080350': 'MUISNE (cabecera cantonal)',
 'par_080351': 'BOLÍVAR',
 'par_080352': 'DAULE',
 'par_080353': 'GALERA',
 'par_080354': 'QUINGUE',
 'par_080355': 'SÁLIMA',
 'par_080356': 'SAN FRANCISCO',
 'par_080357': 'SAN GREGORIO',
 'par_080358': 'SAN JOSÉ DE CHAMANGA (CAB.EN CHAMANGA)',
 'par_080450': 'ROSA ZÁRATE (cabecera cantonal)',
 'par_080451': 'CUBE',
 'par_080452': 'CHURA (CAB. EN EL YERBERO)',
 'par_080453': 'MALIMPIA',
 'par_080454': 'VICHE',
 'par_080455': 'LA UNIÓN',
 'par_080550': 'SAN LORENZO (cabecera cantonal)',
 'par_080551': 'ALTO TAMBO (CAB. EN GUADUAL)',
 'par_080552': 'ANCÓN (CAB. EN PALMA REAL)',
 'par_080553': 'CALDERÓN',
 'par_080554': 'CARONDELET',
 'par_080555': '5 DE JUNIO (CAB. EN UIMBÍ)',
 'par_080556': 'CONCEPCIÓN',
 'par_080557': 'MATAJE (CAB. EN SANTANDER)',
 'par_080558': 'SAN JAVIER DE CACHAVÍ (CAB. EN SAN JAVIER)',
 'par_080559': 'SANTA RITA',
 'par_080560': 'TAMBILLO',
 'par_080561': 'TULULBÍ (CAB. EN RICAURTE)',
 'par_080562': 'URBINA',
 'par_080650': 'ATACAMES (cabecera cantonal)',
 'par_080651': 'LA UNIÓN',
 'par_080652': 'SÚA (CAB. EN LA BOCANA)',
 'par_080653': 'TONCHIGÜE',
 'par_080654': 'TONSUPA (CAB. EN TONSUPA CENTRAL)',
 'par_080750': 'RÍOVERDE (cabecera cantonal)',
 'par_080751': 'CHONTADURO',
 'par_080752': 'CHUMUNDÉ',
 'par_080753': 'LAGARTO',
 'par_080754': 'MONTALVO (CAB. EN HORQUETA)',
 'par_080755': 'ROCAFUERTE',
 'par_080850': 'LA CONCORDIA (cabecera cantonal)',
 'par_080851': 'MONTERREY',
 'par_080852': 'LA VILLEGAS',
 'par_080853': 'PLAN PILOTO',
 'par_090101': 'AYACUCHO',
 'par_090102': 'BOLÍVAR (SAGRARIO)',
 'par_090103': 'CARBO (CONCEPCIÓN)',
 'par_090104': 'FEBRES CORDERO',
 'par_090105': 'GARCÍA MORENO',
 'par_090106': 'LETAMENDI',
 'par_090107': 'NUEVE DE OCTUBRE',
 'par_090108': 'OLMEDO (SAN ALEJO)',
 'par_090109': 'ROCA',
 'par_090110': 'ROCAFUERTE',
 'par_090111': 'SUCRE',
 'par_090112': 'TARQUI',
 'par_090113': 'URDANETA',
 'par_090114': 'XIMENA',
 'par_090115': 'PASCUALES [001]',
 'par_090150': 'GUAYAQUIL (cabecera cantonal y capital provincial)',
 'par_090151': 'CHONGÓN',
 'par_090152': 'JUAN GÓMEZ RENDÓN',
 'par_090153': 'MORRO',
 'par_090154': 'PASCUALES [002]',
 'par_090155': 'PLAYAS (GRAL. VILLAMIL)',
 'par_090156': 'POSORJA',
 'par_090157': 'PUNÁ',
 'par_090158': 'TENGUEL',
 'par_090250': 'ALFREDO BAQUERIZO MORENO (JUJÁN) (cabecera cantonal)',
 'par_090350': 'BALAO (cabecera cantonal)',
 'par_090450': 'BALZAR (cabecera cantonal)',
 'par_090550': 'COLIMES (cabecera cantonal)',
 'par_090551': 'SAN JACINTO',
 'par_090601': 'DAULE',
 'par_090602': 'LA AURORA (SATÉLITE)',
 'par_090603': 'BANIFE',
 'par_090604': 'EMILIANO CAICEDO MARCOS',
 'par_090605': 'MAGRO',
 'par_090606': 'PADRE JUAN BAUTISTA AGUIRRE',
 'par_090607': 'SANTA CLARA',
 'par_090608': 'VICENTE PIEDRAHITA',
 'par_090650': 'DAULE (cabecera cantonal)',
 'par_090651': 'ISIDRO AYORA (SOLEDAD)',
 'par_090652': 'JUAN BAUTISTA AGUIRRE (CAB. EN LOS TINTOS)',
 'par_090653': 'LAUREL (CAB. EN EL LAUREL)',
 'par_090654': 'LIMONAL',
 'par_090655': 'LOMAS DE SARGENTILLO',
 'par_090656': 'LOS LOJAS',
 'par_090657': 'PIEDRAHITA (NOBOL)',
 'par_090701': 'ELOY ALFARO (DURÁN)',
 'par_090702': 'EL RECREO',
 'par_090703': 'DIVINO NIÑO',
 'par_090750': 'ELOY ALFARO (cabecera cantonal)',
 'par_090850': 'VELASCO IBARRA (cabecera cantonal)',
 'par_090851': 'GUAYAS (CAB. EN PUEBLO NUEVO)',
 'par_090852': 'EL ROSARIO',
 'par_090950': 'EL TRIUNFO (cabecera cantonal)',
 'par_091001': 'CAMILO ANDRADE',
 'par_091002': 'ELOY ALFARO',
 'par_091003': 'CHIRIJOS',
 'par_091004': 'CORONEL ENRIQUE VALDEZ',
 'par_091005': 'ROSA MARÍA',
 'par_091006': 'JOSÉ MARÍA VELASCO IBARRA',
 'par_091007': 'VICENTE ROCAFUERTE',
 'par_091008': 'ERNESTO SEMINARIO',
 'par_091009': 'LAS PIÑAS',
 'par_091050': 'MILAGRO (cabecera cantonal)',
 'par_091051': 'CHOBO',
 'par_091052': 'GENERAL ELIZALDE (BUCAY)',
 'par_091053': 'MARISCAL SUCRE',
 'par_091054': 'ROBERTO ASTUDILLO',
 'par_091150': 'NARANJAL (cabecera cantonal)',
 'par_091151': 'JESÚS MARÍA',
 'par_091152': 'SAN CARLOS',
 'par_091153': 'SANTA ROSA DE FLANDES',
 'par_091154': 'TAURA',
 'par_091250': 'NARANJITO (cabecera cantonal)',
 'par_091350': 'PALESTINA (cabecera cantonal)',
 'par_091450': 'PEDRO CARBO (cabecera cantonal)',
 'par_091451': 'VALLE DE LA VIRGEN',
 'par_091452': 'SABANILLA',
 'par_091601': 'SAMBORONDÓN',
 'par_091602': 'LA PUNTILLA (SATÉLITE)',
 'par_091650': 'SAMBORONDÓN (cabecera cantonal)',
 'par_091651': 'TARIFA',
 'par_091850': 'SANTA LUCÍA (cabecera cantonal)',
 'par_091901': 'BOCANA',
 'par_091902': 'CANDILEJOS',
 'par_091903': 'CENTRAL',
 'par_091904': 'PARAÍSO',
 'par_091905': 'SAN MATEO',
 'par_091950': 'EL SALITRE (cabecera cantonal)',
 'par_091951': 'GENERAL VERNAZA',
 'par_091952': 'LA VICTORIA',
 'par_091953': 'JUNQUILLAL',
 'par_092050': 'SAN JACINTO DE YAGUACHI (cabecera cantonal)',
 'par_092051': 'CORONEL LORENZO DE GARAICOA (PEDREGAL)',
 'par_092052': 'CORONEL MARCELINO MARIDUEÑA (SAN CARLOS)',
 'par_092053': 'GENERAL PEDRO J. MONTERO',
 'par_092054': 'SIMÓN BOLÍVAR',
 'par_092055': 'YAGUACHI VIEJO',
 'par_092056': 'VIRGEN DE FÁTIMA',
 'par_092150': 'GENERAL VILLAMIL (cabecera cantonal)',
 'par_092250': 'SIMÓN BOLÍVAR (cabecera cantonal)',
 'par_092251': 'CORONEL LORENZO DE GARAYCOA',
 'par_092350': 'CORONEL MARCELINO MARIDUEÑA (cabecera cantonal)',
 'par_092450': 'LOMAS DE SARGENTILLO (cabecera cantonal)',
 'par_092451': 'ISIDRO AYORA (SOLEDAD)',
 'par_092550': 'NARCISA DE JESÚS (cabecera cantonal)',
 'par_092750': 'GENERAL ANTONIO ELIZALDE (cabecera cantonal)',
 'par_092850': 'ISIDRO AYORA (cabecera cantonal)',
 'par_100101': 'CARANQUI',
 'par_100102': 'GUAYAQUIL DE ALPACHACA',
 'par_100103': 'SAGRARIO',
 'par_100104': 'SAN FRANCISCO',
 'par_100105': 'LA DOLOROSA DEL PRIORATO',
 'par_100150': 'SAN MIGUEL DE IBARRA (cabecera cantonal y capital provincial)',
 'par_100151': 'AMBUQUÍ',
 'par_100152': 'ANGOCHAGUA',
 'par_100153': 'LA CAROLINA',
 'par_100154': 'LA ESPERANZA',
 'par_100155': 'LITA',
 'par_100156': 'SALINAS',
 'par_100157': 'SAN ANTONIO',
 'par_100201': 'ANDRADE MARÍN (LOURDES)',
 'par_100202': 'ATUNTAQUI',
 'par_100250': 'ATUNTAQUI (cabecera cantonal)',
 'par_100251': 'IMBAYA (CAB. EN SAN LUIS DE IMBAYA)',
 'par_100252': 'SAN FRANCISCO DE NATABUELA (CAB. EN NATABUELA)',
 'par_100253': 'SAN JOSÉ DE CHALTURA (CAB. EN CHALTURA)',
 'par_100254': 'SAN ROQUE',
 'par_100301': 'SAGRARIO',
 'par_100302': 'SAN FRANCISCO',
 'par_100350': 'COTACACHI (cabecera cantonal)',
 'par_100351': 'APUELA',
 'par_100352': 'GARCÍA MORENO',
 'par_100353': 'IMANTAG',
 'par_100354': 'PEÑAHERRERA',
 'par_100355': 'PLAZA GUTIÉRREZ',
 'par_100356': 'QUIROGA',
 'par_100357': 'SEIS DE JULIO DE CUELLAJE (CAB. EN CUELLAJE)',
 'par_100358': 'VACAS GALINDO (CAB.EN SAN MIGUEL ALTO)',
 'par_100401': 'JORDÁN',
 'par_100402': 'SAN LUIS',
 'par_100450': 'OTAVALO (cabecera cantonal)',
 'par_100451': 'DR. MIGUEL EGAS CABEZAS (CAB. EN PEGUCHE)',
 'par_100452': 'EUGENIO ESPEJO',
 'par_100453': 'GONZÁLEZ SUÁREZ',
 'par_100454': 'PATAQUÍ',
 'par_100455': 'SAN JOSÉ DE QUICHINCHE',
 'par_100456': 'SAN JUAN DE ILUMÁN',
 'par_100457': 'SAN PABLO',
 'par_100458': 'SAN RAFAEL',
 'par_100459': 'SELVA ALEGRE',
 'par_100550': 'PIMAMPIRO (cabecera cantonal)',
 'par_100551': 'CHUGÁ',
 'par_100552': 'MARIANO ACOSTA',
 'par_100553': 'SAN FRANCISCO DE SIGSIPAMBA',
 'par_100650': 'URCUQUÍ CABECERA CANTONAL (cabecera cantonal)',
 'par_100651': 'CAHUASQUÍ',
 'par_100652': 'LA MERCED DE BUENOS AIRES',
 'par_100653': 'PABLO ARENAS',
 'par_100654': 'SAN BLAS',
 'par_100655': 'TUMBABIRO',
 'par_110101': 'EL SAGRARIO',
 'par_110102': 'SAN SEBASTIÁN',
 'par_110103': 'SUCRE',
 'par_110104': 'VALLE',
 'par_110105': 'CARIGÁN',
 'par_110106': 'PUNZARA',
 'par_110150': 'LOJA (cabecera cantonal y capital provincial)',
 'par_110151': 'CHANTACO',
 'par_110152': 'CHUQUIRIBAMBA',
 'par_110153': 'EL CISNE',
 'par_110154': 'GUALEL',
 'par_110155': 'JIMBILLA',
 'par_110156': 'MALACATOS',
 'par_110157': 'SAN LUCAS',
 'par_110158': 'SAN PEDRO DE VILCABAMBA',
 'par_110159': 'SANTIAGO',
 'par_110160': 'TAQUIL',
 'par_110161': 'VILCABAMBA',
 'par_110162': 'YANGANA',
 'par_110163': 'QUINARA',
 'par_110201': 'CARIAMANGA',
 'par_110202': 'CHILE',
 'par_110203': 'SAN VICENTE',
 'par_110250': 'CARIAMANGA (cabecera cantonal)',
 'par_110251': 'COLAISACA',
 'par_110252': 'EL LUCERO',
 'par_110253': 'UTUANA',
 'par_110254': 'SANGUILLÍN',
 'par_110301': 'CATAMAYO',
 'par_110302': 'SAN JOSÉ',
 'par_110350': 'CATAMAYO (cabecera cantonal)',
 'par_110351': 'EL TAMBO',
 'par_110352': 'GUAYQUICHUMA (CAB. EN EL PRADO)',
 'par_110353': 'SAN PEDRO DE LA BENDITA',
 'par_110354': 'ZAMBI',
 'par_110450': 'CELICA (cabecera cantonal)',
 'par_110451': 'CRUZPAMBA',
 'par_110452': 'CHAQUINAL',
 'par_110453': '12 DE DICIEMBRE (CAB. EN ACHIOTES)',
 'par_110454': 'PINDAL (FEDERICO PÁEZ)',
 'par_110455': 'PÓZUL',
 'par_110456': 'SABANILLA',
 'par_110457': 'TENIENTE MAXIMILIANO RODRÍGUEZ LOAIZA',
 'par_110550': 'CHAGUARPAMBA (cabecera cantonal)',
 'par_110551': 'BUENAVISTA',
 'par_110552': 'EL ROSARIO',
 'par_110553': 'SANTA RUFINA',
 'par_110554': 'AMARILLOS',
 'par_110650': 'AMALUZA (cabecera cantonal)',
 'par_110651': 'BELLAVISTA',
 'par_110652': 'JIMBURA',
 'par_110653': 'SANTA TERESITA',
 'par_110654': '27 DE ABRIL (CAB. EN LA NARANJA)',
 'par_110655': 'EL INGENIO',
 'par_110656': 'EL AIRO',
 'par_110750': 'GONZANAMÁ (cabecera cantonal)',
 'par_110751': 'CHANGAIMINA',
 'par_110752': 'FUNDOCHAMBA',
 'par_110753': 'NAMBACOLA',
 'par_110754': 'PURUNUMA',
 'par_110755': 'QUILANGA (LA PAZ)',
 'par_110756': 'SACAPALCA',
 'par_110757': 'SAN ANTONIO DE LAS ARADAS (CAB. EN LAS ARADAS)',
 'par_110801': 'GENERAL ELOY ALFARO (SAN SEBASTIÁN)',
 'par_110802': 'MACARÁ (MANUEL ENRIQUE RENGEL SUQUILANDA)',
 'par_110850': 'MACARÁ (cabecera cantonal)',
 'par_110851': 'LARAMA',
 'par_110852': 'LA VICTORIA',
 'par_110853': 'SABIANGO (CAB. EN LA CAPILLA)',
 'par_110901': 'CATACOCHA',
 'par_110902': 'LOURDES',
 'par_110950': 'CATACOCHA (cabecera cantonal)',
 'par_110951': 'CANGONAMÁ',
 'par_110952': 'GUACHANAMÁ',
 'par_110953': 'LA TINGUE',
 'par_110954': 'LAURO GUERRERO (CAB. EN CHINCHANGA)',
 'par_110955': 'OLMEDO (SANTA BÁRBARA)',
 'par_110956': 'ORIANGA',
 'par_110957': 'SAN ANTONIO',
 'par_110958': 'CASANGA',
 'par_110959': 'YAMANA',
 'par_111050': 'ALAMOR (cabecera cantonal)',
 'par_111051': 'CIANO',
 'par_111052': 'EL ARENAL',
 'par_111053': 'EL LIMO',
 'par_111054': 'MERCADILLO',
 'par_111055': 'VICENTINO',
 'par_111150': 'SARAGURO (cabecera cantonal)',
 'par_111151': 'EL PARAÍSO DE CELEN',
 'par_111152': 'EL TABLÓN',
 'par_111153': 'LLUZHAPA',
 'par_111154': 'MANÚ',
 'par_111155': 'SAN ANTONIO DE QUMBE',
 'par_111156': 'SAN PABLO DE TENTA',
 'par_111157': 'SAN SEBASTIÁN DE YÚLUC',
 'par_111158': 'SELVA ALEGRE',
 'par_111159': 'URDANETA',
 'par_111160': 'SUMAYPAMBA',
 'par_111250': 'SOZORANGA (cabecera cantonal)',
 'par_111251': 'NUEVA FÁTIMA',
 'par_111252': 'TACAMOROS',
 'par_111350': 'ZAPOTILLO (cabecera cantonal)',
 'par_111351': 'MANGAHURCO',
 'par_111352': 'GARZAREAL',
 'par_111353': 'LIMONES',
 'par_111354': 'PALETILLAS',
 'par_111355': 'BOLASPAMBA',
 'par_111356': 'CAZADEROS',
 'par_111450': 'PINDAL (cabecera cantonal)',
 'par_111451': 'CHAQUINAL',
 'par_111452': '12 DE DICIEMBRE (CAB.EN ACHIOTES)',
 'par_111453': 'MILAGROS',
 'par_111550': 'QUILANGA (cabecera cantonal)',
 'par_111551': 'FUNDOCHAMBA',
 'par_111552': 'SAN ANTONIO DE LAS ARADAS (CAB. EN LAS ARADAS)',
 'par_111650': 'OLMEDO (cabecera cantonal)',
 'par_111651': 'LA TINGUE',
 'par_120101': 'CLEMENTE BAQUERIZO',
 'par_120102': 'DOCTOR CAMILO PONCE',
 'par_120103': 'BARREIRO',
 'par_120104': 'EL SALTO',
 'par_120150': 'BABAHOYO (cabecera cantonal y capital provincial)',
 'par_120151': 'BARREIRO (SANTA RITA)',
 'par_120152': 'CARACOL',
 'par_120153': 'FEBRES CORDERO (CAB. EN MATA DE CACAO)',
 'par_120154': 'PIMOCHA',
 'par_120155': 'LA UNIÓN',
 'par_120250': 'BABA (cabecera cantonal)',
 'par_120251': 'GUARE',
 'par_120252': 'ISLA DE BEJUCAL',
 'par_120350': 'MONTALVO (cabecera cantonal)',
 'par_120351': 'LA ESMERALDA',
 'par_120450': 'PUEBLOVIEJO (cabecera cantonal)',
 'par_120451': 'PUERTO PECHICHE',
 'par_120452': 'SAN JUAN',
 'par_120501': 'QUEVEDO',
 'par_120502': 'SAN CAMILO',
 'par_120503': 'SAN JOSÉ',
 'par_120504': 'GUAYACÁN',
 'par_120505': 'NICOLÁS INFANTE DÍAZ',
 'par_120506': 'SAN CRISTÓBAL',
 'par_120507': 'SIETE DE OCTUBRE',
 'par_120508': '24 DE MAYO',
 'par_120509': 'VENUS DEL RÍO QUEVEDO',
 'par_120510': 'VIVA ALFARO',
 'par_120550': 'QUEVEDO (cabecera cantonal)',
 'par_120551': 'BUENA FÉ',
 'par_120552': 'MOCACHE',
 'par_120553': 'SAN CARLOS',
 'par_120554': 'VALENCIA',
 'par_120555': 'LA ESPERANZA',
 'par_120650': 'CATARAMA (cabecera cantonal)',
 'par_120651': 'RICAURTE',
 'par_120701': '10 DE NOVIEMBRE',
 'par_120702': 'VENTANAS',
 'par_120750': 'VENTANAS (cabecera cantonal)',
 'par_120751': 'QUINSALOMA',
 'par_120752': 'ZAPOTAL',
 'par_120753': 'CHACARITA',
 'par_120754': 'LOS ÁNGELES',
 'par_120801': 'BALZAR DE VINCES',
 'par_120802': 'VINCES CENTRAL',
 'par_120803': 'SAN LORENZO DE VINCES',
 'par_120850': 'VINCES (cabecera cantonal)',
 'par_120851': 'ANTONIO SOTOMAYOR (CAB. EN PLAYAS DE VINCES)',
 'par_120852': 'PALENQUE',
 'par_120950': 'PALENQUE (cabecera cantonal)',
 'par_121001': 'SAN JACINTO DE BUENA FÉ',
 'par_121002': '7 DE AGOSTO',
 'par_121003': '11 DE OCTUBRE',
 'par_121050': 'SAN JACINTO DE BUENA FÉ (cabecera cantonal)',
 'par_121051': 'PATRICIA PILAR',
 'par_121101': 'VALENCIA',
 'par_121102': 'LA UNIÓN',
 'par_121103': 'LA NUEVA UNIÓN',
 'par_121150': 'VALENCIA (cabecera cantonal)',
 'par_121250': 'MOCACHE (cabecera cantonal)',
 'par_121350': 'QUINSALOMA (cabecera cantonal)',
 'par_130101': 'PORTOVIEJO',
 'par_130102': '12 DE MARZO',
 'par_130103': 'COLÓN',
 'par_130104': 'PICOAZÁ',
 'par_130105': 'SAN PABLO',
 'par_130106': 'ANDRÉS DE VERA',
 'par_130107': 'FRANCISCO PACHECO',
 'par_130108': '18 DE OCTUBRE',
 'par_130109': 'SIMÓN BOLÍVAR',
 'par_130150': 'PORTOVIEJO (cabecera cantonal y capital provincial)',
 'par_130151': 'ABDÓN CALDERÓN',
 'par_130152': 'ALHAJUELA',
 'par_130153': 'CRUCITA',
 'par_130154': 'PUEBLO NUEVO',
 'par_130155': 'RIOCHICO',
 'par_130156': 'SAN PLÁCIDO',
 'par_130157': 'CHIRIJOS',
 'par_130250': 'CALCETA (cabecera cantonal)',
 'par_130251': 'MEMBRILLO',
 'par_130252': 'QUIROGA',
 'par_130301': 'CHONE',
 'par_130302': 'SANTA RITA',
 'par_130350': 'CHONE (cabecera cantonal)',
 'par_130351': 'BOYACÁ',
 'par_130352': 'CANUTO',
 'par_130353': 'CONVENTO',
 'par_130354': 'CHIBUNGA',
 'par_130355': 'ELOY ALFARO',
 'par_130356': 'RICAURTE',
 'par_130357': 'SAN ANTONIO',
 'par_130401': 'EL CARMEN',
 'par_130402': '4 DE DICIEMBRE',
 'par_130450': 'EL CARMEN (cabecera cantonal)',
 'par_130451': 'WILFRIDO LOOR MOREIRA',
 'par_130452': 'SAN PEDRO DE SUMA',
 'par_130453': 'SANTA MARÍA',
 'par_130454': 'EL PARAÍSO LA 14 (CAB. EN EL PARAÍSO )',
 'par_130550': 'FLAVIO ALFARO (cabecera cantonal)',
 'par_130551': 'SAN FRANCISCO DE NOVILLO (CAB. EN NOVILLO)',
 'par_130552': 'ZAPALLO',
 'par_130601': 'DOCTOR MIGUEL MORÁN LUCIO',
 'par_130602': 'MANUEL INOCENCIO PARRALES Y GUALE',
 'par_130603': 'SAN LORENZO DE JIPIJAPA',
 'par_130650': 'JIPIJAPA (cabecera cantonal)',
 'par_130651': 'AMÉRICA',
 'par_130652': 'EL ANEGADO (CAB. EN ELOY ALFARO)',
 'par_130653': 'JULCUY',
 'par_130654': 'LA UNIÓN',
 'par_130655': 'MACHALILLA',
 'par_130656': 'MEMBRILLAL',
 'par_130657': 'PEDRO PABLO GÓMEZ (CAB. EN POTRERO NUEVO)',
 'par_130658': 'PUERTO DE CAYO',
 'par_130659': 'PUERTO LÓPEZ',
 'par_130750': 'JUNÍN (cabecera cantonal)',
 'par_130801': 'LOS ESTEROS',
 'par_130802': 'MANTA',
 'par_130803': 'SAN MATEO',
 'par_130804': 'TARQUI',
 'par_130805': 'ELOY ALFARO',
 'par_130850': 'MANTA (cabecera cantonal)',
 'par_130851': 'SAN LORENZO',
 'par_130852': 'SANTA MARIANITA',
 'par_130901': 'ANÍBAL SAN ANDRÉS',
 'par_130902': 'MONTECRISTI',
 'par_130903': 'EL COLORADO',
 'par_130904': 'GENERAL ELOY ALFARO',
 'par_130905': 'LEONIDAS PROAÑO',
 'par_130906': 'ISABEL MUENTES',
 'par_130950': 'MONTECRISTI (cabecera cantonal)',
 'par_130951': 'JARAMIJÓ',
 'par_130952': 'LA PILA',
 'par_131050': 'PAJÁN (cabecera cantonal)',
 'par_131051': 'CAMPOZANO',
 'par_131052': 'CASCOL',
 'par_131053': 'GUALE',
 'par_131054': 'LASCANO',
 'par_131150': 'PICHINCHA (cabecera cantonal)',
 'par_131151': 'BARRAGANETE',
 'par_131152': 'SAN SEBASTIÁN',
 'par_131250': 'ROCAFUERTE (cabecera cantonal)',
 'par_131251': 'SOSOTE',
 'par_131301': 'SANTA ANA',
 'par_131302': 'LODANA',
 'par_131350': 'SANTA ANA DE VUELTA LARGA (cabecera cantonal)',
 'par_131351': 'AYACUCHO',
 'par_131352': 'HONORATO VÁSQUEZ (CAB. EN VÁSQUEZ)',
 'par_131353': 'LA UNIÓN',
 'par_131354': 'OLMEDO',
 'par_131355': 'SAN PABLO (CAB. EN PUEBLO NUEVO)',
 'par_131401': 'BAHÍA DE CARÁQUEZ',
 'par_131402': 'LEONIDAS PLAZA GUTIÉRREZ',
 'par_131450': 'BAHÍA DE CARÁQUEZ (cabecera cantonal)',
 'par_131451': 'CANOA',
 'par_131452': 'COJIMÍES',
 'par_131453': 'CHARAPOTÓ',
 'par_131454': '10 DE AGOSTO',
 'par_131455': 'JAMA',
 'par_131456': 'PEDERNALES',
 'par_131457': 'SAN ISIDRO',
 'par_131458': 'SAN VICENTE',
 'par_131550': 'TOSAGUA (cabecera cantonal)',
 'par_131551': 'BACHILLERO',
 'par_131552': 'ÁNGEL PEDRO GILER',
 'par_131650': 'SUCRE (cabecera cantonal)',
 'par_131651': 'BELLAVISTA',
 'par_131652': 'NOBOA',
 'par_131653': 'ARQUITECTO SIXTO DURÁN BALLÉN (CAB. EN',
 'par_131750': 'PEDERNALES (cabecera cantonal)',
 'par_131751': 'COJIMÍES',
 'par_131752': 'DIEZ DE AGOSTO',
 'par_131753': 'ATAHUALPA',
 'par_131850': 'OLMEDO (cabecera cantonal)',
 'par_131950': 'PUERTO LÓPEZ (cabecera cantonal)',
 'par_131951': 'MACHALILLA',
 'par_131952': 'SALANGO',
 'par_132050': 'JAMA (cabecera cantonal)',
 'par_132150': 'JARAMIJÓ (cabecera cantonal)',
 'par_132250': 'SAN VICENTE (cabecera cantonal)',
 'par_132251': 'CANOA',
 'par_140150': 'MACAS (cabecera cantonal y capital provincial)',
 'par_140151': 'ALSHI (CAB. EN NUEVE DE OCTUBRE)',
 'par_140152': 'CHIGUAZA',
 'par_140153': 'GENERAL PROAÑO (CAB. EN BARAHONA)',
 'par_140154': 'HUASAGA (CAB.EN WAMPUIK)',
 'par_140155': 'MACUMA',
 'par_140156': 'SAN ISIDRO',
 'par_140157': 'SEVILLA DON BOSCO',
 'par_140158': 'SINAÍ',
 'par_140159': 'TAISHA',
 'par_140160': 'ZUÑA',
 'par_140161': 'TUUTINENTZA',
 'par_140162': 'CUCHAENTZA',
 'par_140163': 'SAN JOSÉ DE MORONA',
 'par_140164': 'RÍO BLANCO',
 'par_140201': 'GUALAQUIZA',
 'par_140202': 'MERCEDES MOLINA',
 'par_140250': 'GUALAQUIZA (cabecera cantonal)',
 'par_140251': 'AMAZONAS',
 'par_140252': 'BERMEJOS',
 'par_140253': 'BOMBOÍZA',
 'par_140254': 'CHIGÜINDA',
 'par_140255': 'EL ROSARIO',
 'par_140256': 'NUEVA TARQUI',
 'par_140257': 'SAN MIGUEL DE CUYES',
 'par_140258': 'EL IDEAL',
 'par_140350': 'GENERAL LEONIDAS PLAZA GUTIÉRREZ (cabecera cantonal)',
 'par_140351': 'INDANZA',
 'par_140352': 'PAN DE AZÚCAR',
 'par_140353': 'SAN ANTONIO (CAB. EN SAN ANTONIO CENTRO)',
 'par_140354': 'SAN CARLOS DE LIMÓN (SAN CARLOS DEL ZAMORA)',
 'par_140355': 'SAN JUAN BOSCO',
 'par_140356': 'SAN MIGUEL DE CONCHAY',
 'par_140357': 'SANTA SUSANA DE CHIVIAZA (CAB. EN CHIVIAZA)',
 'par_140358': 'YUNGANZA (CAB. EN EL ROSARIO)',
 'par_140450': 'PALORA (METZERA) (cabecera cantonal)',
 'par_140451': 'ARAPICOS',
 'par_140452': 'CUMANDÁ (CAB. EN COLONIA AGRÍCOLA SEVILLA DE ORO)',
 'par_140453': 'HUAMBOYA',
 'par_140454': 'SANGAY (CAB. EN NAYAMANACA)',
 'par_140455': '16 DE AGOSTO',
 'par_140550': 'SANTIAGO DE MÉNDEZ (cabecera cantonal)',
 'par_140551': 'COPAL',
 'par_140552': 'CHUPIANZA',
 'par_140553': 'PATUCA',
 'par_140554': 'SAN LUIS DE EL ACHO (CAB. EN EL ACHO)',
 'par_140555': 'SANTIAGO',
 'par_140556': 'TAYUZA',
 'par_140557': 'SAN FRANCISCO DE CHINIMBIMI (CAB. EN',
 'par_140650': 'SUCÚA (cabecera cantonal)',
 'par_140651': 'ASUNCIÓN',
 'par_140652': 'HUAMBI',
 'par_140653': 'LOGROÑO',
 'par_140654': 'YAUPI',
 'par_140655': 'SANTA MARIANITA DE JESÚS (CAB. EN SANTA',
 'par_140750': 'HUAMBOYA (cabecera cantonal)',
 'par_140751': 'CHIGUAZA',
 'par_140752': 'PABLO SEXTO',
 'par_140850': 'SAN JUAN BOSCO (cabecera cantonal)',
 'par_140851': 'PAN DE AZÚCAR',
 'par_140852': 'SAN CARLOS DE LIMÓN',
 'par_140853': 'SAN JACINTO DE WAKAMBEIS (CAB. EN WAKAMBEIS)',
 'par_140854': 'SANTIAGO DE PANANZA',
 'par_140950': 'TAISHA (cabecera cantonal)',
 'par_140951': 'HUASAGA (CAB. EN WAMPUIK)',
 'par_140952': 'MACUMA',
 'par_140953': 'TUUTINENTSA',
 'par_140954': 'PUMPUENTSA',
 'par_141050': 'LOGROÑO (cabecera cantonal)',
 'par_141051': 'YAUPI',
 'par_141052': 'SHIMPIS',
 'par_141150': 'PABLO SEXTO (cabecera cantonal)',
 'par_141250': 'SANTIAGO (cabecera cantonal)',
 'par_141251': 'SAN JOSÉ DE MORONA',
 'par_141350': 'SEVILLA DON BOSCO',
 'par_150150': 'TENA (cabecera cantonal y capital provincial)',
 'par_150151': 'AHUANO',
 'par_150152': 'CARLOS JULIO AROSEMENA TOLA (ZATZA-YACU)',
 'par_150153': 'CHONTAPUNTA',
 'par_150154': 'PANO',
 'par_150155': 'PUERTO MISAHUALLÍ',
 'par_150156': 'PUERTO NAPO',
 'par_150157': 'TÁLAG',
 'par_150158': 'SAN JUAN DE MUYUNA',
 'par_150350': 'ARCHIDONA (cabecera cantonal)',
 'par_150351': 'ÁVILA',
 'par_150352': 'COTUNDO',
 'par_150353': 'LORETO',
 'par_150354': 'SAN PABLO DE USHPAYACU',
 'par_150355': 'PUERTO MURIALDO',
 'par_150356': 'HATUN SUMAKU (CAB. EN DIEZ DE AGOSTO)',
 'par_150450': 'EL CHACO (cabecera cantonal)',
 'par_150451': 'GONZALO DÍAZ DE PINEDA',
 'par_150452': 'LINARES',
 'par_150453': 'OYACACHI',
 'par_150454': 'SANTA ROSA',
 'par_150455': 'SARDINAS',
 'par_150750': 'BAEZA (cabecera cantonal)',
 'par_150751': 'COSANGA',
 'par_150752': 'CUYUJA',
 'par_150753': 'PAPALLACTA',
 'par_150754': 'SAN FRANCISCO DE BORJA',
 'par_150755': 'SAN JOSÉ DEL PAYAMINO',
 'par_150756': 'SUMACO',
 'par_150950': 'CARLOS JULIO AROSEMENA TOLA (cabecera cantonal)',
 'par_160150': 'PUYO (cabecera cantonal y capital provincial)',
 'par_160151': 'ARAJUNO',
 'par_160152': 'CANELOS',
 'par_160153': 'CURARAY',
 'par_160154': 'DIEZ DE AGOSTO',
 'par_160155': 'FÁTIMA',
 'par_160156': 'MONTALVO',
 'par_160157': 'POMONA',
 'par_160158': 'RÍO CORRIENTES',
 'par_160159': 'RÍO TIGRE',
 'par_160160': 'SANTA CLARA',
 'par_160161': 'SARAYACU',
 'par_160162': 'SIMÓN BOLÍVAR (CAB. EN MUSHULLACTA)',
 'par_160163': 'TARQUI',
 'par_160164': 'TENIENTE HUGO ORTIZ',
 'par_160165': 'VERACRUZ (CAB. EN INDILLAMA)',
 'par_160166': 'EL TRIUNFO',
 'par_160250': 'MERA (cabecera cantonal)',
 'par_160251': 'MADRE TIERRA',
 'par_160252': 'SHELL',
 'par_160350': 'SANTA CLARA (cabecera cantonal)',
 'par_160351': 'SAN JOSÉ',
 'par_160450': 'ARAJUNO (cabecera cantonal)',
 'par_160451': 'CURARAY',
 'par_170101': 'BELISARIO QUEVEDO',
 'par_170102': 'CARCELÉN',
 'par_170103': 'CENTRO HISTÓRICO',
 'par_170104': 'COCHAPAMBA',
 'par_170105': 'COMITÉ DEL PUEBLO',
 'par_170106': 'COTOCOLLAO',
 'par_170107': 'CHILIBULO',
 'par_170108': 'CHILLOGALLO',
 'par_170109': 'CHIMBACALLE',
 'par_170110': 'EL CONDADO',
 'par_170111': 'GUAMANÍ',
 'par_170112': 'IÑAQUITO',
 'par_170113': 'ITCHIMBÍA',
 'par_170114': 'JIPIJAPA',
 'par_170115': 'KENNEDY',
 'par_170116': 'LA ARGELIA',
 'par_170117': 'LA CONCEPCIÓN',
 'par_170118': 'LA ECUATORIANA',
 'par_170119': 'LA FERROVIARIA',
 'par_170120': 'LA LIBERTAD',
 'par_170121': 'LA MAGDALENA',
 'par_170122': 'LA MENA',
 'par_170123': 'MARISCAL SUCRE',
 'par_170124': 'PONCEANO',
 'par_170125': 'PUENGASÍ',
 'par_170126': 'QUITUMBE',
 'par_170127': 'RUMIPAMBA',
 'par_170128': 'SAN BARTOLO',
 'par_170129': 'SAN ISIDRO DEL INCA',
 'par_170130': 'SAN JUAN',
 'par_170131': 'SOLANDA',
 'par_170132': 'TURUBAMBA',
 'par_170150': 'QUITO (cabecera cantonal y capital provincial)',
 'par_170151': 'ALANGASÍ',
 'par_170152': 'AMAGUAÑA',
 'par_170153': 'ATAHUALPA',
 'par_170154': 'CALACALÍ',
 'par_170155': 'CALDERÓN',
 'par_170156': 'CONOCOTO',
 'par_170157': 'CUMBAYÁ',
 'par_170158': 'CHAVEZPAMBA',
 'par_170159': 'CHECA',
 'par_170160': 'EL QUINCHE',
 'par_170161': 'GUALEA',
 'par_170162': 'GUANGOPOLO',
 'par_170163': 'GUAYLLABAMBA',
 'par_170164': 'LA MERCED',
 'par_170165': 'LLANO CHICO',
 'par_170166': 'LLOA',
 'par_170167': 'MINDO',
 'par_170168': 'NANEGAL',
 'par_170169': 'NANEGALITO',
 'par_170170': 'NAYÓN',
 'par_170171': 'NONO',
 'par_170172': 'PACTO',
 'par_170173': 'PEDRO VICENTE MALDONADO',
 'par_170174': 'PERUCHO',
 'par_170175': 'PIFO',
 'par_170176': 'PÍNTAG',
 'par_170177': 'POMASQUI',
 'par_170178': 'PUÉLLARO',
 'par_170179': 'PUEMBO',
 'par_170180': 'SAN ANTONIO',
 'par_170181': 'SAN JOSÉ DE MINAS',
 'par_170182': 'SAN MIGUEL DE LOS BANCOS',
 'par_170183': 'TABABELA',
 'par_170184': 'TUMBACO',
 'par_170185': 'YARUQUÍ',
 'par_170186': 'ZÁMBIZA',
 'par_170187': 'PUERTO QUITO',
 'par_170201': 'AYORA',
 'par_170202': 'CAYAMBE',
 'par_170203': 'JUAN MONTALVO [001]',
 'par_170250': 'CAYAMBE (cabecera cantonal)',
 'par_170251': 'ASCÁZUBI',
 'par_170252': 'CANGAHUA',
 'par_170253': 'OLMEDO',
 'par_170254': 'OTÓN',
 'par_170255': 'SANTA ROSA DE CUZUBAMBA',
 'par_170256': 'SAN JOSÉ DE AYORA',
 'par_170257': 'JUAN MONTALVO [002]',
 'par_170350': 'MACHACHI (cabecera cantonal)',
 'par_170351': 'ALOAG',
 'par_170352': 'ALOASÍ',
 'par_170353': 'CUTUGLAHUA',
 'par_170354': 'EL CHAUPI',
 'par_170355': 'MANUEL CORNEJO ASTORGA',
 'par_170356': 'TAMBILLO',
 'par_170357': 'UYUMBICHO',
 'par_170450': 'TABACUNDO (cabecera cantonal)',
 'par_170451': 'LA ESPERANZA',
 'par_170452': 'MALCHINGUÍ',
 'par_170453': 'TOCACHI',
 'par_170454': 'TUPIGACHI',
 'par_170501': 'SANGOLQUÍ',
 'par_170502': 'SAN PEDRO DE TABOADA',
 'par_170503': 'SAN RAFAEL',
 'par_170504': 'FAJARDO',
 'par_170550': 'SANGOLQUÍ (cabecera cantonal)',
 'par_170551': 'COTOGCHOA',
 'par_170552': 'RUMIPAMBA',
 'par_170750': 'SAN MIGUEL DE LOS BANCOS (cabecera cantonal)',
 'par_170751': 'MINDO',
 'par_170752': 'PEDRO VICENTE MALDONADO',
 'par_170753': 'PUERTO QUITO',
 'par_170850': 'PEDRO VICENTE MALDONADO (cabecera cantonal)',
 'par_170950': 'PUERTO QUITO (cabecera cantonal)',
 'par_180101': 'ATOCHA – FICOA',
 'par_180102': 'CELIANO MONGE',
 'par_180103': 'HUACHI CHICO',
 'par_180104': 'HUACHI LORETO',
 'par_180105': 'LA MERCED',
 'par_180106': 'LA PENÍNSULA',
 'par_180107': 'MATRIZ',
 'par_180108': 'PISHILATA',
 'par_180109': 'SAN FRANCISCO',
 'par_180150': 'AMBATO (cabecera cantonal y capital provincial)',
 'par_180151': 'AMBATILLO',
 'par_180152': 'ATAHUALPA (CAB. EN CHISALATA)',
 'par_180153': 'AUGUSTO N. MARTÍNEZ',
 'par_180154': 'CONSTANTINO FERNÁNDEZ (CAB. EN CULLITAHUA)',
 'par_180155': 'HUACHI GRANDE',
 'par_180156': 'IZAMBA',
 'par_180157': 'JUAN BENIGNO VELA',
 'par_180158': 'MONTALVO',
 'par_180159': 'PASA',
 'par_180160': 'PICAIHUA',
 'par_180161': 'PILAGÜÍN',
 'par_180162': 'QUISAPINCHA',
 'par_180163': 'SAN BARTOLOMÉ DE PINLLO',
 'par_180164': 'SAN FERNANDO',
 'par_180165': 'SANTA ROSA',
 'par_180166': 'TOTORAS',
 'par_180167': 'CUNCHIBAMBA',
 'par_180168': 'UNAMUNCHO',
 'par_180250': 'BAÑOS (cabecera cantonal)',
 'par_180251': 'LLIGUA',
 'par_180252': 'RÍO NEGRO',
 'par_180253': 'RÍO VERDE',
 'par_180254': 'ULBA',
 'par_180350': 'CEVALLOS (cabecera cantonal)',
 'par_180450': 'MOCHA (cabecera cantonal)',
 'par_180451': 'PINGUILÍ',
 'par_180550': 'PATATE (cabecera cantonal)',
 'par_180551': 'EL TRIUNFO',
 'par_180552': 'LOS ANDES (CAB. EN POATUG)',
 'par_180553': 'SUCRE (CAB. EN SUCRE PATATE-URCU)',
 'par_180650': 'QUERO (cabecera cantonal)',
 'par_180651': 'RUMIPAMBA',
 'par_180652': 'YANAYACU-MOCHAPATA (CAB. EN YANAYACU)',
 'par_180701': 'PELILEO',
 'par_180702': 'PELILEO GRANDE',
 'par_180750': 'PELILEO (cabecera cantonal)',
 'par_180751': 'BENÍTEZ',
 'par_180752': 'BOLÍVAR',
 'par_180753': 'COTALÓ',
 'par_180754': 'CHIQUICHA (CAB. EN CHIQUICHA GRANDE)',
 'par_180755': 'EL ROSARIO',
 'par_180756': 'GARCÍA MORENO',
 'par_180757': 'GUAMBALÓ',
 'par_180758': 'SALASACA',
 'par_180801': 'CIUDAD NUEVA',
 'par_180802': 'PÍLLARO',
 'par_180850': 'PÍLLARO (cabecera cantonal)',
 'par_180851': 'BAQUERIZO MORENO',
 'par_180852': 'EMILIO MARÍA TERÁN',
 'par_180853': 'MARCOS ESPINEL',
 'par_180854': 'PRESIDENTE URBINA',
 'par_180855': 'SAN ANDRÉS',
 'par_180856': 'SAN JOSÉ DE POALÓ',
 'par_180857': 'SAN MIGUELITO',
 'par_180950': 'TISALEO (cabecera cantonal)',
 'par_180951': 'QUINCHICOTO',
 'par_190101': 'EL LIMÓN',
 'par_190102': 'ZAMORA',
 'par_190150': 'ZAMORA (cabecera cantonal y capital provincial)',
 'par_190151': 'CUMBARATZA',
 'par_190152': 'GUADALUPE',
 'par_190153': 'IMBANA (CAB. EN LA VICTORIA DE IMBANA)',
 'par_190154': 'PAQUISHA',
 'par_190155': 'SABANILLA',
 'par_190156': 'TIMBARA',
 'par_190157': 'ZUMBI',
 'par_190158': 'SAN CARLOS DE LAS MINAS',
 'par_190250': 'ZUMBA (cabecera cantonal)',
 'par_190251': 'CHITO',
 'par_190252': 'EL CHORRO',
 'par_190253': 'EL PORVENIR DEL CARMEN',
 'par_190254': 'LA CHONTA',
 'par_190255': 'PALANDA',
 'par_190256': 'PUCAPAMBA',
 'par_190257': 'SAN FRANCISCO DEL VERGEL',
 'par_190258': 'VALLADOLID',
 'par_190259': 'SAN ANDRÉS',
 'par_190350': 'GUAYZIMI (cabecera cantonal)',
 'par_190351': 'ZURMI',
 'par_190352': 'NUEVO PARAÍSO',
 'par_190353': 'NANKAIS (CAB. EN TSARUNTS (SANTA ELENA))',
 'par_190450': '28 DE MAYO (cabecera cantonal)',
 'par_190451': 'LA PAZ',
 'par_190452': 'TUTUPALI',
 'par_190550': 'YANTZAZA (cabecera cantonal)',
 'par_190551': 'CHICAÑA',
 'par_190552': 'EL PANGUI',
 'par_190553': 'LOS ENCUENTROS',
 'par_190650': 'EL PANGUI (cabecera cantonal)',
 'par_190651': 'EL GUISME',
 'par_190652': 'PACHICUTZA',
 'par_190653': 'TUNDAYME',
 'par_190750': 'ZUMBI (cabecera cantonal)',
 'par_190751': 'PAQUISHA',
 'par_190752': 'TRIUNFO DORADO (CAB. EN EL DORADO)',
 'par_190753': 'PANGUINTZA',
 'par_190850': 'PALANDA (cabecera cantonal)',
 'par_190851': 'EL PORVENIR DEL CARMEN',
 'par_190852': 'SAN FRANCISCO DEL VERGEL',
 'par_190853': 'VALLADOLID',
 'par_190854': 'LA CANELA',
 'par_190950': 'PAQUISHA (cabecera cantonal)',
 'par_190951': 'BELLAVISTA',
 'par_190952': 'NUEVO QUITO',
 'par_200150': 'PUERTO BAQUERIZO MORENO (cabecera cantonal y capital provincial)',
 'par_200151': 'EL PROGRESO',
 'par_200152': 'ISLA SANTA MARÍA FLOREANA (CAB. EN PUERTO VELASCO IBARRA)',
 'par_200250': 'PUERTO VILLAMIL (cabecera cantonal)',
 'par_200251': 'TOMÁS DE BERLANGA',
 'par_200350': 'PUERTO AYORA (cabecera cantonal)',
 'par_200351': 'BELLA VISTA',
 'par_200352': 'SANTA ROSA',
 'par_210150': 'NUEVA LOJA (cabecera cantonal y capital provincial)',
 'par_210151': 'CUYABENO',
 'par_210152': 'DURENO',
 'par_210153': 'GENERAL FARFÁN',
 'par_210154': 'TARAPOA',
 'par_210155': 'EL ENO',
 'par_210156': 'PACAYACU',
 'par_210157': 'JAMBELÍ',
 'par_210158': 'SANTA CECILIA',
 'par_210159': 'AGUAS NEGRAS',
 'par_210160': '10 DE AGOSTO',
 'par_210250': 'LUMBAQUÍ (cabecera cantonal)',
 'par_210251': 'EL REVENTADOR',
 'par_210252': 'GONZALO PIZARRO',
 'par_210253': 'LUMBAQUÍ',
 'par_210254': 'PUERTO LIBRE',
 'par_210255': 'SANTA ROSA DE SUCUMBÍOS',
 'par_210350': 'PUERTO EL CARMEN DEL PUTUMAYO (cabecera cantonal)',
 'par_210351': 'PALMA ROJA',
 'par_210352': 'PUERTO BOLÍVAR',
 'par_210353': 'PUERTO RODRÍGUEZ',
 'par_210354': 'SANTA ELENA',
 'par_210355': 'SANSAHUARI',
 'par_210450': 'SHUSHUFINDI (cabecera cantonal)',
 'par_210451': 'LIMONCOCHA',
 'par_210452': 'PAÑACOCHA',
 'par_210453': 'SAN ROQUE (CAB. EN SAN VICENTE)',
 'par_210454': 'SAN PEDRO DE LOS COFÁNES',
 'par_210455': 'SIETE DE JULIO',
 'par_210456': 'LA MAGDALENA',
 'par_210457': 'LA PRIMAVERA',
 'par_210550': 'LA BONITA (cabecera cantonal)',
 'par_210551': 'EL PLAYÓN DE SAN FRANCISCO',
 'par_210552': 'LA SOFÍA',
 'par_210553': 'ROSA FLORIDA',
 'par_210554': 'SANTA BÁRBARA',
 'par_210650': 'EL DORADO DE CASCALES (cabecera cantonal)',
 'par_210651': 'SANTA ROSA DE SUCUMBÍOS',
 'par_210652': 'SEVILLA',
 'par_210653': 'NUEVA TRONCAL (CAB. EN LA TRONCAL)',
 'par_210750': 'TARAPOA (cabecera cantonal)',
 'par_210751': 'CUYABENO',
 'par_210752': 'AGUAS NEGRAS',
 'par_220150': 'EL COCA (PUERTO FRANCISCO DE ORELLANA) (cabecera cantonal y capital provincial)',
 'par_220151': 'DAYUMA',
 'par_220152': 'TARACOA',
 'par_220153': 'ALEJANDRO LABAKA',
 'par_220154': 'EL DORADO',
 'par_220155': 'EL EDÉN',
 'par_220156': 'GARCÍA MORENO',
 'par_220157': 'INÉS ARANGO (CAB. EN WESTERN)',
 'par_220158': 'LA BELLEZA',
 'par_220159': 'NUEVO PARAÍSO (CAB. EN UNIÓN',
 'par_220160': 'SAN JOSÉ DE GUAYUSA',
 'par_220161': 'SAN LUIS DE ARMENIA',
 'par_220201': 'NUEVO ROCAFUERTE',
 'par_220202': 'TIPUTINI [001]',
 'par_220250': 'NUEVO ROCAFUERTE (cabecera cantonal)',
 'par_220251': 'CAPITÁN AUGUSTO RIVADENEYRA',
 'par_220252': 'CONONACO',
 'par_220253': 'SANTA MARÍA DE HUIRIRIMA',
 'par_220254': 'TIPUTINI [002]',
 'par_220255': 'YASUNÍ',
 'par_220350': 'LA JOYA DE LOS SACHAS (cabecera cantonal)',
 'par_220351': 'ENOKANQUI (CAB. EN EL PARAÍSO)',
 'par_220352': 'POMPEYA',
 'par_220353': 'SAN CARLOS',
 'par_220354': 'SAN SEBASTIÁN DEL COCA',
 'par_220355': 'LAGO SAN PEDRO',
 'par_220356': 'RUMIPAMBA',
 'par_220357': 'TRES DE NOVIEMBRE',
 'par_220358': 'UNIÓN MILAGREÑA',
 'par_220450': 'LORETO (cabecera cantonal)',
 'par_220451': 'ÁVILA (CAB. EN HUIRUNO)',
 'par_220452': 'PUERTO MURIALDO',
 'par_220453': 'SAN JOSÉ DE PAYAMINO',
 'par_220454': 'SAN JOSÉ DE DAHUANO',
 'par_220455': 'SAN VICENTE DE HUATICOCHA',
 'par_230101': 'ABRAHAM CALAZACÓN',
 'par_230102': 'BOMBOLÍ',
 'par_230103': 'CHIGUILPE',
 'par_230104': 'RÍO TOACHI',
 'par_230105': 'RÍO VERDE',
 'par_230106': 'SANTO DOMINGO DE LOS COLORADOS',
 'par_230107': 'ZARACAY',
 'par_230150': 'SANTO DOMINGO DE LOS COLORADOS (cabecera cantonal y capital provincial)',
 'par_230151': 'ALLURIQUÍN',
 'par_230152': 'PUERTO LIMÓN',
 'par_230153': 'LUZ DE AMÉRICA',
 'par_230154': 'SAN JACINTO DEL BÚA',
 'par_230155': 'VALLE HERMOSO',
 'par_230156': 'EL ESFUERZO',
 'par_230157': 'SANTA MARÍA DEL TOACHI',
 'par_230250': 'LA CONCORDIA (cabecera cantonal)',
 'par_230251': 'MONTERREY',
 'par_230252': 'LA VILLEGAS',
 'par_230253': 'PLAN PILOTO',
 'par_240101': 'BALLENITA',
 'par_240102': 'SANTA ELENA',
 'par_240150': 'SANTA ELENA (cabecera cantonal y capital provincial)',
 'par_240151': 'ATAHUALPA',
 'par_240152': 'COLONCHE',
 'par_240153': 'CHANDUY',
 'par_240154': 'MANGLARALTO',
 'par_240155': 'SIMÓN BOLÍVAR',
 'par_240156': 'SAN JOSÉ DE ANCÓN',
 'par_240250': 'LA LIBERTAD (cabecera cantonal)',
 'par_240301': 'CARLOS ESPINOZA LARREA',
 'par_240302': 'GENERAL ALBERTO ENRÍQUEZ GALLO',
 'par_240303': 'VICENTE ROCAFUERTE',
 'par_240304': 'SANTA ROSA',
 'par_240350': 'SALINAS (cabecera cantonal)',
 'par_240351': 'ANCONCITO',
 'par_240352': 'JOSÉ LUIS TAMAYO',
 'prov_01': 'AZUAY',
 'prov_02': 'BOLÍVAR',
 'prov_03': 'CAÑAR',
 'prov_04': 'CARCHI',
 'prov_05': 'COTOPAXI',
 'prov_06': 'CHIMBORAZO',
 'prov_07': 'EL ORO',
 'prov_08': 'ESMERALDAS',
 'prov_09': 'GUAYAS',
 'prov_10': 'IMBABURA',
 'prov_11': 'LOJA',
 'prov_12': 'LOS RÍOS',
 'prov_13': 'MANABÍ',
 'prov_14': 'MORONA SANTIAGO',
 'prov_15': 'NAPO',
 'prov_16': 'PASTAZA',
 'prov_17': 'PICHINCHA',
 'prov_18': 'TUNGURAHUA',
 'prov_19': 'ZAMORA CHINCHIPE',
 'prov_20': 'GALÁPAGOS',
 'prov_21': 'SUCUMBÍOS',
 'prov_22': 'ORELLANA',
 'prov_23': 'SANTO DOMINGO DE LOS TSÁCHILAS',
 'prov_24': 'SANTA ELENA'}

_GEO_SMALL_WORDS = {"de", "del", "la", "las", "los", "el", "y"}


def _format_geo_label(label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return ""
    words = text.lower().split()
    pretty = []
    for idx, word in enumerate(words):
        if idx > 0 and word in _GEO_SMALL_WORDS:
            pretty.append(word)
        else:
            pretty.append(word[:1].upper() + word[1:])
    return " ".join(pretty)


def geo_choice_label(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    raw = str(value).strip()
    if not raw:
        return ""
    label = GEO_CHOICE_LABELS.get(raw)
    return _format_geo_label(label) if label else raw

def public_css() -> None:
    st.markdown(
        """
        <style>
        .tv-public-intro {
            margin-bottom: 0.7rem;
        }
        .tv-public-intro h2 {
            margin-bottom: 0.15rem;
            color: #221a4f;
            font-size: 2rem;
            font-weight: 750;
        }
        .tv-public-intro p {
            color: #667085;
            font-size: 1rem;
            margin-top: 0;
        }
        .tv-kpi {
            background: #ffffff;
            border: 1px solid #eceaf5;
            border-radius: 16px;
            padding: 16px 18px;
            min-height: 128px;
            box-shadow: 0 3px 12px rgba(25, 18, 60, 0.05);
        }
        .tv-kpi-label {
            font-size: 0.86rem;
            color: #62677a;
            font-weight: 600;
            min-height: 40px;
        }
        .tv-kpi-value {
            font-size: 2rem;
            line-height: 1.05;
            font-weight: 800;
            color: #6639b7;
            margin-top: 6px;
        }
        .tv-kpi-detail {
            font-size: 0.78rem;
            color: #8b8fa0;
            margin-top: 6px;
        }
        .tv-card {
            background: #ffffff;
            border: 1px solid #eceaf5;
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 3px 12px rgba(25, 18, 60, 0.045);
            height: 100%;
        }
        .tv-card-title {
            color: #21194d;
            font-size: 1.05rem;
            font-weight: 750;
            margin-bottom: 10px;
        }
        .tv-level {
            display: inline-block;
            padding: 8px 14px;
            border-radius: 11px;
            background: #f2ebff;
            color: #6639b7;
            font-weight: 750;
            margin-bottom: 8px;
        }
        .tv-finding {
            padding: 5px 0;
            color: #505668;
            line-height: 1.45;
            font-size: 0.93rem;
        }
        .tv-finding-dot {
            color: #7144c6;
            font-weight: 900;
            padding-right: 7px;
        }
        .tv-rank-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 9px 2px;
            border-bottom: 1px solid #f0eef6;
            color: #424758;
        }
        .tv-rank-number {
            display: inline-flex;
            width: 24px;
            height: 24px;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: #7046c3;
            color: white;
            font-size: 0.75rem;
            font-weight: 700;
            margin-right: 8px;
        }
        .tv-section-caption {
            color: #777c8d;
            font-size: 0.88rem;
            margin-top: -5px;
            margin-bottom: 8px;
        }
        .tv-footer {
            margin-top: 14px;
            padding: 12px 16px;
            background: #f7f3ff;
            color: #6c6680;
            border-radius: 12px;
            font-size: 0.82rem;
            text-align: center;
        }
        div[data-testid="stMetric"] {
            background-color: transparent;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def normalize_province_name(value: Any) -> str:
    """Normaliza provincia tanto desde etiquetas como desde valores XML de KOBO.

    La exportación recomendada usa valores XML, por ejemplo ``prov_01`` (Azuay)
    y ``prov_03`` (Cañar). También se conserva compatibilidad con nombres y
    códigos numéricos INEC.
    """
    if value is None or pd.isna(value):
        return ""

    text = norm_text(value)
    if not text:
        return ""

    aliases = {
        "santo domingo": "santo domingo de los tsachilas",
        "sto domingo": "santo domingo de los tsachilas",
        "santo domingo tsachilas": "santo domingo de los tsachilas",
        "zamora": "zamora chinchipe",
        "morona": "morona santiago",
    }

    # Nombres oficiales o etiquetas completas.
    for province in ECUADOR_PROVINCES:
        if province in text:
            return province

    for alias, province in aliases.items():
        if alias in text:
            return province

    code_map = {
        1: "azuay",
        2: "bolivar",
        3: "canar",
        4: "carchi",
        5: "cotopaxi",
        6: "chimborazo",
        7: "el oro",
        8: "esmeraldas",
        9: "guayas",
        10: "imbabura",
        11: "loja",
        12: "los rios",
        13: "manabi",
        14: "morona santiago",
        15: "napo",
        16: "pastaza",
        17: "pichincha",
        18: "tungurahua",
        19: "zamora chinchipe",
        20: "galapagos",
        21: "sucumbios",
        22: "orellana",
        23: "santo domingo de los tsachilas",
        24: "santa elena",
    }

    # Valores XML actuales: prov_01, prov-01, prov01.
    xml_match = re.fullmatch(r"prov(?:incia)?[_\-\s]?0?([1-9]|1[0-9]|2[0-4])", text)
    if xml_match:
        return code_map.get(int(xml_match.group(1)), "")

    # Código numérico 01-24.
    code_match = re.fullmatch(r"0?([1-9]|1[0-9]|2[0-4])", text)
    if code_match:
        return code_map.get(int(code_match.group(1)), "")

    return ""

def detect_province_column(df: pd.DataFrame) -> str | None:
    """Detecta provincia en una tabla normal o en un repeat ya aplanado."""
    if df.empty:
        return None

    preferred = get_secret("PROVINCE_COLUMN", "")
    if preferred:
        found = find_column(df, preferred, [])
        if found:
            return found

    # Nombres técnicos del XLSForm primero.
    for field_name in ["provincia_operacion", "provincia_operación", "provincia"]:
        found = find_field_column(df, field_name)
        if found:
            return found

    candidates = []
    for col in df.columns:
        col_norm = norm_text(col)
        if "provincia" not in col_norm:
            continue
        sample = df[col].dropna().head(80)
        valid = sum(bool(normalize_province_name(v)) for v in sample)
        candidates.append((valid, col))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        if candidates[0][0] > 0:
            return candidates[0][1]

    return None


def detect_repeat_province_column(df: pd.DataFrame) -> str | None:
    """Prioriza específicamente ``provincia_operacion`` dentro de hojas repeat."""
    if df.empty:
        return None

    for field_name in ["provincia_operacion", "provincia_operación"]:
        found = find_field_column(df, field_name)
        if found:
            return found

    return detect_province_column(df)


def _find_id_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    if df.empty:
        return None
    wanted = {norm_id(c) for c in candidates}
    for col in df.columns:
        if norm_id(col) in wanted:
            return col
    return None


def filter_repeat_to_public_records(repeat_df: pd.DataFrame, public_df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    """Filtra un repeat a las observaciones públicas más recientes cuando KOBO exporta llaves padre.

    Si no se encuentra una relación inequívoca se conserva el repeat completo; esto
    permite seguir mostrando cobertura sin perder datos en variantes de exportación.
    Devuelve además la columna que identifica al padre, útil para no contar dos
    localidades de la misma empresa en una misma provincia.
    """
    if repeat_df.empty or public_df.empty:
        return repeat_df.copy(), None

    key_pairs = [
        (["_parent_index", "parent_index"], ["_index", "index"]),
        (["parent_key", "_parent_key", "PARENT_KEY"], ["key", "KEY"]),
        (["_parent_uuid", "parent_uuid"], ["_uuid", "uuid"]),
        (["_parent_id", "parent_id"], ["_id", "id"]),
    ]

    for repeat_candidates, main_candidates in key_pairs:
        repeat_key = _find_id_column(repeat_df, repeat_candidates)
        main_key = _find_id_column(public_df, main_candidates)
        if not repeat_key or not main_key:
            continue

        allowed = {
            str(v).strip()
            for v in public_df[main_key].dropna()
            if str(v).strip()
        }
        if not allowed:
            continue

        filtered = repeat_df[
            repeat_df[repeat_key].astype(str).str.strip().isin(allowed)
        ].copy()

        # Si la relación existe pero no devuelve filas, no se fuerza un repeat vacío:
        # otra variante de exportación puede usar índices de distinto tipo.
        if not filtered.empty:
            return filtered, repeat_key

    # Intento adicional para _parent_index numérico vs _index exportado como "1.0".
    repeat_key = _find_id_column(repeat_df, ["_parent_index", "parent_index"])
    main_key = _find_id_column(public_df, ["_index", "index"])
    if repeat_key and main_key:
        main_numeric = pd.to_numeric(public_df[main_key], errors="coerce").dropna()
        repeat_numeric = pd.to_numeric(repeat_df[repeat_key], errors="coerce")
        if not main_numeric.empty:
            filtered = repeat_df[repeat_numeric.isin(set(main_numeric.tolist()))].copy()
            if not filtered.empty:
                return filtered, repeat_key

    return repeat_df.copy(), None


def province_counts_from_repeat_sheets(
    repeat_sheets: dict[str, pd.DataFrame],
    public_df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    """Construye cobertura provincial a partir de todos los repeats de KOBO.

    Busca hojas que contengan ``provincia_operacion``. Cuando existe una llave de
    relación padre, cuenta una sola vez cada provincia por encuesta/empresa aun si
    se registraron varias localidades dentro de la misma provincia.
    """
    empty = pd.DataFrame(columns=["province_key", "Provincia", "Registros", "lat", "lon"])
    if not repeat_sheets:
        return empty, []

    rows: list[pd.DataFrame] = []
    used_sheets: list[str] = []

    for sheet_name, sheet_df in repeat_sheets.items():
        if sheet_df.empty:
            continue

        province_col = detect_repeat_province_column(sheet_df)
        if not province_col:
            continue

        normalized = sheet_df[province_col].apply(normalize_province_name)
        if not (normalized != "").any():
            continue

        filtered, parent_col = filter_repeat_to_public_records(sheet_df, public_df)
        normalized = filtered[province_col].apply(normalize_province_name)
        tmp = pd.DataFrame({"province_key": normalized})
        tmp = tmp[tmp["province_key"] != ""].copy()
        if tmp.empty:
            continue

        if parent_col and parent_col in filtered.columns:
            tmp["__parent"] = filtered.loc[tmp.index, parent_col].astype(str).str.strip()
            tmp = tmp.drop_duplicates(subset=["__parent", "province_key"])
        else:
            # Sin llave padre, se conserva cada localidad válida como registro territorial.
            tmp["__parent"] = ""

        tmp["__sheet"] = str(sheet_name)
        rows.append(tmp)
        used_sheets.append(str(sheet_name))

    if not rows:
        return empty, []

    combined = pd.concat(rows, ignore_index=True)
    counts = (
        combined["province_key"]
        .value_counts()
        .rename_axis("province_key")
        .reset_index(name="Registros")
    )
    counts["Provincia"] = counts["province_key"].map(PROVINCE_DISPLAY)
    counts["lat"] = counts["province_key"].apply(lambda x: ECUADOR_PROVINCES[x][0])
    counts["lon"] = counts["province_key"].apply(lambda x: ECUADOR_PROVINCES[x][1])
    return counts, used_sheets



def detect_repeat_geopoint_column(df: pd.DataFrame) -> str | None:
    """Detecta el GPS específico de cada localidad del repeat ``localidades_operacion``."""
    if df.empty:
        return None

    for field_name in [
        "geopunto_localidad_operacion",
        "geopoint_localidad_operacion",
        "georreferenciacion_localidad_operacion",
        "georreferenciación_localidad_operacion",
    ]:
        found = find_field_column(df, field_name)
        if found:
            return found

    candidates: list[tuple[int, int, str]] = []
    for col in df.columns:
        col_norm = norm_text(col)
        col_id = norm_id(col)
        if not (
            "geopunto" in col_id
            or "geopoint" in col_id
            or "georreferenci" in col_norm
            or "gps" in col_norm
        ):
            continue

        locality_bonus = 0
        if "localidad" in col_norm or "localidadoperacion" in col_id:
            locality_bonus += 4
        if "1541" in col_id:
            locality_bonus += 2

        valid_coords = 0
        for value in df[col].dropna().head(120):
            lat, lon = parse_ecuador_coordinates(value)
            if lat is not None and lon is not None:
                valid_coords += 1
        candidates.append((valid_coords, locality_bonus, col))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best = candidates[0]
    return best[2] if best[0] > 0 or best[1] > 0 else None



def _location_text(value: Any) -> str:
    """Convierte valores XML territoriales de KOBO a etiquetas legibles."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value).strip()
    if not text or norm_text(text) in {"nan", "none", "null"}:
        return ""

    # Los códigos geográficos (prov_XX, can_XXXX, par_XXXXXX, ciu_XXXXXX)
    # se traducen con el catálogo oficial incluido en el XLSForm.
    if text in GEO_CHOICE_LABELS:
        return geo_choice_label(text)

    # Para otros valores técnicos se mantiene una limpieza conservadora.
    if "_" in text and not re.fullmatch(r"\d+", text):
        text = re.sub(r"_+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def georeferenced_localities_from_repeat_sheets(
    repeat_sheets: dict[str, pd.DataFrame],
    public_df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    """Extrae localidades operativas georreferenciadas de los repeats de KOBO.

    La versión actualizada del XLSForm incorpora ``geopunto_localidad_operacion``
    (pregunta 15.4.1). Esos puntos se priorizan en el mapa por encima del centroide
    provincial y conservan provincia, cantón, parroquia, ciudad/localidad y actividad.
    """
    columns = [
        "lat", "lon", "Provincia", "Canton", "Parroquia", "Localidad",
        "Actividad", "Referencia", "__parent", "__sheet",
    ]
    if not repeat_sheets:
        return pd.DataFrame(columns=columns), []

    rows: list[dict[str, Any]] = []
    used_sheets: list[str] = []

    for sheet_name, sheet_df in repeat_sheets.items():
        if sheet_df.empty:
            continue

        geopoint_col = detect_repeat_geopoint_column(sheet_df)
        if not geopoint_col:
            continue

        province_col = detect_repeat_province_column(sheet_df)
        canton_col = find_field_column(sheet_df, "canton_operacion")
        parish_col = find_field_column(sheet_df, "parroquia_operacion")
        city_col = find_field_column(sheet_df, "ciudad_localidad_operacion")
        activity_col = find_field_column(sheet_df, "actividad_localidad")
        if not any([province_col, canton_col, parish_col, city_col]):
            continue

        filtered, parent_col = filter_repeat_to_public_records(sheet_df, public_df)
        added_here = 0

        for _, row in filtered.iterrows():
            lat, lon = parse_ecuador_coordinates(row.get(geopoint_col))
            if lat is None or lon is None:
                continue
            if not (-5.5 <= lat <= 2.2 and -92.5 <= lon <= -74.0):
                continue

            province_raw = row.get(province_col) if province_col else None
            province_key = normalize_province_name(province_raw)
            province = PROVINCE_DISPLAY.get(province_key, _location_text(province_raw))
            canton = _location_text(row.get(canton_col)) if canton_col else ""
            parish = _location_text(row.get(parish_col)) if parish_col else ""
            city = _location_text(row.get(city_col)) if city_col else ""
            activity = _location_text(row.get(activity_col)) if activity_col else ""

            reference_parts: list[str] = []
            for value in [city, parish, canton, province]:
                if value and value not in reference_parts:
                    reference_parts.append(value)
            reference = " · ".join(reference_parts) or "Localidad georreferenciada"

            parent_value = ""
            if parent_col and parent_col in filtered.columns:
                parent_value = _location_text(row.get(parent_col))

            rows.append({
                "lat": float(lat),
                "lon": float(lon),
                "Provincia": province,
                "Canton": canton,
                "Parroquia": parish,
                "Localidad": city,
                "Actividad": activity,
                "Referencia": reference,
                "__parent": parent_value,
                "__sheet": str(sheet_name),
            })
            added_here += 1

        if added_here:
            used_sheets.append(str(sheet_name))

    if not rows:
        return pd.DataFrame(columns=columns), []

    result = pd.DataFrame(rows)
    if "__parent" in result.columns and (result["__parent"].astype(str).str.strip() != "").any():
        result = result.drop_duplicates(
            subset=["__parent", "lat", "lon", "Referencia"], keep="last"
        )
    else:
        result = result.drop_duplicates(subset=["lat", "lon", "Referencia"], keep="last")

    return result.reset_index(drop=True), sorted(set(used_sheets))


def _map_zoom_from_points(*frames: pd.DataFrame) -> int:
    """Calcula un zoom estable según la dispersión de las coordenadas reales."""
    coords: list[tuple[float, float]] = []
    for frame in frames:
        if frame is None or frame.empty or "lat" not in frame.columns or "lon" not in frame.columns:
            continue
        for lat, lon in zip(frame["lat"], frame["lon"]):
            try:
                lat_f = float(lat)
                lon_f = float(lon)
            except Exception:
                continue
            if -5.5 <= lat_f <= 2.2 and -92.5 <= lon_f <= -74.0:
                coords.append((lat_f, lon_f))

    if not coords:
        return 5
    if len(coords) == 1:
        return 9

    lats = [p[0] for p in coords]
    lons = [p[1] for p in coords]
    span = max(max(lats) - min(lats), max(lons) - min(lons))
    if span >= 8:
        return 4
    if span >= 4:
        return 5
    if span >= 2:
        return 6
    if span >= 1:
        return 7
    if span >= 0.4:
        return 8
    return 9

def detect_geopoint_column(df: pd.DataFrame) -> str | None:
    """Selecciona la columna que realmente contiene coordenadas, no solo una etiqueta con 'GPS'."""
    if df.empty:
        return None

    preferred = get_secret("GEOPOINT_COLUMN", "")
    if preferred:
        col = find_column(df, preferred, [])
        if col:
            return col

    terms = [
        "geopoint",
        "geopunto",
        "geolocalizacion",
        "geolocalización",
        "georreferencia",
        "georreferenciacion",
        "georreferenciación",
        "ubicacion gps",
        "ubicación gps",
        "coordenadas",
        "gps",
    ]
    terms_norm = [norm_text(term) for term in terms]

    candidates: list[tuple[int, int, str]] = []
    for col in df.columns:
        col_norm = norm_text(col)
        col_id = norm_id(col)
        if not any(term in col_norm for term in terms_norm) and "geopoint" not in col_id:
            continue

        sample = df[col].dropna().head(100)
        valid_coords = 0
        for value in sample:
            lat, lon = parse_ecuador_coordinates(value)
            if lat is not None and lon is not None:
                valid_coords += 1

        name_bonus = 0
        if col_id == "geopoint" or col_id.endswith("geopoint"):
            name_bonus += 3
        if "georeferenciaciondeladireccion" in col_id or "georreferenciaciondeladireccion" in col_id:
            name_bonus += 2

        candidates.append((valid_coords, name_bonus, col))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return candidates[0][2]


def detect_lat_lon_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    if df.empty:
        return None, None

    lat_col = None
    lon_col = None

    for col in df.columns:
        col_norm = norm_text(col)
        col_id = norm_id(col)

        if lat_col is None and (
            col_id in {"lat", "latitude", "latitud", "geolocation0"}
            or "latitude" in col_norm
            or "latitud" in col_norm
        ):
            lat_col = col

        if lon_col is None and (
            col_id in {"lon", "lng", "longitude", "longitud", "geolocation1"}
            or "longitude" in col_norm
            or "longitud" in col_norm
        ):
            lon_col = col

    return lat_col, lon_col


def parse_ecuador_coordinates(value: Any) -> tuple[float | None, float | None]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None, None

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            lat = float(value[0])
            lon = float(value[1])
            if -5.5 <= lat <= 2.0 and -82.5 <= lon <= -74.0:
                return lat, lon
        except Exception:
            pass

    text = str(value).strip()
    numbers = re.findall(r"-?\d+(?:\.\d+)?", text)

    if len(numbers) < 2:
        return None, None

    try:
        first = float(numbers[0])
        second = float(numbers[1])
    except Exception:
        return None, None

    if -5.5 <= first <= 2.0 and -82.5 <= second <= -74.0:
        return first, second

    if -82.5 <= first <= -74.0 and -5.5 <= second <= 2.0:
        return second, first

    return None, None


def latest_public_records(df: pd.DataFrame, company_col: str | None) -> pd.DataFrame:
    """Devuelve una observación por empresa para evitar doble conteo público."""
    if df.empty:
        return df.copy()

    if not company_col or company_col not in df.columns:
        return df.copy()

    tmp = df.copy()
    tmp["__company_public"] = tmp[company_col].apply(normalize_company)

    date_candidates = [
        c
        for c in tmp.columns
        if any(
            k in norm_text(c)
            for k in [
                "fecha de envio",
                "fecha de envío",
                "submission",
                "_submission_time",
                "end",
                "fin",
            ]
        )
    ]

    if date_candidates:
        date_col = date_candidates[0]
        tmp["__public_date"] = pd.to_datetime(tmp[date_col], errors="coerce")
        tmp = tmp.sort_values(["__company_public", "__public_date"], na_position="first")

    latest = tmp.drop_duplicates(subset=["__company_public"], keep="last").copy()
    return latest.drop(columns=["__company_public", "__public_date"], errors="ignore")


def get_public_latest_date(df: pd.DataFrame) -> str:
    if df.empty:
        return "Sin fecha"

    candidates = [
        c
        for c in df.columns
        if any(
            k in norm_text(c)
            for k in [
                "fecha de envio",
                "fecha de envío",
                "submission",
                "_submission_time",
                "end",
                "fin",
            ]
        )
    ]

    for col in candidates:
        parsed = pd.to_datetime(df[col], errors="coerce")
        if parsed.notna().any():
            return parsed.max().strftime("%d/%m/%Y")

    return "Sin fecha"


def calculate_public_scores(
    public_df: pd.DataFrame,
) -> tuple[float | None, dict[int, float | None], list[float]]:
    if public_df.empty:
        return None, {p["id"]: None for p in PRINCIPLES}, []

    principle_values: dict[int, list[float]] = {p["id"]: [] for p in PRINCIPLES}
    company_totals: list[float] = []

    for _, row in public_df.iterrows():
        objective_scores = {
            obj_id: objective_score(row, public_df, obj_id)
            for obj_id in OBJECTIVES
        }
        p_scores = {
            p["id"]: principle_score(row, public_df, p["id"], objective_scores)
            for p in PRINCIPLES
        }

        valid_company_scores = [score for score in p_scores.values() if score is not None]
        if valid_company_scores:
            company_totals.append(float(np.mean(valid_company_scores)))

        for pid, score in p_scores.items():
            if score is not None:
                principle_values[pid].append(score)

    principle_average = {
        pid: (float(np.mean(values)) if values else None)
        for pid, values in principle_values.items()
    }
    total = float(np.mean(company_totals)) if company_totals else None

    return total, principle_average, company_totals


def public_level_counts(company_scores: list[float]) -> dict[str, int]:
    counts = {
        "Crítico": 0,
        "Inicial": 0,
        "En construcción": 0,
        "Avanzado": 0,
    }

    for score in company_scores:
        level = level_from_score(score)
        if level in counts:
            counts[level] += 1

    return counts


def public_province_counts(
    public_df: pd.DataFrame,
    province_col: str | None,
) -> pd.DataFrame:
    empty = pd.DataFrame(columns=["province_key", "Provincia", "Registros", "lat", "lon"])

    if public_df.empty or not province_col or province_col not in public_df.columns:
        return empty

    province_series = public_df[province_col].apply(normalize_province_name)
    counts = (
        province_series[province_series != ""]
        .value_counts()
        .rename_axis("province_key")
        .reset_index(name="Registros")
    )

    if counts.empty:
        return empty

    counts["Provincia"] = counts["province_key"].map(PROVINCE_DISPLAY)
    counts["lat"] = counts["province_key"].apply(lambda x: ECUADOR_PROVINCES[x][0])
    counts["lon"] = counts["province_key"].apply(lambda x: ECUADOR_PROVINCES[x][1])
    return counts


def public_georeferenced_points(public_df: pd.DataFrame) -> pd.DataFrame:
    points: list[dict[str, Any]] = []

    if public_df.empty:
        return pd.DataFrame(columns=["lat", "lon", "Provincia"])

    geopoint_col = detect_geopoint_column(public_df)
    lat_col, lon_col = detect_lat_lon_columns(public_df)
    province_col = detect_province_column(public_df)

    for _, row in public_df.iterrows():
        lat = None
        lon = None

        if geopoint_col:
            lat, lon = parse_ecuador_coordinates(row.get(geopoint_col))

        if (lat is None or lon is None) and lat_col and lon_col:
            try:
                test_lat = float(row.get(lat_col))
                test_lon = float(row.get(lon_col))
                if -5.5 <= test_lat <= 2.0 and -82.5 <= test_lon <= -74.0:
                    lat = test_lat
                    lon = test_lon
            except Exception:
                pass

        if lat is None or lon is None:
            continue

        province = ""
        if province_col:
            key = normalize_province_name(row.get(province_col))
            province = PROVINCE_DISPLAY.get(key, "")

        points.append({"lat": lat, "lon": lon, "Provincia": province})

    return pd.DataFrame(points)




def _set_public_map_province(province: str) -> None:
    """Activa una vista provincial del mapa."""
    st.session_state["tv_map_focus_province"] = str(province or "")
    st.session_state["tv_map_focus_lat"] = None
    st.session_state["tv_map_focus_lon"] = None
    st.session_state["tv_map_focus_label"] = ""


def _set_public_map_locality(
    province: str,
    lat: float,
    lon: float,
    label: str,
) -> None:
    """Activa una vista puntual sobre una localidad georreferenciada."""
    st.session_state["tv_map_focus_province"] = str(province or "")
    st.session_state["tv_map_focus_lat"] = float(lat)
    st.session_state["tv_map_focus_lon"] = float(lon)
    st.session_state["tv_map_focus_label"] = str(label or "Localidad georreferenciada")


def _reset_public_map_focus() -> None:
    """Restablece la vista nacional."""
    st.session_state["tv_map_focus_province"] = ""
    st.session_state["tv_map_focus_lat"] = None
    st.session_state["tv_map_focus_lon"] = None
    st.session_state["tv_map_focus_label"] = ""


def render_professional_ecuador_map(
    province_df: pd.DataFrame,
    locality_geo_df: pd.DataFrame,
    company_geo_df: pd.DataFrame,
    height: int = 540,
    focus_province: str = "",
    focus_lat: float | None = None,
    focus_lon: float | None = None,
    focus_label: str = "",
) -> None:
    """Mapa nativo de Streamlit con foco provincial y por localidad.

    Jerarquía cartográfica:
    1. Morado intenso: geopuntos exactos de localidades operativas (15.4.1).
    2. Naranja: dirección principal de la empresa (5.1).
    3. Morado medio: cobertura provincial contextual cuando todavía no existe
       geopunto de localidad.

    Los círculos son deliberadamente discretos. El tamaño crece de forma
    logarítmica con el número de registros para evitar burbujas gigantes.
    """
    rows: list[dict[str, Any]] = []

    focus_province = str(focus_province or "").strip()
    focus_label = str(focus_label or "").strip()
    has_point_focus = focus_lat is not None and focus_lon is not None

    # --------------------------------------------------------
    # Vista puntual: una localidad seleccionada.
    # --------------------------------------------------------
    if has_point_focus:
        rows.append(
            {
                "lat": float(focus_lat),
                "lon": float(focus_lon),
                "color": "#5B21B6FF",
                "size": 720.0,
                "tipo": "Localidad operativa GPS",
                "detalle": focus_label or "Localidad georreferenciada",
            }
        )

        if focus_label:
            st.caption(f"📍 Vista enfocada: {focus_label}")

        map_df = pd.DataFrame(rows)
        zoom = 12

    else:
        # ----------------------------------------------------
        # Cobertura provincial contextual.
        # ----------------------------------------------------
        province_source = province_df.copy()

        if focus_province and not province_source.empty:
            province_source = province_source[
                province_source["Provincia"].astype(str).str.strip() == focus_province
            ].copy()

        if not province_source.empty:
            for _, item in province_source.iterrows():
                try:
                    lat = float(item.get("lat"))
                    lon = float(item.get("lon"))
                    count = max(1.0, float(item.get("Registros", 1) or 1))
                except Exception:
                    continue

                if not (-5.5 <= lat <= 2.2 and -92.5 <= lon <= -74.0):
                    continue

                # 1 registro ≈ 430 m. Crecimiento lento y tope inferior a 900 m.
                size_m = min(
                    880.0,
                    320.0 + 160.0 * float(np.log1p(count)),
                )

                rows.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "color": "#5B21B6D9",
                        "size": size_m,
                        "tipo": "Cobertura provincial",
                        "detalle": f"{item.get('Provincia', 'Provincia')}: {int(count)} registro(s)",
                    }
                )

        # ----------------------------------------------------
        # Geopuntos exactos de localidades.
        # ----------------------------------------------------
        locality_source = locality_geo_df.copy()

        if focus_province and not locality_source.empty:
            locality_source = locality_source[
                locality_source["Provincia"].astype(str).str.strip() == focus_province
            ].copy()

        if not locality_source.empty:
            for _, item in locality_source.iterrows():
                try:
                    lat = float(item.get("lat"))
                    lon = float(item.get("lon"))
                except Exception:
                    continue

                if not (-5.5 <= lat <= 2.2 and -92.5 <= lon <= -74.0):
                    continue

                rows.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "color": "#5B21B6FF",
                        "size": 620.0 if not focus_province else 680.0,
                        "tipo": "Localidad operativa GPS",
                        "detalle": str(
                            item.get("Referencia", "Localidad georreferenciada")
                        ),
                    }
                )

        # ----------------------------------------------------
        # Dirección principal, como referencia complementaria.
        # ----------------------------------------------------
        company_source = company_geo_df.copy()

        if focus_province and not company_source.empty and "Provincia" in company_source.columns:
            company_source = company_source[
                company_source["Provincia"].astype(str).str.strip() == focus_province
            ].copy()

        if not company_source.empty:
            for _, item in company_source.iterrows():
                try:
                    lat = float(item.get("lat"))
                    lon = float(item.get("lon"))
                except Exception:
                    continue

                if not (-5.5 <= lat <= 2.2 and -92.5 <= lon <= -74.0):
                    continue

                province = str(item.get("Provincia", "") or "").strip()
                rows.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "color": "#F47A48F2",
                        "size": 470.0,
                        "tipo": "Dirección principal GPS",
                        "detalle": province or "Dirección principal georreferenciada",
                    }
                )

        if not rows:
            st.info("No hay coordenadas territoriales válidas para representar en el mapa.")
            return

        map_df = pd.DataFrame(rows)

        if focus_province:
            st.caption(
                f"📌 Vista provincial: {focus_province}. "
                "Los puntos morados sólidos corresponden a localidades con GPS."
            )
            province_points = locality_source if not locality_source.empty else province_source
            zoom = max(8, _map_zoom_from_points(province_points))
        else:
            exact_for_zoom = locality_geo_df if not locality_geo_df.empty else company_geo_df
            zoom = _map_zoom_from_points(exact_for_zoom, company_geo_df, province_df)

    st.markdown(
        """
        <div style="display:flex; gap:18px; align-items:center; flex-wrap:wrap;
                    margin:0 0 8px 2px; color:#5f6472; font-size:0.82rem;">
            <span style="display:flex;align-items:center;gap:7px;">
                <span style="width:11px;height:11px;border-radius:50%;background:#5B21B6;display:inline-block;"></span>
                Localidad operativa GPS
            </span>
            <span style="display:flex;align-items:center;gap:7px;">
                <span style="width:10px;height:10px;border-radius:50%;background:#F47A48;display:inline-block;"></span>
                Dirección principal GPS
            </span>
            <span style="display:flex;align-items:center;gap:7px;">
                <span style="width:10px;height:10px;border-radius:50%;background:#5B21B6D9;display:inline-block;border:1px solid #4C1D95;"></span>
                Cobertura provincial (referencia)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    common_kwargs = dict(
        data=map_df,
        latitude="lat",
        longitude="lon",
        color="color",
        size="size",
        zoom=int(max(1, min(15, zoom))),
    )

    try:
        st.map(**common_kwargs, width="stretch", height=height)
    except TypeError:
        st.map(**common_kwargs, use_container_width=True)


def public_weps_figure(principle_scores: dict[int, float | None]) -> go.Figure:
    labels = []
    values = []
    colors = []
    text_values = []

    for p in PRINCIPLES:
        pid = p["id"]
        score = principle_scores.get(pid)
        short_title = p["title"] if len(p["title"]) <= 45 else p["title"][:42] + "..."

        labels.append(f"WEP {pid} · {short_title}")
        values.append(0 if score is None else score)
        colors.append(color_from_score(score))
        text_values.append("Sin cálculo" if score is None else f"{score:.1f}%")

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=text_values,
            textposition="auto",
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        height=330,
        margin=dict(l=10, r=10, t=15, b=25),
        xaxis=dict(range=[0, 100], title="Avance promedio (%)", fixedrange=True, ticksuffix="%"),
        yaxis=dict(autorange="reversed", fixedrange=True, automargin=True),
        showlegend=False,
        dragmode=False,
    )
    return fig


def public_levels_figure(level_counts: dict[str, int]) -> go.Figure:
    levels = ["Crítico", "Inicial", "En construcción", "Avanzado"]
    counts = [level_counts.get(level, 0) for level in levels]
    total = sum(counts)
    percentages = [(count / total * 100 if total else 0) for count in counts]
    colors = ["#DC2626", "#EA580C", "#E8B235", "#16A34A"]

    fig = go.Figure(
        go.Bar(
            x=levels,
            y=counts,
            marker_color=colors,
            text=[f"{pct:.0f}%<br>{count}" for pct, count in zip(percentages, counts)],
            textposition="outside",
            hovertemplate="%{x}<br>%{y} empresas<extra></extra>",
        )
    )

    fig.update_layout(
        height=330,
        margin=dict(l=10, r=10, t=35, b=25),
        yaxis=dict(visible=False, fixedrange=True),
        xaxis=dict(fixedrange=True),
        showlegend=False,
        dragmode=False,
    )
    return fig


def render_public_summary(
    df: pd.DataFrame,
    company_col: str | None,
    repeat_sheets: dict[str, pd.DataFrame] | None = None,
) -> None:
    public_css()

    # Para resultados institucionales se conserva la observación más reciente
    # de cada empresa, evitando que una actualización duplique su peso.
    public_df = latest_public_records(df, company_col)

    total_score, principle_scores, company_scores = calculate_public_scores(public_df)
    general_level = level_from_score(total_score)

    # La cobertura territorial se toma primero del repeat ``localidades_operacion``.
    # Si el export no incluye hojas repeat, se usa la provincia disponible en la tabla principal.
    repeat_sheets = repeat_sheets or {}
    province_df, province_repeat_sheets = province_counts_from_repeat_sheets(repeat_sheets, public_df)
    province_source = "repeat" if not province_df.empty else "main"

    if province_df.empty:
        province_col = detect_province_column(public_df)
        province_df = public_province_counts(public_df, province_col)

    # Puntos exactos de localidades operativas (15.4.1) y dirección principal (5.1).
    locality_geo_df, locality_repeat_sheets = georeferenced_localities_from_repeat_sheets(
        repeat_sheets, public_df
    )
    geo_df = public_georeferenced_points(public_df)

    companies = (
        public_df[company_col].nunique()
        if company_col and company_col in public_df.columns
        else len(public_df)
    )
    surveys = len(df)
    provinces = len(province_df)
    last_update = get_public_latest_date(df)

    # Encabezado
    st.markdown(
        f"""
        <div class="tv-public-intro">
            <h2>Resumen público</h2>
            <p>
                Resultados agregados del proceso Turismo Violeta ·
                Última actualización: <b>{last_update}</b>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # KPI principales
    k1, k2, k3, k4, k5 = st.columns(5)
    kpis = [
        (k1, "Empresas participantes", companies, "Organizaciones registradas"),
        (k2, "Registros recibidos", surveys, "Encuestas acumuladas"),
        (k3, "Provincias con cobertura", provinces, "De 24 provincias del Ecuador"),
        (k4, "Principios WEPs", 7, "Principios evaluados"),
        (k5, "Indicadores analizados", 48, "Organizados en 13 objetivos"),
    ]

    for column, label, value, detail in kpis:
        with column:
            st.markdown(
                f"""
                <div class="tv-kpi">
                    <div class="tv-kpi-label">{label}</div>
                    <div class="tv-kpi-value">{value}</div>
                    <div class="tv-kpi-detail">{detail}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")

    # Avance general + resultados destacados
    left, right = st.columns([0.9, 1.35])

    with left:
        st.markdown(
            '<div class="tv-card-title">Avance general del proceso</div>',
            unsafe_allow_html=True,
        )
        d1, d2 = st.columns([0.85, 1.15])

        with d1:
            st.plotly_chart(
                donut(total_score, "", height=235),
                use_container_width=True,
                config=CHART_CONFIG,
                key="public_general_donut",
            )

        with d2:
            st.markdown(
                f"""
                <div style="padding-top:34px;">
                    <div class="tv-level">{general_level}</div>
                    <div style="color:#565b6c; line-height:1.5; font-size:0.95rem; margin-top:7px;">
                        El avance general resume el desempeño agregado de las empresas
                        en los siete principios WEPs.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    valid_principles = [
        (p["id"], p["title"], principle_scores.get(p["id"]))
        for p in PRINCIPLES
        if principle_scores.get(p["id"]) is not None
    ]
    strongest = max(valid_principles, key=lambda x: x[2]) if valid_principles else None

    with right:
        st.markdown(
            """
            <div class="tv-card">
                <div class="tv-card-title">Logros y resultados destacados</div>
            """,
            unsafe_allow_html=True,
        )

        findings = []
        if provinces:
            findings.append(f"Cobertura territorial registrada en {provinces} provincias del Ecuador.")
        if not locality_geo_df.empty:
            findings.append(
                f"{len(locality_geo_df)} localidades operativas cuentan con georreferenciación GPS específica."
            )
        findings.append(f"{companies} empresas forman parte de la medición agregada.")
        if total_score is not None:
            findings.append(
                f"El avance promedio general alcanza {total_score:.1f}% y se ubica en nivel {general_level}."
            )
        if strongest:
            findings.append(
                f"El mayor avance promedio corresponde al Principio WEPs {strongest[0]}, con {strongest[2]:.1f}%."
            )
        findings.append(
            "La medición integra 7 principios WEPs, 13 objetivos y 48 indicadores para orientar planes de mejora y seguimiento."
        )

        for finding in findings:
            st.markdown(
                f"""
                <div class="tv-finding">
                    <span class="tv-finding-dot">●</span>{finding}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # Estado de navegación cartográfica.
    focus_province = str(st.session_state.get("tv_map_focus_province", "") or "").strip()
    focus_lat = st.session_state.get("tv_map_focus_lat")
    focus_lon = st.session_state.get("tv_map_focus_lon")
    focus_label = str(st.session_state.get("tv_map_focus_label", "") or "").strip()

    # Cobertura territorial
    st.markdown(
        """
        <div class="tv-card-title">Cobertura territorial y georreferenciación</div>
        <div class="tv-section-caption">
            Localidades operativas georreferenciadas por provincia, cantón, parroquia y ciudad/localidad, con la dirección principal como referencia complementaria.
        </div>
        """,
        unsafe_allow_html=True,
    )

    map_col, rank_col = st.columns([3.4, 1])

    with map_col:
        if not province_df.empty or not locality_geo_df.empty or not geo_df.empty:
            render_professional_ecuador_map(
                province_df,
                locality_geo_df,
                geo_df,
                height=540,
                focus_province=focus_province,
                focus_lat=focus_lat,
                focus_lon=focus_lon,
                focus_label=focus_label,
            )
        else:
            st.info(
                "Aún no se detectaron campos de provincia o georreferenciación para construir el mapa."
            )

    with rank_col:
        st.markdown(
            """
            <div class="tv-card">
                <div class="tv-card-title">Provincias con mayor presencia registrada</div>
            """,
            unsafe_allow_html=True,
        )

        reset_col, _ = st.columns([0.62, 0.38])
        with reset_col:
            st.button(
                "↺ Ver todo Ecuador",
                key="tv_map_reset",
                on_click=_reset_public_map_focus,
                use_container_width=True,
            )

        if not province_df.empty:
            ranking = province_df.sort_values(
                ["Registros", "Provincia"],
                ascending=[False, True],
            ).head(8)

            for rank, (_, item) in enumerate(ranking.iterrows(), start=1):
                province_name = str(item["Provincia"])
                count_value = int(item["Registros"])

                c_rank, c_name, c_count, c_action = st.columns(
                    [0.14, 0.48, 0.12, 0.26],
                    vertical_alignment="center",
                )

                with c_rank:
                    st.markdown(
                        f"<span class='tv-rank-number'>{rank}</span>",
                        unsafe_allow_html=True,
                    )

                with c_name:
                    if focus_province == province_name:
                        st.markdown(f"**{province_name}**")
                    else:
                        st.write(province_name)

                with c_count:
                    st.markdown(f"**{count_value}**")

                with c_action:
                    st.button(
                        "Ver",
                        key=f"tv_province_{norm_id(province_name)}",
                        help=f"Mostrar localidades de {province_name} y acercar el mapa.",
                        on_click=_set_public_map_province,
                        args=(province_name,),
                        use_container_width=True,
                    )

                st.markdown(
                    "<div style='border-bottom:1px solid #f0eef6; margin:1px 0 7px 0;'></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Sin información provincial disponible.")

        # Cuando se selecciona una provincia se muestra el detalle territorial
        # más específico disponible y cada localidad puede enfocar el mapa.
        if focus_province:
            st.markdown(
                f"""
                <div style="margin-top:14px; color:#21194d; font-size:0.91rem; font-weight:800;">
                    Localidades en {focus_province}
                </div>
                """,
                unsafe_allow_html=True,
            )

            province_localities = locality_geo_df.copy()
            if not province_localities.empty:
                province_localities = province_localities[
                    province_localities["Provincia"].astype(str).str.strip()
                    == focus_province
                ].copy()

            if not province_localities.empty:
                province_localities = province_localities.sort_values(
                    ["Canton", "Parroquia", "Localidad", "Referencia"],
                    na_position="last",
                )

                for idx, (_, loc) in enumerate(
                    province_localities.head(12).iterrows(),
                    start=1,
                ):
                    reference = str(
                        loc.get("Referencia", "Localidad georreferenciada") or
                        "Localidad georreferenciada"
                    ).strip()
                    activity = str(loc.get("Actividad", "") or "").strip()

                    l_text, l_action = st.columns(
                        [0.76, 0.24],
                        vertical_alignment="center",
                    )

                    with l_text:
                        st.markdown(
                            f"<div style='font-size:0.80rem; line-height:1.35; color:#4f5565;'>"
                            f"<b>{idx}. {reference}</b>"
                            f"{('<br><span style=\"color:#7b8090;\">' + activity + '</span>') if activity else ''}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    with l_action:
                        st.button(
                            "📍",
                            key=(
                                f"tv_locality_{norm_id(focus_province)}_"
                                f"{idx}_{round(float(loc['lat']), 5)}_"
                                f"{round(float(loc['lon']), 5)}"
                            ),
                            help=f"Acercar el mapa a {reference}.",
                            on_click=_set_public_map_locality,
                            args=(
                                focus_province,
                                float(loc["lat"]),
                                float(loc["lon"]),
                                reference,
                            ),
                            use_container_width=True,
                        )

                    st.markdown(
                        "<div style='border-bottom:1px solid #f4f2f8; margin:4px 0 6px 0;'></div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption(
                    "La provincia tiene cobertura declarada, pero todavía no hay "
                    "geopuntos válidos de localidad en los registros disponibles."
                )

        if province_source == "repeat" and province_repeat_sheets:
            st.markdown(
                """
                <div style="margin-top:14px; color:#767b8c; font-size:0.82rem;">
                    La cobertura provincial se conserva como referencia contextual; los puntos GPS de localidad tienen prioridad cartográfica.
                </div>
                """,
                unsafe_allow_html=True,
            )

        if not locality_geo_df.empty and not focus_province:
            st.markdown(
                f"""
                <div style="margin-top:12px; color:#21194d; font-size:0.88rem; font-weight:700;">
                    Localidades georreferenciadas ({len(locality_geo_df)})
                </div>
                """,
                unsafe_allow_html=True,
            )
            refs = locality_geo_df["Referencia"].dropna().astype(str).str.strip()
            refs = [ref for ref in refs if ref][:5]
            for ref in refs:
                st.markdown(
                    f"<div style='padding:5px 0; color:#626779; font-size:0.79rem; line-height:1.35;'>📍 {ref}</div>",
                    unsafe_allow_html=True,
                )

        if not geo_df.empty:
            st.markdown(
                f"""
                <div style="margin-top:10px; color:#767b8c; font-size:0.82rem;">
                    🟠 {len(geo_df)} direcciones principales cuentan con GPS válido.
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # Principios WEPs + niveles de avance
    chart_left, chart_right = st.columns([1.25, 1])

    with chart_left:
        st.markdown(
            '<div class="tv-card-title">Avance promedio por principio WEPs</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            public_weps_figure(principle_scores),
            use_container_width=True,
            config=CHART_CONFIG,
            key="public_weps_summary",
        )

    with chart_right:
        st.markdown(
            '<div class="tv-card-title">Distribución de empresas por nivel</div>',
            unsafe_allow_html=True,
        )
        level_counts = public_level_counts(company_scores)
        st.plotly_chart(
            public_levels_figure(level_counts),
            use_container_width=True,
            config=CHART_CONFIG,
            key="public_level_distribution",
        )

    # Pie
    st.markdown(
        """
        <div class="tv-footer">
            ☁ Actualización automática desde KOBO
            &nbsp;&nbsp;·&nbsp;&nbsp;
            Los resultados corresponden a información agregada y de carácter público.
            &nbsp;&nbsp;·&nbsp;&nbsp;
            La consulta detallada por empresa permanece protegida mediante el código creado por la organización en la encuesta.
        </div>
        """,
        unsafe_allow_html=True,
    )



def _admin_join_key(value: Any) -> str:
    """Normaliza llaves de relación entre hoja principal y repeats de KOBO."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    numeric_like = text.replace(",", ".")
    if re.fullmatch(r"-?\d+\.0+", numeric_like):
        return numeric_like.split(".", 1)[0]
    return text


def admin_company_score_table(df: pd.DataFrame, company_col: str | None) -> pd.DataFrame:
    """Construye una fila analítica por empresa con avance general y los 7 WEPs."""
    columns = ["Empresa", "Avance general", "Nivel"] + [f"WEP {i}" for i in range(1, 8)]
    if df.empty or not company_col or company_col not in df.columns:
        return pd.DataFrame(columns=columns)

    latest = latest_public_records(df, company_col)
    rows: list[dict[str, Any]] = []
    for _, row in latest.iterrows():
        company = str(row.get(company_col, "") or "").strip()
        if not company:
            continue
        objective_scores = {oid: objective_score(row, latest, oid) for oid in OBJECTIVES}
        p_scores = {
            p["id"]: principle_score(row, latest, p["id"], objective_scores)
            for p in PRINCIPLES
        }
        total = overall_score(p_scores)
        item: dict[str, Any] = {
            "Empresa": company,
            "Avance general": total,
            "Nivel": level_from_score(total),
        }
        for pid in range(1, 8):
            item[f"WEP {pid}"] = p_scores.get(pid)
        rows.append(item)
    return pd.DataFrame(rows, columns=columns)


def admin_objective_average_table(df: pd.DataFrame) -> pd.DataFrame:
    """Promedio de los 13 objetivos en el conjunto filtrado."""
    rows: list[dict[str, Any]] = []
    if df.empty:
        return pd.DataFrame(columns=["Objetivo", "Nombre", "Avance promedio", "Nivel", "Empresas con cálculo"])

    for oid, meta in OBJECTIVES.items():
        values = []
        for _, row in df.iterrows():
            score = objective_score(row, df, oid)
            if score is not None:
                values.append(float(score))
        avg = float(np.mean(values)) if values else None
        rows.append({
            "Objetivo": oid,
            "Nombre": meta["title"],
            "Avance promedio": avg,
            "Nivel": level_from_score(avg),
            "Empresas con cálculo": len(values),
        })
    return pd.DataFrame(rows)


def admin_indicator_average_table(df: pd.DataFrame) -> pd.DataFrame:
    """Promedio de los 48 indicadores en el conjunto filtrado."""
    rows: list[dict[str, Any]] = []
    if df.empty:
        return pd.DataFrame(columns=["Indicador", "Nombre", "Avance promedio", "Nivel", "Empresas con cálculo", "Referencia"])

    for iid, meta in INDICATORS.items():
        values = []
        for _, row in df.iterrows():
            score = indicator_score(row, df, iid)
            if score is not None:
                values.append(float(score))
        avg = float(np.mean(values)) if values else None
        rows.append({
            "Indicador": iid,
            "Nombre": meta["title"],
            "Avance promedio": avg,
            "Nivel": level_from_score(avg),
            "Empresas con cálculo": len(values),
            "Referencia": meta.get("ref", ""),
        })
    return pd.DataFrame(rows)


def _admin_link_repeat_to_companies(
    repeat_df: pd.DataFrame,
    main_df: pd.DataFrame,
    company_col: str | None,
) -> pd.DataFrame:
    """Añade __admin_company a un repeat cuando KOBO exporta una llave padre utilizable."""
    result = repeat_df.copy()
    result["__admin_company"] = ""
    if result.empty or main_df.empty or not company_col or company_col not in main_df.columns:
        return result

    key_pairs = [
        (["_parent_index", "parent_index"], ["_index", "index"]),
        (["parent_key", "_parent_key", "PARENT_KEY"], ["key", "KEY"]),
        (["_parent_uuid", "parent_uuid"], ["_uuid", "uuid"]),
        (["_parent_id", "parent_id"], ["_id", "id"]),
    ]

    for repeat_candidates, main_candidates in key_pairs:
        repeat_key = _find_id_column(result, repeat_candidates)
        main_key = _find_id_column(main_df, main_candidates)
        if not repeat_key or not main_key:
            continue

        mapping: dict[str, str] = {}
        for _, row in main_df.iterrows():
            key = _admin_join_key(row.get(main_key))
            company = str(row.get(company_col, "") or "").strip()
            if key and company:
                mapping[key] = company
        if not mapping:
            continue

        linked = result[repeat_key].apply(_admin_join_key).map(mapping).fillna("")
        if linked.astype(str).str.strip().ne("").any():
            result["__admin_company"] = linked
            return result

    return result


def admin_company_province_map(
    repeat_sheets: dict[str, pd.DataFrame],
    main_df: pd.DataFrame,
    company_col: str | None,
) -> dict[str, set[str]]:
    """Devuelve provincias declaradas por cada empresa usando localidades_operacion/repeats."""
    mapping: dict[str, set[str]] = {}
    if main_df.empty or not company_col or company_col not in main_df.columns:
        return mapping

    for company in main_df[company_col].dropna().astype(str):
        if company.strip():
            mapping.setdefault(normalize_company(company), set())

    for _, sheet_df in (repeat_sheets or {}).items():
        if sheet_df.empty:
            continue
        province_col = detect_repeat_province_column(sheet_df)
        if not province_col:
            continue
        linked = _admin_link_repeat_to_companies(sheet_df, main_df, company_col)
        if "__admin_company" not in linked.columns:
            continue
        for _, row in linked.iterrows():
            company = str(row.get("__admin_company", "") or "").strip()
            if not company:
                continue
            pkey = normalize_province_name(row.get(province_col))
            province = PROVINCE_DISPLAY.get(pkey, _location_text(row.get(province_col)))
            if province:
                mapping.setdefault(normalize_company(company), set()).add(province)

    # Respaldo por provincia en la tabla principal si existiera.
    province_col = detect_province_column(main_df)
    if province_col:
        for _, row in main_df.iterrows():
            company = str(row.get(company_col, "") or "").strip()
            if not company:
                continue
            pkey = normalize_province_name(row.get(province_col))
            province = PROVINCE_DISPLAY.get(pkey, _location_text(row.get(province_col)))
            if province:
                mapping.setdefault(normalize_company(company), set()).add(province)
    return mapping


def admin_heatmap_figure(score_table: pd.DataFrame) -> go.Figure:
    """Matriz empresa × WEP para detectar patrones rápidamente."""
    if score_table.empty:
        return go.Figure()
    cols = [f"WEP {i}" for i in range(1, 8)]
    z = score_table[cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    text = np.where(np.isnan(z), "—", np.vectorize(lambda x: f"{x:.1f}%")(np.nan_to_num(z)))
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=cols,
            y=score_table["Empresa"].astype(str).tolist(),
            zmin=0,
            zmax=100,
            colorscale=[
                [0.0, "#dc2626"],
                [0.25, "#ea580c"],
                [0.50, "#7c3aed"],
                [0.75, "#6d28d9"],
                [1.0, "#16a34a"],
            ],
            colorbar=dict(title="Avance %"),
            text=text,
            hovertemplate="%{y}<br>%{x}: %{z:.1f}%<extra></extra>",
            hoverongaps=False,
        )
    )
    fig.update_layout(
        height=max(330, min(850, 90 + len(score_table) * 34)),
        margin=dict(l=10, r=10, t=25, b=10),
        xaxis=dict(side="top", fixedrange=True),
        yaxis=dict(autorange="reversed", fixedrange=True, automargin=True),
        dragmode=False,
    )
    return fig


def admin_objectives_figure(table: pd.DataFrame) -> go.Figure:
    valid = table.dropna(subset=["Avance promedio"]).copy()
    if valid.empty:
        return go.Figure()
    valid = valid.sort_values("Objetivo", ascending=False)
    fig = go.Figure(
        go.Bar(
            x=valid["Avance promedio"],
            y=[f"Obj. {int(i)} · {str(n)[:58]}" for i, n in zip(valid["Objetivo"], valid["Nombre"])],
            orientation="h",
            marker_color=[color_from_score(v) for v in valid["Avance promedio"]],
            text=[f"{v:.1f}%" for v in valid["Avance promedio"]],
            textposition="auto",
            hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=15, b=20),
        xaxis=dict(range=[0, 100], ticksuffix="%", fixedrange=True),
        yaxis=dict(fixedrange=True, automargin=True),
        showlegend=False,
        dragmode=False,
    )
    return fig


def admin_indicator_gaps_figure(table: pd.DataFrame, top_n: int = 12) -> go.Figure:
    valid = table.dropna(subset=["Avance promedio"]).copy()
    if valid.empty:
        return go.Figure()
    valid = valid.sort_values("Avance promedio", ascending=True).head(top_n)
    valid = valid.sort_values("Avance promedio", ascending=False)
    fig = go.Figure(
        go.Bar(
            x=valid["Avance promedio"],
            y=[f"Ind. {int(i)} · {str(n)[:52]}" for i, n in zip(valid["Indicador"], valid["Nombre"])],
            orientation="h",
            marker_color=[color_from_score(v) for v in valid["Avance promedio"]],
            text=[f"{v:.1f}%" for v in valid["Avance promedio"]],
            textposition="auto",
            hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        height=470,
        margin=dict(l=10, r=10, t=15, b=20),
        xaxis=dict(range=[0, 100], ticksuffix="%", fixedrange=True),
        yaxis=dict(fixedrange=True, automargin=True),
        showlegend=False,
        dragmode=False,
    )
    return fig


def _admin_nonempty_field_table(row: pd.Series, search: str = "") -> pd.DataFrame:
    records = []
    search_norm = norm_text(search)
    for col, value in row.items():
        if str(col).startswith("__"):
            continue
        if value is None or (isinstance(value, float) and np.isnan(value)):
            continue
        text = str(value).strip()
        if not text or norm_text(text) in {"nan", "none", "null"}:
            continue
        if search_norm and search_norm not in norm_text(col) and search_norm not in norm_text(text):
            continue
        records.append({"Campo": str(col), "Valor": text})
    return pd.DataFrame(records)


def _admin_filter_repeat_for_company(
    repeat_df: pd.DataFrame,
    main_df: pd.DataFrame,
    company_col: str | None,
    company_name: str,
) -> pd.DataFrame:
    linked = _admin_link_repeat_to_companies(repeat_df, main_df, company_col)
    if "__admin_company" not in linked.columns:
        return linked.iloc[0:0].copy()
    wanted = normalize_company(company_name)
    return linked[linked["__admin_company"].apply(normalize_company) == wanted].copy()


def render_admin_dashboard(
    df: pd.DataFrame,
    company_col: str | None,
    code_col: str | None,
    repeat_sheets: dict[str, pd.DataFrame] | None = None,
) -> None:
    """Panel privado: análisis agregado, comparación y detalle sin código por empresa."""
    repeat_sheets = repeat_sheets or {}
    if not company_col or company_col not in df.columns:
        st.error("No se detectó la columna de empresa; no es posible construir el panel administrativo.")
        return

    latest = latest_public_records(df, company_col)
    base_scores = admin_company_score_table(latest, company_col)
    province_map = admin_company_province_map(repeat_sheets, latest, company_col)

    st.markdown("### Filtros administrativos")
    st.caption(
        "Los filtros afectan los indicadores agregados, mapas, comparaciones y tablas del panel. "
        "Una selección vacía de empresas equivale a incluir todas."
    )

    all_companies = sorted(base_scores["Empresa"].dropna().astype(str).unique().tolist(), key=str.casefold)
    all_levels = ["Crítico", "Inicial", "En construcción", "Avanzado"]
    all_provinces = sorted({p for values in province_map.values() for p in values}, key=str.casefold)

    f1, f2 = st.columns([1.55, 1])
    with f1:
        selected_companies = st.multiselect(
            "Empresas",
            all_companies,
            default=[],
            placeholder="Todas las empresas",
            key="admin_filter_companies",
        )
    with f2:
        selected_levels = st.multiselect(
            "Nivel general",
            all_levels,
            default=all_levels,
            key="admin_filter_levels",
        )

    f3, f4 = st.columns([1.2, 1])
    with f3:
        selected_provinces = st.multiselect(
            "Provincia de operación",
            all_provinces,
            default=[],
            placeholder="Todas las provincias",
            key="admin_filter_provinces",
        )
    with f4:
        score_range = st.slider(
            "Rango de avance general",
            min_value=0,
            max_value=100,
            value=(0, 100),
            step=1,
            key="admin_filter_score_range",
        )

    score_table = base_scores.copy()
    if selected_companies:
        score_table = score_table[score_table["Empresa"].isin(selected_companies)].copy()
    if selected_levels:
        score_table = score_table[score_table["Nivel"].isin(selected_levels)].copy()
    else:
        score_table = score_table.iloc[0:0].copy()
    score_numeric = pd.to_numeric(score_table["Avance general"], errors="coerce")
    score_table = score_table[(score_numeric >= score_range[0]) & (score_numeric <= score_range[1])].copy()

    if selected_provinces and not score_table.empty:
        wanted_provinces = set(selected_provinces)
        score_table = score_table[
            score_table["Empresa"].apply(
                lambda company: bool(
                    province_map.get(normalize_company(company), set()) & wanted_provinces
                )
            )
        ].copy()

    selected_names = set(score_table["Empresa"].astype(str).tolist())
    filtered = latest[latest[company_col].astype(str).isin(selected_names)].copy()

    if filtered.empty:
        st.warning("Los filtros actuales no devuelven empresas. Ajuste la selección para continuar.")
        return

    st.markdown(
        f"**Empresas incluidas:** {len(filtered)} de {len(latest)} · "
        f"**Registros históricos en fuente:** {len(df)}"
    )

    admin_section = st.radio(
        "Vista administrativa",
        ["Resumen general", "Comparación y brechas", "Detalle por empresa", "Datos y calidad"],
        horizontal=True,
        label_visibility="collapsed",
        key="admin_subnavigation",
    )

    # ========================================================
    # RESUMEN GENERAL
    # ========================================================
    if admin_section == "Resumen general":
        total_score, principle_scores, company_scores = calculate_public_scores(filtered)
        levels = public_level_counts(company_scores)
        objective_table = admin_objective_average_table(filtered)
        indicator_table = admin_indicator_average_table(filtered)
        province_df, _ = province_counts_from_repeat_sheets(repeat_sheets, filtered)
        locality_geo_df, _ = georeferenced_localities_from_repeat_sheets(repeat_sheets, filtered)
        company_geo_df = public_georeferenced_points(filtered)

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Empresas", len(filtered))
        k2.metric("Avance promedio", score_display(total_score))
        k3.metric("Nivel promedio", level_from_score(total_score))
        k4.metric("Provincias", len(province_df))
        k5.metric("Localidades GPS", len(locality_geo_df))

        left, right = st.columns([0.8, 1.4])
        with left:
            st.plotly_chart(
                donut(total_score, "Avance agregado", height=280),
                use_container_width=True,
                config=CHART_CONFIG,
                key="admin_general_donut",
            )
        with right:
            st.markdown("#### Distribución de empresas por nivel")
            st.plotly_chart(
                public_levels_figure(levels),
                use_container_width=True,
                config=CHART_CONFIG,
                key="admin_general_levels",
            )

        st.markdown("#### Avance promedio por principio WEPs")
        st.plotly_chart(
            public_weps_figure(principle_scores),
            use_container_width=True,
            config=CHART_CONFIG,
            key="admin_general_weps",
        )

        st.markdown("#### Cobertura territorial del conjunto filtrado")
        render_professional_ecuador_map(
            province_df,
            locality_geo_df,
            company_geo_df,
            height=520,
        )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Objetivos")
            st.plotly_chart(
                admin_objectives_figure(objective_table),
                use_container_width=True,
                config=CHART_CONFIG,
                key="admin_general_objectives",
            )
        with c2:
            st.markdown("#### Principales brechas de indicadores")
            st.plotly_chart(
                admin_indicator_gaps_figure(indicator_table, 12),
                use_container_width=True,
                config=CHART_CONFIG,
                key="admin_general_indicator_gaps",
            )

        with st.expander("Ver tabla completa de objetivos"):
            display_obj = objective_table.copy()
            display_obj["Avance promedio"] = display_obj["Avance promedio"].apply(
                lambda x: None if pd.isna(x) else round(float(x), 1)
            )
            st.dataframe(display_obj, use_container_width=True, hide_index=True)

        with st.expander("Ver tabla completa de 48 indicadores"):
            display_ind = indicator_table.copy()
            display_ind["Avance promedio"] = display_ind["Avance promedio"].apply(
                lambda x: None if pd.isna(x) else round(float(x), 1)
            )
            st.dataframe(display_ind, use_container_width=True, hide_index=True)

    # ========================================================
    # COMPARACIÓN Y BRECHAS
    # ========================================================
    elif admin_section == "Comparación y brechas":
        st.markdown("#### Matriz comparativa empresa × principio WEPs")
        st.plotly_chart(
            admin_heatmap_figure(score_table),
            use_container_width=True,
            config=CHART_CONFIG,
            key="admin_heatmap",
        )

        ranking = score_table.copy().sort_values("Avance general", ascending=False, na_position="last")
        ranking_display = ranking.copy()
        for col in ["Avance general"] + [f"WEP {i}" for i in range(1, 8)]:
            ranking_display[col] = pd.to_numeric(ranking_display[col], errors="coerce").round(1)
        st.markdown("#### Ranking y perfil de avance por empresa")
        st.dataframe(ranking_display, use_container_width=True, hide_index=True)

        selector_type = st.selectbox(
            "Comparar resultados por",
            ["Principio WEPs", "Objetivo", "Indicador"],
            key="admin_compare_type",
        )
        comparison_rows: list[dict[str, Any]] = []

        if selector_type == "Principio WEPs":
            pid = st.selectbox(
                "Principio",
                list(range(1, 8)),
                format_func=lambda x: f"WEP {x} · {next(p['title'] for p in PRINCIPLES if p['id'] == x)}",
                key="admin_compare_wep",
            )
            for _, row in filtered.iterrows():
                objective_scores = {oid: objective_score(row, filtered, oid) for oid in OBJECTIVES}
                score = principle_score(row, filtered, pid, objective_scores)
                comparison_rows.append({"Empresa": str(row.get(company_col, "")), "Avance": score})

        elif selector_type == "Objetivo":
            oid = st.selectbox(
                "Objetivo",
                list(OBJECTIVES.keys()),
                format_func=lambda x: f"Objetivo {x} · {OBJECTIVES[x]['title']}",
                key="admin_compare_objective",
            )
            for _, row in filtered.iterrows():
                comparison_rows.append({
                    "Empresa": str(row.get(company_col, "")),
                    "Avance": objective_score(row, filtered, oid),
                })

        else:
            iid = st.selectbox(
                "Indicador",
                list(INDICATORS.keys()),
                format_func=lambda x: f"Indicador {x} · {INDICATORS[x]['title']}",
                key="admin_compare_indicator",
            )
            for _, row in filtered.iterrows():
                comparison_rows.append({
                    "Empresa": str(row.get(company_col, "")),
                    "Avance": indicator_score(row, filtered, iid),
                })

        comparison = pd.DataFrame(comparison_rows).dropna(subset=["Avance"]).sort_values("Avance")
        if not comparison.empty:
            fig = go.Figure(
                go.Bar(
                    x=comparison["Avance"],
                    y=comparison["Empresa"],
                    orientation="h",
                    marker_color=[color_from_score(v) for v in comparison["Avance"]],
                    text=[f"{v:.1f}%" for v in comparison["Avance"]],
                    textposition="auto",
                    hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
                )
            )
            fig.update_layout(
                height=max(330, min(900, 100 + len(comparison) * 34)),
                xaxis=dict(range=[0, 100], ticksuffix="%", fixedrange=True),
                yaxis=dict(fixedrange=True, automargin=True),
                margin=dict(l=10, r=10, t=20, b=20),
                showlegend=False,
                dragmode=False,
            )
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key="admin_comparison_bar")
        else:
            st.info("No existen valores calculados para la selección actual.")

    # ========================================================
    # DETALLE POR EMPRESA
    # ========================================================
    elif admin_section == "Detalle por empresa":
        company_options = sorted(filtered[company_col].dropna().astype(str).unique().tolist(), key=str.casefold)
        selected_company = st.selectbox(
            "Empresa a revisar sin código de acceso",
            company_options,
            key="admin_company_detail",
        )
        company_rows = filtered[
            filtered[company_col].apply(normalize_company) == normalize_company(selected_company)
        ].copy()
        if company_rows.empty:
            st.warning("No se encontró la empresa seleccionada dentro del conjunto filtrado.")
        else:
            row = latest_row(company_rows)
            st.info(
                "Vista administrativa: se presenta exactamente el mismo diagnóstico detallado disponible para la empresa, "
                "sin solicitar su CLAVE de acceso."
            )
            render_result(row, filtered, selected_company)

            st.divider()
            st.markdown("### Respuestas completas de la encuesta")
            search = st.text_input(
                "Buscar campo o valor",
                key="admin_field_search",
                placeholder="Ej.: remuneración, comité, capacitación, RUC...",
            )
            field_table = _admin_nonempty_field_table(row, search)
            st.dataframe(field_table, use_container_width=True, hide_index=True, height=520)

            st.markdown("### Registros repetibles vinculados")
            found_repeat = False
            for sheet_name, sheet_df in repeat_sheets.items():
                company_repeat = _admin_filter_repeat_for_company(
                    sheet_df,
                    latest,
                    company_col,
                    selected_company,
                )
                if company_repeat.empty:
                    continue
                found_repeat = True
                with st.expander(f"{sheet_name} · {len(company_repeat)} registro(s)"):
                    show = company_repeat.drop(columns=["__admin_company"], errors="ignore").copy()
                    nonempty_cols = [
                        col for col in show.columns
                        if show[col].notna().any() and show[col].astype(str).str.strip().ne("").any()
                    ]
                    st.dataframe(show[nonempty_cols], use_container_width=True, hide_index=True)
            if not found_repeat:
                st.caption("No se encontraron filas repeat vinculadas de forma inequívoca a esta empresa.")

    # ========================================================
    # DATOS Y CALIDAD
    # ========================================================
    else:
        st.markdown("### Calidad de la fuente y estructura KOBO")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Filas cargadas", len(df))
        d2.metric("Empresas únicas", latest[company_col].nunique())
        d3.metric("Columnas", len(df.columns))
        d4.metric("Hojas repeat", len(repeat_sheets))

        st.write(f"Columna empresa detectada: `{company_col}`")
        st.write(f"Campo de acceso detectado: `{code_col}`")
        valid_code_cols = detect_access_code_columns(df)
        st.write(f"Columnas válidas para código de acceso: `{valid_code_cols}`")

        if valid_code_cols:
            code_debug = []
            for col in valid_code_cols:
                if col in df.columns:
                    nonempty = df[col].apply(normalize_access_code).ne("")
                    code_debug.append({
                        "columna": col,
                        "valores no vacíos": int(nonempty.sum()),
                        "valores únicos": int(df.loc[nonempty, col].apply(normalize_access_code).nunique()),
                    })
            if code_debug:
                st.markdown("#### Cobertura del campo de acceso")
                st.dataframe(pd.DataFrame(code_debug), use_container_width=True, hide_index=True)

        repeat_debug = []
        for sheet_name, sheet_df in repeat_sheets.items():
            repeat_debug.append({
                "hoja": sheet_name,
                "filas": len(sheet_df),
                "columnas": len(sheet_df.columns),
                "provincia detectada": detect_repeat_province_column(sheet_df),
                "GPS localidad detectado": detect_repeat_geopoint_column(sheet_df),
            })
        if repeat_debug:
            st.markdown("#### Hojas repeat")
            st.dataframe(pd.DataFrame(repeat_debug), use_container_width=True, hide_index=True)

        score_fields = (
            [p["score_field"] for p in PRINCIPLES]
            + [o["score_field"] for o in OBJECTIVES.values()]
            + [i["score_field"] for i in INDICATORS.values()]
        )
        found = []
        missing = []
        for field in score_fields:
            col = find_field_column(df, field)
            if col:
                found.append({"campo esperado": field, "columna encontrada": col})
            else:
                missing.append({"campo esperado": field})

        q1, q2 = st.columns(2)
        with q1:
            st.markdown(f"#### Campos de cálculo encontrados ({len(found)})")
            st.dataframe(pd.DataFrame(found), use_container_width=True, hide_index=True, height=430)
        with q2:
            st.markdown(f"#### Campos de cálculo no encontrados ({len(missing)})")
            if missing:
                st.dataframe(pd.DataFrame(missing), use_container_width=True, hide_index=True, height=430)
            else:
                st.success("Todos los campos de cálculo esperados fueron detectados.")

        st.markdown("#### Columnas de la tabla principal")
        st.dataframe(pd.DataFrame({"columna": list(df.columns)}), use_container_width=True, hide_index=True, height=500)

        csv_data = filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Descargar registros filtrados (CSV)",
            data=csv_data,
            file_name="turismo_violeta_admin_filtrado.csv",
            mime="text/csv",
            key="admin_download_filtered",
        )


def render_diagnostics(
    df: pd.DataFrame,
    company_col: str | None,
    code_col: str | None,
    repeat_sheets: dict[str, pd.DataFrame] | None = None,
) -> None:
    st.subheader("Panel administrativo integral")
    st.caption(
        "Acceso privado para revisar todas las empresas, comparar resultados, filtrar la base y abrir el detalle completo "
        "de cada organización sin solicitar su código individual."
    )

    password = st.text_input("Clave de administrador", type="password", key="admin_dashboard_password")
    if password != get_secret("ADMIN_PASSWORD", "TurismoVioleta2026"):
        st.warning("Ingrese la clave de administrador para acceder al panel integral.")
        return

    st.success("Acceso administrativo habilitado.")
    st.caption(f"Versión: {APP_VERSION}")

    if st.button(
        "Actualizar datos desde KOBO",
        help="Limpia el caché y vuelve a descargar la exportación configurada en KOBO_DATA_URL.",
        key="admin_refresh_kobo",
    ):
        st.cache_data.clear()
        st.rerun()

    render_admin_dashboard(df, company_col, code_col, repeat_sheets)

def main() -> None:
    render_header()

    url = get_secret("KOBO_DATA_URL", "")
    token = get_secret("KOBO_TOKEN", "")

    if not url:
        st.error("No hay KOBO_DATA_URL configurada en Streamlit Secrets.")
        return

    try:
        with st.spinner("Cargando datos desde KOBO..."):
            df, repeat_sheets = load_data_from_source(url, token)
    except Exception as exc:
        st.error("No se pudo cargar la fuente de datos de KOBO.")
        st.exception(exc)
        st.stop()

    if df.empty:
        st.warning("La fuente de KOBO no devolvió registros.")
        return

    company_col = detect_company_column(df)
    code_col = detect_access_code_column(df)

    # Navegación condicional: solo se renderiza la sección visible.
    # Esto evita inicializar componentes HTML/Leaflet dentro de pestañas ocultas,
    # que era la causa de las teselas incompletas o desalineadas del mapa.
    st.markdown(
        """
        <style>
        div[role="radiogroup"] {
            gap: 0.25rem;
            border-bottom: 1px solid #e7e7ec;
            padding-bottom: 0.15rem;
            margin-bottom: 1.2rem;
        }
        div[role="radiogroup"] label {
            background: transparent;
            padding: 0.42rem 0.72rem;
            border-radius: 8px 8px 0 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    section = st.radio(
        "Navegación principal",
        ["Consulta por empresa", "Resumen público", "Diagnóstico técnico"],
        horizontal=True,
        label_visibility="collapsed",
        key="main_navigation",
    )

    if section == "Consulta por empresa":
        render_company_view(df, company_col, code_col)
    elif section == "Resumen público":
        render_public_summary(df, company_col, repeat_sheets)
    else:
        render_diagnostics(df, company_col, code_col, repeat_sheets)


if __name__ == "__main__":
    main()
