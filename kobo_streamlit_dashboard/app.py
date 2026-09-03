from __future__ import annotations

import io
import json
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

APP_VERSION = "v18.6 mapa Ecuador profesional Esri Leaflet"

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


@st.cache_data(ttl=300, show_spinner=False)
def load_data_from_source(url: str, token: str) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Carga la exportación de KOBO y conserva las hojas de grupos repetibles.

    KOBO exporta los ``begin_repeat`` a hojas adicionales del XLSX. La versión
    anterior leía únicamente la primera hoja, por lo que campos como
    ``provincia_operacion`` dentro de ``localidades_operacion`` no estaban
    disponibles para el resumen público.

    Devuelve:
      1. DataFrame principal (primera hoja del libro, como en la versión previa).
      2. Diccionario con las demás hojas/repeats del XLSX.
    """
    if not url:
        return pd.DataFrame(), {}

    clean_token = sanitize_kobo_token(token)
    headers = {}
    if clean_token:
        headers["Authorization"] = f"Token {clean_token}"

    response = requests.get(url, headers=headers, timeout=90)

    if response.status_code == 401:
        raise RuntimeError(
            "KOBO rechazó la autenticación (401 Unauthorized). Revise que KOBO_TOKEN contenga solo la clave API, "
            "sin la palabra Token, sin comillas adicionales, sin espacios, y que pertenezca a la cuenta del servidor "
            "eu.kobotoolbox.org con permiso sobre este formulario."
        )

    if response.status_code == 403:
        raise RuntimeError(
            "KOBO respondió 403 Forbidden. El token existe, pero la cuenta no tiene permisos suficientes sobre este asset/export. "
            "Comparta el proyecto con esa cuenta o use el token de la cuenta propietaria."
        )

    response.raise_for_status()
    content = response.content
    lower_url = url.lower()
    content_type = str(response.headers.get("Content-Type", "")).lower()

    # CSV no puede contener hojas repeat separadas. Se mantiene compatibilidad.
    if lower_url.endswith(".csv") or "data.csv" in lower_url or "text/csv" in content_type:
        df = pd.read_csv(io.BytesIO(content), dtype=str)
        df.columns = [clean_col(c) for c in df.columns]
        df = df.dropna(how="all")
        return df, {}

    # En XLSX se leen TODAS las hojas. La primera continúa siendo la tabla principal.
    try:
        workbook = pd.read_excel(io.BytesIO(content), sheet_name=None, dtype=str)
    except Exception:
        # Respaldo: algunas URLs de exportación no exponen claramente el formato.
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
    repeat_sheets = {
        name: sheet
        for name, sheet in cleaned_sheets.items()
        if name != main_sheet_name
    }

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
    preferred = get_secret("COMPANY_COLUMN", "")
    return find_column(
        df,
        preferred,
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
    preferred = get_secret("ACCESS_CODE_COLUMN", "")
    columns = detect_access_code_columns(df)
    if preferred:
        preferred_found = find_column(df, preferred, [])
        if preferred_found:
            return preferred_found
    return columns[0] if columns else None


def detect_access_code_columns(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []

    preferred = get_secret("ACCESS_CODE_COLUMN", "")
    ordered: list[str] = []

    def add(col: str | None) -> None:
        if col and col in df.columns and col not in ordered:
            ordered.append(col)

    add(find_column(df, preferred, []))

    strong_terms = [
        "cree un codigo de acceso",
        "cree un código de acceso",
        "codigo de acceso",
        "código de acceso",
        "ingresar luego",
        "codigo para poder ingresar",
        "código para poder ingresar",
        "necesario tener este codigo",
        "necesario tener este código",
    ]
    strong_terms_norm = [norm_text(x) for x in strong_terms]
    for col in df.columns:
        col_norm = norm_text(col)
        if any(term in col_norm for term in strong_terms_norm):
            add(col)

    for col in df.columns:
        col_norm = norm_text(col)
        if col_norm in {"codigo", "código", "codigo_acceso", "codigo acceso", "_id", "uuid", "meta/instanceid", "instanceid"}:
            add(col)

    return ordered


def normalize_access_code(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
    text = text.replace("\xa0", " ").strip().strip('"').strip("'").strip()
    text = re.sub(r"\s+", "", text)

    numeric_like = text.replace(",", ".")
    if re.fullmatch(r"\d+\.0+", numeric_like):
        numeric_like = numeric_like.split(".", 1)[0]
    elif re.fullmatch(r"\d+(?:\.\d+)?[eE][+\-]?\d+", numeric_like):
        try:
            numeric_like = str(int(float(numeric_like)))
        except Exception:
            pass
    text = numeric_like
    return text.upper()


def find_valid_records_by_code(company_records: pd.DataFrame, code_columns: list[str], typed_code: str) -> tuple[pd.DataFrame, str | None]:
    typed_norm = normalize_access_code(typed_code)
    if not typed_norm:
        return company_records.iloc[0:0], None

    for col in code_columns:
        if col not in company_records.columns:
            continue
        normalized_series = company_records[col].apply(normalize_access_code)
        mask = normalized_series == typed_norm
        if mask.any():
            return company_records.loc[mask].copy(), col

    return company_records.iloc[0:0], None


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

    if st.button("Actualizar datos desde KOBO", help="Limpia el caché de Streamlit y vuelve a consultar la fuente de KOBO."):
        st.cache_data.clear()
        st.rerun()

    if not company_col:
        st.error("No se detectó la columna de nombre de empresa. Revise COMPANY_COLUMN en Secrets.")
        return

    code_columns = detect_access_code_columns(df)
    if not code_columns:
        st.error("No se detectó ninguna columna de código de acceso. Revise que el formulario exporte el campo 'Código de acceso'.")
        return

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
        st.info("Seleccione la empresa y escriba el código de acceso creado al final de la encuesta.")
        with st.expander("Ayuda rápida"):
            st.write("La app compara el código ignorando espacios accidentales, mayúsculas/minúsculas y conversiones de Excel como .0.")
            st.write(f"Columna de empresa detectada: {company_col}")
            st.write(f"Columnas de código detectadas: {', '.join(code_columns)}")
        return

    valid_records, matched_code_col = find_valid_records_by_code(company_records, code_columns, typed_code)

    if valid_records.empty:
        st.error("No se encontró una encuesta con esa combinación de empresa y código. Verifique que la app ya haya actualizado los datos desde KOBO.")
        with st.expander("Ayuda rápida"):
            st.write(f"Columna usada como empresa: {company_col}")
            st.write(f"Columnas revisadas como código: {', '.join(code_columns)}")
            st.write("El código se compara de forma robusta: sin espacios, sin .0 de Excel y sin diferenciar mayúsculas/minúsculas.")
            st.write("Si acabas de enviar la encuesta, presiona 'Actualizar datos desde KOBO'.")
            admin_pw = st.text_input("Clave de administrador para ver códigos disponibles de esta empresa", type="password", key="admin_code_debug")
            if admin_pw == get_secret("ADMIN_PASSWORD", "TurismoVioleta2026"):
                debug_rows = []
                for col in code_columns:
                    if col in company_records.columns:
                        for raw in company_records[col].dropna().astype(str).unique():
                            debug_rows.append({"columna": col, "valor exportado": raw, "valor normalizado": normalize_access_code(raw)})
                st.dataframe(pd.DataFrame(debug_rows), use_container_width=True, hide_index=True)
        return

    st.success(f"Acceso validado con la columna: {matched_code_col}")
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

    # Primero se buscan nombres oficiales dentro de valores como
    # "17 - Pichincha", "ec_17_pichincha" o etiquetas completas.
    for province in ECUADOR_PROVINCES:
        if province in text:
            return province

    for alias, province in aliases.items():
        if alias in text:
            return province

    # Respaldo para formularios que exporten únicamente código INEC 01-24.
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
    code_match = re.fullmatch(r"(?:0?)([1-9]|1[0-9]|2[0-4])", text)
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


def render_professional_ecuador_map(
    province_df: pd.DataFrame,
    geo_df: pd.DataFrame,
    height: int = 540,
) -> None:
    """Renderiza un mapa Leaflet profesional centrado en Ecuador.

    El mapa se ejecuta dentro de un componente HTML aislado y no depende de
    ``Scattermapbox``/``Scattermap`` de Plotly. Usa Esri World Topographic
    como mapa base profesional, Esri World Street Map y OpenStreetMap como
    alternativas, marcadores agregados por provincia y clustering de puntos
    GPS exactos. No requiere token de Mapbox ni API key de CARTO.
    """

    province_points: list[dict[str, Any]] = []
    if not province_df.empty:
        max_count = max(float(province_df["Registros"].max()), 1.0)
        for _, item in province_df.iterrows():
            try:
                count = int(float(item.get("Registros", 0)))
                lat = float(item.get("lat"))
                lon = float(item.get("lon"))
            except Exception:
                continue

            # Escala visual compacta: 38–62 px según presencia relativa.
            size = 38 + int((count / max_count) * 24)
            province_points.append(
                {
                    "name": str(item.get("Provincia", "Provincia")),
                    "count": count,
                    "lat": lat,
                    "lon": lon,
                    "size": size,
                }
            )

    gps_points: list[dict[str, Any]] = []
    if not geo_df.empty:
        for _, item in geo_df.iterrows():
            try:
                lat = float(item.get("lat"))
                lon = float(item.get("lon"))
            except Exception:
                continue

            province = str(item.get("Provincia", "") or "").strip()
            gps_points.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "province": province,
                }
            )

    province_json = json.dumps(province_points, ensure_ascii=False)
    gps_json = json.dumps(gps_points, ensure_ascii=False)

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />

        <link
            rel="stylesheet"
            href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
            integrity="sha256-p4NxAoJBhIINfQ3ynhHdMcVS5tKXYxFt2Z6V8K2Cw7Y="
            crossorigin=""
        />
        <link
            rel="stylesheet"
            href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"
        />
        <link
            rel="stylesheet"
            href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"
        />

        <style>
            html, body {{
                width: 100%;
                height: 100%;
                margin: 0;
                padding: 0;
                background: transparent;
                font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }}

            #map-wrap {{
                position: relative;
                width: 100%;
                height: {height - 4}px;
                border: 1px solid #e7e4f0;
                border-radius: 18px;
                overflow: hidden;
                box-shadow: 0 4px 18px rgba(31, 24, 67, 0.07);
                background: #eef5f8;
            }}

            #ecuador-map {{
                width: 100%;
                height: 100%;
            }}

            .leaflet-control-zoom a {{
                color: #2c2454 !important;
                border: none !important;
            }}

            .leaflet-control-zoom {{
                border: none !important;
                box-shadow: 0 3px 14px rgba(20, 20, 40, 0.16) !important;
                border-radius: 10px !important;
                overflow: hidden;
            }}

            .leaflet-control-attribution {{
                font-size: 9px !important;
                background: rgba(255,255,255,0.86) !important;
            }}

            .province-div-icon,
            .gps-div-icon {{
                background: transparent;
                border: none;
            }}

            .province-bubble {{
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 999px;
                background: linear-gradient(145deg, #7c4dce, #5d35b2);
                border: 3px solid rgba(255,255,255,0.96);
                box-shadow: 0 5px 18px rgba(80, 43, 157, 0.34);
                color: #ffffff;
                font-weight: 800;
                font-size: 14px;
                line-height: 1;
                user-select: none;
            }}

            .gps-pin {{
                position: relative;
                width: 30px;
                height: 38px;
                transform: translate(-1px, -2px);
                filter: drop-shadow(0 4px 5px rgba(0,0,0,0.22));
            }}

            .gps-pin svg {{
                width: 30px;
                height: 38px;
                display: block;
            }}

            .leaflet-tooltip.tv-tooltip {{
                border: 0;
                border-radius: 9px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.15);
                padding: 8px 10px;
                color: #29233f;
                font-size: 12px;
                font-weight: 600;
            }}

            .map-legend {{
                background: rgba(255,255,255,0.94);
                border: 1px solid rgba(227,223,239,0.95);
                border-radius: 12px;
                padding: 9px 12px;
                box-shadow: 0 3px 14px rgba(20, 20, 40, 0.12);
                color: #4e4a61;
                font-size: 11px;
                line-height: 1.35;
            }}

            .map-legend-row {{
                display: flex;
                align-items: center;
                gap: 7px;
                margin: 3px 0;
                white-space: nowrap;
            }}

            .legend-province {{
                width: 13px;
                height: 13px;
                border-radius: 50%;
                background: #6d43c0;
                border: 2px solid white;
                box-shadow: 0 1px 4px rgba(0,0,0,0.18);
            }}

            .legend-gps {{
                width: 10px;
                height: 10px;
                border-radius: 50% 50% 50% 0;
                background: #f47a48;
                transform: rotate(-45deg);
                margin-left: 2px;
            }}

            .map-title-chip {{
                background: rgba(255,255,255,0.95);
                border: 1px solid rgba(227,223,239,0.95);
                border-radius: 12px;
                padding: 9px 12px;
                box-shadow: 0 3px 14px rgba(20, 20, 40, 0.12);
                color: #252047;
            }}

            .map-title-chip strong {{
                display: block;
                font-size: 12px;
                margin-bottom: 2px;
            }}

            .map-title-chip span {{
                font-size: 10px;
                color: #777185;
            }}

            .marker-cluster-small,
            .marker-cluster-medium,
            .marker-cluster-large {{
                background-color: rgba(111, 68, 194, 0.22) !important;
            }}

            .marker-cluster-small div,
            .marker-cluster-medium div,
            .marker-cluster-large div {{
                background-color: #6f44c2 !important;
                color: white !important;
                font-weight: 800 !important;
            }}

            #galapagos-inset {{
                display: none;
                position: absolute;
                left: 14px;
                bottom: 62px;
                width: 205px;
                height: 138px;
                z-index: 800;
                border: 3px solid white;
                border-radius: 12px;
                box-shadow: 0 5px 18px rgba(0,0,0,0.23);
                overflow: hidden;
                background: #eef5f8;
            }}

            #galapagos-label {{
                display: none;
                position: absolute;
                left: 22px;
                bottom: 174px;
                z-index: 900;
                background: rgba(255,255,255,0.93);
                color: #312858;
                border-radius: 7px;
                padding: 3px 7px;
                font-size: 10px;
                font-weight: 700;
                box-shadow: 0 2px 8px rgba(0,0,0,0.12);
            }}
        </style>
    </head>

    <body>
        <div id="map-wrap">
            <div id="ecuador-map"></div>
            <div id="galapagos-label">Galápagos</div>
            <div id="galapagos-inset"></div>
        </div>

        <script
            src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
            crossorigin=""
        ></script>
        <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

        <script>
            const provincePoints = {province_json};
            const gpsPoints = {gps_json};

            const mainlandBounds = L.latLngBounds(
                [-5.45, -81.35],
                [1.65, -74.95]
            );

            const maxBounds = L.latLngBounds(
                [-7.0, -83.0],
                [3.0, -73.5]
            );

            const map = L.map('ecuador-map', {{
                zoomControl: false,
                attributionControl: true,
                preferCanvas: true,
                maxBounds: maxBounds,
                maxBoundsViscosity: 0.72,
                minZoom: 5,
                maxZoom: 13
            }});

            // Mapas base profesionales sin CARTO ni Mapbox.
            // Esri Topographic se utiliza por defecto; si sus teselas fallan,
            // el mapa cambia automáticamente a OpenStreetMap.
            const esriTopo = L.tileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}',
                {{
                    maxZoom: 19,
                    attribution: 'Tiles &copy; Esri &mdash; Sources: Esri, HERE, Garmin, USGS, NGA, EPA, NPS, INCREMENT P'
                }}
            );

            const esriStreet = L.tileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}',
                {{
                    maxZoom: 19,
                    attribution: 'Tiles &copy; Esri'
                }}
            );

            const osm = L.tileLayer(
                'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
                {{
                    maxZoom: 19,
                    attribution: '&copy; OpenStreetMap contributors'
                }}
            );

            let baseLayer = esriTopo;
            let esriTileErrors = 0;
            esriTopo.on('tileerror', function() {{
                esriTileErrors += 1;
                if (esriTileErrors >= 4 && map.hasLayer(esriTopo)) {{
                    map.removeLayer(esriTopo);
                    osm.addTo(map);
                    baseLayer = osm;
                }}
            }});

            esriTopo.addTo(map);
            map.fitBounds(mainlandBounds, {{padding: [8, 8]}});

            L.control.zoom({{position: 'topright'}}).addTo(map);
            L.control.scale({{position: 'bottomright', imperial: false}}).addTo(map);
            L.control.layers(
                {{
                    'Topográfico': esriTopo,
                    'Calles': esriStreet,
                    'OpenStreetMap': osm
                }},
                null,
                {{position: 'topright', collapsed: true}}
            ).addTo(map);

            const titleControl = L.control({{position: 'topleft'}});
            titleControl.onAdd = function() {{
                const div = L.DomUtil.create('div', 'map-title-chip');
                div.innerHTML = '<strong>Ecuador</strong><span>Cobertura territorial y puntos GPS</span>';
                L.DomEvent.disableClickPropagation(div);
                return div;
            }};
            titleControl.addTo(map);

            const legend = L.control({{position: 'bottomleft'}});
            legend.onAdd = function() {{
                const div = L.DomUtil.create('div', 'map-legend');
                div.innerHTML = `
                    <div class="map-legend-row">
                        <span class="legend-province"></span>
                        <span>Cobertura por provincia</span>
                    </div>
                    <div class="map-legend-row">
                        <span class="legend-gps"></span>
                        <span>Georreferencia exacta</span>
                    </div>
                `;
                L.DomEvent.disableClickPropagation(div);
                return div;
            }};
            legend.addTo(map);

            // Marcadores agregados de provincia.
            provincePoints
                .filter(p => p.lon > -85)
                .forEach(p => {{
                    const icon = L.divIcon({{
                        className: 'province-div-icon',
                        html: `<div class="province-bubble" style="width:${{p.size}}px;height:${{p.size}}px;">${{p.count}}</div>`,
                        iconSize: [p.size, p.size],
                        iconAnchor: [p.size / 2, p.size / 2]
                    }});

                    L.marker([p.lat, p.lon], {{icon, zIndexOffset: 250}})
                        .bindTooltip(
                            `<b>${{p.name}}</b><br>${{p.count}} registro${{p.count === 1 ? '' : 's'}} territorial${{p.count === 1 ? '' : 'es'}}`,
                            {{className: 'tv-tooltip', direction: 'top', offset: [0, -8]}}
                        )
                        .addTo(map);
                }});

            // Puntos GPS con clustering.
            const cluster = L.markerClusterGroup({{
                showCoverageOnHover: false,
                spiderfyOnMaxZoom: true,
                removeOutsideVisibleBounds: true,
                maxClusterRadius: 48,
                disableClusteringAtZoom: 10
            }});

            const pinSvg = `
                <div class="gps-pin">
                    <svg viewBox="0 0 30 38" xmlns="http://www.w3.org/2000/svg">
                        <path d="M15 1C7.8 1 2 6.8 2 14c0 9.4 13 23 13 23s13-13.6 13-23C28 6.8 22.2 1 15 1z"
                              fill="#f47a48" stroke="#ffffff" stroke-width="2"/>
                        <circle cx="15" cy="14" r="5" fill="#ffffff"/>
                    </svg>
                </div>`;

            gpsPoints
                .filter(p => p.lon > -85)
                .forEach(p => {{
                    const icon = L.divIcon({{
                        className: 'gps-div-icon',
                        html: pinSvg,
                        iconSize: [30, 38],
                        iconAnchor: [15, 36],
                        popupAnchor: [0, -32]
                    }});

                    const marker = L.marker([p.lat, p.lon], {{icon}});
                    marker.bindTooltip(
                        p.province
                            ? `<b>Registro georreferenciado</b><br>${{p.province}}`
                            : '<b>Registro georreferenciado</b>',
                        {{className: 'tv-tooltip', direction: 'top', offset: [0, -20]}}
                    );
                    cluster.addLayer(marker);
                }});

            map.addLayer(cluster);

            // Inset automático para Galápagos cuando existan registros allí.
            const galProvincePoints = provincePoints.filter(p => p.lon <= -85);
            const galGpsPoints = gpsPoints.filter(p => p.lon <= -85);

            if (galProvincePoints.length > 0 || galGpsPoints.length > 0) {{
                document.getElementById('galapagos-inset').style.display = 'block';
                document.getElementById('galapagos-label').style.display = 'block';

                const galMap = L.map('galapagos-inset', {{
                    zoomControl: false,
                    attributionControl: false,
                    dragging: true,
                    scrollWheelZoom: false,
                    doubleClickZoom: true,
                    minZoom: 5,
                    maxZoom: 12
                }});
                const galEsri = L.tileLayer(
                    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}',
                    {{
                        maxZoom: 19,
                        attribution: 'Tiles &copy; Esri'
                    }}
                );
                const galOsm = L.tileLayer(
                    'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
                    {{maxZoom: 19}}
                );
                let galTileErrors = 0;
                galEsri.on('tileerror', function() {{
                    galTileErrors += 1;
                    if (galTileErrors >= 3 && galMap.hasLayer(galEsri)) {{
                        galMap.removeLayer(galEsri);
                        galOsm.addTo(galMap);
                    }}
                }});
                galEsri.addTo(galMap);
                galMap.setView([-0.75, -90.55], 7);

                galProvincePoints.forEach(p => {{
                    const insetSize = Math.max(30, Math.min(44, p.size - 8));
                    const icon = L.divIcon({{
                        className: 'province-div-icon',
                        html: `<div class="province-bubble" style="width:${{insetSize}}px;height:${{insetSize}}px;font-size:12px;">${{p.count}}</div>`,
                        iconSize: [insetSize, insetSize],
                        iconAnchor: [insetSize / 2, insetSize / 2]
                    }});
                    L.marker([p.lat, p.lon], {{icon}})
                        .bindTooltip(`<b>${{p.name}}</b><br>${{p.count}} registro(s)`, {{className: 'tv-tooltip'}})
                        .addTo(galMap);
                }});

                galGpsPoints.forEach(p => {{
                    const icon = L.divIcon({{
                        className: 'gps-div-icon',
                        html: pinSvg,
                        iconSize: [27, 34],
                        iconAnchor: [13, 32]
                    }});
                    L.marker([p.lat, p.lon], {{icon}}).addTo(galMap);
                }});
            }}

            // Evita que el scroll de la página haga zoom accidental en el mapa.
            map.scrollWheelZoom.disable();
            map.on('click', function() {{
                map.scrollWheelZoom.enable();
            }});
            map.on('mouseout', function() {{
                map.scrollWheelZoom.disable();
            }});

            // Corrige tamaño tras cargar el iframe de Streamlit.
            setTimeout(() => map.invalidateSize(), 250);
            setTimeout(() => map.invalidateSize(), 800);
        </script>
    </body>
    </html>
    """

    st.components.v1.html(
        html,
        height=height,
        scrolling=False,
    )


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

    # Los puntos exactos se toman de la georreferenciación 5.1 de la tabla principal.
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

    # Cobertura territorial
    st.markdown(
        """
        <div class="tv-card-title">Cobertura territorial y georreferenciación</div>
        <div class="tv-section-caption">
            Provincias declaradas en las localidades de operación y puntos GPS registrados en KOBO.
        </div>
        """,
        unsafe_allow_html=True,
    )

    map_col, rank_col = st.columns([3.4, 1])

    with map_col:
        if not province_df.empty or not geo_df.empty:
            render_professional_ecuador_map(
                province_df,
                geo_df,
                height=540,
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

        if not province_df.empty:
            ranking = province_df.sort_values("Registros", ascending=False).head(5)
            for rank, (_, item) in enumerate(ranking.iterrows(), start=1):
                st.markdown(
                    f"""
                    <div class="tv-rank-row">
                        <span>
                            <span class="tv-rank-number">{rank}</span>
                            {item["Provincia"]}
                        </span>
                        <b>{int(item["Registros"])}</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Sin información provincial disponible.")

        if province_source == "repeat" and province_repeat_sheets:
            st.markdown(
                f"""
                <div style="margin-top:15px; color:#767b8c; font-size:0.82rem;">
                    Cobertura obtenida de localidades de operación registradas en KOBO.
                </div>
                """,
                unsafe_allow_html=True,
            )

        if not geo_df.empty:
            st.markdown(
                f"""
                <div style="margin-top:10px; color:#767b8c; font-size:0.82rem;">
                    📍 {len(geo_df)} empresas cuentan con coordenadas geográficas válidas.
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
            La consulta detallada por empresa permanece protegida mediante código de acceso.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_diagnostics(
    df: pd.DataFrame,
    company_col: str | None,
    code_col: str | None,
    repeat_sheets: dict[str, pd.DataFrame] | None = None,
) -> None:
    st.subheader("Diagnóstico técnico")
    password = st.text_input("Clave de administrador", type="password")
    if password != get_secret("ADMIN_PASSWORD", "TurismoVioleta2026"):
        st.warning("Ingrese la clave de administrador para ver el diagnóstico.")
        return

    st.write(f"Versión: {APP_VERSION}")
    st.write(f"Filas cargadas: {len(df)}")
    st.write(f"Columnas cargadas: {len(df.columns)}")
    st.write(f"Columna empresa detectada: {company_col}")
    st.write(f"Columna código principal detectada: {code_col}")
    st.write(f"Todas las columnas posibles de código: {detect_access_code_columns(df)}")

    repeat_sheets = repeat_sheets or {}
    st.write(f"Hojas repeat detectadas: {list(repeat_sheets.keys()) if repeat_sheets else 'Ninguna'}")
    if repeat_sheets:
        repeat_debug = []
        for sheet_name, sheet_df in repeat_sheets.items():
            repeat_debug.append(
                {
                    "hoja": sheet_name,
                    "filas": len(sheet_df),
                    "columnas": len(sheet_df.columns),
                    "provincia detectada": detect_repeat_province_column(sheet_df),
                }
            )
        st.write("Diagnóstico de hojas repeat:")
        st.dataframe(pd.DataFrame(repeat_debug), use_container_width=True, hide_index=True)

    score_fields = [p["score_field"] for p in PRINCIPLES] + [o["score_field"] for o in OBJECTIVES.values()] + [i["score_field"] for i in INDICATORS.values()]
    found = []
    missing = []
    for field in score_fields:
        col = find_field_column(df, field)
        if col:
            found.append({"campo esperado": field, "columna encontrada": col})
        else:
            missing.append({"campo esperado": field})
    st.write("Campos de cálculo encontrados:")
    st.dataframe(pd.DataFrame(found), use_container_width=True, hide_index=True)
    st.write("Campos de cálculo no encontrados:")
    st.dataframe(pd.DataFrame(missing), use_container_width=True, hide_index=True)

    st.write("Primeras columnas detectadas:")
    st.dataframe(pd.DataFrame({"columna": list(df.columns)[:120]}), use_container_width=True, hide_index=True)


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

    tab1, tab2, tab3 = st.tabs(["Consulta por empresa", "Resumen público", "Diagnóstico técnico"])
    with tab1:
        render_company_view(df, company_col, code_col)
    with tab2:
        render_public_summary(df, company_col, repeat_sheets)
    with tab3:
        render_diagnostics(df, company_col, code_col, repeat_sheets)


if __name__ == "__main__":
    main()
