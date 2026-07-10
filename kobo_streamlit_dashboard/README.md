# Dashboard Turismo Violeta - v11 reconstruido desde cero

Versión limpia sin HTML renderizable como texto. Usa solo componentes nativos de Streamlit y Plotly.

## Archivos a reemplazar en GitHub
- app.py
- requirements.txt

## Secrets recomendados en Streamlit
KOBO_DATA_URL = "https://docs.google.com/spreadsheets/d/1PSFsSwHAvXHCeoWO2DzBmZln67FxwE9SBuxb_ET5ufo/gviz/tq?tqx=out:csv&sheet=Externos"
COMPANY_COLUMN = "1. Nombre legal de la organización"
ADMIN_PASSWORD = "TurismoVioleta2026"

ACCESS_CODE_COLUMN puede dejarse vacío o eliminarse. La app detecta automáticamente la columna que contiene "Código de acceso".
