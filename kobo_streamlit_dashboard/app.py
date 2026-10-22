from __future__ import annotations

"""Turismo Violeta, visualizador del screening V18.

Archivo principal autónomo: streamlit run visualizador_turismo_violeta_v18.py
Dependencias (las mismas del visualizador original):
    streamlit>=1.50,<2 pandas>=2.2,<4
    plotly>=5.24,<8 openpyxl>=3.1,<4
Secrets existentes: KOBO_DATA_URL, KOBO_TOKEN, ADMIN_PASSWORD.
KOBO_DATA_URL es opcional: la fuente predeterminada es la exportación TURISMO V18.
La URL de la antigua exportación facilitada en esta revisión se migra a TURISMO.
Otros opcionales: COMPANY_COLUMN, ACCESS_CODE_COLUMN, PROVINCE_COLUMN, KOBO_FORM_URL.
No incluir credenciales en este archivo. ADMIN_PASSWORD no tiene valor por defecto.

La lógica analítica usa la biblioteca estándar y puede importarse sin Streamlit.
Los indicadores antiguos no se convierten al modelo V18. El cálculo se reconstruye
desde las respuestas, se contrasta con sc_* y se muestra la calidad por separado.
"""

import csv
import hashlib
import hmac
import html
import io
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

APP_VERSION = 'v23.5 · diagnóstico V18 y consulta compacta'
MODEL_VERSION = 'TV_SCREENING_20261021_V18_VMT'
DASHBOARD_URL = 'https://dashboard-turismo-violeta.streamlit.app/'
SCREENING_SPEC = {'dimensions': [{'id': 1, 'title': 'Gobernanza, compromiso institucional y liderazgo', 'weight': 15},
                {'id': 2, 'title': 'Corresponsabilidad de los cuidados y bienestar', 'weight': 10},
                {'id': 3, 'title': 'Cadena de valor, proveedores, comunidades y territorio', 'weight': 10},
                {'id': 4,
                 'title': 'Experiencias turísticas seguras y con enfoque de igualdad de género',
                 'weight': 20},
                {'id': 5,
                 'title': 'Prevención y respuesta frente a la VBG, el acoso y la discriminación',
                 'weight': 30},
                {'id': 6, 'title': 'Igualdad laboral, desarrollo profesional y trabajo digno', 'weight': 15}],
 'questions': [{'num': 31,
                'name': 'weps_31',
                'dim': 1,
                'dimension': 'Gobernanza, compromiso institucional y liderazgo',
                'weight': 20,
                'question': 'La empresa u organización turística cuenta con un plan de igualdad de género '
                            'vigente o con otras herramientas de planificación para la igualdad de género.',
                'help': 'Responder Sí si existe un plan vigente de igualdad de género u otra herramienta de '
                        'planificación para la igualdad. Las etapas del plan se registran a continuación y '
                        'no se suponen por esta respuesta.',
                'positive': 'Plan de igualdad de género u otra herramienta de planificación vigente '
                            'declarada.',
                'action': 'Definir una herramienta inicial de planificación para la igualdad de género con '
                          'objetivos, acciones y responsables.',
                'wep': 1,
                'secondary': '',
                'objective': 'O03, gobernanza',
                'limit': 'Identifica la existencia de un plan o de otra herramienta de planificación. No '
                         'acredita aprobación, implementación o comunicación: estas etapas se recogen en una '
                         'selección múltiple complementaria. No calcula I047 ni ejecución del plan.',
                'gate': '',
                'gates_any': [],
                'critical': False,
                'source_item': 'P1'},
               {'num': 6,
                'name': 'weps_06',
                'dim': 1,
                'dimension': 'Gobernanza, compromiso institucional y liderazgo',
                'weight': 25,
                'question': 'La empresa u organización turística ha designado una instancia responsable '
                            '(Comité de Género u otra) o punto focal, con funciones definidas para '
                            'implementar acciones de igualdad de género.',
                'help': 'Puede tratarse de un Comité de Género, otra instancia o un punto focal. Responder '
                        'Sí si se ha designado y tiene funciones definidas para implementar acciones de '
                        'igualdad de género.',
                'positive': 'Instancia responsable o punto focal designado con funciones de implementación '
                            'de acciones de igualdad de género.',
                'action': 'Designar una instancia responsable o punto focal y definir sus funciones para '
                          'implementar acciones de igualdad de género.',
                'wep': 1,
                'secondary': '',
                'objective': 'O03, gobernanza',
                'limit': 'Identifica designación y funciones, sin exigir una figura única ni una formalidad '
                         'adicional a la redacción definitiva. No calcula composición del Comité, número de '
                         'actas ni cobertura de sus acciones.',
                'gate': '',
                'gates_any': [],
                'critical': False,
                'source_item': 'P2'},
               {'num': 5,
                'name': 'weps_05',
                'dim': 1,
                'dimension': 'Gobernanza, compromiso institucional y liderazgo',
                'weight': 20,
                'question': 'Las empresas u organizaciones aplican medidas concretas para aumentar la '
                            'participación de las mujeres en cargos de liderazgo, administración o de toma '
                            'de decisiones o áreas donde participan mayoritariamente los hombres en el '
                            'sector turístico.',
                'help': 'Considerar medidas concretas en liderazgo, administración, decisiones o áreas del '
                        'sector turístico donde participan mayoritariamente los hombres.',
                'positive': 'Medidas concretas para aumentar la participación de mujeres en liderazgo, '
                            'administración, decisiones o áreas de predominio masculino.',
                'action': 'Identificar una barrera y aplicar una medida de participación de mujeres en '
                          'liderazgo, administración, decisiones o áreas de predominio masculino.',
                'wep': 1,
                'secondary': '4',
                'objective': 'O01/O02, liderazgo',
                'limit': 'No calcula I007 ni porcentaje de mujeres en liderazgo; faltan personas por sexo y '
                         'nivel.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'P3'},
               {'num': 28,
                'name': 'weps_28',
                'dim': 1,
                'dimension': 'Gobernanza, compromiso institucional y liderazgo',
                'weight': 20,
                'question': 'La empresa u organización turística revisa anualmente los resultados de las '
                            'acciones de su plan de igualdad con la instancia responsable y registra los '
                            'ajustes acordados.',
                'help': 'Responder Sí si la revisión se realizó durante los últimos doce meses con la '
                        'instancia responsable y existen registros de los ajustes acordados.',
                'positive': 'Revisión anual con la instancia responsable y ajustes registrados.',
                'action': 'Revisar los resultados del plan con la instancia responsable y registrar los '
                          'ajustes, sus responsables y plazos.',
                'wep': 7,
                'secondary': '',
                'objective': 'O12, seguimiento',
                'limit': 'Identifica revisión anual y registro de ajustes. No calcula I046 ni I047 sin '
                         'número de informes y acciones planificadas y ejecutadas.',
                'gate': '',
                'gates_any': [],
                'critical': False,
                'source_item': 'P4'},
               {'num': 30,
                'name': 'weps_30',
                'dim': 1,
                'dimension': 'Gobernanza, compromiso institucional y liderazgo',
                'weight': 15,
                'question': 'La empresa u organización comunica sus acciones y avances en igualdad de género '
                            'mediante documentos de respaldo.',
                'help': 'Responder sobre comunicación de acciones y avances en igualdad de género respaldada '
                        'por documentos. La redacción definitiva no exige un informe anual ni difusión '
                        'pública.',
                'positive': 'Acciones y avances en igualdad de género comunicados con documentos de '
                            'respaldo.',
                'action': 'Reunir documentos que respalden las acciones y avances en igualdad de género y '
                          'utilizarlos para su comunicación.',
                'wep': 7,
                'secondary': '',
                'objective': 'O13, comunicación de avances',
                'limit': 'Identifica comunicación respaldada documentalmente. No requiere carácter público, '
                         'periodicidad anual o formato de informe. El detalle opcional no puntúa ni calcula '
                         'número de informes o I048.',
                'gate': '',
                'gates_any': [],
                'critical': False,
                'source_item': 'P5'},
               {'num': 33,
                'name': 'weps_33',
                'dim': 2,
                'dimension': 'Corresponsabilidad de los cuidados y bienestar',
                'weight': 15,
                'question': 'La empresa u organización identifica anualmente las necesidades de cuidado y '
                            'conciliación de su personal, considerando niñas y niños, adultos mayores, '
                            'personas con discapacidad y personas con movilidad reducida.',
                'help': 'Considerar una identificación realizada durante los últimos doce meses e incluir '
                        'niñas y niños, adultos mayores, personas con discapacidad y personas con movilidad '
                        'reducida.',
                'positive': 'Necesidades de cuidado y conciliación del personal identificadas anualmente.',
                'action': 'Realizar y registrar una revisión anual de las necesidades de cuidado y '
                          'conciliación del personal.',
                'wep': 2,
                'secondary': '',
                'objective': 'Cuidados y conciliación',
                'limit': 'No mide personas beneficiarias, cobertura ni uso efectivo de apoyos.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'P6'},
               {'num': 7,
                'name': 'weps_07',
                'dim': 2,
                'dimension': 'Corresponsabilidad de los cuidados y bienestar',
                'weight': 40,
                'question': 'La empresa u organización turística aplica los derechos de maternidad, '
                            'paternidad, lactancia y los permisos de cuidado que correspondan a su régimen '
                            'laboral, y ofrece o facilita apoyos y servicios de cuidado acordes con las '
                            'necesidades identificadas, incluidas las condiciones o espacios de lactancia '
                            'que correspondan a sus obligaciones.',
                'help': 'Pregunta unificada P7 y P9. Considerar derechos y permisos del régimen laboral, '
                        'apoyos y servicios según las necesidades identificadas y condiciones de lactancia '
                        'aplicables según el tamaño y obligaciones de la organización. Responder Sí cuando '
                        'se cubran los componentes que correspondan.',
                'positive': 'Derechos y permisos de cuidado aplicados y apoyos, servicios y condiciones de '
                            'lactancia pertinentes disponibles.',
                'action': 'Revisar conjuntamente los derechos y permisos aplicables, los apoyos de cuidado '
                          'necesarios y las condiciones de lactancia que correspondan, y atender el '
                          'componente faltante.',
                'wep': 2,
                'secondary': '',
                'objective': 'Cuidados y conciliación',
                'limit': 'Integra P7/weps_07 y P9/weps_34 en una sola respuesta. No separa el estado de cada '
                         'componente ni calcula cobertura, personas beneficiarias o cumplimiento normativo '
                         'integral. weps_34 deja de ser pregunta y no conserva un peso independiente.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'P7'},
               {'num': 8,
                'name': 'weps_08',
                'dim': 2,
                'dimension': 'Corresponsabilidad de los cuidados y bienestar',
                'weight': 15,
                'question': 'La empresa u organización aplica medidas de organización del trabajo que '
                            'facilitan la conciliación y los cuidados, como flexibilidad horaria, permisos, '
                            'adaptación de turnos, teletrabajo o retorno progresivo.',
                'help': 'Considerar medidas disponibles de organización del trabajo, como flexibilidad '
                        'horaria, permisos, adaptación de turnos o retorno progresivo. No se exige que todas '
                        'las modalidades sean viables.',
                'positive': 'Medidas de organización del trabajo para conciliación y cuidados.',
                'action': 'Definir una medida viable de organización del trabajo que responda a las '
                          'responsabilidades de cuidado del personal.',
                'wep': 2,
                'secondary': '',
                'objective': 'Cuidados y conciliación',
                'limit': 'No calcula cobertura de flexibilidad, horas ni personas que la utilizan.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'P8'},
               {'num': 35,
                'name': 'weps_35',
                'dim': 2,
                'dimension': 'Corresponsabilidad de los cuidados y bienestar',
                'weight': 7.5,
                'question': 'La empresa u organización registra la aplicación de las acciones, medidas, y/o '
                            'estrategias de cuidado que han sido requeridas por hombres y mujeres.',
                'help': 'Considerar registros de medidas solicitadas y efectivamente aplicadas, reconociendo '
                        'los requerimientos de mujeres y hombres. Su comunicación se pregunta por separado.',
                'positive': 'Aplicación de acciones, medidas o estrategias de cuidado requeridas por mujeres '
                            'y hombres registrada.',
                'action': 'Crear o completar un registro de las medidas de cuidado solicitadas y aplicadas, '
                          'distinguiendo los requerimientos de mujeres y hombres.',
                'wep': 2,
                'secondary': '',
                'objective': 'Cuidados y conciliación',
                'limit': 'Identifica el registro de la aplicación de medidas de cuidado. No mide su '
                         'comunicación, cantidad, cobertura o igualdad de uso por sexo.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'P10'},
               {'num': 42,
                'name': 'tv_cuidados_comunicacion',
                'dim': 2,
                'dimension': 'Corresponsabilidad de los cuidados y bienestar',
                'weight': 7.5,
                'question': 'La empresa u organización comunica las acciones medidas o estrategias de '
                            'cuidado aplicadas.',
                'help': 'Responder sobre la comunicación de las acciones, medidas o estrategias de cuidado '
                        'aplicadas. La existencia del registro no sustituye esta comunicación.',
                'positive': 'Acciones, medidas o estrategias de cuidado aplicadas comunicadas.',
                'action': 'Comunicar al personal las acciones, medidas o estrategias de cuidado aplicadas.',
                'wep': 2,
                'secondary': '',
                'objective': 'Cuidados y conciliación',
                'limit': 'Identifica comunicación de las medidas de cuidado aplicadas. No calcula alcance de '
                         'la comunicación, personas informadas ni cobertura de medidas.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'P10b'},
               {'num': 38,
                'name': 'weps_38',
                'dim': 2,
                'dimension': 'Corresponsabilidad de los cuidados y bienestar',
                'weight': 15,
                'question': 'La organización turística revisa las condiciones de accesibilidad, inclusión y '
                            'apoyos de cuidado de sus experiencias, recoge las observaciones de visitantes y '
                            'las utiliza para realizar mejoras.',
                'help': 'Incluye las condiciones de accesibilidad, inclusión y apoyos de cuidado durante la '
                        'experiencia turística. Responder Sí si se revisan esas condiciones, se recogen '
                        'observaciones de visitantes y se utilizan para mejorar.',
                'positive': 'Experiencias revisadas en accesibilidad, inclusión y cuidados, con mejoras '
                            'basadas en observaciones de visitantes.',
                'action': 'Revisar las condiciones de accesibilidad, inclusión y cuidado, recoger '
                          'observaciones de visitantes y acordar una mejora concreta.',
                'wep': 2,
                'secondary': '3, 6',
                'objective': 'Cuidados y bienestar en la experiencia turística; aporte a O04',
                'limit': 'Identifica revisión de accesibilidad, inclusión y cuidados y uso de observaciones '
                         'de visitantes. No calcula tasas de accesibilidad, satisfacción ni mejoras '
                         'efectivas.',
                'gate': 'atiende_turistas',
                'gates_any': [],
                'critical': False,
                'source_item': 'P18'},
               {'num': 39,
                'name': 'weps_39',
                'dim': 3,
                'dimension': 'Cadena de valor, proveedores, comunidades y territorio',
                'weight': 25,
                'question': '¿La empresa u organización implementa medidas para priorizar o facilitar la '
                            'participación de empresas y/o emprendimientos liderados por mujeres, '
                            'organizaciones comunitarias y proveedores locales en su cadena de valor?',
                'help': 'Considerar medidas para priorizar o facilitar la participación de negocios '
                        'liderados por mujeres, organizaciones comunitarias y proveedores locales, según los '
                        'vínculos existentes.',
                'positive': 'Medidas para priorizar o facilitar la participación de negocios de mujeres, '
                            'organizaciones comunitarias y proveedores locales.',
                'action': 'Definir y aplicar una medida para facilitar la participación de negocios de '
                          'mujeres, organizaciones comunitarias o proveedores locales.',
                'wep': 5,
                'secondary': '6',
                'objective': 'O09, compras y proveedores',
                'limit': 'Identifica medidas de inclusión en la cadena de valor. No calcula I038 ni '
                         'porcentaje de proveedoras sin importes y proveedores comerciales.',
                'gate': '',
                'gates_any': ['tiene_proveedores', 'vinculo_comunidad'],
                'critical': False,
                'source_item': 'P11'},
               {'num': 24,
                'name': 'weps_24',
                'dim': 3,
                'dimension': 'Cadena de valor, proveedores, comunidades y territorio',
                'weight': 15,
                'question': 'La empresa u organización turística incorpora criterios y compromisos de '
                            'igualdad de género y prevención de violencia y/o acoso en la selección y '
                            'vinculación con proveedores.',
                'help': 'Valorar los criterios y compromisos utilizados en la selección y vinculación con '
                        'proveedores. La actuación ante situaciones de violencia, acoso, abuso o '
                        'discriminación se registra en la siguiente pregunta.',
                'positive': 'Criterios y compromisos de igualdad de género y prevención de violencia o acoso '
                            'en la vinculación con proveedores.',
                'action': 'Incluir criterios y compromisos de igualdad de género y prevención de violencia o '
                          'acoso en la selección y vinculación con proveedores.',
                'wep': 5,
                'secondary': '',
                'objective': 'O09, compras y proveedores',
                'limit': 'Identifica criterios y compromisos con proveedores; la respuesta a incidentes se '
                         'recoge por separado. No calcula I037 ni cobertura de proveedores sin recuentos.',
                'gate': 'tiene_proveedores',
                'gates_any': [],
                'critical': False,
                'source_item': 'P12'},
               {'num': 43,
                'name': 'tv_proveedores_respuesta_vbg',
                'dim': 3,
                'dimension': 'Cadena de valor, proveedores, comunidades y territorio',
                'weight': 10,
                'question': 'La empresa u organización cuenta con procedimiento de actuación ante '
                            'situaciones de violencia de género, acoso, abuso o discriminación.',
                'help': 'En esta dimensión se valora la aplicación del procedimiento a la relación con '
                        'proveedores. Puede apoyarse en el procedimiento general siempre que defina cómo '
                        'actuar en esa relación. El procedimiento general se valora por separado en '
                        'prevención y respuesta a la VBG.',
                'positive': 'Procedimiento de actuación ante violencia de género, acoso, abuso o '
                            'discriminación aplicable a la relación con proveedores.',
                'action': 'Definir cómo actuar ante violencia de género, acoso, abuso o discriminación en la '
                          'vinculación con proveedores.',
                'wep': 5,
                'secondary': '3',
                'objective': 'O09, vinculación con proveedores; aporte a O05 en respuesta a incidentes',
                'limit': 'Identifica la aplicación del procedimiento a la relación con proveedores. No '
                         'sustituye weps_12 ni supone su cumplimiento; no calcula casos, tiempos o eficacia '
                         'de la respuesta.',
                'gate': 'tiene_proveedores',
                'gates_any': [],
                'critical': False,
                'source_item': 'P12b'},
               {'num': 21,
                'name': 'weps_21',
                'dim': 3,
                'dimension': 'Cadena de valor, proveedores, comunidades y territorio',
                'weight': 15,
                'question': 'La empresa u organización implementa acciones para fortalecer las capacidades '
                            'de sus proveedores locales (grupos de mujeres) en su cadena de valor.',
                'help': 'Responder sobre acciones realizadas para fortalecer capacidades de proveedores '
                        'locales conformados por grupos de mujeres, dentro de la cadena de valor.',
                'positive': 'Acciones de fortalecimiento de capacidades de proveedores locales conformados '
                            'por grupos de mujeres.',
                'action': 'Identificar una necesidad de los grupos de mujeres proveedoras locales y realizar '
                          'una acción de fortalecimiento de sus capacidades.',
                'wep': 4,
                'secondary': '5',
                'objective': 'O06, formación de proveedoras',
                'limit': 'No calcula número de actividades ni personas formadas.',
                'gate': 'tiene_proveedores',
                'gates_any': [],
                'critical': False,
                'source_item': 'P13'},
               {'num': 26,
                'name': 'weps_26',
                'dim': 3,
                'dimension': 'Cadena de valor, proveedores, comunidades y territorio',
                'weight': 20,
                'question': 'La empresa u organización turística establece y cumple condiciones claras de '
                            'remuneración y pago con sus proveedores y comunidades, reconociendo el aporte '
                            'de las mujeres en los servicios prestados.',
                'help': 'Responder sobre condiciones claras de remuneración y pago establecidas y cumplidas, '
                        'reconociendo el aporte de las mujeres en los servicios prestados.',
                'positive': 'Condiciones claras de remuneración y pago establecidas y cumplidas, con '
                            'reconocimiento del aporte de las mujeres.',
                'action': 'Establecer condiciones claras de remuneración y pago, reconocer el aporte de las '
                          'mujeres y revisar su cumplimiento.',
                'wep': 6,
                'secondary': '',
                'objective': 'O10, pagos y vínculo comunitario',
                'limit': 'Identifica condiciones de remuneración y pago y reconocimiento del aporte de las '
                         'mujeres. No calcula I043, pagos por sexo ni distribución de beneficios.',
                'gate': '',
                'gates_any': ['tiene_proveedores', 'vinculo_comunidad'],
                'critical': False,
                'source_item': 'P14'},
               {'num': 27,
                'name': 'weps_27',
                'dim': 3,
                'dimension': 'Cadena de valor, proveedores, comunidades y territorio',
                'weight': 15,
                'question': 'La empresa u organización turística acuerda la difusión de los saberes '
                            'ancestrales de mujeres vinculados con la conservación y el patrimonio cultural, '
                            'uso de conocimientos, imágenes y/o expresiones culturales.',
                'help': 'Considerar acuerdos sobre difusión de saberes ancestrales de mujeres vinculados con '
                        'conservación y patrimonio, y sobre el uso de conocimientos, imágenes o expresiones '
                        'culturales.',
                'positive': 'Difusión de saberes ancestrales de mujeres y uso de conocimientos, imágenes o '
                            'expresiones culturales acordados.',
                'action': 'Acordar con las mujeres involucradas la difusión de sus saberes y las condiciones '
                          'de uso de conocimientos, imágenes o expresiones culturales.',
                'wep': 6,
                'secondary': '',
                'objective': 'O11, saberes y patrimonio',
                'limit': 'Identifica acuerdos de difusión y uso de saberes, conocimientos, imágenes o '
                         'expresiones culturales. La redacción definitiva no exige condiciones adicionales '
                         'de retribución. No calcula I044/I045 o número de actividades.',
                'gate': 'vinculo_comunidad',
                'gates_any': [],
                'critical': False,
                'source_item': 'P15'},
               {'num': 36,
                'name': 'weps_36',
                'dim': 4,
                'dimension': 'Experiencias turísticas seguras y con enfoque de igualdad de género',
                'weight': 45,
                'question': 'La organización turística identifica y evalúa riesgos diferenciados que pueden '
                            'afectar la seguridad, el bienestar y la inclusión de mujeres y personas en '
                            'situación de mayor vulnerabilidad durante la experiencia turística.',
                'help': 'Considerar riesgos diferenciados de seguridad, bienestar e inclusión para mujeres y '
                        'personas en mayor vulnerabilidad durante recorridos, transporte, alojamiento u '
                        'otros servicios.',
                'positive': 'Riesgos diferenciados de la experiencia turística identificados y evaluados.',
                'action': 'Identificar y evaluar riesgos diferenciados de una experiencia turística y '
                          'acordar medidas de seguridad, bienestar e inclusión.',
                'wep': 3,
                'secondary': '6',
                'objective': 'O04, riesgos y experiencias seguras',
                'limit': 'No mide incidencia de violencia ni demuestra eliminación de riesgos.',
                'gate': 'atiende_turistas',
                'gates_any': [],
                'critical': False,
                'source_item': 'P16'},
               {'num': 37,
                'name': 'weps_37',
                'dim': 4,
                'dimension': 'Experiencias turísticas seguras y con enfoque de igualdad de género',
                'weight': 35,
                'question': 'La organización turística informa a turistas sobre normas de convivencia, '
                            'conductas no permitidas y canales de ayuda; además, el personal de contacto '
                            'directo ha recibido capacitación durante los últimos doce meses.',
                'help': 'Responder Sí si turistas reciben información sobre normas, conductas no permitidas '
                        'y canales de ayuda, y las personas de contacto directo recibieron formación en los '
                        'últimos doce meses.',
                'positive': 'Información de convivencia y ayuda para turistas, con formación reciente de las '
                            'personas de contacto directo.',
                'action': 'Comunicar normas, conductas no permitidas y canales de ayuda a turistas y formar '
                          'a las personas de contacto directo.',
                'wep': 3,
                'secondary': '6',
                'objective': 'O04/O05, experiencias seguras',
                'limit': 'Identifica información a turistas y formación reciente del contacto directo. No '
                         'calcula cobertura de personas informadas o capacitadas.',
                'gate': 'atiende_turistas',
                'gates_any': [],
                'critical': False,
                'source_item': 'P17'},
               {'num': 22,
                'name': 'weps_22',
                'dim': 4,
                'dimension': 'Experiencias turísticas seguras y con enfoque de igualdad de género',
                'weight': 20,
                'question': 'La organización turística cuenta con lineamientos para usar lenguaje, imágenes '
                            'y mensajes inclusivos, no sexistas y libres de estereotipos, y revisa sus '
                            'contenidos internos, digitales y promocionales.',
                'help': 'Responder Sí si existen lineamientos y se revisan los contenidos internos, '
                        'digitales y promocionales para evitar lenguaje, imágenes o mensajes sexistas y '
                        'estereotipos.',
                'positive': 'Lineamientos de comunicación inclusiva y revisión de contenidos.',
                'action': 'Definir lineamientos de lenguaje e imágenes inclusivos y revisar una pieza '
                          'interna, digital o promocional para corregir sesgos.',
                'wep': 5,
                'secondary': '7',
                'objective': 'O08, comunicación y marketing',
                'limit': 'No calcula I035, número de monitoreos, ni acredita una política de marketing '
                         'completa.',
                'gate': '',
                'gates_any': [],
                'critical': False,
                'source_item': 'P20'},
               {'num': 9,
                'name': 'weps_09',
                'dim': 5,
                'dimension': 'Prevención y respuesta frente a la VBG, el acoso y la discriminación',
                'weight': 10,
                'question': 'La organización turística cuenta con una política o declaración vigente de cero '
                            'tolerancia frente a la violencia basada en género, el acoso laboral, el acoso '
                            'sexual y la discriminación, aprobada y difundida.',
                'help': 'La política o declaración debe estar vigente, aprobada y difundida. Considerar '
                        'violencia basada en género, acoso laboral y sexual y discriminación.',
                'positive': 'Política o declaración de cero tolerancia vigente, aprobada y difundida.',
                'action': 'Aprobar y difundir una política o declaración vigente de cero tolerancia a la '
                          'violencia, el acoso y la discriminación.',
                'wep': 3,
                'secondary': '2',
                'objective': 'O05, prevención de violencia',
                'limit': 'No calcula casos, sanciones ni efectividad de la política.',
                'gate': '',
                'gates_any': [],
                'critical': True,
                'source_item': 'P21'},
               {'num': 12,
                'name': 'weps_12',
                'dim': 5,
                'dimension': 'Prevención y respuesta frente a la VBG, el acoso y la discriminación',
                'weight': 25,
                'question': 'La organización turística dispone de un protocolo o procedimiento escrito para '
                            'prevenir y actuar frente a violencia basada en género, acoso laboral, acoso '
                            'sexual y discriminación.',
                'help': 'Debe existir un protocolo o procedimiento escrito de prevención y actuación frente '
                        'a violencia basada en género, acoso laboral y sexual y discriminación.',
                'positive': 'Protocolo escrito de prevención y actuación frente a violencia, acoso y '
                            'discriminación.',
                'action': 'Preparar un procedimiento escrito de prevención y actuación con pasos, '
                          'responsabilidades y rutas de apoyo.',
                'wep': 3,
                'secondary': '',
                'objective': 'O05, prevención y respuesta',
                'limit': 'No calcula I011/I012 ni resolución en plazo; faltan casos y resultados.',
                'gate': '',
                'gates_any': [],
                'critical': True,
                'source_item': 'P22'},
               {'num': 15,
                'name': 'weps_15',
                'dim': 5,
                'dimension': 'Prevención y respuesta frente a la VBG, el acoso y la discriminación',
                'weight': 25,
                'question': 'La organización turística dispone de canales de reporte accesibles y '
                            'confidenciales y rutas internas y externas de actuación y derivación.',
                'help': 'Responder Sí si los canales son accesibles y confidenciales y se han definido rutas '
                        'internas y externas de actuación y derivación. La existencia de un contacto por sí '
                        'sola no cubre todos los componentes.',
                'positive': 'Canales accesibles y confidenciales y rutas internas y externas de actuación y '
                            'derivación.',
                'action': 'Adecuar un canal accesible y confidencial y definir las rutas internas y externas '
                          'de actuación y derivación.',
                'wep': 3,
                'secondary': '',
                'objective': 'O05, canales y derivación',
                'limit': 'Identifica accesibilidad, confidencialidad y rutas de actuación y derivación. No '
                         'calcula I016/I017 ni eficacia, uso o confianza de los canales.',
                'gate': '',
                'gates_any': [],
                'critical': True,
                'source_item': 'P23'},
               {'num': 16,
                'name': 'weps_16',
                'dim': 5,
                'dimension': 'Prevención y respuesta frente a la VBG, el acoso y la discriminación',
                'weight': 15,
                'question': 'La organización turística conoce las rutas oficiales y ha definido cómo activar '
                            'la protección y comunicar a las autoridades una sospecha de trata de personas o '
                            'explotación sexual de niñas, niños y adolescentes en contextos turísticos.',
                'help': 'Responder Sí si se conocen las rutas oficiales y se ha definido quién y cómo '
                        'activará la protección y la comunicación a las autoridades ante una sospecha.',
                'positive': 'Rutas oficiales conocidas y activación de protección y comunicación a '
                            'autoridades definida.',
                'action': 'Identificar las rutas oficiales y definir responsables y pasos para activar '
                          'protección y comunicar sospechas de trata o explotación sexual.',
                'wep': 3,
                'secondary': '',
                'objective': 'O04, trata y explotación sexual',
                'limit': 'Identifica conocimiento de rutas oficiales y activación de protección y '
                         'comunicación a autoridades. No calcula I018/I019/I036 sin reportes y activaciones '
                         'únicos.',
                'gate': '',
                'gates_any': [],
                'critical': True,
                'source_item': 'P24'},
               {'num': 17,
                'name': 'weps_17',
                'dim': 5,
                'dimension': 'Prevención y respuesta frente a la VBG, el acoso y la discriminación',
                'weight': 15,
                'question': 'El personal de la organización turística y las personas responsables de recibir '
                            'reportes y activar rutas, han recibido capacitación específica durante los '
                            'últimos doce meses sobre violencia basada en género, acoso laboral, acoso '
                            'sexual, discriminación, confidencialidad y no revictimización.',
                'help': 'Responder Sí si en los últimos doce meses recibieron formación tanto el personal '
                        'como quienes reciben reportes y activan rutas. Incluir confidencialidad y no '
                        'revictimización. Si no hay personal adicional, responder sobre la persona '
                        'responsable de la organización.',
                'positive': 'Personal y personas responsables de reportes y rutas con formación específica '
                            'reciente.',
                'action': 'Programar formación específica para el personal y las personas responsables de '
                          'reportes y rutas, con confidencialidad y no revictimización.',
                'wep': 3,
                'secondary': '4',
                'objective': 'O07, formación en prevención',
                'limit': 'Identifica formación reciente del personal y responsables. No calcula I022 ni '
                         'cobertura de capacitación sin participantes únicos y población de referencia.',
                'gate': '',
                'gates_any': [],
                'critical': False,
                'source_item': 'P25'},
               {'num': 23,
                'name': 'weps_23',
                'dim': 5,
                'dimension': 'Prevención y respuesta frente a la VBG, el acoso y la discriminación',
                'weight': 10,
                'question': 'La organización turística cuenta con procedimientos para atender incidentes de '
                            'acoso, discriminación u otras situaciones que afecten a turistas, personal o '
                            'comunidades vinculadas.',
                'help': 'El procedimiento debe cubrir a turistas, personal y comunidades vinculadas según '
                        'corresponda. Responder sobre un procedimiento disponible, aunque no se hayan '
                        'presentado incidentes.',
                'positive': 'Procedimientos de atención de incidentes que afectan a turistas, personal o '
                            'comunidades vinculadas.',
                'action': 'Definir pasos y responsabilidades para atender incidentes que afecten a turistas, '
                          'personal o comunidades vinculadas.',
                'wep': 3,
                'secondary': '6',
                'objective': 'O05, prevención y respuesta a incidentes de violencia, acoso o discriminación',
                'limit': 'Identifica procedimientos disponibles para incidentes que afectan a turistas, '
                         'personal o comunidades. No calcula casos, tiempos, derivaciones ni resolución '
                         'efectiva.',
                'gate': '',
                'gates_any': [],
                'critical': False,
                'source_item': 'P19'},
               {'num': 1,
                'name': 'weps_01',
                'dim': 6,
                'dimension': 'Igualdad laboral, desarrollo profesional y trabajo digno',
                'weight': 20,
                'question': 'La organización turística aplica procedimientos de selección y contratación con '
                            'criterios explícitos de igualdad y no discriminación, mediante convocatorias y '
                            'perfiles libres de sesgos de género.',
                'help': 'Considerar criterios explícitos de igualdad y no discriminación en selección, '
                        'convocatorias y perfiles, aunque no exista una vacante actual.',
                'positive': 'Selección y contratación con criterios de igualdad y convocatorias y perfiles '
                            'sin sesgos.',
                'action': 'Revisar criterios, perfiles y convocatorias de selección y contratación para '
                          'eliminar sesgos de género.',
                'wep': 2,
                'secondary': '1',
                'objective': 'O01, selección y contratación',
                'limit': 'No calcula I003 ni participación por sexo en selección.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'P26'},
               {'num': 2,
                'name': 'weps_02',
                'dim': 6,
                'dimension': 'Igualdad laboral, desarrollo profesional y trabajo digno',
                'weight': 15,
                'question': 'La organización turística aplica criterios transparentes para la promoción y el '
                            'desarrollo profesional, y analiza ascensos, cambios de cargo y acceso a '
                            'capacitación con datos desagregados por sexo.',
                'help': 'Responder Sí si los criterios de promoción y desarrollo son transparentes y se '
                        'analizan ascensos, cambios de cargo y capacitación con datos desagregados por sexo.',
                'positive': 'Promoción y desarrollo con criterios transparentes y análisis de procesos por '
                            'sexo.',
                'action': 'Comunicar criterios transparentes de promoción y desarrollo y revisar los '
                          'registros de ascensos, cambios de cargo y capacitación por sexo.',
                'wep': 2,
                'secondary': '1, 4',
                'objective': 'O01/O06, promoción y desarrollo',
                'limit': 'No calcula I004 ni participación por sexo en promociones.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'P27'},
               {'num': 3,
                'name': 'weps_03',
                'dim': 6,
                'dimension': 'Igualdad laboral, desarrollo profesional y trabajo digno',
                'weight': 15,
                'question': 'La organización turística garantiza igualdad de acceso a procesos de '
                            'capacitación y formación para fortalecer el perfil profesional.',
                'help': 'Responder sobre oportunidades y reglas de acceso a formación, aunque la plantilla '
                        'actual sea de un solo sexo.',
                'positive': 'Igualdad de acceso a capacitación y formación profesional.',
                'action': 'Revisar cómo se ofrecen las oportunidades de formación para asegurar igualdad de '
                          'acceso.',
                'wep': 4,
                'secondary': '2',
                'objective': 'O06, desarrollo profesional',
                'limit': 'No calcula I005 ni cobertura de formación por sexo; faltan participantes y '
                         'población.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'P28'},
               {'num': 4,
                'name': 'weps_04',
                'dim': 6,
                'dimension': 'Igualdad laboral, desarrollo profesional y trabajo digno',
                'weight': 20,
                'question': 'La organización turística analiza periódicamente las remuneraciones para '
                            'identificar y corregir diferencias salariales entre mujeres y hombres en '
                            'trabajos iguales o de igual valor.',
                'help': 'Responder Sí si se revisan periódicamente las remuneraciones de trabajos iguales o '
                        'de igual valor y se adoptan correcciones ante diferencias no justificadas.',
                'positive': 'Análisis periódico de remuneraciones y corrección de diferencias salariales sin '
                            'justificación.',
                'action': 'Comparar remuneraciones de trabajos iguales o de igual valor y acordar cómo '
                          'corregir diferencias no justificadas.',
                'wep': 2,
                'secondary': '1',
                'objective': 'O01, remuneración',
                'limit': 'No calcula I006 ni brecha salarial; faltan remuneraciones comparables por sexo y '
                         'nivel.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'P29'},
               {'num': 18,
                'name': 'weps_18',
                'dim': 6,
                'dimension': 'Igualdad laboral, desarrollo profesional y trabajo digno',
                'weight': 10,
                'question': 'La organización turística ejecuta un Plan de capacitación en igualdad de '
                            'género.',
                'help': 'Responder Sí si existe un plan de capacitación en igualdad de género y se han '
                        'realizado acciones de ese plan. Una capacitación aislada sin plan no cubre el '
                        'enunciado.',
                'positive': 'Plan de capacitación en igualdad de género en ejecución.',
                'action': 'Definir un plan de capacitación en igualdad de género y ejecutar una primera '
                          'actividad.',
                'wep': 4,
                'secondary': '',
                'objective': 'O07, formación en igualdad',
                'limit': 'Identifica ejecución declarada de un plan de capacitación. No calcula I023 a I034 '
                         'ni cobertura sin actividades y participantes únicos.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'P30'},
               {'num': 41,
                'name': 'tv_riesgos_laborales_genero',
                'dim': 6,
                'dimension': 'Igualdad laboral, desarrollo profesional y trabajo digno',
                'weight': 20,
                'question': 'La organización turística evalúa los riesgos laborales con perspectiva de '
                            'género y aplica medidas preventivas acordes con las tareas y las necesidades '
                            'del personal.',
                'help': 'Considerar riesgos físicos, ergonómicos y psicosociales y la adecuación de equipos '
                        'o implementos de protección cuando corresponda. Responder Sí si se evalúan los '
                        'riesgos con perspectiva de género y se aplican medidas preventivas.',
                'positive': 'Riesgos laborales evaluados con perspectiva de género y medidas preventivas '
                            'aplicadas.',
                'action': 'Revisar riesgos físicos, ergonómicos y psicosociales con perspectiva de género y '
                          'aplicar una medida preventiva acorde con las tareas y necesidades del personal.',
                'wep': 3,
                'secondary': '2',
                'objective': 'Trabajo digno, seguridad y salud laboral (aporte preventivo a O01 y O05)',
                'limit': 'Nuevo indicador de screening sobre riesgos laborales y prevención (WEP 3; vínculo '
                         'WEP 2). No tiene un número equivalente verificado entre los 48 indicadores '
                         'anteriores ni mide tasas de accidentes o eficacia preventiva.',
                'gate': 'emplea_personal',
                'gates_any': [],
                'critical': False,
                'source_item': 'N1'}],
 'access_label': 'Para ingresar posteriormente al dashboard, cree un código de acceso que contenga al menos '
                 'un número, una letra mayúscula y un signo. Conserve este código al finalizar el '
                 'formulario.',
 'field_labels': {'consentimiento': '¿La persona que responde acepta registrar la información de la empresa '
                                    'u organización para este diagnóstico?',
                  'nombre_legal': 'Nombre legal de la empresa u organización',
                  'ruc': 'Número de RUC',
                  'registro_turistico': 'Número de registro turístico, si dispone de él',
                  'CLAVE': 'Para ingresar posteriormente al dashboard, cree un código de acceso que contenga '
                           'al menos un número, una letra mayúscula y un signo. Conserve este código al '
                           'finalizar el formulario.',
                  'actividad_turistica': 'Actividad turística principal',
                  'provincia_operacion': 'Provincia de operación',
                  'canton_operacion': 'Cantón de operación',
                  'contacto_nombre': 'Persona de contacto o punto focal',
                  'contacto_correo': 'Correo de contacto',
                  'contacto_telefono': 'Teléfono de contacto',
                  'emplea_personal': '¿La empresa u organización turística tiene personal que trabaja de '
                                     'forma habitual en su operación?',
                  'tiene_proveedores': '¿La empresa u organización turística compra bienes o servicios a '
                                       'proveedores?',
                  'vinculo_comunidad': '¿La empresa u organización turística desarrolla actividades o '
                                       'contrata servicios con una comunidad local?',
                  'atiende_turistas': '¿La empresa u organización turística presta servicios directamente a '
                                      'turistas?',
                  'weps_31': 'La empresa u organización turística cuenta con un plan de igualdad de género '
                             'vigente o con otras herramientas de planificación para la igualdad de género.',
                  'tv_plan_etapas': 'El plan de igualdad de género ha sido:',
                  'weps_06': 'La empresa u organización turística ha designado una instancia responsable '
                             '(Comité de Género u otra) o punto focal, con funciones definidas para '
                             'implementar acciones de igualdad de género.',
                  'weps_05': 'Las empresas u organizaciones aplican medidas concretas para aumentar la '
                             'participación de las mujeres en cargos de liderazgo, administración o de toma '
                             'de decisiones o áreas donde participan mayoritariamente los hombres en el '
                             'sector turístico.',
                  'weps_28': 'La empresa u organización turística revisa anualmente los resultados de las '
                             'acciones de su plan de igualdad con la instancia responsable y registra los '
                             'ajustes acordados.',
                  'weps_30': 'La empresa u organización comunica sus acciones y avances en igualdad de '
                             'género mediante documentos de respaldo.',
                  'tv_comunicacion_igualdad_detalle': 'Detalle los documentos de respaldo utilizados para '
                                                      'comunicar acciones y avances en igualdad de género.',
                  'weps_33': 'La empresa u organización identifica anualmente las necesidades de cuidado y '
                             'conciliación de su personal, considerando niñas y niños, adultos mayores, '
                             'personas con discapacidad y personas con movilidad reducida.',
                  'weps_07': 'La empresa u organización turística aplica los derechos de maternidad, '
                             'paternidad, lactancia y los permisos de cuidado que correspondan a su régimen '
                             'laboral, y ofrece o facilita apoyos y servicios de cuidado acordes con las '
                             'necesidades identificadas, incluidas las condiciones o espacios de lactancia '
                             'que correspondan a sus obligaciones.',
                  'weps_08': 'La empresa u organización aplica medidas de organización del trabajo que '
                             'facilitan la conciliación y los cuidados, como flexibilidad horaria, permisos, '
                             'adaptación de turnos, teletrabajo o retorno progresivo.',
                  'weps_35': 'La empresa u organización registra la aplicación de las acciones, medidas, y/o '
                             'estrategias de cuidado que han sido requeridas por hombres y mujeres.',
                  'tv_cuidados_comunicacion': 'La empresa u organización comunica las acciones medidas o '
                                              'estrategias de cuidado aplicadas.',
                  'weps_38': 'La organización turística revisa las condiciones de accesibilidad, inclusión y '
                             'apoyos de cuidado de sus experiencias, recoge las observaciones de visitantes '
                             'y las utiliza para realizar mejoras.',
                  'weps_39': '¿La empresa u organización implementa medidas para priorizar o facilitar la '
                             'participación de empresas y/o emprendimientos liderados por mujeres, '
                             'organizaciones comunitarias y proveedores locales en su cadena de valor?',
                  'weps_24': 'La empresa u organización turística incorpora criterios y compromisos de '
                             'igualdad de género y prevención de violencia y/o acoso en la selección y '
                             'vinculación con proveedores.',
                  'tv_proveedores_respuesta_vbg': 'La empresa u organización cuenta con procedimiento de '
                                                  'actuación ante situaciones de violencia de género, acoso, '
                                                  'abuso o discriminación.',
                  'weps_21': 'La empresa u organización implementa acciones para fortalecer las capacidades '
                             'de sus proveedores locales (grupos de mujeres) en su cadena de valor.',
                  'weps_26': 'La empresa u organización turística establece y cumple condiciones claras de '
                             'remuneración y pago con sus proveedores y comunidades, reconociendo el aporte '
                             'de las mujeres en los servicios prestados.',
                  'weps_27': 'La empresa u organización turística acuerda la difusión de los saberes '
                             'ancestrales de mujeres vinculados con la conservación y el patrimonio '
                             'cultural, uso de conocimientos, imágenes y/o expresiones culturales.',
                  'weps_36': 'La organización turística identifica y evalúa riesgos diferenciados que pueden '
                             'afectar la seguridad, el bienestar y la inclusión de mujeres y personas en '
                             'situación de mayor vulnerabilidad durante la experiencia turística.',
                  'weps_37': 'La organización turística informa a turistas sobre normas de convivencia, '
                             'conductas no permitidas y canales de ayuda; además, el personal de contacto '
                             'directo ha recibido capacitación durante los últimos doce meses.',
                  'weps_22': 'La organización turística cuenta con lineamientos para usar lenguaje, imágenes '
                             'y mensajes inclusivos, no sexistas y libres de estereotipos, y revisa sus '
                             'contenidos internos, digitales y promocionales.',
                  'weps_09': 'La organización turística cuenta con una política o declaración vigente de '
                             'cero tolerancia frente a la violencia basada en género, el acoso laboral, el '
                             'acoso sexual y la discriminación, aprobada y difundida.',
                  'weps_12': 'La organización turística dispone de un protocolo o procedimiento escrito para '
                             'prevenir y actuar frente a violencia basada en género, acoso laboral, acoso '
                             'sexual y discriminación.',
                  'weps_15': 'La organización turística dispone de canales de reporte accesibles y '
                             'confidenciales y rutas internas y externas de actuación y derivación.',
                  'weps_16': 'La organización turística conoce las rutas oficiales y ha definido cómo '
                             'activar la protección y comunicar a las autoridades una sospecha de trata de '
                             'personas o explotación sexual de niñas, niños y adolescentes en contextos '
                             'turísticos.',
                  'weps_17': 'El personal de la organización turística y las personas responsables de '
                             'recibir reportes y activar rutas, han recibido capacitación específica durante '
                             'los últimos doce meses sobre violencia basada en género, acoso laboral, acoso '
                             'sexual, discriminación, confidencialidad y no revictimización.',
                  'weps_23': 'La organización turística cuenta con procedimientos para atender incidentes de '
                             'acoso, discriminación u otras situaciones que afecten a turistas, personal o '
                             'comunidades vinculadas.',
                  'weps_01': 'La organización turística aplica procedimientos de selección y contratación '
                             'con criterios explícitos de igualdad y no discriminación, mediante '
                             'convocatorias y perfiles libres de sesgos de género.',
                  'weps_02': 'La organización turística aplica criterios transparentes para la promoción y '
                             'el desarrollo profesional, y analiza ascensos, cambios de cargo y acceso a '
                             'capacitación con datos desagregados por sexo.',
                  'weps_03': 'La organización turística garantiza igualdad de acceso a procesos de '
                             'capacitación y formación para fortalecer el perfil profesional.',
                  'weps_04': 'La organización turística analiza periódicamente las remuneraciones para '
                             'identificar y corregir diferencias salariales entre mujeres y hombres en '
                             'trabajos iguales o de igual valor.',
                  'weps_18': 'La organización turística ejecuta un Plan de capacitación en igualdad de '
                             'género.',
                  'tv_riesgos_laborales_genero': 'La organización turística evalúa los riesgos laborales con '
                                                 'perspectiva de género y aplica medidas preventivas acordes '
                                                 'con las tareas y las necesidades del personal.',
                  'compromisos_iniciales': '¿En qué una o dos categorías concentrará la empresa u '
                                           'organización sus primeras acciones?',
                  'plazo_inicial': '¿En qué plazo revisará la empresa u organización sus primeras acciones?',
                  'evidencia_institucional': 'Cargar un documento de respaldo, si la empresa u organización '
                                             'desea aportarlo'},
 'province_codes': {'prov_01': 'Azuay',
                    'prov_02': 'Bolívar',
                    'prov_03': 'Cañar',
                    'prov_04': 'Carchi',
                    'prov_05': 'Cotopaxi',
                    'prov_06': 'Chimborazo',
                    'prov_07': 'El Oro',
                    'prov_08': 'Esmeraldas',
                    'prov_09': 'Guayas',
                    'prov_10': 'Imbabura',
                    'prov_11': 'Loja',
                    'prov_12': 'Los Ríos',
                    'prov_13': 'Manabí',
                    'prov_14': 'Morona Santiago',
                    'prov_15': 'Napo',
                    'prov_16': 'Pastaza',
                    'prov_17': 'Pichincha',
                    'prov_18': 'Tungurahua',
                    'prov_19': 'Zamora Chinchipe',
                    'prov_20': 'Galápagos',
                    'prov_21': 'Sucumbíos',
                    'prov_22': 'Orellana',
                    'prov_23': 'Santo Domingo de los Tsáchilas',
                    'prov_24': 'Santa Elena'},
 'provinces': {'Azuay': (-2.9001, -79.0059),
               'Bolívar': (-1.5926, -79.0009),
               'Cañar': (-2.5589, -78.9388),
               'Carchi': (0.8119, -77.7173),
               'Chimborazo': (-1.6731, -78.6483),
               'Cotopaxi': (-0.9333, -78.6167),
               'El Oro': (-3.2581, -79.9554),
               'Esmeraldas': (0.9682, -79.6517),
               'Galápagos': (-0.9538, -90.9656),
               'Guayas': (-2.1709, -79.9224),
               'Imbabura': (0.3517, -78.1223),
               'Loja': (-3.9931, -79.2042),
               'Los Ríos': (-1.8022, -79.5344),
               'Manabí': (-1.0546, -80.4545),
               'Morona Santiago': (-2.3087, -78.1114),
               'Napo': (-0.9938, -77.8129),
               'Orellana': (-0.4664, -76.9868),
               'Pastaza': (-1.4924, -78.0026),
               'Pichincha': (-0.1807, -78.4678),
               'Santa Elena': (-2.2267, -80.8587),
               'Santo Domingo de los Tsáchilas': (-0.2531, -79.1754),
               'Sucumbíos': (0.086, -76.889),
               'Tungurahua': (-1.2491, -78.6168),
               'Zamora Chinchipe': (-4.0692, -78.9567)},
 'resources': [('Kit de herramientas',
                'https://drive.google.com/file/d/1HptIHOysGnvgHqDwnZtF378xBlzN-7Qf/view?usp=sharing',
                'https://drive.google.com/uc?export=download&id=1HptIHOysGnvgHqDwnZtF378xBlzN-7Qf'),
               ('Protocolo Turismo Violeta',
                'https://drive.google.com/file/d/1RCn4RY32XfRb17PY6KUqQTweVFdV7OkJ/view?usp=sharing',
                'https://drive.google.com/uc?export=download&id=1RCn4RY32XfRb17PY6KUqQTweVFdV7OkJ'),
               ('Principios WEPs',
                'https://drive.google.com/file/d/106phjBRNH5eO2Np-vZsKtpzyvEXGJcDJ/view?usp=sharing',
                'https://drive.google.com/uc?export=download&id=106phjBRNH5eO2Np-vZsKtpzyvEXGJcDJ'),
               ('Plan de Igualdad, referencia MDT',
                'https://drive.google.com/file/d/10IV3CXp_bhXdSkchwdauhQG_X6QYV8UP/view?usp=sharing',
                'https://drive.google.com/uc?export=download&id=10IV3CXp_bhXdSkchwdauhQG_X6QYV8UP'),
               ('Prevención de explotación sexual de niñas, niños y adolescentes',
                'https://drive.google.com/file/d/11fCKoWBOz4bySCaGcq8w9-8jVMkViLvy/view?usp=sharing',
                'https://drive.google.com/uc?export=download&id=11fCKoWBOz4bySCaGcq8w9-8jVMkViLvy'),
               ('Seguridad en el turismo',
                'https://drive.google.com/file/d/1qfi0A43nPG_ES4C5DWIt3s3Gbewnl0Id/view?usp=sharing',
                'https://drive.google.com/uc?export=download&id=1qfi0A43nPG_ES4C5DWIt3s3Gbewnl0Id')],
 'plan_options': {'redactado': 'Redactado',
                  'aprobado': 'Aprobado',
                  'implementado': 'Implementado',
                  'comunicado': 'Comunicado',
                  'otra_herramienta': 'Se cuenta solo con otra herramienta de planificación, sin un plan de '
                                      'igualdad',
                  'por_verificar': 'Hay etapas pendientes de verificar'},
 'commitment_options': {'d05': 'Prevención y respuesta frente a la VBG, el acoso y la discriminación',
                        'd01': 'Gobernanza, compromiso institucional y liderazgo',
                        'd02': 'Corresponsabilidad de los cuidados y bienestar',
                        'd03': 'Cadena de valor, proveedores, comunidades y territorio',
                        'd04': 'Experiencias turísticas seguras y con enfoque de igualdad de género',
                        'd06': 'Igualdad laboral, desarrollo profesional y trabajo digno'},
 'export': {'name': 'TURISMO',
            'data_url_xlsx': 'https://eu.kobotoolbox.org/api/v2/assets/aNkhE5Duz8KUKnmWprvmGj/export-settings/esBoyPbm9atXfvUAYUgBFZx/data.xlsx',
            'data_url_csv': 'https://eu.kobotoolbox.org/api/v2/assets/aNkhE5Duz8KUKnmWprvmGj/export-settings/esBoyPbm9atXfvUAYUgBFZx/data.csv'},
 'legacy_export_urls': ['https://eu.kobotoolbox.org/api/v2/assets/aNkhE5Duz8KUKnmWprvmGj/export-settings/esiszWGaPvmxknKyqMd7UdQ/data.xlsx',
                        'https://eu.kobotoolbox.org/api/v2/assets/aNkhE5Duz8KUKnmWprvmGj/export-settings/esiszWGaPvmxknKyqMd7UdQ/data.csv']}
DIMENSIONS = SCREENING_SPEC['dimensions']
QUESTIONS = SCREENING_SPEC['questions']
QUESTION_MAP = {q['name']: q for q in QUESTIONS}
PROFILE_FIELDS = ('emplea_personal', 'tiene_proveedores', 'vinculo_comunidad', 'atiende_turistas')
TRANSVERSALS = {7: ('Comunicación, posicionamiento y mercado', (30,22,37,27,42)),
                8: ('Medición, mejora continua y reconocimiento', (31,6,28,30,35))}
PLAN_STAGES = (
    ('redactado', 'Plan de igualdad de género redactado.', 'Confirmar o completar la redacción del plan. '),
    ('aprobado', 'Plan de igualdad de género aprobado.', 'Confirmar u obtener la aprobación del plan. '),
    ('implementado', 'Plan de igualdad de género implementado.', 'Confirmar o iniciar la implementación del plan. '),
    ('comunicado', 'Plan de igualdad de género comunicado.', 'Confirmar o realizar la comunicación del plan. '),
)
DEFAULT_KOBO_DATA_URL = SCREENING_SPEC['export']['data_url_xlsx']
ROUTE_LABELS = {
    'proteccion_prioritaria': 'Empezar por la protección',
    'completar_informacion': 'Completar las respuestas',
    'continuar_diagnostico': 'Revisar con más detalle',
    'continuar_acompanamiento': 'Empezar las mejoras con apoyo',
    'no_evaluable': 'Sin resultado V18',
}
ROUTE_TEXT = {
    'proteccion_prioritaria': 'Conviene empezar por las medidas básicas de protección y buscar apoyo para ponerlas en marcha.',
    'completar_informacion': 'Hace falta completar o confirmar algunas respuestas antes de decidir cómo continuar.',
    'continuar_diagnostico': 'El siguiente paso es revisar los avances con más detalle y reunir los documentos que los respaldan.',
    'continuar_acompanamiento': 'Se puede empezar por una o dos mejoras, con apoyo para definir responsables y plazos.',
    'no_evaluable': 'Hace falta revisar o completar este registro para obtener un resultado con el diagnóstico V18.',
}
ROUTE_COLORS = {'proteccion_prioritaria':'#C2414A','completar_informacion':'#A16207',
                'continuar_diagnostico':'#16815A','continuar_acompanamiento':'#75449B','no_evaluable':'#64748B'}
CHART_CONFIG = {'displayModeBar':False,'staticPlot':True,'scrollZoom':False,'responsive':True}
STATUS_COLORS = {'yes':'#16815A','no':'#D97706','unknown':'#3B82F6','empty':'#D8DDE5'}
PLAN_DESCRIPTIONS = {
    'redactado': ('El plan está escrito', 'Existe un documento con objetivos, acciones y responsables para trabajar la igualdad de género.', 'el plan está escrito', 'si el plan está por escrito', 'Confirmar si existe el documento del plan y, si falta, prepararlo.'),
    'aprobado': ('El plan tiene aprobación interna', 'La dirección o la instancia responsable ha aprobado el plan para su aplicación.', 'el plan tiene aprobación interna', 'si el plan tiene aprobación interna', 'Confirmar la aprobación del plan y, si falta, gestionarla con la instancia responsable.'),
    'implementado': ('Las acciones del plan están en ejecución', 'La empresa está llevando a la práctica las acciones que contempla su Plan de Igualdad.', 'se están ejecutando las acciones del Plan de Igualdad', 'si las acciones del plan se están ejecutando', 'Confirmar qué acciones están en marcha y definir el inicio de las que siguen pendientes.'),
    'comunicado': ('El plan se ha dado a conocer', 'El personal y las personas que deben aplicar el plan conocen su contenido y sus responsabilidades.', 'el plan se ha dado a conocer a quienes deben aplicarlo', 'si el plan se ha comunicado a quienes deben aplicarlo', 'Confirmar a quiénes se ha comunicado el plan y completar la comunicación que haga falta.'),
}
QUESTION_PURPOSES = {
    'weps_31': 'Contar con una herramienta de planificación ayuda a convertir la intención de trabajar por la igualdad en objetivos, acciones y responsables concretos.',
    'weps_06': 'Una instancia responsable o punto focal permite dar continuidad a las acciones de igualdad y conocer quién debe coordinar su aplicación.',
    'weps_05': 'Las medidas de participación de mujeres ayudan a revisar barreras de acceso a la dirección, la administración y las áreas donde predominan los hombres.',
    'weps_28': 'La revisión periódica del plan permite reconocer lo que funcionó y ajustar las acciones que necesitan mejorar.',
    'weps_30': 'Comunicar avances con documentos de respaldo permite mostrar qué acciones se han realizado y compartir sus resultados de forma clara.',
    'weps_33': 'Conocer las necesidades de cuidado del personal permite organizar apoyos que respondan a su situación familiar y a sus responsabilidades.',
    'weps_07': 'Esta pregunta reúne derechos y permisos de cuidado, apoyos necesarios y condiciones de lactancia que correspondan a la organización. Conviene revisar cada componente para identificar cuál requiere atención.',
    'weps_08': 'La organización de horarios, permisos y turnos puede facilitar que el personal compatibilice su trabajo con las responsabilidades de cuidado.',
    'weps_35': 'Registrar las medidas de cuidado solicitadas y aplicadas permite conocer qué apoyos se utilizan y si atienden las necesidades de mujeres y hombres.',
    'tv_cuidados_comunicacion': 'Comunicar las medidas de cuidado permite que el personal conozca los apoyos disponibles y la forma de solicitarlos.',
    'weps_38': 'Revisar accesibilidad y apoyos de cuidado ayuda a que más personas puedan participar en los servicios y actividades turísticas.',
    'weps_39': 'Facilitar la participación de negocios liderados por mujeres y de proveedores comunitarios y locales amplía sus oportunidades dentro de la cadena de valor.',
    'weps_24': 'Incorporar compromisos de igualdad y prevención de violencia en la relación con proveedores permite establecer expectativas claras desde su selección.',
    'tv_proveedores_respuesta_vbg': 'Definir cómo responder a incidentes en la relación con proveedores permite identificar responsables y activar las medidas de atención que correspondan.',
    'weps_21': 'Fortalecer las capacidades de los grupos de mujeres proveedoras puede ayudarles a sostener su participación en la cadena de valor.',
    'weps_26': 'Las condiciones claras de remuneración y pago permiten reconocer los aportes de las mujeres y revisar el cumplimiento de los acuerdos con proveedores y comunidades.',
    'weps_27': 'Acordar la difusión de saberes y el uso de conocimientos e imágenes permite que las mujeres involucradas participen en las decisiones sobre su patrimonio cultural.',
    'weps_36': 'Reconocer los riesgos de las actividades turísticas permite preparar medidas preventivas y una respuesta ante situaciones que afecten la seguridad de las personas.',
    'weps_37': 'Dar a conocer las normas de convivencia y los canales de ayuda, junto con la capacitación del personal de contacto, permite orientar a turistas y responder ante situaciones que afecten su seguridad.',
    'weps_22': 'Revisar la comunicación y la promoción ayuda a identificar contenidos que reproduzcan estereotipos o discriminación y a corregirlos.',
    'weps_09': 'Una declaración de cero tolerancia establece el compromiso de la organización frente a la violencia, el acoso y la discriminación. Su aplicación requiere que ese compromiso sea conocido.',
    'weps_12': 'Un procedimiento escrito permite saber cómo prevenir la violencia y cómo actuar cuando se comunica una situación de acoso o discriminación.',
    'weps_15': 'Los canales accesibles y confidenciales facilitan que las personas comuniquen una situación y conozcan las opciones de atención y derivación.',
    'weps_16': 'Conocer las rutas de protección permite definir cómo actuar ante una sospecha de trata de personas o explotación sexual de niñas, niños y adolescentes.',
    'weps_17': 'La capacitación del personal y de quienes reciben reportes ayuda a aplicar los procedimientos y cuidar la confidencialidad y el trato a las personas afectadas.',
    'weps_23': 'Organizar la respuesta a incidentes ayuda a definir responsabilidades y a conectar la atención con las medidas de protección de la organización.',
    'weps_01': 'Los criterios de selección y contratación permiten revisar que las oportunidades de empleo se ofrezcan sin sesgos o discriminación de género.',
    'weps_02': 'Los criterios transparentes de promoción y desarrollo profesional permiten revisar cómo se distribuyen las oportunidades entre mujeres y hombres.',
    'weps_03': 'La igualdad de acceso a la formación ayuda a que el personal fortalezca sus capacidades y amplíe sus posibilidades de desarrollo profesional.',
    'weps_04': 'La revisión de remuneraciones permite identificar diferencias entre mujeres y hombres que realizan trabajos iguales o de igual valor. Esta respuesta no determina el tamaño de una brecha salarial.',
    'weps_18': 'La formación en igualdad de género permite traducir los compromisos del plan en prácticas de trabajo y responsabilidades compartidas.',
    'tv_riesgos_laborales_genero': 'Revisar los riesgos laborales con perspectiva de género permite adecuar la prevención a las tareas, los equipos y las necesidades del personal.',
}
QUESTION_MESSAGES = {
    'weps_31': ('De acuerdo con la respuesta, la empresa ya cuenta con un plan u otra herramienta para organizar su trabajo en igualdad.', 'Preparar una herramienta sencilla que reúna los objetivos de igualdad, las acciones y las personas responsables.'),
    'weps_06': ('Ya hay una persona o un equipo a cargo de impulsar las acciones de igualdad, con funciones definidas.', 'Acordar quién se hará cargo de las acciones de igualdad y dejar claras sus funciones.'),
    'weps_05': ('La empresa ya toma medidas para que más mujeres participen en puestos de liderazgo y espacios donde predominan los hombres.', 'Identificar qué dificulta la participación de las mujeres y poner en marcha una medida para reducir esa barrera.'),
    'weps_28': ('Según lo indicado en la encuesta, el plan se revisa cada año y se dejan por escrito los ajustes acordados.', 'Revisar los resultados del plan con el equipo responsable y acordar los ajustes, las personas a cargo y los plazos.'),
    'weps_30': ('La empresa comunica lo que hace en igualdad y cuenta con documentos que respaldan esos avances.', 'Reunir los documentos que muestran los avances en igualdad y usarlos para dar a conocer lo realizado.'),
    'weps_33': ('La empresa revisa cada año qué necesidades de cuidado tiene su personal.', 'Conversar con el personal sobre sus necesidades de cuidado y dejar un registro que se revise cada año.'),
    'weps_07': ('De acuerdo con la respuesta, se aplican los derechos y permisos de cuidado y se facilitan los apoyos y las condiciones de lactancia que corresponden.', 'Revisar los permisos, los apoyos de cuidado y las condiciones de lactancia, y atender lo que todavía haga falta.'),
    'weps_08': ('Ya se ajustan horarios, permisos u otras condiciones de trabajo para facilitar las responsabilidades de cuidado.', 'Elegir un ajuste de horarios, permisos o turnos que ayude al personal a atender sus responsabilidades de cuidado.'),
    'weps_35': ('Existe un registro de los apoyos de cuidado que solicitan y reciben las mujeres y los hombres del equipo.', 'Llevar un registro sencillo de los apoyos de cuidado solicitados y utilizados por mujeres y hombres.'),
    'tv_cuidados_comunicacion': ('El personal recibe información sobre las medidas de cuidado que se aplican en la empresa.', 'Explicar al personal qué apoyos de cuidado se están aplicando y cómo puede acceder a ellos.'),
    'weps_38': ('Se revisan las condiciones de acceso y cuidado de las experiencias turísticas y se hacen mejoras a partir de los comentarios de visitantes.', 'Revisar las condiciones de acceso y cuidado, escuchar a visitantes y acordar una mejora concreta.'),
    'weps_39': ('La empresa ya facilita la participación de negocios de mujeres, organizaciones comunitarias y proveedores locales.', 'Elegir una medida que facilite trabajar con negocios de mujeres, organizaciones comunitarias o proveedores locales.'),
    'weps_24': ('La igualdad y la prevención de la violencia forman parte de los criterios para trabajar con proveedores.', 'Incluir compromisos de igualdad y prevención de la violencia al elegir proveedores y acordar cómo se trabajará con ellos.'),
    'tv_proveedores_respuesta_vbg': ('Ya se ha definido cómo actuar ante violencia, acoso, abuso o discriminación en la relación con proveedores.', 'Acordar los pasos y las personas responsables de actuar ante estos incidentes en la relación con proveedores.'),
    'weps_21': ('Se realizan actividades para fortalecer las capacidades de los grupos de mujeres que proveen bienes o servicios a la empresa.', 'Preguntar a los grupos de mujeres proveedoras qué apoyo necesitan y organizar una actividad para fortalecer sus capacidades.'),
    'weps_26': ('Las condiciones de pago están claras, se cumplen los acuerdos y se reconoce el trabajo de las mujeres.', 'Acordar condiciones claras de pago, reconocer el trabajo de las mujeres y revisar que los acuerdos se cumplan.'),
    'weps_27': ('Las mujeres participan en los acuerdos sobre la difusión de sus saberes y el uso de sus conocimientos e imágenes.', 'Acordar con las mujeres involucradas cómo se difundirán sus saberes y cómo podrán usarse sus conocimientos e imágenes.'),
    'weps_36': ('Se revisan los riesgos que pueden afectar de manera distinta a mujeres y personas en mayor situación de vulnerabilidad durante las actividades turísticas.', 'Revisar una experiencia turística, identificar a quiénes pueden afectar sus riesgos y acordar medidas de seguridad e inclusión.'),
    'weps_37': ('Las personas visitantes reciben información sobre convivencia y ayuda, y el personal de contacto ha recibido capacitación reciente.', 'Explicar a turistas las normas y los canales de ayuda y capacitar al personal que les atiende.'),
    'weps_22': ('La empresa tiene criterios para comunicar sin estereotipos y revisa sus mensajes e imágenes.', 'Acordar criterios de comunicación inclusiva y revisar una pieza de comunicación para corregir posibles sesgos.'),
    'weps_09': ('Existe un compromiso de cero tolerancia frente a la violencia, el acoso y la discriminación, aprobado y dado a conocer.', 'Aprobar y dar a conocer el compromiso de cero tolerancia frente a la violencia, el acoso y la discriminación.'),
    'weps_12': ('La empresa cuenta con un procedimiento escrito para prevenir y atender situaciones de violencia, acoso o discriminación.', 'Escribir los pasos para prevenir y atender estas situaciones, señalando quién actúa y dónde se puede buscar apoyo.'),
    'weps_15': ('Hay canales confidenciales y accesibles para comunicar una situación y opciones de atención dentro y fuera de la empresa.', 'Habilitar un canal accesible y confidencial y explicar cómo recibir atención dentro y fuera de la empresa.'),
    'weps_16': ('Se conocen las rutas oficiales de protección y se ha definido cómo actuar y avisar a las autoridades ante una sospecha.', 'Identificar las rutas oficiales y acordar quién activa la protección y avisa a las autoridades ante una sospecha de trata o explotación sexual.'),
    'weps_17': ('El personal y quienes atienden los reportes han recibido formación reciente para prevenir la violencia y responder de forma adecuada.', 'Organizar una capacitación para el personal y quienes atienden reportes, cuidando la confidencialidad y evitando que las personas afectadas tengan que repetir innecesariamente su relato.'),
    'weps_23': ('La empresa ya tiene pasos definidos para atender incidentes que afectan a turistas, al personal o a las comunidades vinculadas.', 'Acordar qué hacer y quién debe actuar cuando un incidente afecte a turistas, al personal o a las comunidades vinculadas.'),
    'weps_01': ('La selección y contratación de personal ya incorporan criterios de igualdad y evitan sesgos de género.', 'Revisar los requisitos y los anuncios de contratación para quitar sesgos que puedan excluir a mujeres u hombres.'),
    'weps_02': ('Hay criterios claros para crecer dentro de la empresa y se revisan las oportunidades que reciben mujeres y hombres.', 'Explicar los criterios para ascender y acceder a formación y revisar cómo se distribuyen esas oportunidades entre mujeres y hombres.'),
    'weps_03': ('El personal tiene igualdad de oportunidades para acceder a la formación profesional.', 'Revisar cómo se ofrecen las capacitaciones y facilitar que mujeres y hombres tengan las mismas oportunidades de participar.'),
    'weps_04': ('La empresa compara las remuneraciones y corrige las diferencias sin justificación entre trabajos iguales o de igual valor.', 'Comparar las remuneraciones de trabajos iguales o de igual valor y acordar cómo corregir las diferencias que no tengan justificación.'),
    'weps_18': ('Ya se están realizando actividades del plan de capacitación en igualdad de género.', 'Preparar un plan de capacitación en igualdad de género y realizar una primera actividad.'),
    'tv_riesgos_laborales_genero': ('Se revisan los riesgos del trabajo con perspectiva de género y se aplican medidas para prevenirlos.', 'Revisar los riesgos físicos, ergonómicos y psicosociales del trabajo y aplicar una medida que responda a las tareas y necesidades del personal.'),
}
RESPONSE_LABELS = {'si':'Sí','no':'No','ns':'No sabe / por verificar','sin_respuesta':'Sin respuesta',
                   'invalida':'Por verificar (valor no reconocido)','no_aplica':'No aplica','aplicabilidad_pendiente':'Perfil por confirmar'}


def text_value(value: Any) -> str:
    if value is None:
        return ''
    try:
        if isinstance(value, float) and math.isnan(value):
            return ''
    except (TypeError, ValueError):
        pass
    s = str(value)
    return '' if s.strip().lower() in {'nan','none','null','<na>','nat'} else s


def norm_text(value: Any) -> str:
    s = unicodedata.normalize('NFKD', text_value(value))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', s).strip().lower()


def norm_id(value: Any) -> str:
    return re.sub('[^a-z0-9]+', '', norm_text(value))


def clean_col(value: Any) -> str:
    return re.sub(r'\s+', ' ', text_value(value).replace('\n',' ')).strip()


def canonical_field(value: Any) -> str:
    # Only the final group segment is a field. Never confuse weps_31 with
    # sc_peso_weps_31 or score_weps_31 through a substring match.
    return norm_text(re.split(r'[/\\.:]', clean_col(value))[-1])


class RecordFields:
    def __init__(self, record: Mapping[str, Any]):
        self.record = dict(record)
        self.by_name: dict[str, list[str]] = {}
        self.issues: list[str] = []
        for k in self.record:
            self.by_name.setdefault(canonical_field(k), []).append(k)

    def get(self, field: str, default: Any = None, aliases: Iterable[str] = ()) -> Any:
        candidates = [field] if field in self.record and norm_text(field)!=canonical_field(field) else self.by_name.get(canonical_field(field), [])
        if not candidates:
            for alias in [*aliases,SCREENING_SPEC.get('field_labels',{}).get(field,'')]:
                if not alias:continue
                candidates = [k for k in self.record if norm_text(k) == norm_text(alias) or norm_text(str(k).rsplit('/',1)[-1]) == norm_text(alias)]
                if candidates:
                    break
        nonempty = [(k,self.record[k]) for k in candidates if text_value(self.record[k]).strip()]
        values = {text_value(v) for _,v in nonempty}
        if len(values) > 1:
            issue = f'Campo ambiguo: {field}'
            if issue not in self.issues:
                self.issues.append(issue)
            return default
        return nonempty[0][1] if nonempty else default

    def has(self, field: str) -> bool:
        return bool(self.by_name.get(canonical_field(field)))


def normalize_response(value: Any) -> str:
    # Numeric 0/1 and the former maturity scale are deliberately not recoded.
    value = norm_text(value)
    if value in {'si','yes'}: return 'si'
    if value in {'no'}: return 'no'
    if value in {'ns','no sabe','no sabe / por verificar','no sabe/por verificar','por verificar'}: return 'ns'
    return 'sin_respuesta' if not value else 'invalida'


def finite_number(value: Any) -> float | None:
    s = text_value(value).strip().replace(',','.')
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', s): return None
    n = float(s)
    return n if math.isfinite(n) else None


def classify_record(fields: RecordFields) -> str:
    marker = text_value(fields.get('sc_version_modelo')).strip()
    if marker:
        return 'v18' if marker == MODEL_VERSION else 'otra_version'
    # Exports without calculates can still be identified by the four new profile
    # fields and textual binary responses. No historical maturity score is used.
    new_fields = ('tv_cuidados_comunicacion', 'tv_proveedores_respuesta_vbg', 'tv_riesgos_laborales_genero')
    if all(fields.has(n) or any(norm_text(k)==norm_text(SCREENING_SPEC['field_labels'].get(n,'')) for k in fields.record) for n in new_fields) and all(normalize_response(fields.get(g)) in {'si','no'} for g in PROFILE_FIELDS):
        present = [normalize_response(fields.get(q['name'], aliases=[q['question']])) for q in QUESTIONS]
        if any(x in {'si','no','ns'} for x in present) and 'invalida' not in present:
            return 'v18_sin_marca'
    return 'historico_o_no_identificado'


def multiple_selection(fields: RecordFields, field: str, options: Mapping[str,str]) -> dict[str,Any]:
    """Read combined or expanded Kobo select_multiple exports, preserving conflicts."""
    raw = fields.get(field)
    supplied = bool(text_value(raw).strip()) if not isinstance(raw,(list,tuple)) else bool(raw)
    aliases = {norm_text(label): code for code,label in options.items()}
    aliases.update({norm_text(code):code for code in options})
    unknown = []
    selected = set()
    if supplied:
        if isinstance(raw,(list,tuple)):
            parts = list(raw)
        else:
            value = text_value(raw).strip()
            if value.startswith('['):
                try:
                    decoded = json.loads(value)
                    parts = decoded if isinstance(decoded,list) else [value]
                except ValueError:
                    parts = [value]
            elif norm_text(value) in aliases:
                parts = [value]
            elif re.search('[;,|]',value):
                parts = re.split('[;,|]',value)
            elif all(token in options for token in value.split()):
                parts = value.split()
            else:
                # Label exports can combine labels with spaces; consume known
                # whole labels, longest first, without guessing stages.
                remaining = norm_text(value)
                parts = []
                for label in sorted(aliases,key=len,reverse=True):
                    pattern = r'(?<!\w)'+re.escape(label)+r'(?!\w)'
                    if re.search(pattern,remaining):
                        parts.append(aliases[label]);remaining=re.sub(pattern,' ',remaining)
                if remaining.strip():unknown.append(remaining.strip())
        for part in parts:
            code=aliases.get(norm_text(part))
            if code:selected.add(code)
            elif text_value(part).strip():unknown.append(text_value(part))
    expanded={}
    for key,value in fields.record.items():
        normalized=str(key).replace('\\','/').rstrip('/')
        bits=normalized.split('/')
        code=bits[-1]
        if len(bits)<2 or norm_text(bits[-2])!=norm_text(field) or code not in options:continue
        v=norm_text(value)
        if v in {'1','1.0','true','si','yes'}:expanded[code]=True
        elif v in {'0','0.0','false','no',''}:expanded[code]=False
        else:unknown.append(code+' (valor expandido no reconocido)')
    expanded_selected={k for k,v in expanded.items() if v}
    conflict=bool(supplied and expanded and any((code in selected)!=flag for code,flag in expanded.items()))
    if not supplied and expanded:selected=expanded_selected
    return {'selected':selected,'present':supplied or bool(expanded),'unknown':unknown,'conflict':conflict}


def plan_diagnostic(fields: RecordFields) -> dict[str,Any]:
    active=normalize_response(fields.get('weps_31'))=='si'
    selection=multiple_selection(fields,'tv_plan_etapas',SCREENING_SPEC['plan_options']) if active else {'selected':set(),'present':False,'unknown':[],'conflict':False}
    selected=selection['selected']
    other=active and 'otra_herramienta' in selected
    invalid=bool(selection['unknown'] or selection['conflict'] or (other and len(selected)>1))
    pending=bool(active and (not selected or 'por_verificar' in selected or invalid))
    confirmed=[code for code,_,_ in PLAN_STAGES if code in selected] if active and not other else []
    advances=[positive for code,positive,_ in PLAN_STAGES if code in confirmed]
    actions=([action.strip() for code,_,action in PLAN_STAGES if code not in selected] if not other else ['Revisar que la herramienta existente defina objetivos, acciones y responsables para la igualdad de género.']) if active else []
    if other:state='Se declaró otra herramienta de planificación para la igualdad de género, sin un plan de igualdad.'
    elif pending:state=f'Hay etapas pendientes de verificar. Etapas confirmadas: {len(confirmed)} de 4.'
    else:state=f'Etapas confirmadas del plan: {len(confirmed)} de 4.'
    return {**selection,'active':active,'other_tool':int(other),'pending':int(pending),'invalid':invalid,
            'confirmed':confirmed,'count':len(confirmed),'advances':advances,'actions':actions,'state_text':state,
            'kobo_advances':''.join('• '+positive+' ' for code,positive,_ in PLAN_STAGES if code in confirmed),
            'kobo_actions':('Revisar que la herramienta existente defina objetivos, acciones y responsables para la igualdad de género.' if other else ''.join(action for code,_,action in PLAN_STAGES if code not in selected)) if active else ''}


def resolve_source_url(configured: str='') -> str:
    """Migrate only the obsolete export explicitly supplied with this project."""
    url=text_value(configured).strip()
    return DEFAULT_KOBO_DATA_URL if not url or url in SCREENING_SPEC['legacy_export_urls'] else url


def calculate_screening(record: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct the V18 screening, then compare independently to exported sc_*.

    Parameters missing from a raw-response export use the V18 defaults; invalid
    or inconsistent weights block valuation instead of silently changing it.
    """
    f = RecordFields(record)
    classification = classify_record(f)
    issues: list[str] = []
    notices: list[str] = []
    if classification == 'v18_sin_marca':
        notices.append('Registro identificado por estructura y respuestas; falta la marca del modelo.')
    consent = normalize_response(f.get('consentimiento'))
    profile = {g: normalize_response(f.get(g)) for g in PROFILE_FIELDS}
    if consent != 'si': issues.append('Consentimiento no afirmativo o ausente.')
    if classification not in {'v18','v18_sin_marca'}:
        issues.append('Versión distinta o no identificada; no se mezcla con V18.')
    missing_profile = [g for g,v in profile.items() if v not in {'si','no'}]
    if missing_profile: issues.append('Perfil de aplicación incompleto: '+', '.join(missing_profile))
    bad_parameters: list[str] = []

    def parameter(name: str, default: float) -> float:
        raw = f.get(name)
        if any(v is not None and str(v).strip().lower() in {'nan','inf','-inf','infinity','-infinity'}
               for v in (f.record[k] for k in f.by_name.get(norm_text(name),[]))):
            bad_parameters.append(name); return float(default)
        if not text_value(raw).strip(): return float(default)
        n = finite_number(raw)
        if n is None or not 0 <= n <= 100:
            bad_parameters.append(name); return float(default)
        return n

    dim_weights = {d['id']:parameter(f"sc_peso_d{d['id']:02d}",d['weight']) for d in DIMENSIONS}
    q_weights = {q['name']:parameter('sc_peso_'+q['name'],q['weight']) for q in QUESTIONS}
    thresholds = {key:parameter('sc_umbral_'+key,val) for key,val in [('cobertura',80),('puntaje',75),('vbg',90)]}
    if not math.isclose(sum(dim_weights.values()),100,abs_tol=1e-7): bad_parameters.append('suma de pesos de dimensiones')
    for d in DIMENSIONS:
        if not math.isclose(sum(q_weights[q['name']] for q in QUESTIONS if q['dim']==d['id']),100,abs_tol=1e-7):
            bad_parameters.append(f"suma de pesos de indicadores D{d['id']}")
    if bad_parameters: issues.append('Parámetros inválidos: '+', '.join(bad_parameters))
    practices=[]
    for q in QUESTIONS:
        gate=q['gate']
        any_gates=q.get('gates_any',[])
        if any_gates:
            applies=True if any(profile[g]=='si' for g in any_gates) else (False if all(profile[g]=='no' for g in any_gates) else None)
        else:
            applies = (profile[gate]=='si') if gate and profile[gate] in {'si','no'} else (None if gate else True)
        raw=f.get(q['name'],aliases=[q['question']])
        response=normalize_response(raw)
        if applies is True and response=='invalida': issues.append('Respuesta no reconocida: '+q['name'])
        status=response if applies is True else ('no_aplica' if applies is False else 'aplicabilidad_pendiente')
        action=(q['action'] if response=='no' else ('Verificar si existe la práctica: '+quote_survey(q['question']) if response not in {'si','no'} else 'Mantener la práctica y conservar evidencia.')) if applies is True else ''
        practices.append({**q,'applies':applies,'response':response,'status':status,'weight':q_weights[q['name']],
                          'finding':q['positive'] if applies is True and response=='si' else '', 'next_action':action})
    dim_results=[]
    for d in DIMENSIONS:
        items=[p for p in practices if p['dim']==d['id'] and p['applies'] is True]
        known=[p for p in items if p['response'] in {'si','no'}]
        yes=[p for p in items if p['response']=='si']; no=[p for p in items if p['response']=='no']
        unknown=[p for p in items if p['response'] not in {'si','no'}]
        aw=sum(p['weight'] for p in items);kw=sum(p['weight'] for p in known);yw=sum(p['weight'] for p in yes)
        dim_results.append({**d,'weight':dim_weights[d['id']],'app_weight':aw,'known_weight':kw,'yes_weight':yw,
                            'score':100*yw/kw if kw else None,'coverage':100*kw/aw if aw else None,
                            'applicable':len(items),'yes':len(yes),'no':len(no),'unknown':len(unknown),
                            'advances':[p['finding'] for p in yes],'actions':[p['next_action'] for p in no],
                            'verify':[p['next_action'] for p in unknown]})
    known_dims=[d for d in dim_results if d['score'] is not None]
    active_dims=[d for d in dim_results if d['coverage'] is not None]
    known_dw=sum(d['weight'] for d in known_dims);active_dw=sum(d['weight'] for d in active_dims)
    score=sum(d['weight']*d['score'] for d in known_dims)/known_dw if known_dw else None
    coverage=sum(d['weight']*d['coverage'] for d in active_dims)/active_dw if active_dw else None
    plan=plan_diagnostic(f)
    if plan['invalid']:issues.append('Selección de etapas del plan inconsistente o no reconocida; verificar en Kobo.')
    critical=[p for p in practices if p['critical'] and p['applies'] is True]
    critical_no=sum(p['response']=='no' for p in critical)
    critical_pending=sum(p['response'] not in {'si','no'} for p in critical)
    vbg=next(d['score'] for d in dim_results if d['id']==5)
    compatible=classification in {'v18','v18_sin_marca'}
    evaluable=compatible and consent=='si' and not missing_profile and not bad_parameters and not f.issues
    if not evaluable: route='no_evaluable';score=None;coverage=None
    elif critical_no: route='proteccion_prioritaria'
    elif critical_pending or coverage is None or coverage < thresholds['cobertura'] or plan['pending']: route='completar_informacion'
    elif score is not None and score>=thresholds['puntaje'] and vbg is not None and vbg>=thresholds['vbg'] and math.isclose(coverage,100,abs_tol=1e-9): route='continuar_diagnostico'
    else: route='continuar_acompanamiento'
    expected={}
    for d in dim_results:
        prefix=f"sc_d{d['id']:02d}_"
        expected.update({prefix+'peso_aplicable':d['app_weight'],prefix+'peso_conocido':d['known_weight'],prefix+'peso_si':d['yes_weight'],
                         prefix+'puntaje':d['score'],prefix+'cobertura':d['coverage'],prefix+'aplicables':d['applicable'],
                         prefix+'si':d['yes'],prefix+'no':d['no'],prefix+'por_verificar':d['unknown'],prefix+'pendientes':d['no']+d['unknown']})
    totals={s:sum(d[key] for d in dim_results) for s,key in [('aplicables','applicable'),('si','yes'),('no','no'),('por_verificar','unknown')]}
    expected.update({'sc_total_'+k:v for k,v in totals.items()})
    expected.update({'sc_indice_global':score,'sc_cobertura_global':coverage,'sc_criticos_no':critical_no,
                     'sc_criticos_pendientes':critical_pending,'sc_peso_dim_aplicable':active_dw,'sc_peso_dim_conocida':known_dw,'sc_ruta':route})
    expected.update({'sc_aplica_'+p['name']:int(p['applies'] is True) for p in practices})
    expected.update({'sc_plan_otra_herramienta':plan['other_tool'],'sc_plan_verificacion_pendiente':plan['pending'],
                     'sc_plan_etapas_confirmadas':plan['count'],'sc_plan_avances':plan['kobo_advances'],
                     'sc_plan_acciones':plan['kobo_actions'],'sc_plan_estado_texto':plan['state_text']})
    transversal_results=[]
    for tid,(title,nums) in TRANSVERSALS.items():
        ps=[p for p in practices if p['num'] in nums and p['applies'] is True]
        t={'id':tid,'title':title,'applicable':len(ps),'yes':sum(p['response']=='si' for p in ps),
           'no':sum(p['response']=='no' for p in ps),'unknown':sum(p['response'] not in {'si','no'} for p in ps),
           'questions':[p['name'] for p in ps]}
        transversal_results.append(t)
        expected.update({f'sc_t{tid:02d}_'+k:t[v] for k,v in [('aplicables','applicable'),('si','yes'),('no','no'),('por_verificar','unknown')]})
    differences=[];checked=0
    if evaluable:
        for field,wanted in expected.items():
            raw=f.get(field)
            if not text_value(raw).strip():
                if wanted is None or wanted=='': continue
                # A missing column is allowed in raw-response exports, but an
                # exported calculate that is blank did not pass the comparison.
                if f.has(field):
                    differences.append({'Campo':field,'Kobo':'(vacío)','Recalculado':wanted})
                continue
            checked+=1
            actual=text_value(raw) if isinstance(wanted,str) else finite_number(raw)
            if field=='sc_plan_estado_texto' and isinstance(actual,str):
                # XPath test engines may stringify integer-valued numbers as
                # 1.0 where Kobo writes 1; both denote the same stage count.
                actual=re.sub(r'\b([0-4])\.0(?= de 4\.)',r'\1',actual)
            ok=(actual is None and wanted is None) or (actual.strip()==wanted.strip() if isinstance(wanted,str) else actual is not None and wanted is not None and math.isclose(actual,wanted,rel_tol=1e-9,abs_tol=.05))
            if not ok: differences.append({'Campo':field,'Kobo':text_value(raw),'Recalculado':wanted})
    issues.extend(f.issues)
    if f.issues:
        evaluable=False;score=None;coverage=None;route='no_evaluable'
    return {'classification':classification,'evaluable':evaluable,'score':score,'coverage':coverage,
            'route':route,'route_label':ROUTE_LABELS[route],'route_text':ROUTE_TEXT[route],
            'dimensions':dim_results,'practices':practices,'transversals':transversal_results,'plan':plan,
            'totals':totals,'critical_no':critical_no,'critical_pending':critical_pending,
            'issues':issues,'notices':notices,'differences':differences,'checked_fields':checked,
            'expected_fields':expected,'thresholds':thresholds,
            'provisional':coverage is None or coverage<100 or bool(plan['pending']) or bool(issues) or bool(differences)}


def company_name(record: Mapping[str, Any]) -> str:
    f=RecordFields(record)
    return text_value(f.get('nombre_legal',aliases=['Nombre legal de la empresa','Nombre legal de la organización'])).strip()


def company_key(record: Mapping[str, Any]) -> str:
    f=RecordFields(record);ruc=re.sub(r'\D','',text_value(f.get('ruc',aliases=['Número de RUC'])))
    if len(ruc)==13: return 'ruc:'+ruc
    return 'nombre:'+norm_text(company_name(record)) if company_name(record) else ''


def record_date(record: Mapping[str, Any]) -> datetime:
    f=RecordFields(record)
    for field in ['_submission_time','end','fecha_registro','today','start']:
        s=text_value(f.get(field)).strip()
        if not s: continue
        try:
            if re.fullmatch(r'\d+(?:\.\d+)?',s) and 20000<=float(s)<=60000:
                return (datetime(1899,12,30,tzinfo=timezone.utc)+timedelta(days=float(s)))
            dt=datetime.fromisoformat(s.replace('Z','+00:00'))
            return dt.replace(tzinfo=ZoneInfo('America/Guayaquil')) if dt.tzinfo is None else dt
        except (ValueError,TypeError,OverflowError): pass
    return datetime.min.replace(tzinfo=timezone.utc)


def date_display(record: Mapping[str, Any]) -> str:
    d=record_date(record)
    return d.astimezone(ZoneInfo('America/Guayaquil')).strftime('%d/%m/%Y') if d.year>1 else 'Sin fecha'


def latest_records(records: list[dict[str,Any]]) -> list[dict[str,Any]]:
    # Identity uses RUC first, not just display names. Never double-count updates.
    groups={}
    for i,row in enumerate(records):
        key=company_key(row)
        if not key: continue
        previous=groups.get(key)
        if previous is None or (record_date(row),i) >= previous[:2]: groups[key]=(record_date(row),i,row)
    return [x[2] for x in groups.values()]


def model_signature(result: dict[str,Any]) -> str:
    payload={'dims':[(d['id'],d['weight']) for d in result['dimensions']],
             'questions':[(p['name'],p['weight']) for p in result['practices']], 'thresholds':result['thresholds']}
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:12]


def analyze_latest(records: list[dict[str,Any]]) -> list[dict[str,Any]]:
    return [{'record':r,'result':calculate_screening(r),'company':company_name(r),'key':company_key(r)} for r in latest_records(records)]


def summarize(entries: list[dict[str,Any]]) -> dict[str,Any]:
    valid=[e for e in entries if e['result']['evaluable']]
    signatures={model_signature(e['result']) for e in valid}
    same_model=len(signatures)<=1
    def avg(values):
        values=[v for v in values if v is not None]
        return sum(values)/len(values) if values else None
    return {'companies':len(valid),'evaluable':valid,'same_parameters':same_model,
            'score':avg([e['result']['score'] for e in valid]) if same_model else None,
            'coverage':avg([e['result']['coverage'] for e in valid]) if same_model else None,
            'scores_n':sum(e['result']['score'] is not None for e in valid),
            'dimensions':[{'id':d['id'],'title':d['title'],
                           'score':avg([e['result']['dimensions'][d['id']-1]['score'] for e in valid]) if same_model else None,
                           'coverage':avg([e['result']['dimensions'][d['id']-1]['coverage'] for e in valid]) if same_model else None,
                           'companies':sum(e['result']['dimensions'][d['id']-1]['score'] is not None for e in valid)} for d in DIMENSIONS],
            'routes':dict(Counter(e['result']['route'] for e in valid)),
            'discrepancies':sum(bool(e['result']['differences']) for e in valid)}


def credentials_match(record: Mapping[str,Any], typed_code: str, override: str='') -> bool:
    f=RecordFields(record)
    # Codes preserve case, punctuation and spaces. No match against RUC, telephone,
    # _id, arbitrary values or historical scores. Configured alias is explicit.
    if override and norm_id(canonical_field(override)) in {'id','uuid','index','instanceid','ruc','nombrelegal','contactotelefono','contactocorreo','submissionid'}:
        return False
    raw=f.get(override or 'CLAVE',aliases=[] if override else [SCREENING_SPEC['access_label']])
    stored=text_value(raw)
    if not stored or not typed_code or f.issues: return False
    a=unicodedata.normalize('NFC',stored).encode('utf-8');b=unicodedata.normalize('NFC',typed_code).encode('utf-8')
    return hmac.compare_digest(a,b)


def admin_password_matches(typed: str, expected: str) -> bool:
    return bool(typed and expected) and hmac.compare_digest(typed.encode(),expected.encode())


def csv_safe(value: Any) -> str:
    value=text_value(value)
    return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value


def csv_bytes(rows: list[dict[str,Any]]) -> bytes:
    if not rows: return b''
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=list(rows[0]),delimiter=';')
    writer.writeheader();writer.writerows({k:csv_safe(v) for k,v in row.items()} for row in rows)
    return out.getvalue().encode('utf-8-sig')


def percent(value: float|None) -> str:
    return 'Sin información' if value is None else f'{value:.1f}'.replace('.',',')+' %'


def join_words(items: Iterable[str]) -> str:
    values=list(items)
    return values[0] if len(values)==1 else (', '.join(values[:-1])+' y '+values[-1] if values else '')


def quote_survey(value: Any) -> str:
    return '"'+text_value(value).strip()+'"'


def diagnostic_reading(result: dict[str,Any]) -> dict[str,str]:
    totals=result['totals']
    summary=f"De acuerdo con las respuestas, la empresa ya aplica {totals['si']} de las {totals['aplicables']} medidas que corresponden a su actividad. Quedan {totals['no']} por poner en marcha."
    if totals['por_verificar']:summary+=f" Además, hay {totals['por_verificar']} respuestas por confirmar."
    if result['score'] is not None:summary+=' Teniendo en cuenta el peso de cada tema, el resultado general es '+percent(result['score'])+'.'
    # These fragments are copied literally from the survey, so quotation marks
    # distinguish them from the interpretation and recommendations that follow.
    names={'weps_09':'política o declaración vigente de cero tolerancia',
           'weps_12':'protocolo o procedimiento escrito para prevenir y actuar frente a violencia basada en género',
           'weps_15':'canales de reporte accesibles y confidenciales y rutas internas y externas de actuación y derivación',
           'weps_16':'activar la protección y comunicar a las autoridades una sospecha de trata de personas o explotación sexual de niñas, niños y adolescentes'}
    missing=[quote_survey(names[p['name']]) for p in result['practices'] if p['critical'] and p['applies'] is True and p['response']=='no']
    route=result['route']
    if route=='proteccion_prioritaria':
        title='Por dónde empezar: reforzar las medidas básicas de protección'
        action='En la encuesta aparece la respuesta '+quote_survey('No')+' en las preguntas sobre '+join_words(missing)+'. Conviene empezar por estas medidas y acordar quién se hará cargo y cómo se pondrán en marcha.'
    elif route=='completar_informacion':
        title='Por dónde empezar: completar la información pendiente'
        action='Conviene confirmar las respuestas pendientes antes de decidir el siguiente paso del diagnóstico.'
        if result['plan']['pending']:action+=' En particular, hace falta aclarar la situación del Plan de Igualdad, que se explica más abajo.'
    elif route=='continuar_diagnostico':
        title='Siguiente paso: profundizar el diagnóstico'
        action='De acuerdo con las respuestas, se puede pasar a una revisión más detallada. El siguiente paso es reunir los documentos que muestran los avances y acordar qué mejoras se van a realizar.'
    else:
        title='Por dónde empezar: organizar las primeras mejoras'
        action='Conviene elegir una o dos de las mejoras identificadas y definir quién las realizará, qué apoyo se necesita y cuándo se revisará su avance.'
    if result['coverage'] is not None and math.isclose(result['coverage'],100):
        information='Se respondieron todas las preguntas que corresponden a la actividad de la empresa. El avance se muestra en el resultado general.'
    else:
        information='Todavía hay respuestas por confirmar. Completar esa información ayudará a entender mejor la situación de la empresa.'
    return {'summary':summary,'title':title,'action':action,'information':information}


def plan_presentation(result: dict[str,Any]) -> dict[str,Any]:
    plan=result['plan']
    intro='Para conocer la situación del Plan de Igualdad, se revisa si está escrito, si fue aprobado, si sus acciones ya están en marcha y si el equipo lo conoce.'
    if not plan['active']:
        response=next(p['response'] for p in result['practices'] if p['name']=='weps_31')
        summary=('La respuesta '+quote_survey('No')+' indica que la empresa todavía no cuenta con un Plan de Igualdad ni con otra herramienta de planificación para la igualdad. La primera acción es definir objetivos, acciones y responsables.' if response=='no' else 'Todavía falta confirmar si la empresa cuenta con un Plan de Igualdad u otra herramienta para organizar sus acciones de igualdad.')
        return {'intro':intro,'summary':summary,'aspects':[],'pending':True}
    if plan['other_tool']:
        return {'intro':'En el formulario se seleccionó '+quote_survey(SCREENING_SPEC['plan_options']['otra_herramienta'])+'. La empresa indicó que utiliza otra herramienta para organizar sus acciones de igualdad de género.',
                'summary':'Conviene revisar que esa herramienta identifique los objetivos de igualdad, las acciones previstas y las personas responsables de llevarlas a cabo.',
                'aspects':[],'pending':bool(plan['pending'])}
    selected=[PLAN_DESCRIPTIONS[code][2] for code,_,_ in PLAN_STAGES if code in plan['confirmed']]
    selected_quotes=[quote_survey(SCREENING_SPEC['plan_options'][code]) for code,_,_ in PLAN_STAGES if code in plan['confirmed']]
    pending=[PLAN_DESCRIPTIONS[code][3] for code,_,_ in PLAN_STAGES if code not in plan['confirmed']]
    summary=('En la encuesta se marcó '+join_words(selected_quotes)+'. Según esa respuesta, '+join_words(selected)+'.') if selected else 'Todavía no hay información sobre estos cuatro aspectos del plan.'
    if pending:summary+=' Queda por confirmar '+join_words(pending)+'.'
    if plan['invalid']:summary+=' Algunas opciones no coinciden entre sí o no se pudieron interpretar. Conviene revisarlas.'
    aspects=[{'code':code,'title':PLAN_DESCRIPTIONS[code][0],'meaning':PLAN_DESCRIPTIONS[code][1],
              'selected':code in plan['confirmed'],'next_action':PLAN_DESCRIPTIONS[code][4] if code not in plan['confirmed'] else ''} for code,_,_ in PLAN_STAGES]
    return {'intro':intro,'summary':summary,'aspects':aspects,'pending':bool(pending or plan['pending'])}


def question_analysis(practice: dict[str,Any], dimension: dict[str,Any]) -> dict[str,Any]:
    purpose=QUESTION_PURPOSES[practice['name']]
    if practice['applies'] is not True:
        comment='Según el perfil indicado en la encuesta, esta pregunta no corresponde a la actividad de la empresa y queda fuera del resultado.' if practice['applies'] is False else 'Hace falta completar el perfil de la empresa para saber si esta pregunta corresponde a su actividad.'
    elif practice['response'] in {'si','no'}:
        if practice['response']=='si':
            comment=QUESTION_MESSAGES[practice['name']][0]+' '+purpose
        else:
            comment=purpose+' Para empezar: '+QUESTION_MESSAGES[practice['name']][1]
    else:
        comment='Antes de sacar una conclusión, conviene confirmar si esta medida ya se aplica. '+purpose
    return {'comment':comment,'response_label':RESPONSE_LABELS[practice['status']]}


def plan_rows(result: dict[str,Any]) -> list[dict[str,Any]]:
    rows=[{'Dimensión':p['dimension'],'Pregunta':p['name'],'Práctica evaluada':p['question'],
             'Estado':RESPONSE_LABELS[p['status']],'Avance':QUESTION_MESSAGES[p['name']][0] if p['applies'] is True and p['response']=='si' else '',
             'Acción inicial':QUESTION_MESSAGES[p['name']][1] if p['applies'] is True and p['response']=='no' else (p['next_action'] if p['applies'] is True and p['response'] not in {'si','no'} else ''),
             'WEP principal':p['wep'],'WEP vinculados':p['secondary'],'Objetivo del plan':p['objective'],
             'Alcance de medición':p['limit']} for p in result['practices']]
    dimensions={d['id']:d for d in result['dimensions']}
    for row,practice in zip(rows,result['practices']):
        view=question_analysis(practice,dimensions[practice['dim']])
        row.update({'Comentario sobre la respuesta':view['comment']})
    plan=result['plan']
    if plan['active']:
        if plan['other_tool']:
            items=[('otra_herramienta','Otra herramienta de planificación para la igualdad de género.',True,plan['actions'][0])]
        else:
            items=[(code,positive,code in plan['confirmed'],'' if code in plan['confirmed'] else action.strip()) for code,positive,action in PLAN_STAGES]
        for code,positive,confirmed,action in items:
            rows.append({'Dimensión':'Planificación complementaria','Pregunta':'tv_plan_etapas/'+code,
                         'Práctica evaluada':positive,'Estado':'Indicado en la encuesta' if confirmed else 'Por confirmar o completar',
                         'Avance':positive if confirmed else '', 'Acción inicial':action,
                         'WEP principal':1,'WEP vinculados':'7','Objetivo del plan':QUESTION_MAP['weps_31']['objective'],
                         'Alcance de medición':'Información descriptiva de las etapas. No añade peso al índice ni mide ejecución del plan.'})
    return rows


def score_svg(score: float|None, title: str) -> str:
    """Standalone, printable chart for the downloaded HTML report."""
    esc=lambda value:html.escape(text_value(value))
    known=score is not None and math.isfinite(score)
    base=STATUS_COLORS['no'] if known else STATUS_COLORS['empty']
    ring=f'<circle cx="60" cy="60" r="43" fill="none" stroke="{base}" stroke-width="13"/>'
    if known:
        ring+=f'<circle cx="60" cy="60" r="43" fill="none" stroke="{STATUS_COLORS["yes"]}" stroke-width="13" pathLength="100" stroke-dasharray="{score:g} {100-score:g}" transform="rotate(-90 60 60)"/>'
        center=f'<text x="60" y="65" text-anchor="middle" font-size="17" fill="#253346">{esc(percent(score))}</text>'
    else:
        center='<text x="60" y="58" text-anchor="middle" font-size="10" fill="#62586D">Sin</text><text x="60" y="72" text-anchor="middle" font-size="10" fill="#62586D">información</text>'
    return f'<figure class="tv-donut"><svg viewBox="0 0 120 120" width="190" height="190" role="img" aria-label="{esc(title)}: {esc(percent(score))}">{ring}{center}</svg><figcaption>{esc(title)}</figcaption></figure>'


QUESTIONS_TABLE_CSS = '''
.tv-questions-wrap{border:1px solid #DDD6E5;border-radius:10px;overflow:hidden;margin:14px 0 22px;background:#FFFFFF;color:#253346}
.tv-questions-table{width:100%;table-layout:fixed;border-collapse:collapse;margin:0;font-size:14px;line-height:1.55}
.tv-questions-table th{background:#F3EDF8;color:#542778;font-weight:650;text-align:left;padding:12px 14px;border:0;border-bottom:1px solid #DDD6E5}
.tv-questions-table td{vertical-align:top;text-align:left;padding:13px 14px;border:0;white-space:normal;overflow-wrap:anywhere;word-break:normal;color:#253346;background:#FFFFFF}
.tv-questions-table tbody tr+tr td{border-top:1px solid #E8E3EC}
.tv-questions-table .tv-question-number{font-weight:700;color:#75449B;margin-right:5px}
.tv-questions-table .tv-response{display:inline-block;border-radius:6px;padding:4px 9px;font-weight:650;font-size:13px;white-space:normal}
.tv-questions-table .tv-response.advance{background:#E8F7EE;color:#145A40}.tv-questions-table .tv-response.improvement{background:#FFF4DF;color:#854D0E}
.tv-questions-table .tv-response.verify{background:#EAF2FF;color:#1E40AF}.tv-questions-table .tv-response.neutral{background:#F1F3F6;color:#64748B}
.tv-questions-table .tv-comment-copy{border-left:3px solid #C6B0D9;padding-left:10px;line-height:1.55}
.tv-questions-table .tv-comment-copy[data-status="si"]{border-color:#16815A}.tv-questions-table .tv-comment-copy[data-status="no"]{border-color:#D97706}
.tv-questions-table .tv-question-meta{font-size:12px;color:#62586D;line-height:1.5;margin-top:8px}
@media(max-width:760px){.tv-questions-table colgroup,.tv-questions-table thead{display:none}.tv-questions-table,.tv-questions-table tbody,.tv-questions-table tr,.tv-questions-table td{display:block;width:100%;box-sizing:border-box}.tv-questions-table tr{padding:10px 14px}.tv-questions-table tbody tr+tr{border-top:1px solid #E8E3EC}.tv-questions-table td{padding:5px 0;border:0!important}.tv-questions-table td:before{content:attr(data-label);display:block;font-size:12px;font-weight:650;color:#62586D;margin-bottom:4px}}
'''


def objective_label(value: str) -> str:
    match=re.match(r'^(O\d{2}(?:/O\d{2})*),\s*(.+)$',value)
    if not match:return value
    title=match[2]
    return title[0].upper()+title[1:]+' ('+match[1]+')'


def questions_table_html(practices: list[dict[str,Any]], dimension: dict[str,Any]) -> str:
    esc=lambda value:html.escape(text_value(value))
    rows=[]
    for position,practice in enumerate(practices,1):
        view=question_analysis(practice,dimension)
        color='advance' if practice['status']=='si' else ('improvement' if practice['status']=='no' else ('neutral' if practice['status']=='no_aplica' else 'verify'))
        answer=quote_survey(view['response_label']) if practice['status'] in {'si','no'} else view['response_label']
        weps=str(practice['wep'])+(' (relación con '+practice['secondary']+')' if practice['secondary'] else '')
        weight=f"{practice['weight']:g}".replace('.',',')+' %'
        rows.append('<tr data-question="'+esc(practice['name'])+'">'
            '<td data-label="Pregunta"><span class="tv-question-number">'+str(position)+'.</span> '+esc(quote_survey(practice['question']))+'</td>'
            '<td data-label="Respuesta"><span class="tv-response '+color+'">'+esc(answer)+'</span></td>'
            '<td data-label="Comentario y primer paso"><div class="tv-comment-copy" data-status="'+esc(practice['status'])+'">'+esc(view['comment'])+'</div></td>'
            '<td data-label="Relación con el plan">'+esc(objective_label(practice['objective']))+'<div class="tv-question-meta">WEP: '+esc(weps)+'<br>Peso de la pregunta: '+esc(weight)+'</div></td></tr>')
    return '<div class="tv-questions-wrap"><table class="tv-questions-table"><colgroup><col style="width:34%"><col style="width:9%"><col style="width:40%"><col style="width:17%"></colgroup><thead><tr><th>Pregunta</th><th>Respuesta</th><th>Comentario y primer paso</th><th>Relación con el plan</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def html_report(name: str, result: dict[str,Any], record: Mapping[str,Any]) -> bytes:
    esc=lambda x:html.escape(text_value(x))
    blocks=[]
    for d in result['dimensions']:
        questions=[p for p in result['practices'] if p['dim']==d['id']]
        chart=score_svg(d['score'],'Avance en esta dimensión') if d['applicable'] else '<p>Esta dimensión no corresponde a la actividad indicada en la encuesta.</p>'
        observations=''.join('<p class="advance">'+esc(QUESTION_MESSAGES[p['name']][0])+'</p>' for p in questions if p['applies'] is True and p['response']=='si')
        observations+=''.join('<p class="improvement"><strong>Para empezar:</strong> '+esc(QUESTION_MESSAGES[p['name']][1])+'</p>' for p in questions if p['applies'] is True and p['response']=='no')
        observations+=''.join('<p class="verify"><strong>Por confirmar:</strong> '+esc(item)+'</p>' for item in d['verify'])
        blocks.append(f"<h2>{d['id']}. {esc(d['title'])}</h2><p>Avance: {percent(d['score'])}. Información respondida: {percent(d['coverage'])}.</p>{chart}{observations}<h3>Preguntas, respuestas y comentarios</h3>{questions_table_html(questions,d)}")
    links=''.join(f'<p><a href="{esc(r[1])}">{esc(r[0])}</a></p>' for r in SCREENING_SPEC['resources'])
    presentation=plan_presentation(result)
    plan_block='<h2>Situación del Plan de Igualdad</h2><p>'+esc(presentation['intro'])+'</p><p class="verify">'+esc(presentation['summary'])+'</p>'
    for aspect in presentation['aspects']:
        status=('En la encuesta se marcó '+quote_survey(SCREENING_SPEC['plan_options'][aspect['code']])+'.') if aspect['selected'] else 'No se marcó esta opción. Conviene confirmar si ya se cumple o si todavía está pendiente.'
        next_action='<p><strong>Siguiente paso:</strong> '+esc(aspect['next_action'])+'</p>' if aspect['next_action'] else ''
        plan_block+='<article class="tv-question"><h3>'+esc(aspect['title'])+'</h3><p>'+esc(aspect['meaning'])+'</p><p class="'+('advance' if aspect['selected'] else 'verify')+'">'+esc(status)+'</p>'+next_action+'</article>'
    detail=text_value(RecordFields(record).get('tv_comunicacion_igualdad_detalle')).strip() if normalize_response(RecordFields(record).get('weps_30'))=='si' else ''
    if detail:plan_block+='<h2>Documentos mencionados en la encuesta</h2><p>'+esc(quote_survey(detail))+'</p>'
    overview=score_svg(result['score'],'Resultado general')
    reading=diagnostic_reading(result)
    for d in result['dimensions']:
        value=d['score']
        bars=(f'<div class="tv-track"><div style="width:{value:g}%"></div></div>' if value is not None else '<div class="tv-track unavailable"></div>')
        overview+=f'<div class="tv-score-row"><span>D{d["id"]}. {esc(d["title"])}</span>{bars}<strong>{esc(percent(value))}</strong></div>'
    content=f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Diagnóstico Turismo Violeta</title>
<style>body{{font:15px Georgia,serif;color:#253346;max-width:1100px;margin:35px auto;padding:0 20px}}h1,h2{{color:#542778}}table{{border-collapse:collapse;width:100%;margin:20px 0}}th,td{{border:1px solid #ddd;padding:9px;vertical-align:top;text-align:left}}th{{background:#f2eaf7}}.advance{{background:#E8F7EE;color:#145A40}}.improvement{{background:#FFF4DF;color:#854D0E}}.verify{{background:#EAF2FF;color:#1E40AF}}p.advance,p.improvement,p.verify{{padding:13px 16px;border-radius:8px}}p.improvement{{border-left:4px solid #D97706}}.neutral{{color:#64748B}}.tv-donut{{margin:12px 0;text-align:center;width:220px}}.tv-donut figcaption{{font-weight:bold}}.tv-score-row{{display:grid;grid-template-columns:minmax(240px,1.5fr) 1fr 115px;gap:16px;align-items:center;margin:16px 0}}.tv-track{{height:14px;border-radius:7px;background:#F1F3F6;overflow:hidden}}.tv-track div{{height:100%;background:#16815A}}.tv-track.unavailable{{background:#D8DDE5}}.tv-reading{{background:#FAF7FD;border-left:5px solid #75449B;padding:18px 22px;border-radius:10px;line-height:1.65;margin:20px 0}}.tv-question{{border:1px solid #E8DDF1;padding:16px 20px;margin:18px 0;border-radius:10px;break-inside:avoid}}.tv-question h3{{font-size:16px;line-height:1.55}}.tv-question-comment{{background:#FAFAFC;color:#253346;border-left:3px solid #C6B0D9;padding:14px 18px;margin:16px 0;line-height:1.6}}.tv-question-comment p{{margin:8px 0 0}}@media print{{body{{print-color-adjust:exact;-webkit-print-color-adjust:exact}}table{{font-size:10px}}h2{{break-after:avoid}}tr{{break-inside:avoid}}details table{{display:table}}}}@media(max-width:650px){{.tv-score-row{{grid-template-columns:1fr;gap:5px}}}}</style>
<style>{QUESTIONS_TABLE_CSS}</style>
<h1>Turismo Violeta: diagnóstico inicial</h1><h2>{esc(name)}</h2><p>Fecha: {esc(date_display(record))}. Modelo: {MODEL_VERSION}.</p>
<p>Avance inicial: <b>{percent(result['score'])}</b>. Información respondida: <b>{percent(result['coverage'])}</b>.</p>
<div class="tv-reading"><h2>Lectura del diagnóstico</h2><p>{esc(reading['summary'])}</p><p><strong>{esc(reading['title'])}</strong></p><p>{esc(reading['action'])}</p><p>{esc(reading['information'])}</p></div>
<p>Verde: lo que ya está en marcha. Ámbar: lo que se puede mejorar. Azul: lo que falta confirmar.</p>
<h2>Resultados del diagnóstico</h2>{overview}<p>Los resultados tienen en cuenta el peso de cada tema y las respuestas que se pudieron confirmar.</p>
{plan_block}{''.join(blocks)}<h2>Dimensiones transversales</h2><p>Comunicación y mejora continua reutilizan respuestas y no añaden puntos al índice.</p>
<h2>Herramientas</h2>{links}<p><a href="{DASHBOARD_URL}">Consultar el dashboard</a></p></html>'''
    return content.encode('utf-8')


def flatten_record(record: Mapping[str,Any], prefix: str='') -> dict[str,Any]:
    out={}
    for k,v in record.items():
        key=prefix+str(k)
        if isinstance(v,dict): out.update(flatten_record(v,key+'/'))
        elif isinstance(v,(list,tuple)):
            if all(isinstance(item,(str,int,float,bool)) for item in v):out[key]=' '.join(map(str,v))
        else: out[key]=v
    return out


def parse_json_page(payload: Any) -> tuple[list[dict[str,Any]],str|None]:
    if isinstance(payload,list): values=payload;next_url=None
    elif isinstance(payload,dict) and isinstance(payload.get('results'),list):values=payload['results'];next_url=payload.get('next')
    else: raise ValueError('La respuesta JSON de Kobo no contiene una lista de registros.')
    return [flatten_record(r) for r in values if isinstance(r,dict)],text_value(next_url).strip() or None


def fetch_kobo_bytes(url: str, token: str, max_bytes: int=100_000_000) -> tuple[bytes,str]:
    """HTTPS only; signed-download redirects never receive the Kobo token."""
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('La fuente de Kobo debe ser una URL HTTPS válida.')
    clean_token=re.sub(r'^(?:Token|Bearer)\s+','',text_value(token).strip(),flags=re.I)
    headers={'Accept':'application/json, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, text/csv', 'Cache-Control':'no-cache'}
    if clean_token: headers['Authorization']='Token '+clean_token
    # Synchronous exports may redirect to a signed storage download. Continue
    # reading that file while stripping credentials before any origin change.
    from urllib.request import HTTPRedirectHandler, build_opener
    class SameOriginRedirect(HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,hdrs,newurl):
            new=urlsplit(newurl)
            if new.scheme!='https' or new.username or new.password:
                raise ValueError('La fuente redirige a una URL no válida.')
            forwarded=super().redirect_request(req,fp,code,msg,hdrs,newurl)
            if forwarded is not None and (new.hostname,new.port)!=(parsed.hostname,parsed.port):
                forwarded.remove_header('Authorization');forwarded.remove_header('Cookie')
            return forwarded
    opener=build_opener(SameOriginRedirect())
    with opener.open(Request(url,headers=headers),timeout=60) as response:
        data=response.read(max_bytes+1)
        if len(data)>max_bytes: raise ValueError('La fuente supera el tamaño máximo de lectura configurado.')
        return data,text_value(response.headers.get('Content-Type','')).lower()


def load_source_uncached(url: str, token: str) -> tuple[Any,dict[str,Any]]:
    """Read XML-header exports or paginated API JSON without dropping new fields."""
    import pandas as pd
    data,kind=fetch_kobo_bytes(url,token)
    if 'json' in kind or data.lstrip().startswith((b'{',b'[')):
        rows,nxt=parse_json_page(json.loads(data));seen={url};pages=1
        while nxt:
            nxt=urljoin(url,nxt)
            if urlsplit(nxt)[:2]!=urlsplit(url)[:2]: raise ValueError('Kobo devolvió una página en otro servidor.')
            if nxt in seen or pages>=500: raise ValueError('La paginación de Kobo está incompleta o es circular.')
            seen.add(nxt);pages+=1;more,_=fetch_kobo_bytes(nxt,token);page,nxt=parse_json_page(json.loads(more));rows.extend(page)
        frame=pd.DataFrame(rows)
        if frame.columns.duplicated().any():raise ValueError('Hay encabezados duplicados en la fuente.')
        return frame,{}
    if data[:2]==b'PK':
        sheets=pd.read_excel(io.BytesIO(data),sheet_name=None,dtype=str,keep_default_na=False)
        if 'survey' in sheets and 'type' in sheets['survey'].columns:
            raise ValueError('La fuente es un XLSForm. Se necesita la exportación de respuestas, no la definición del formulario.')
        cleaned={str(k):v.rename(columns=clean_col).dropna(how='all') for k,v in sheets.items()}
        if not cleaned:return pd.DataFrame(),{}
        name=next(iter(cleaned));frame=cleaned.pop(name)
    else:
        try: frame=pd.read_csv(io.BytesIO(data),dtype=str,keep_default_na=False,sep=None,engine='python',encoding='utf-8-sig')
        except (UnicodeDecodeError,ValueError) as exc: raise ValueError('La fuente no corresponde a una exportación CSV/XLSX ni JSON de Kobo.') from exc
        frame=frame.rename(columns=clean_col);cleaned={}
    if frame.columns.duplicated().any(): raise ValueError('Hay encabezados duplicados en la exportación.')
    # Drop fully blank rows without turning legitimate No or zero values into nulls.
    frame=frame.loc[frame.apply(lambda r:any(text_value(v).strip() for v in r),axis=1)].reset_index(drop=True)
    return frame,cleaned


def get_secret(name: str, default: str='') -> str:
    try: return text_value(st.secrets.get(name,default)).strip()
    except Exception: return default


def find_field_column(df: Any, field_name: str) -> str|None:
    if field_name in df.columns:return field_name
    candidates=[c for c in df.columns if canonical_field(c)==canonical_field(field_name)]
    return candidates[0] if len(candidates)==1 else None


def records_from_frame(df: Any) -> list[dict[str,Any]]:
    return [{str(k):v for k,v in row.items()} for row in df.to_dict(orient='records')]


def province_label(record: Mapping[str,Any]) -> str:
    f=RecordFields(record);raw=f.get(get_secret('PROVINCE_COLUMN') or 'provincia_operacion',aliases=['Provincia de operación','15.1 Provincia'])
    value=norm_text(raw)
    if value in SCREENING_SPEC['province_codes']:return SCREENING_SPEC['province_codes'][value]
    for name in SCREENING_SPEC['provinces']:
        if value==norm_text(name):return name
    return 'Sin provincia'


def public_provinces(entries: list[dict[str,Any]]) -> list[dict[str,Any]]:
    counts=Counter(province_label(e['record']) for e in entries)
    return [{'Provincia':name,'Empresas':n,'lat':SCREENING_SPEC['provinces'][name][0],'lon':SCREENING_SPEC['provinces'][name][1]}
            for name,n in counts.items() if name in SCREENING_SPEC['provinces']]


def render_header() -> None:
    st.title('Dashboard empresarial | Turismo Violeta')
    st.caption(APP_VERSION)
    st.write('Una primera mirada a cómo está la empresa en igualdad de género y por dónde puede empezar a mejorar. Los resultados se organizan en seis dimensiones y dos temas transversales.')


def public_css() -> None:
    st.markdown('''<style>
    .block-container {padding-top:2rem;max-width:1550px}
    .tv-card {background:#fff;border:1px solid #e9e3ef;border-radius:14px;padding:18px 22px;margin:12px 0}
    .tv-kpi {background:#faf7fd;border:1px solid #e9e3ef;border-radius:12px;padding:16px;min-height:112px}
    .tv-kpi-label {font-size:.85rem;color:#62586d}.tv-kpi-value {font-size:1.8rem;color:#542778;font-weight:750}
    div[role="radiogroup"] {gap:.25rem;border-bottom:1px solid #e7e7ec;padding-bottom:.3rem;margin-bottom:1rem}
    div[role="radiogroup"] label {padding:.4rem .7rem;border-radius:8px 8px 0 0}
    .tv-reading {background:#FAF7FD;border:1px solid #E8DDF1;border-left:5px solid #75449B;border-radius:12px;padding:20px 24px;margin:18px 0 24px}
    .tv-reading h3 {font-size:1.15rem;margin:0 0 12px;color:#542778}
    .tv-reading p {margin:10px 0;line-height:1.65;color:#253346}
    .tv-reading .tv-information {font-size:.9rem;color:#62586D}
    .tv-question-comment {background:#FAFAFC;color:#253346;border-left:3px solid #C6B0D9;padding:14px 18px;margin:14px 0 16px;border-radius:0 8px 8px 0;line-height:1.6}
    .tv-question-comment p {margin:8px 0 0}
    .tv-answer {font-weight:650;padding:6px 12px;border-radius:6px;display:inline-block;margin-top:8px}
    .tv-answer.advance {background:#E8F7EE;color:#145A40}.tv-answer.improvement {background:#FFF4DF;color:#854D0E}
    .tv-answer.verify {background:#EAF2FF;color:#1E40AF}.tv-answer.neutral {background:#F1F3F6;color:#64748B}
    </style>''',unsafe_allow_html=True)
    st.markdown('<style>'+QUESTIONS_TABLE_CSS+'</style>',unsafe_allow_html=True)


def metric_cards(cards: list[tuple[str,Any]]) -> None:
    for col,(label,value) in zip(st.columns(len(cards)),cards):
        with col:
            st.markdown(f'<div class="tv-kpi"><div class="tv-kpi-label">{html.escape(label)}</div><div class="tv-kpi-value">{html.escape(str(value))}</div></div>',unsafe_allow_html=True)


def score_figure(score: float|None, title: str, height: int=250) -> Any:
    known=score is not None and math.isfinite(score)
    fig=go.Figure(go.Pie(
        values=[score,100-score] if known else [1],
        labels=['Avances según las respuestas','Por mejorar'] if known else ['Sin información'],
        hole=.78,sort=False,direction='clockwise',rotation=0,
        marker=dict(colors=[STATUS_COLORS['yes'],STATUS_COLORS['no']] if known else [STATUS_COLORS['empty']],line=dict(color='white',width=2)),
        textinfo='none',hovertemplate='%{label}: %{value:.1f} %<extra></extra>' if known else None,
        hoverinfo=None if known else 'skip'))
    fig.add_annotation(text=percent(score) if known else 'Sin información',x=.5,y=.5,showarrow=False,font=dict(size=25 if known else 16,color='#253346'))
    fig.update_layout(title=dict(text=title,x=.5,xanchor='center',font=dict(size=15)),height=height,
                      margin=dict(l=15,r=15,t=45,b=15),showlegend=False,paper_bgcolor='rgba(0,0,0,0)')
    return fig


def practice_counts_figure(dimensions: list[dict[str,Any]]) -> Any:
    labels=[f"D{d['id']}" for d in dimensions]
    fig=go.Figure()
    for field,label,color in [('yes','En marcha',STATUS_COLORS['yes']),('no','Por mejorar',STATUS_COLORS['no']),('unknown','Por confirmar',STATUS_COLORS['unknown'])]:
        fig.add_trace(go.Bar(x=[d[field] for d in dimensions],y=labels,name=label,orientation='h',marker_color=color,
                            text=[str(d[field]) if d[field] else '' for d in dimensions],textposition='inside',
                            customdata=[d['title'] for d in dimensions],hovertemplate='%{customdata}<br>'+label+': %{x}<extra></extra>'))
    fig.update_layout(title='Respuestas por dimensión',barmode='stack',height=330,margin=dict(l=15,r=20,t=50,b=60),
                      xaxis=dict(title='Número de prácticas aplicables',dtick=1,fixedrange=True),
                      yaxis=dict(autorange='reversed',fixedrange=True),
                      legend=dict(orientation='h',yanchor='top',y=-.2,x=0),paper_bgcolor='rgba(0,0,0,0)')
    return fig


def render_questions(practices: list[dict[str,Any]], dimension: dict[str,Any]) -> None:
    st.markdown(questions_table_html(practices,dimension),unsafe_allow_html=True)


def dimension_figure(dimensions: list[dict[str,Any]], title: str='') -> Any:
    values=[d['score'] for d in dimensions]
    fig=go.Figure(go.Bar(x=values,y=[f"D{d['id']}. {d['title']}" for d in dimensions],orientation='h',
                        marker_color='#75449B',text=[percent(x) for x in values],textposition='outside',cliponaxis=False))
    fig.update_layout(title=title,height=410,margin=dict(l=10,r=100,t=30,b=30),
                      xaxis=dict(range=[0,105],title='Avance inicial (%)',fixedrange=True),
                      yaxis=dict(autorange='reversed',fixedrange=True,automargin=True),showlegend=False)
    return fig


def route_figure(routes: dict[str,int]) -> Any:
    keys=[r for r in ROUTE_LABELS if routes.get(r,0)]
    fig=go.Figure(go.Bar(x=[routes[k] for k in keys],y=[ROUTE_LABELS[k] for k in keys],orientation='h',
                        marker_color=[ROUTE_COLORS[k] for k in keys],text=[routes[k] for k in keys],textposition='outside'))
    fig.update_layout(height=360,margin=dict(l=10,r=40,t=25,b=25),xaxis=dict(title='Empresas',dtick=1),yaxis=dict(autorange='reversed',automargin=True),showlegend=False)
    return fig


def render_resources(key: str) -> None:
    with st.expander('Herramientas para las primeras acciones'):
        for label,url,download in SCREENING_SPEC['resources']:
            st.markdown(f'[{label}]({url}) · [Descargar]({download})')
        form_url=get_secret('KOBO_FORM_URL')
        if form_url and urlsplit(form_url).scheme=='https':
            st.link_button('Abrir formulario para responder o cargar documentación',form_url)


def plan_stage_rows(result: dict[str,Any]) -> list[dict[str,Any]]:
    plan=result['plan']
    if not plan['active'] or plan['other_tool']:return []
    return [{'Etapa':SCREENING_SPEC['plan_options'][code],
             'Estado':'Indicado en la encuesta' if code in plan['confirmed'] else 'Por confirmar o completar',
             'Primera acción':'' if code in plan['confirmed'] else action.strip()} for code,_,action in PLAN_STAGES]


def render_plan(record: Mapping[str,Any], result: dict[str,Any]) -> None:
    presentation=plan_presentation(result)
    st.subheader('Situación del Plan de Igualdad')
    st.write(presentation['intro'])
    st.info(presentation['summary'])
    aspects=presentation['aspects']
    for offset in range(0,len(aspects),2):
        for column,aspect in zip(st.columns(2),aspects[offset:offset+2]):
            with column:
                with st.container(border=True):
                    st.markdown('**'+aspect['title']+'**')
                    st.write(aspect['meaning'])
                    if aspect['selected']:
                        st.success('En la encuesta se marcó '+quote_survey(SCREENING_SPEC['plan_options'][aspect['code']])+'.')
                    else:
                        st.info('No se marcó esta opción. Conviene confirmar si ya se cumple o si todavía está pendiente.')
                        st.write('**Siguiente paso:** '+aspect['next_action'])
    st.caption('Esta información ayuda a entender cómo se organiza el plan. Se muestra por separado del resultado general.')
    f=RecordFields(record)
    if normalize_response(f.get('weps_30'))=='si':
        detail=text_value(f.get('tv_comunicacion_igualdad_detalle')).strip()
        if detail:
            st.markdown('**Documentos mencionados en la encuesta**')
            st.write(quote_survey(detail))
    evidence=text_value(f.get('evidencia_institucional_URL')).strip()
    if evidence:
        parsed=urlsplit(evidence)
        if parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password:
            st.link_button('Consultar respaldo adjunto en Kobo',evidence)


def render_result(entry: dict[str,Any], key: str='company') -> None:
    result=entry['result'];record=entry['record'];name=entry['company']
    st.divider();st.subheader(name or 'Resultado de la empresa')
    st.caption('Fecha del registro: '+date_display(record))
    if not result['evaluable']:
        st.info('Este registro no se puede valorar con el modelo V18. Se requiere una respuesta completa del formulario actualizado.')
        for issue in result['issues']:st.caption(issue)
        return
    metric_cards([('Avance inicial',percent(result['score'])),('Información respondida',percent(result['coverage'])),('Medidas por poner en marcha',result['totals']['no']),('Respuestas por confirmar',result['totals']['por_verificar'])])
    reading=diagnostic_reading(result)
    esc=lambda value:html.escape(text_value(value))
    st.markdown('<div class="tv-reading"><h3>Lectura del diagnóstico</h3><p>'+esc(reading['summary'])+'</p><p><strong>'+esc(reading['title'])+'</strong></p><p>'+esc(reading['action'])+'</p><p class="tv-information">'+esc(reading['information'])+'</p></div>',unsafe_allow_html=True)
    if result['provisional']:st.info('Todavía hay información que necesita revisarse para completar el diagnóstico.')
    if result['critical_pending']:st.warning(f"Hay {result['critical_pending']} medidas básicas de protección por verificar.")
    if result['differences']:st.warning('Hay diferencias entre este resultado y el que aparece en Kobo. La administración puede revisar el detalle para aclararlas.')
    st.caption('Verde: lo que ya está en marcha. Ámbar: lo que se puede mejorar. Azul: lo que falta confirmar.')
    general,comparison=st.columns([1,2])
    with general:
        st.plotly_chart(score_figure(result['score'],'Resultado general',height=330),width='stretch',config=CHART_CONFIG,key=key+'_general_donut')
    with comparison:
        st.plotly_chart(dimension_figure(result['dimensions']),width='stretch',config=CHART_CONFIG,key=key+'_dims')
    st.plotly_chart(practice_counts_figure(result['dimensions']),width='stretch',config=CHART_CONFIG,key=key+'_response_counts')
    render_plan(record,result)
    for d in result['dimensions']:
        with st.expander(f"{d['id']}. {d['title']}",expanded=True):
            questions=[p for p in result['practices'] if p['dim']==d['id']]
            if d['applicable']==0:
                st.info('Según la actividad indicada en la encuesta, esta dimensión no corresponde a la empresa.');continue
            st.caption(f"Peso de esta dimensión en el resultado general: {d['weight']:g} %. Avance: {percent(d['score'])}. Información respondida: {percent(d['coverage'])}.")
            chart,counts=st.columns([1,2])
            with chart:
                st.plotly_chart(score_figure(d['score'],'Avance en esta dimensión',height=210),width='stretch',config=CHART_CONFIG,key=f"{key}_donut_d{d['id']:02d}")
            with counts:
                st.markdown('**Respuestas de esta dimensión**')
                metric_cards([('En marcha',d['yes']),('Por mejorar',d['no']),('Por confirmar',d['unknown'])])
            left,right=st.columns(2)
            with left:
                st.markdown('**Lo que ya está en marcha**')
                if d['advances']:
                    for p in questions:
                        if p['applies'] is True and p['response']=='si':st.success(QUESTION_MESSAGES[p['name']][0])
                else:st.write('Por ahora, las respuestas no muestran medidas en marcha en esta dimensión.')
            with right:
                st.markdown('**Qué se puede mejorar y por dónde empezar**')
                if d['actions']:
                    for p in questions:
                        if p['applies'] is True and p['response']=='no':st.warning(QUESTION_MESSAGES[p['name']][1])
                else:st.write('De acuerdo con las respuestas, no hay medidas pendientes de poner en marcha en esta dimensión.')
                if d['verify']:
                    st.markdown('**Por confirmar**')
                    for item in d['verify']:st.info(item)
            st.markdown('**Preguntas, respuestas y comentarios**')
            render_questions(questions,d)
    st.subheader('Dimensiones transversales')
    for t in result['transversals']:
        st.write(f"**{t['id']}. {t['title']}:** de {t['applicable']} medidas que corresponden a la empresa, {t['yes']} ya están en marcha, {t['no']} están pendientes y {t['unknown']} necesitan confirmarse.")
    st.caption('Estas dimensiones reutilizan respuestas y no añaden puntos al índice. Los vínculos con WEPs y objetivos son parciales; no equivalen a medir todos sus resultados.')
    f=RecordFields(record);commitments=multiple_selection(f,'compromisos_iniciales',SCREENING_SPEC['commitment_options'])['selected']
    if commitments:
        labels=[d['title'] for d in result['dimensions'] if f"d{d['id']:02d}" in commitments]
        st.write('**Categorías elegidas para las primeras acciones:** '+('; '.join(labels) if labels else 'Revisar selección en el formulario.'))
        deadline=text_value(f.get('plazo_inicial'))
        if deadline in {'30','60','90'}:st.write('**Plazo de revisión:** '+deadline+' días.')
    a,b=st.columns(2)
    slug=re.sub('[^a-z0-9]+','_',norm_text(name)).strip('_')[:70] or 'empresa'
    a.download_button('Descargar diagnóstico y acciones (HTML)',data=html_report(name,result,record),file_name=f'diagnostico_{slug}_V18.html',mime='text/html',key=key+'_html',on_click='ignore')
    b.download_button('Descargar matriz de acciones (CSV)',data=csv_bytes(plan_rows(result)),file_name=f'acciones_{slug}_V18.csv',mime='text/csv',key=key+'_csv',on_click='ignore')
    render_resources(key)


def render_company_view(entries: list[dict[str,Any]]) -> None:
    st.subheader('Acceso a resultados de empresa')
    available=[e for e in entries if e['company'] and normalize_response(RecordFields(e['record']).get('consentimiento'))=='si']
    if not available:
        st.info('Aún no hay registros con consentimiento disponibles para la consulta.');return
    available=sorted(available,key=lambda e:(norm_text(e['company']),e['key']))
    names=Counter(norm_text(e['company']) for e in available)
    def label(i):
        e=available[i]
        return e['company']+(' (RUC termina en '+e['key'][-4:]+')' if names[norm_text(e['company'])]>1 else '')
    with st.form('company_access'):
        a,b=st.columns([1.2,1])
        choice=a.selectbox('Nombre de empresa',range(len(available)),format_func=label,key='company_selection')
        code=b.text_input('Código de acceso',type='password',key='company_code')
        submitted=st.form_submit_button('Consultar diagnóstico')
    if not submitted:return
    entry=available[choice]
    if not credentials_match(entry['record'],code,get_secret('ACCESS_CODE_COLUMN')):
        st.error('La empresa y el código de acceso no coinciden.');return
    st.success('Código validado. Se muestran los resultados de la empresa seleccionada.')
    render_result(entry,'company_result')


def render_map(entries: list[dict[str,Any]], key: str) -> None:
    data=public_provinces(entries)
    st.subheader('Cobertura territorial')
    st.caption('Empresas por provincia de operación. Los puntos representan referencias provinciales y no ubicaciones exactas de empresas.')
    if not data:st.info('No se dispone de provincias válidas para representar en el mapa.');return
    frame=pd.DataFrame(data).sort_values(['Empresas','Provincia'],ascending=[False,True])
    left,right=st.columns([3,1])
    province=right.selectbox('Enfocar provincia',['Todo Ecuador']+frame['Provincia'].tolist(),key=key+'_province')
    mapped=frame if province=='Todo Ecuador' else frame[frame['Provincia']==province]
    mapped=mapped.copy();mapped['color']='#75449BDD';mapped['size']=mapped['Empresas'].apply(lambda n:min(10000,2400+1000*math.log1p(n)))
    with left:st.map(mapped,latitude='lat',longitude='lon',color='color',size='size',zoom=5 if province=='Todo Ecuador' else 8)
    right.dataframe(frame[['Provincia','Empresas']],hide_index=True,width='stretch')


def aggregate_practices(entries: list[dict[str,Any]]) -> list[dict[str,Any]]:
    valid=[e for e in entries if e['result']['evaluable']]
    rows=[]
    for q in QUESTIONS:
        items=[next(p for p in e['result']['practices'] if p['name']==q['name']) for e in valid]
        items=[p for p in items if p['applies'] is True]
        yes=sum(p['response']=='si' for p in items);no=sum(p['response']=='no' for p in items);unknown=len(items)-yes-no
        rows.append({'Dimensión':q['dim'],'Indicador':q['name'],'Práctica':q['question'],'Empresas aplicables':len(items),
                     'Sí':yes,'No':no,'Por verificar':unknown,'% Sí entre respuestas conocidas':100*yes/(yes+no) if yes+no else None,
                     'Información disponible (%)':100*(yes+no)/len(items) if items else None,
                     'Acción inicial':QUESTION_MESSAGES[q['name']][1],'WEP principal':q['wep'],'Objetivo del plan':q['objective']})
    return rows


def render_public_summary(entries: list[dict[str,Any]], records_n: int) -> None:
    summary=summarize(entries);valid=summary['evaluable']
    st.subheader('Resumen público')
    metric_cards([('Empresas con diagnóstico V18',summary['companies']),('Avance promedio',percent(summary['score'])),
                  ('Información respondida',percent(summary['coverage'])),('Dimensiones',6)])
    st.caption(f"Se toma la respuesta más reciente de cada empresa. En {summary['scores_n']} empresas hay información para calcular un resultado. El promedio resume esos resultados y ayuda a comparar los avances.")
    if not valid:st.info('Aún no hay diagnósticos V18 válidos para resumir. Los registros de otras versiones se revisan por separado en administración.');return
    if not summary['same_parameters']:st.warning('Algunas empresas tienen pesos o criterios de cálculo distintos. Para compararlas, la administración debe elegir un mismo esquema de cálculo.')
    st.caption('Esta primera mirada se basa en lo indicado en las encuestas. El siguiente paso es revisar los avances con los documentos que los respaldan.')
    a,b=st.columns([1.3,1])
    with a:
        st.markdown('**Avances por dimensión**')
        st.plotly_chart(dimension_figure(summary['dimensions']),width='stretch',config=CHART_CONFIG,key='public_dimensions')
    with b:
        st.markdown('**Siguiente paso recomendado**')
        st.plotly_chart(route_figure(summary['routes']),width='stretch',config=CHART_CONFIG,key='public_routes')
    render_map(valid,'public_map')
    st.subheader('Avances y primeras prioridades')
    table=aggregate_practices(valid)
    known=[r for r in table if r['Sí']+r['No']]
    positives=sorted(known,key=lambda r:(-r['Sí'],r['Indicador']))[:5]
    gaps=sorted([r for r in table if r['No']],key=lambda r:(-r['No'],r['Indicador']))[:5]
    a,b=st.columns(2)
    with a:
        st.markdown('**Lo que ya está en marcha**')
        for r in positives:
            if r['Sí']:st.write(f"{r['Sí']} empresas: {QUESTION_MESSAGES[r['Indicador']][0]}")
    with b:
        st.markdown('**Acciones iniciales más frecuentes**')
        for r in gaps:st.write(f"{r['No']} empresas: {r['Acción inicial']}")
    st.caption('Los vínculos con los siete WEPs se mantienen en la consulta individual. Las dimensiones 7 y 8 son transversales y no duplican puntuación.')
    render_resources('public')


def company_summary_row(e: dict[str,Any]) -> dict[str,Any]:
    r=e['result']
    return {'Empresa':e['company'],'Provincia':province_label(e['record']),'Avance (%)':r['score'],
            'Información respondida (%)':r['coverage'],'Siguiente paso':r['route_label'],
            'Medidas de protección pendientes':r['critical_no'],'Medidas en marcha':r['totals']['si'],
            'Medidas pendientes':r['totals']['no'],'Por confirmar':r['totals']['por_verificar'],
            'Aspectos del plan indicados en la encuesta':r['plan']['count'] if r['plan']['active'] and not r['plan']['other_tool'] else None,
            'Otra herramienta de planificación':bool(r['plan']['other_tool']),
            'Etapas por verificar':bool(r['plan']['pending']),
            'Diferencias con Kobo':len(r['differences']),'Fecha':date_display(e['record']),
            **{f"D{d['id']} (%)":d['score'] for d in r['dimensions']}}


def render_admin_dashboard(entries: list[dict[str,Any]], records: list[dict[str,Any]]) -> None:
    st.subheader('Panel administrativo')
    configured=get_secret('ADMIN_PASSWORD')
    typed=st.text_input('Clave de administrador',type='password',key='admin_password')
    if not configured:
        st.info('El acceso administrativo debe ser habilitado por quien administra la aplicación.');return
    if not admin_password_matches(typed,configured):
        st.info('Ingresar la clave de administrador para continuar.');return
    with st.expander('Exportaciones de Kobo'):
        st.write('Exportación TURISMO, con nombres XML de los campos de V18. Las descargas pueden requerir acceso a Kobo.')
        a,b=st.columns(2)
        a.link_button('Descargar respuestas originales (Excel)',SCREENING_SPEC['export']['data_url_xlsx'])
        b.link_button('Descargar respuestas originales (CSV)',SCREENING_SPEC['export']['data_url_csv'])
    if st.button('Actualizar datos desde Kobo',key='refresh_data'):
        st.cache_data.clear();st.rerun()
    valid=[e for e in entries if e['result']['evaluable']]
    historical=[e for e in entries if not e['result']['evaluable']]
    signatures=sorted({model_signature(e['result']) for e in valid})
    selected_signature=st.selectbox('Esquema de cálculo',['Todos']+signatures,key='admin_model_signature') if len(signatures)>1 else 'Todos'
    if selected_signature!='Todos':valid=[e for e in valid if model_signature(e['result'])==selected_signature]
    a,b,c=st.columns([1.5,1,1.3])
    ids=[e['key'] for e in valid];label={e['key']:e['company'] for e in valid}
    selected=a.multiselect('Empresas',ids,format_func=lambda x:label[x],key='admin_companies')
    provinces=sorted({province_label(e['record']) for e in valid})
    selected_provinces=b.multiselect('Provincia de operación',provinces,key='admin_provinces')
    routes=[k for k in ROUTE_LABELS if k!='no_evaluable']
    selected_routes=c.multiselect('Siguiente paso',routes,default=routes,format_func=lambda x:ROUTE_LABELS[x],key='admin_routes')
    a,b=st.columns([1.5,1])
    limits=a.slider('Rango de avance inicial',0,100,(0,100),key='admin_score_range')
    include_unknown=b.checkbox('Incluir empresas que todavía no tienen resultado',value=True,key='admin_include_unknown')
    filtered=[e for e in valid if (not selected or e['key'] in selected)
              and (not selected_provinces or province_label(e['record']) in selected_provinces)
              and e['result']['route'] in selected_routes
              and ((include_unknown and e['result']['score'] is None) or (e['result']['score'] is not None and limits[0]<=e['result']['score']<=limits[1]))]
    st.caption(f"Los filtros muestran {len(filtered)} empresas con diagnóstico V18. En Datos y calidad se pueden revisar {len(historical)} registros que necesitan atención. En total, la fuente contiene {len(records)} envíos.")
    view=st.radio('Vista administrativa',['Resumen general','Comparación y brechas','Detalle por empresa','Datos y calidad'],horizontal=True,key='admin_view')
    if view=='Datos y calidad':
        quality=[]
        for e in entries:
            r=e['result']
            quality.append({'Empresa':e['company'],'Versión':r['classification'],'Valorable V18':r['evaluable'],
                            'Diferencias con Kobo':len(r['differences']),'Campos contrastados':r['checked_fields'],
                            'Observaciones':'; '.join(r['issues']+r['notices'])})
        st.dataframe(pd.DataFrame(quality),hide_index=True,width='stretch')
        discrepancy=[{'Empresa':e['company'],**diff} for e in entries for diff in e['result']['differences']]
        if discrepancy:st.dataframe(pd.DataFrame(discrepancy),hide_index=True,width='stretch')
        st.caption('Se vuelve a calcular el resultado a partir de las respuestas y se compara con los cálculos que vienen de Kobo. Solo se comparan los campos incluidos en la descarga.')
        st.download_button('Descargar control de calidad (CSV)',csv_bytes(quality),file_name='calidad_diagnosticos_V18.csv',mime='text/csv',key='admin_quality_download')
        return
    if not filtered:st.info('Los filtros no devuelven diagnósticos V18.');return
    summary=summarize(filtered)
    if view=='Resumen general':
        metric_cards([('Empresas',len(filtered)),('Avance promedio',percent(summary['score'])),('Información respondida',percent(summary['coverage'])),('Con diferencias de cálculo',summary['discrepancies'])])
        if not summary['same_parameters']:st.warning('Filtrar un esquema de cálculo para obtener promedios comparables.')
        a,b=st.columns([1.3,1])
        with a:st.plotly_chart(dimension_figure(summary['dimensions']),width='stretch',config=CHART_CONFIG,key='admin_dims')
        with b:st.plotly_chart(route_figure(summary['routes']),width='stretch',config=CHART_CONFIG,key='admin_route_chart')
        render_map(filtered,'admin_map')
    elif view=='Comparación y brechas':
        table=[company_summary_row(e) for e in filtered]
        st.dataframe(pd.DataFrame(table),hide_index=True,width='stretch')
        if summary['same_parameters']:
            matrix=[[d['score'] for d in e['result']['dimensions']] for e in filtered]
            fig=go.Figure(go.Heatmap(z=matrix,x=[f'D{i}' for i in range(1,7)],y=[e['company'] for e in filtered],
                                    zmin=0,zmax=100,colorscale=[[0,'#F4EAF7'],[1,'#542778']],colorbar=dict(title='Prácticas (%)'),hoverongaps=False))
            fig.update_layout(height=max(350,min(900,len(filtered)*34+100)),yaxis=dict(autorange='reversed',automargin=True))
            st.plotly_chart(fig,width='stretch',config=CHART_CONFIG,key='admin_heatmap')
        practices=aggregate_practices(filtered)
        st.markdown('**Avances, mejoras y primeros pasos por pregunta**')
        st.dataframe(pd.DataFrame(practices),hide_index=True,width='stretch')
        a,b=st.columns(2)
        a.download_button('Descargar comparación (CSV)',csv_bytes(table),file_name='comparacion_empresas_V18.csv',mime='text/csv',key='admin_comparison_download')
        b.download_button('Descargar prácticas y brechas (CSV)',csv_bytes(practices),file_name='practicas_brechas_V18.csv',mime='text/csv',key='admin_practices_download')
    else:
        selected_id=st.selectbox('Empresa',range(len(filtered)),format_func=lambda i:filtered[i]['company'],key='admin_company_detail')
        render_result(filtered[selected_id],'admin_detail')
    with st.expander('Ponderaciones y alcance del cálculo'):
        weights=[{'Dimensión':d['title'],'Peso (%)':d['weight']} for d in filtered[0]['result']['dimensions']]
        st.dataframe(pd.DataFrame(weights),hide_index=True,width='stretch')
        st.write('Los pesos de esta versión son una propuesta técnica. VBG tiene el mayor peso y sus medidas básicas determinan la prioridad de protección. Las dimensiones transversales no vuelven a sumarse.')
        st.write('No se calculan brechas salariales, cobertura de formación, eficacia de canales o ejecución del plan sin los datos específicos que requieren esos indicadores.')


def main() -> None:
    global st,pd,go
    import streamlit as st
    import pandas as pd
    import plotly.graph_objects as go
    st.set_page_config(page_title='Dashboard Turismo Violeta',page_icon='📊',layout='wide')
    public_css();render_header()
    url=resolve_source_url(get_secret('KOBO_DATA_URL'));token=get_secret('KOBO_TOKEN')
    @st.cache_data(ttl=300,show_spinner=False)
    def load_data_from_source(source_url: str,source_token: str):return load_source_uncached(source_url,source_token)
    try:
        with st.spinner('Cargando respuestas de Kobo...'):df,_=load_data_from_source(url,token)
    except Exception:
        # Never expose request headers, token, configured URL or raw payloads.
        st.error('No se pudo cargar la fuente de respuestas. Revisar la configuración, los permisos y el formato de exportación.');return
    if df.empty:st.info('La fuente de Kobo todavía no devuelve respuestas.');return
    records=records_from_frame(df)
    custom_name=get_secret('COMPANY_COLUMN')
    if custom_name:
        col=find_field_column(df,custom_name)
        if col:
            for r in records:
                if not company_name(r):r['nombre_legal']=r.get(col)
    entries=analyze_latest(records)
    section=st.radio('Navegación principal',['Consulta por empresa','Resumen público','Panel administrativo'],horizontal=True,label_visibility='collapsed',key='main_navigation')
    if section=='Consulta por empresa':render_company_view(entries)
    elif section=='Resumen público':render_public_summary(entries,len(records))
    else:render_admin_dashboard(entries,records)


if __name__=='__main__':
    main()
