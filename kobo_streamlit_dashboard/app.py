from __future__ import annotations

import io
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

APP_VERSION = "v17 indicadores expandidos sin barra horizontal"

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
def load_data_from_source(url: str, token: str) -> pd.DataFrame:
    if not url:
        return pd.DataFrame()

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

    if lower_url.endswith(".csv") or "data.csv" in lower_url:
        df = pd.read_csv(io.BytesIO(content), dtype=str)
    else:
        df = pd.read_excel(io.BytesIO(content), dtype=str)

    df.columns = [clean_col(c) for c in df.columns]
    df = df.dropna(how="all")
    return df


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


def render_public_summary(df: pd.DataFrame, company_col: str | None) -> None:
    st.subheader("Resumen público agregado")
    col1, col2, col3 = st.columns(3)
    col1.metric("Encuestas", len(df))
    col2.metric("Empresas", df[company_col].nunique() if company_col else "Sin columna")
    date_col = find_column(df, "", ["fecha de envio", "fecha de envío", "submission", "end", "fin"])
    if date_col and len(df):
        col3.metric("Última actualización", parse_date(df.iloc[-1].get(date_col)))
    else:
        col3.metric("Última actualización", "Sin fecha")

    st.info("Los resultados agregados se actualizan desde KOBO según el tiempo de caché configurado en la app. La vista individual requiere nombre de empresa y código de acceso.")


def render_diagnostics(df: pd.DataFrame, company_col: str | None, code_col: str | None) -> None:
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
            df = load_data_from_source(url, token)
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
        render_public_summary(df, company_col)
    with tab3:
        render_diagnostics(df, company_col, code_col)


if __name__ == "__main__":
    main()
