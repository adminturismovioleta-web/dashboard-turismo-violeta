import hashlib
import html
import re
from datetime import datetime
from urllib.parse import quote

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ============================================================
# Dashboard Turismo Violeta - KOBO / Google Sheets
# Versión enfocada en lectura empresarial: principios, objetivos e indicadores.
# ============================================================

DEFAULT_GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1PSFsSwHAvXHCeoWO2DzBmZln67FxwE9SBuxb_ET5ufo/edit?usp=sharing"
DEFAULT_GOOGLE_SHEET_ID = "1PSFsSwHAvXHCeoWO2DzBmZln67FxwE9SBuxb_ET5ufo"
DEFAULT_SHEET_NAME = "Externos"

st.set_page_config(
    page_title="Turismo Violeta | Dashboard empresarial",
    page_icon="🟣",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Catálogo de lectura
# -----------------------------
PRINCIPLES = {
    1: {
        "code": "E.1.1",
        "title": "Promover la igualdad de género desde la dirección al más alto nivel",
        "objectives": [1, 2, 3],
        "focus": "compromiso de alta dirección, gobernanza, Comité de Igualdad, políticas institucionales y seguimiento del plan",
        "docs": "Principios WEPs; Acuerdo MDT-2025-102; documentos WEPs 1 al 8 cuando existan brechas de gobernanza.",
    },
    2: {
        "code": "E.1.2",
        "title": "Trato equitativo, derechos humanos y no discriminación en el trabajo",
        "objectives": [1, 2, 5, 7],
        "focus": "trato equitativo, igualdad en selección, promoción, formación, remuneración y condiciones laborales",
        "docs": "Principios WEPs; Acuerdo MDT-2025-102; Protocolo Turismo Violeta; Tool Kit; documentos WEPs 1 al 10.",
    },
    3: {
        "code": "E.1.3",
        "title": "Salud, seguridad, bienestar y vida libre de violencia",
        "objectives": [4, 5, 7],
        "focus": "prevención de violencia y acoso, rutas de atención, salud, seguridad, bienestar y protección",
        "docs": "Protocolo Turismo Violeta; Tool Kit; Acuerdo MDT-2025-102; Manual ESNNA; documentos WEPs 9 al 17.",
    },
    4: {
        "code": "E.1.4",
        "title": "Educación, formación y desarrollo profesional de mujeres y grupos subrepresentados",
        "objectives": [6, 7],
        "focus": "educación, formación, capacitación, desarrollo profesional y participación de mujeres y grupos subrepresentados",
        "docs": "Principios WEPs; Tool Kit para capacitación y fortalecimiento de capacidades; documentos WEPs 18 al 21.",
    },
    5: {
        "code": "E.1.5",
        "title": "Desarrollo empresarial, cadena de suministro y marketing a favor del empoderamiento de las mujeres",
        "objectives": [8, 9],
        "focus": "compras responsables, cadena de valor, proveedores, marketing responsable y prácticas empresariales con enfoque de igualdad",
        "docs": "Principios WEPs; Tool Kit para marketing, proveedores y cadena de valor; documentos WEPs 22 al 24.",
    },
    6: {
        "code": "E.1.6",
        "title": "Igualdad mediante iniciativas comunitarias y participación territorial",
        "objectives": [10, 11],
        "focus": "iniciativas comunitarias, participación territorial, pagos transparentes, alianzas locales y saberes ancestrales",
        "docs": "Principios WEPs; Plan Integral de Seguridad Turística; Protocolo Turismo Violeta; documentos WEPs 25 al 27.",
    },
    7: {
        "code": "E.1.7",
        "title": "Medición, reporte y mejora continua",
        "objectives": [11],
        "focus": "seguimiento periódico, indicadores, reporte, evidencias y actualización del plan de igualdad",
        "docs": "Matriz de indicadores, reportes internos, evidencias de seguimiento y actualización anual del plan.",
    },
}

OBJECTIVES = {
    1: {
        "code": "E.2.1",
        "title": "Compromiso institucional y liderazgo de alta dirección",
        "principles": [1, 2],
        "indicators": list(range(1, 4)),
        "reading": "Formalizar el compromiso de la dirección, comunicarlo internamente y convertirlo en responsabilidades concretas.",
    },
    2: {
        "code": "E.2.2",
        "title": "Política interna de igualdad y no discriminación",
        "principles": [1, 2],
        "indicators": list(range(4, 8)),
        "reading": "Revisar políticas internas para asegurar criterios explícitos de igualdad, no discriminación y derechos humanos.",
    },
    3: {
        "code": "E.2.3",
        "title": "Comité de Igualdad y gobernanza del plan",
        "principles": [1],
        "indicators": [8, 9, 20, 21, 22],
        "reading": "Formalizar el Comité de Igualdad, generar actas, capacitar integrantes y establecer seguimiento periódico.",
    },
    4: {
        "code": "E.2.4",
        "title": "Prevención de violencia, acoso y discriminación",
        "principles": [3],
        "indicators": list(range(10, 18)),
        "reading": "Consolidar rutas de prevención, atención y derivación; reforzar confidencialidad, protección y cero represalias.",
    },
    5: {
        "code": "E.2.5",
        "title": "Condiciones laborales, bienestar y vida libre de violencia",
        "principles": [2, 3],
        "indicators": [18, 19, 23, 24, 25, 26],
        "reading": "Alinear condiciones laborales, bienestar, seguridad y mecanismos de respuesta frente a riesgos psicosociales y violencia.",
    },
    6: {
        "code": "E.2.6",
        "title": "Educación, formación y desarrollo profesional",
        "principles": [4],
        "indicators": [27, 28, 29, 30],
        "reading": "Planificar formación periódica, fortalecer capacidades y crear oportunidades de desarrollo profesional.",
    },
    7: {
        "code": "E.2.7",
        "title": "Selección, promoción, remuneración y participación laboral",
        "principles": [2, 3, 4],
        "indicators": [31, 32, 33, 34, 35, 36],
        "reading": "Revisar procesos de selección, promoción y remuneración para reducir brechas y asegurar criterios transparentes.",
    },
    8: {
        "code": "E.2.8",
        "title": "Cadena de suministro y compras con enfoque de igualdad",
        "principles": [5],
        "indicators": [35, 36, 37, 38],
        "reading": "Incorporar criterios de igualdad en compras, proveedores, contratación y relaciones con la cadena de valor.",
    },
    9: {
        "code": "E.2.9",
        "title": "Marketing, comunicación y servicios turísticos responsables",
        "principles": [5],
        "indicators": [40, 41, 42],
        "reading": "Ajustar comunicación, marketing y servicios para evitar estereotipos y fortalecer el empoderamiento de las mujeres.",
    },
    10: {
        "code": "E.2.10",
        "title": "Participación territorial e iniciativas comunitarias",
        "principles": [6],
        "indicators": [39, 43, 44, 45],
        "reading": "Fortalecer alianzas locales, participación comunitaria, pagos transparentes y articulación territorial.",
    },
    11: {
        "code": "E.2.11",
        "title": "Seguimiento, indicadores, evidencias y mejora continua",
        "principles": [6, 7],
        "indicators": [46, 47, 48, 49, 50],
        "reading": "Definir indicadores, levantar evidencias, revisar avances periódicamente y actualizar el plan con base en resultados.",
    },
}

# -----------------------------
# Estilo
# -----------------------------
st.markdown(
    """
    <style>
        :root {
            --tv-primary: #7a2ea8;
            --tv-primary-dark: #2a1b3f;
            --tv-orange: #d85604;
            --tv-orange-soft: #fff1e8;
            --tv-soft: #faf7ff;
            --tv-panel: #ffffff;
            --tv-text: #152033;
            --tv-muted: #667085;
            --tv-border: #e7e2ee;
            --tv-line: #111827;
            --tv-good: #137333;
            --tv-mid: #b06000;
            --tv-bad: #a50e0e;
        }
        .main .block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
        #MainMenu, footer, header {visibility: hidden; height: 0;}
        [data-testid="stToolbar"], [data-testid="StyledFullScreenButton"], .modebar {display:none !important;}
        .tv-hero {
            padding: 1.35rem 1.55rem;
            border-radius: 24px;
            background: linear-gradient(135deg, #191d32 0%, #2c3f56 100%);
            margin-bottom: 1.15rem;
            color: white;
            box-shadow: 0 18px 42px rgba(16,24,40,.08);
        }
        .tv-title {font-size: 1.85rem; font-weight: 800; margin-bottom: .35rem;}
        .tv-subtitle {font-size: .98rem; opacity: .92; max-width: 1050px;}
        .tv-grid {display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .9rem; margin: .85rem 0 1rem;}
        .tv-kpi {
            padding: 1rem 1.05rem; border:1px solid var(--tv-border); border-radius: 22px; background: var(--tv-panel);
            min-height: 116px; display:flex; flex-direction:column; justify-content:center; box-shadow: 0 12px 28px rgba(16,24,40,.04);
        }
        .tv-kpi-label {font-size:.82rem; color: var(--tv-muted); margin-bottom:.25rem;}
        .tv-kpi-value {font-size:1.65rem; line-height:1.05; font-weight:800; color: var(--tv-text); word-break:break-word;}
        .tv-kpi-note {font-size:.78rem; color: var(--tv-muted); margin-top:.25rem;}
        .tv-section-title {font-size:1.25rem; font-weight:800; margin: 1.25rem 0 .65rem 0; color: var(--tv-text);}
        .tv-card {border:1px solid var(--tv-border); border-radius:20px; background:#fff; padding:1rem 1.1rem; margin:.55rem 0 1rem;}
        .tv-callout {border:1px solid var(--tv-border); border-left: 6px solid var(--tv-orange); border-radius:18px; background:#fff; padding:1rem 1.1rem; margin:.5rem 0 1rem;}
        .tv-callout strong {color: var(--tv-text);}
        .tv-small {font-size:.86rem; color: var(--tv-muted);}
        .tv-pill {display:inline-block; padding:.22rem .62rem; border-radius:999px; background: var(--tv-orange-soft); color: var(--tv-orange); font-size:.8rem; font-weight:700; margin-right:.35rem;}
        .tv-p-good {color: var(--tv-good); font-weight:800;}
        .tv-p-mid {color: var(--tv-mid); font-weight:800;}
        .tv-p-bad {color: var(--tv-bad); font-weight:800;}
        .tv-principle {
            border:1px solid var(--tv-border); border-radius:18px; background:#fff; margin:.7rem 0 1rem; overflow:hidden;
        }
        .tv-principle-head {display:flex; gap:.7rem; align-items:flex-start; padding:.95rem 1rem; border-bottom:1px solid var(--tv-border); background:#fff;}
        .tv-triangle {width:0; height:0; border-top:9px solid transparent; border-bottom:9px solid transparent; border-left:14px solid var(--tv-orange); margin-top:.2rem; flex:0 0 auto;}
        .tv-principle-title {font-weight:850; color:var(--tv-orange); font-size:1.05rem; line-height:1.28;}
        .tv-principle-body {border-top:5px solid var(--tv-line); background:#f7f7f8; padding:.85rem .95rem;}
        .tv-result-title {font-size:.9rem; font-weight:850; color: var(--tv-text); text-transform:uppercase; margin-bottom:.15rem;}
        .tv-result-text {font-size:.88rem; color:#4f5666; line-height:1.45; font-style:italic;}
        .tv-progress-wrap {height:10px; background:#ebe7f2; border-radius:999px; overflow:hidden; margin:.55rem 0 .25rem;}
        .tv-progress-bar {height:100%; background:linear-gradient(90deg, var(--tv-orange), var(--tv-primary)); border-radius:999px;}
        .tv-objective {border:1px solid #d9d9df; border-radius:14px; background:#fff; margin:.55rem 0; overflow:hidden;}
        .tv-objective-title {background:#f4f4f6; padding:.65rem .8rem; font-weight:800; color:var(--tv-text); border-bottom:1px solid #d9d9df;}
        .tv-objective-body {padding:.7rem .8rem; line-height:1.45;}
        .tv-table {width:100%; border-collapse:collapse; font-size:.92rem; margin:.5rem 0 1rem;}
        .tv-table th {text-align:left; background:#f6f6f8; color:#5f6675; padding:.65rem .6rem; border:1px solid #e3e3e7; font-weight:750;}
        .tv-table td {padding:.65rem .6rem; border:1px solid #e8e8eb; vertical-align:top;}
        .tv-table tr:nth-child(even) td {background:#fbfbfc;}
        .tv-ring-row {display:flex; align-items:center; gap:1rem; flex-wrap:wrap;}
        .tv-ring {
            width:108px; height:108px; border-radius:50%; display:grid; place-items:center; font-weight:850; font-size:1.35rem;
            background: conic-gradient(var(--tv-orange) var(--pct), #edf0f5 0);
        }
        .tv-ring-inner {width:78px; height:78px; border-radius:50%; background:#fff; display:grid; place-items:center; color:var(--tv-orange);}
        @media (max-width: 900px) {.tv-grid {grid-template-columns: repeat(2, minmax(0, 1fr));}}
        @media (max-width: 560px) {.tv-grid {grid-template-columns: 1fr;} .tv-title{font-size:1.45rem;}}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Configuración y utilidades
# -----------------------------
def get_secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def extract_sheet_id(url_or_id: str) -> str:
    if not url_or_id:
        return DEFAULT_GOOGLE_SHEET_ID
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", str(url_or_id))
    if m:
        return m.group(1)
    return str(url_or_id).strip()


def build_google_csv_url(sheet_url=None, sheet_id=None, sheet_name=DEFAULT_SHEET_NAME):
    final_id = sheet_id or extract_sheet_id(sheet_url or DEFAULT_GOOGLE_SHEET_URL)
    return f"https://docs.google.com/spreadsheets/d/{final_id}/gviz/tq?tqx=out:csv&sheet={quote(sheet_name)}"


def normalize_text(value) -> str:
    value = "" if value is None else str(value)
    value = value.strip().lower()
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    for a, b in replacements.items():
        value = value.replace(a, b)
    value = re.sub(r"\s+", " ", value)
    return value


def safe_column_name(col):
    col = str(col).strip()
    col = re.sub(r"\s+", " ", col)
    return col


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [safe_column_name(c) for c in df.columns]
    df = df.drop(columns=[c for c in df.columns if df[c].isna().all()], errors="ignore")
    df = df.dropna(how="all")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_from_url(url: str) -> pd.DataFrame:
    if str(url).lower().endswith(".xlsx"):
        return clean_dataframe(pd.read_excel(url))
    return clean_dataframe(pd.read_csv(url))


@st.cache_data(ttl=300, show_spinner=False)
def load_from_google(sheet_url: str, sheet_id: str, sheet_name: str) -> pd.DataFrame:
    return load_from_url(build_google_csv_url(sheet_url=sheet_url, sheet_id=sheet_id, sheet_name=sheet_name))


def load_data():
    # Compatible con los secretos anteriores y con los nuevos.
    direct_url = get_secret("KOBO_DATA_URL", None)
    sheet_url = get_secret("GOOGLE_SHEET_URL", DEFAULT_GOOGLE_SHEET_URL)
    sheet_id = get_secret("GOOGLE_SHEET_ID", extract_sheet_id(sheet_url))
    sheet_name = get_secret("GOOGLE_SHEET_NAME", DEFAULT_SHEET_NAME)

    with st.sidebar.expander("Fuente de datos", expanded=False):
        st.caption("Fuente conectada. El botón de carga manual solo se mantiene para pruebas locales.")
        st.code(direct_url or build_google_csv_url(sheet_url=sheet_url, sheet_id=sheet_id, sheet_name=sheet_name), language="text")
        uploaded = st.file_uploader("Subir archivo temporal", type=["xlsx", "csv"])

    if uploaded is not None:
        if uploaded.name.lower().endswith(".csv"):
            return clean_dataframe(pd.read_csv(uploaded))
        return clean_dataframe(pd.read_excel(uploaded))

    try:
        if direct_url:
            return load_from_url(direct_url)
        return load_from_google(sheet_url, sheet_id, sheet_name)
    except Exception as exc:
        st.error("No fue posible leer la fuente de datos. Verifique que la hoja esté compartida como pública o que el enlace CSV esté disponible.")
        st.exception(exc)
        st.stop()


def find_col(df: pd.DataFrame, candidates=None, contains=None, regex=None, secret_name=None):
    if secret_name:
        forced = get_secret(secret_name, "")
        if forced and forced in df.columns:
            return forced
    candidates = candidates or []
    contains = contains or []
    normalized = {normalize_text(c): c for c in df.columns}
    for c in candidates:
        key = normalize_text(c)
        if key in normalized:
            return normalized[key]
    for original in df.columns:
        n = normalize_text(original)
        if any(token in n for token in contains):
            return original
        if regex and re.search(regex, n, flags=re.I):
            return original
    return None


def find_company_col(df: pd.DataFrame):
    return find_col(
        df,
        candidates=["1. Nombre legal de la organización", "Nombre legal de la organización", "nombre_organizacion", "empresa", "organizacion", "organization", "company"],
        contains=["nombre legal de la organizacion", "empresa", "organizacion", "organization", "company"],
        secret_name="COMPANY_COLUMN",
    )


def find_access_col(df: pd.DataFrame):
    return find_col(
        df,
        candidates=["codigo_acceso", "código de acceso", "codigo", "_id", "id", "_uuid", "uuid", "meta/instanceID", "instanceID", "_submission__id", "audit"],
        contains=["codigo_acceso", "codigo de acceso", "_id", "uuid", "instanceid", "submission", "audit"],
        secret_name="ACCESS_CODE_COLUMN",
    )


def find_date_col(df: pd.DataFrame):
    return find_col(
        df,
        candidates=["end", "fecha_envio", "submission_time", "_submission_time", "today", "start"],
        contains=["fecha de envio", "fecha_envio", "submission", "end", "start", "today", "fecha"],
    )


def find_total_people_col(df: pd.DataFrame):
    return find_col(df, candidates=["Total de personas en la organización", "total_area", "Número total de personas: ${total_area}"], contains=["total de personas", "total_area", "numero total de personas"])


def find_general_score_col(df: pd.DataFrame):
    return find_col(
        df,
        candidates=["puntaje_general", "calificacion_general", "calificación general", "avance_general", "score_total", "total_score", "porcentaje_general"],
        contains=["puntaje general", "calificacion general", "calificación general", "avance general", "score total", "porcentaje general"],
        regex=r"(puntaje|calificacion|avance|score).*?(general|total)|(?:general|total).*?(puntaje|calificacion|avance|score)",
        secret_name="GENERAL_SCORE_COLUMN",
    )


def find_level_col(df: pd.DataFrame):
    return find_col(df, candidates=["nivel_avance", "nivel de avance", "nivel", "nivel_general"], contains=["nivel de avance", "nivel_avance", "nivel general"], secret_name="LEVEL_COLUMN")


def find_reading_col(df: pd.DataFrame):
    return find_col(df, candidates=["lectura_para_plan", "Lectura para plan", "lectura plan", "recomendacion_plan"], contains=["lectura para plan", "lectura plan", "recomendacion plan"], secret_name="READING_COLUMN")


def parse_date_series(s: pd.Series) -> pd.Series:
    raw = s.copy()
    parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    numeric = pd.to_numeric(raw, errors="coerce")
    excel_mask = parsed.isna() & numeric.between(20000, 70000)
    if excel_mask.any():
        parsed.loc[excel_mask] = pd.to_datetime(numeric.loc[excel_mask], unit="D", origin="1899-12-30", errors="coerce")
    return parsed


def parse_numeric_text(value):
    if value is None or pd.isna(value):
        return np.nan
    txt = str(value).strip()
    if txt == "":
        return np.nan
    # Manejo de formatos latinos y porcentajes.
    txt = txt.replace("%", "")
    if re.search(r"\d+\.\d{3}", txt) and "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    elif "," in txt and "." not in txt:
        txt = txt.replace(",", ".")
    try:
        return float(txt)
    except Exception:
        return np.nan


def column_scale(col: str):
    n = normalize_text(col)
    if "0 a 5" in n or "0-5" in n or "0/5" in n:
        return 5
    if "0 a 10" in n or "0-10" in n or "0/10" in n:
        return 10
    return None


def score_value(value, col: str = ""):
    if value is None or pd.isna(value):
        return np.nan
    txt = normalize_text(value)
    if txt in {"", "nan", "none", "no aplica", "n/a", "na", "no sabe", "no responde"}:
        return np.nan

    num = parse_numeric_text(value)
    if pd.notna(num):
        scale = column_scale(col)
        if scale and 0 <= num <= scale:
            return float(num / scale * 100)
        if 0 <= num <= 1:
            return float(num * 100)
        if 0 <= num <= 5 and any(t in normalize_text(col) for t in ["weps-tv", "documento", "accion", "acción"]):
            return float(num / 5 * 100)
        if 0 <= num <= 100:
            return float(num)

    positive = ["si", "sí", "cumple", "implementado", "alto", "existe", "cuenta con", "formalizado", "aprobado"]
    partial = ["parcial", "en proceso", "medio", "algunas", "algunos", "a veces", "limitado", "en construccion", "en construcción"]
    negative = ["no", "bajo", "no cumple", "no existe", "pendiente", "inicial", "ninguno", "ninguna"]
    if any(p in txt for p in partial):
        return 50
    if txt in {"1", "true", "verdadero"} or any(p == txt or txt.startswith(p + " ") for p in positive):
        return 100
    if txt in {"0", "false", "falso"} or any(p == txt or txt.startswith(p + " ") for p in negative):
        return 0
    return np.nan


def extract_numbers(col: str):
    n = normalize_text(col)
    nums = []
    for pat in [r"indicador(?:es)?\s*(\d{1,2})", r"weps-tv\s*(\d{1,2})", r"weps[\s_\-]*(\d{1,2})", r"objetivo\s*(\d{1,2})", r"principio\s*(\d{1,2})"]:
        nums.extend([int(x) for x in re.findall(pat, n) if str(x).isdigit()])
    return nums


def extract_principle_id(col: str):
    n = normalize_text(col)
    # Evitar confundir documentos WEPS-TV con principios WEPs.
    if "weps-tv" in n:
        return None
    for pat in [r"principio\s*weps?\s*(\d)", r"resultado\s+del\s+principio\s+weps?\s*(\d)", r"calculo\s+interno\s*:?\s*weps?\s*(\d{1,2})", r"cálculo\s+interno\s*:?\s*weps?\s*(\d{1,2})"]:
        m = re.search(pat, n)
        if m:
            num = int(m.group(1))
            if 1 <= num <= 7:
                return num
    return None


def extract_objective_id(col: str):
    n = normalize_text(col)
    m = re.search(r"objetivo\s*(\d{1,2})", n)
    if m:
        num = int(m.group(1))
        if num in OBJECTIVES:
            return num
    return None


def infer_indicator_columns(df: pd.DataFrame):
    forced = get_secret("SCORE_COLUMNS", "")
    if forced:
        cols = [c.strip() for c in str(forced).split(",") if c.strip() in df.columns]
        if cols:
            return cols

    excluded_tokens = [
        "start", "end", "today", "username", "audit", "url", "consent", "consentimiento", "nombre legal", "representante", "ruc", "identidad", "direccion",
        "georeferenciacion", "latitude", "longitude", "altitude", "precision", "pagina web", "telefono", "correo", "contacto", "facebook", "instagram", "tiktok",
        "linkedin", "youtube", "red social", "principal actividad", "tiempo de operar", "certificacion", "cadena de valor", "relacion laboral", "descripcion",
        "numero de mujeres", "numero de hombres", "total de personas", "diversidad sexo", "composicion etnica", "nacionalidad", "edad", "discapacidad",
    ]
    included_tokens = [
        "calculo interno", "cálculo interno", "avance calculado", "resultado del principio", "puntaje", "score", "weps-tv", "0 a 5", "0-5",
        "principio weps", "objetivo", "indicador", "politica", "protocolo", "mecanismo", "capacitacion", "prevencion", "igualdad", "acoso", "violencia",
    ]
    cols = []
    for col in df.columns:
        n = normalize_text(col)
        if any(tok in n for tok in excluded_tokens):
            continue
        if any(tok in n for tok in included_tokens):
            sample_scores = df[col].head(80).map(lambda x: score_value(x, col))
            if sample_scores.notna().any():
                cols.append(col)
    return cols


def compute_row_score(row: pd.Series, indicator_cols):
    # Priorizar columnas de principio si existen para no mezclar demasiadas preguntas.
    pcols = [c for c in indicator_cols if extract_principle_id(c)]
    use_cols = pcols if pcols else indicator_cols
    values = [score_value(row.get(c), c) for c in use_cols]
    values = [v for v in values if pd.notna(v)]
    if not values:
        return np.nan
    return float(np.mean(values))


def level_from_score(score):
    if pd.isna(score):
        return "Sin cálculo"
    if score >= 80:
        return "Avanzado"
    if score >= 60:
        return "En consolidación"
    if score >= 40:
        return "En construcción"
    if score >= 20:
        return "Inicial"
    return "Crítico"


def status_from_score(score):
    if pd.isna(score):
        return "Sin dato"
    if score >= 80:
        return "Cumplido"
    if score >= 50:
        return "Parcial"
    return "Pendiente"


def generate_access_code(row: pd.Series, company_col: str, date_col: str = None):
    company = str(row.get(company_col, "empresa"))
    date_value = str(row.get(date_col, "")) if date_col else ""
    raw = f"{company}|{date_value}|turismo-violeta"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8].upper()
    return f"TV-{digest}"


def prepare_model(df: pd.DataFrame):
    company_col = find_company_col(df)
    access_col = find_access_col(df)
    date_col = find_date_col(df)
    total_people_col = find_total_people_col(df)
    score_col = find_general_score_col(df)
    level_col = find_level_col(df)
    reading_col = find_reading_col(df)
    indicator_cols = infer_indicator_columns(df)

    if company_col is None:
        st.error("No encontré una columna de empresa. Define COMPANY_COLUMN en secrets o revisa el nombre de la columna de empresa.")
        st.stop()

    dfm = df.copy()
    dfm["__empresa__"] = dfm[company_col].astype(str).str.strip()
    dfm = dfm[dfm["__empresa__"].notna() & (dfm["__empresa__"].astype(str).str.len() > 0)]

    if date_col:
        dfm["__fecha__"] = parse_date_series(dfm[date_col])
    else:
        dfm["__fecha__"] = pd.NaT

    if score_col:
        dfm["__score__"] = dfm[score_col].map(lambda x: score_value(x, score_col))
        source_score = f"columna: {score_col}"
    else:
        dfm["__score__"] = dfm.apply(lambda r: compute_row_score(r, indicator_cols), axis=1)
        source_score = "cálculo automático por principios/indicadores"

    if level_col:
        dfm["__nivel__"] = dfm[level_col].fillna(dfm["__score__"].map(level_from_score)).astype(str)
    else:
        dfm["__nivel__"] = dfm["__score__"].map(level_from_score)

    if access_col:
        dfm["__codigo_base__"] = dfm[access_col].astype(str).str.strip()
    else:
        dfm["__codigo_base__"] = ""
    dfm["__codigo_dashboard__"] = dfm.apply(lambda r: generate_access_code(r, company_col, date_col), axis=1)

    meta = {
        "company_col": company_col,
        "access_col": access_col,
        "date_col": date_col,
        "total_people_col": total_people_col,
        "score_col": score_col,
        "level_col": level_col,
        "reading_col": reading_col,
        "indicator_cols": indicator_cols,
        "source_score": source_score,
    }
    return dfm, meta


def validate_access(row: pd.Series, code: str):
    typed = normalize_text(code)
    accepted = [row.get("__codigo_base__", ""), row.get("__codigo_dashboard__", "")]
    accepted = [normalize_text(x) for x in accepted if str(x).strip()]
    return bool(typed and typed in accepted)


def priority_class(score):
    if pd.isna(score):
        return "tv-p-mid"
    if score >= 70:
        return "tv-p-good"
    if score >= 40:
        return "tv-p-mid"
    return "tv-p-bad"


def format_score(score):
    if pd.isna(score):
        return "Sin cálculo"
    return f"{float(score):.1f}%"


def format_date(value):
    if value is None or pd.isna(value):
        return "Sin fecha"
    try:
        return pd.to_datetime(value).strftime("%d/%m/%Y")
    except Exception:
        return "Sin fecha"


def principle_scores(row: pd.Series, indicator_cols):
    records = []
    principle_cols = []
    for col in indicator_cols:
        pid = extract_principle_id(col)
        if pid:
            principle_cols.append((pid, col))

    for pid, meta in PRINCIPLES.items():
        vals = []
        source_cols = []
        for cpid, col in principle_cols:
            if cpid == pid:
                val = score_value(row.get(col), col)
                if pd.notna(val):
                    vals.append(val)
                    source_cols.append(col)
        if not vals:
            # Fallback: usa columnas de objetivos vinculados o indicadores numéricos mapeados.
            obj_ids = meta["objectives"]
            target_indicator_nums = set()
            for oid in obj_ids:
                target_indicator_nums.update(OBJECTIVES.get(oid, {}).get("indicators", []))
            for col in indicator_cols:
                nums = extract_numbers(col)
                if nums and any(n in target_indicator_nums for n in nums):
                    val = score_value(row.get(col), col)
                    if pd.notna(val):
                        vals.append(val)
                        source_cols.append(col)
        score = float(np.mean(vals)) if vals else np.nan
        records.append({
            "pid": pid,
            "Código": meta["code"],
            "Principio": f"Principio WEPs {pid}",
            "Título": meta["title"],
            "Puntaje": round(score, 1) if pd.notna(score) else np.nan,
            "Nivel": level_from_score(score),
            "Columnas": source_cols,
        })
    return pd.DataFrame(records)


def objective_scores(row: pd.Series, indicator_cols, principles_df: pd.DataFrame):
    records = []
    for oid, obj in OBJECTIVES.items():
        vals = []
        source_cols = []
        # Objetivo directo si existe.
        for col in indicator_cols:
            if extract_objective_id(col) == oid:
                val = score_value(row.get(col), col)
                if pd.notna(val):
                    vals.append(val)
                    source_cols.append(col)
        # Indicadores vinculados.
        if not vals:
            indicator_nums = set(obj["indicators"])
            for col in indicator_cols:
                nums = set(extract_numbers(col))
                if nums & indicator_nums:
                    val = score_value(row.get(col), col)
                    if pd.notna(val):
                        vals.append(val)
                        source_cols.append(col)
        # Fallback por principio vinculado.
        if not vals and not principles_df.empty:
            pvals = principles_df[principles_df["pid"].isin(obj["principles"])]["Puntaje"].dropna().tolist()
            vals.extend(pvals)
        score = float(np.mean(vals)) if vals else np.nan
        records.append({
            "oid": oid,
            "Código": obj["code"],
            "Objetivo": f"Objetivo {oid}: {obj['title']}",
            "Principios vinculados": ", ".join([f"WEPs {p}" for p in obj["principles"]]),
            "Indicadores": ", ".join(map(str, obj["indicators"])),
            "Puntaje": round(score, 1) if pd.notna(score) else np.nan,
            "Nivel": level_from_score(score),
            "Lectura": obj["reading"],
            "Columnas": source_cols,
        })
    return pd.DataFrame(records)


def build_indicator_table(row: pd.Series, indicator_cols, max_rows=15):
    records = []
    for col in indicator_cols:
        sc = score_value(row.get(col), col)
        if pd.isna(sc):
            continue
        records.append({
            "Indicador / evidencia": col,
            "Resultado": html.escape(str(row.get(col, "")))[:140],
            "Puntaje": round(float(sc), 1),
            "Estado": status_from_score(sc),
            "Prioridad": "Alta" if sc < 50 else ("Media" if sc < 80 else "Baja"),
        })
    table = pd.DataFrame(records)
    if table.empty:
        return table
    order = {"Alta": 0, "Media": 1, "Baja": 2}
    table["__order__"] = table["Prioridad"].map(order)
    table = table.sort_values(["__order__", "Puntaje", "Indicador / evidencia"]).drop(columns="__order__")
    return table.head(max_rows)


def html_table(df: pd.DataFrame, columns=None):
    if df is None or df.empty:
        return "<p class='tv-small'>Sin información suficiente para mostrar esta tabla.</p>"
    dfx = df.copy()
    if columns:
        dfx = dfx[columns]
    rows = []
    header = "".join([f"<th>{html.escape(str(c))}</th>" for c in dfx.columns])
    for _, r in dfx.iterrows():
        cells = []
        for c in dfx.columns:
            val = r[c]
            if isinstance(val, float) and pd.notna(val):
                val = f"{val:.1f}"
            cells.append(f"<td>{html.escape(str(val))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table class='tv-table'><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def general_plan_reading(score, principles_df, objectives_df, indicator_df):
    low_principles = principles_df.dropna(subset=["Puntaje"]).sort_values("Puntaje").head(2) if principles_df is not None else pd.DataFrame()
    low_objectives = objectives_df.dropna(subset=["Puntaje"]).sort_values("Puntaje").head(3) if objectives_df is not None else pd.DataFrame()
    weak_indicators = indicator_df[indicator_df["Prioridad"].eq("Alta")].head(5) if indicator_df is not None and not indicator_df.empty else pd.DataFrame()

    if pd.isna(score):
        opening = "El registro todavía no cuenta con suficientes campos calculables para producir una calificación general confiable."
    elif score >= 80:
        opening = "La empresa muestra un avance alto. El plan no debe empezar desde cero: conviene consolidar evidencias, reportar avances y sostener la mejora continua."
    elif score >= 60:
        opening = "La empresa presenta una base favorable. El plan debe convertir los avances existentes en responsabilidades, plazos, evidencias y seguimiento periódico."
    elif score >= 40:
        opening = "La empresa se encuentra en construcción. El plan debe ordenar las acciones por prioridad y cerrar primero las brechas institucionales, documentales y de prevención."
    elif score >= 20:
        opening = "La empresa está en una fase inicial. El plan debe empezar por compromisos básicos, responsables, protocolos, capacitación y evidencias mínimas."
    else:
        opening = "La empresa presenta brechas críticas. El plan debe iniciar con acciones fundacionales y de corto plazo antes de avanzar a mediciones o procesos complejos."

    parts = [opening]
    if not low_principles.empty:
        pp = "; ".join([f"{r['Principio']} ({format_score(r['Puntaje'])})" for _, r in low_principles.iterrows()])
        parts.append(f"A nivel de principios, la prioridad se concentra en: {pp}.")
    if not low_objectives.empty:
        oo = "; ".join([f"{r['Código']} {r['Objetivo'].split(': ', 1)[-1]} ({format_score(r['Puntaje'])})" for _, r in low_objectives.iterrows()])
        parts.append(f"A nivel de objetivos, el plan debería iniciar por: {oo}.")
    if not weak_indicators.empty:
        parts.append("A nivel de indicadores, las evidencias pendientes deben traducirse en actividades verificables: política/protocolo, responsable, fecha de implementación y documento de soporte.")
    return " ".join(parts)


def recommended_actions(score, principles_df, objectives_df):
    actions = []
    if pd.isna(score) or score < 40:
        actions.extend([
            ["Alta", "Formalizar compromiso interno de igualdad, prevención de violencia y no acoso.", "30 días"],
            ["Alta", "Designar Comité o responsable del plan con funciones, actas y calendario de seguimiento.", "30 días"],
            ["Alta", "Definir ruta mínima de actuación ante acoso, discriminación o violencia.", "45 días"],
        ])
    elif score < 70:
        actions.extend([
            ["Alta", "Convertir brechas en actividades, responsables, plazos e indicadores.", "30 días"],
            ["Media", "Planificar capacitación periódica para directivos y equipos operativos.", "60 días"],
            ["Media", "Consolidar evidencias documentales de cumplimiento y seguimiento.", "90 días"],
        ])
    else:
        actions.extend([
            ["Media", "Fortalecer medición periódica y revisión anual del plan.", "60 días"],
            ["Media", "Documentar buenas prácticas para replicarlas en áreas con menor avance.", "90 días"],
            ["Baja", "Preparar reporte de resultados y actualización de indicadores.", "12 meses"],
        ])
    if objectives_df is not None and not objectives_df.empty:
        lows = objectives_df.dropna(subset=["Puntaje"]).sort_values("Puntaje").head(2)
        for _, r in lows.iterrows():
            if r["Puntaje"] < 60:
                actions.append(["Alta", f"Priorizar {r['Código']} - {r['Objetivo'].split(': ', 1)[-1]}", "60 días"])
    return pd.DataFrame(actions, columns=["Prioridad", "Acción sugerida", "Plazo"])


def render_kpi(label, value, note=""):
    return f"""
    <div class="tv-kpi">
        <div class="tv-kpi-label">{html.escape(str(label))}</div>
        <div class="tv-kpi-value">{html.escape(str(value))}</div>
        <div class="tv-kpi-note">{html.escape(str(note))}</div>
    </div>
    """


def render_principle_card(row, objectives_df):
    score = row["Puntaje"]
    pct = 0 if pd.isna(score) else max(0, min(100, float(score)))
    cls = priority_class(score)
    pmeta = PRINCIPLES[row["pid"]]
    obj_rows = objectives_df[objectives_df["oid"].isin(pmeta["objectives"])].copy()
    linked_obj = ", ".join([f"{OBJECTIVES[o]['code'].replace('E.2.', '')}" for o in pmeta["objectives"]])
    body = f"""
    <div class="tv-principle">
        <div class="tv-principle-head">
            <div class="tv-triangle"></div>
            <div>
                <div class="tv-principle-title">» » {html.escape(row['Código'])}. {html.escape(row['Principio'])}: {html.escape(row['Título'])}</div>
                <div class="tv-small">Objetivos vinculados: {html.escape(linked_obj)} · Enfoque: {html.escape(pmeta['focus'])}</div>
            </div>
        </div>
        <div class="tv-principle-body">
            <div class="tv-result-title">Resultado del {html.escape(row['Principio'])}</div>
            <div class="tv-result-text">
                Avance calculado: <span class="{cls}">{format_score(score)}</span> | Nivel: {html.escape(row['Nivel'])}. 
                Lectura para plan: {html.escape(pmeta['focus'].capitalize())}. Documentos de apoyo: {html.escape(pmeta['docs'])}
            </div>
            <div class="tv-progress-wrap"><div class="tv-progress-bar" style="width:{pct:.0f}%"></div></div>
    """
    for _, o in obj_rows.iterrows():
        body += f"""
            <div class="tv-objective">
                <div class="tv-objective-title">» » {html.escape(o['Código'])}. {html.escape(o['Objetivo'])}</div>
                <div class="tv-objective-body">
                    <div><strong>Principios WEPs/TV vinculados:</strong> {html.escape(o['Principios vinculados'])}</div>
                    <div><strong>Avance calculado:</strong> <span class="{priority_class(o['Puntaje'])}">{format_score(o['Puntaje'])}</span> | <strong>Nivel:</strong> {html.escape(o['Nivel'])}</div>
                    <div><strong>Lectura para plan:</strong> {html.escape(o['Lectura'])}</div>
                    <div class="tv-small"><strong>Indicadores que sustentan este objetivo:</strong> {html.escape(o['Indicadores'])}</div>
                </div>
            </div>
        """
    body += "</div></div>"
    return body

# -----------------------------
# Carga principal
# -----------------------------
df_raw = load_data()
df, meta = prepare_model(df_raw)

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Turismo Violeta")
st.sidebar.caption("Dashboard conectado a KOBO / Google Sheets")
page = st.sidebar.radio("Vista", ["Resumen público", "Consulta empresarial", "Diagnóstico técnico"], index=0)
st.sidebar.divider()
st.sidebar.caption("Columnas detectadas")
st.sidebar.write(f"Empresa: `{meta['company_col']}`")
st.sidebar.write(f"Código: `{meta['access_col'] or 'código generado'}`")
st.sidebar.write(f"Puntaje: `{meta['source_score']}`")
st.sidebar.write(f"Indicadores evaluables: `{len(meta['indicator_cols'])}`")

# -----------------------------
# Encabezado
# -----------------------------
st.markdown(
    """
    <div class="tv-hero">
        <div class="tv-title">Dashboard empresarial | Turismo Violeta</div>
        <div class="tv-subtitle">Consulta pública de resultados agregados y acceso individual por empresa mediante código. La lectura se organiza por principios WEPs, objetivos, indicadores y acciones sugeridas para el plan.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Página 1: resumen público
# -----------------------------
if page == "Resumen público":
    total_records = len(df)
    total_companies = df["__empresa__"].nunique()
    avg_score = df["__score__"].mean()
    last_date = df["__fecha__"].max()

    kpis = "<div class='tv-grid'>" + "".join([
        render_kpi("Encuestas", f"{total_records:,}".replace(",", "."), "Registros recibidos"),
        render_kpi("Empresas", f"{total_companies:,}".replace(",", "."), "Organizaciones únicas"),
        render_kpi("Promedio general", "Sin cálculo" if pd.isna(avg_score) else f"{avg_score:.1f}%", "Calificación agregada"),
        render_kpi("Última actualización", format_date(last_date), "Fecha de envío más reciente"),
    ]) + "</div>"
    st.markdown(kpis, unsafe_allow_html=True)

    st.markdown('<div class="tv-section-title">Calificación general agregada</div>', unsafe_allow_html=True)
    left, right = st.columns([1.1, 1])
    with left:
        if df["__score__"].notna().any():
            hist = df[df["__score__"].notna()].copy()
            hist["Rango"] = pd.cut(hist["__score__"], bins=[-1, 20, 40, 60, 80, 101], labels=["0-20", "21-40", "41-60", "61-80", "81-100"])
            counts = hist.groupby("Rango", observed=False).size().reset_index(name="Encuestas")
            fig = px.bar(counts, x="Rango", y="Encuestas", text="Encuestas")
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), xaxis_title="Rango de puntaje", yaxis_title="Encuestas")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Aún no se detectan columnas suficientes para graficar puntajes generales.")
    with right:
        level_counts = df["__nivel__"].fillna("Sin cálculo").value_counts().reset_index()
        level_counts.columns = ["Nivel", "Encuestas"]
        fig = px.pie(level_counts, names="Nivel", values="Encuestas", hole=.48)
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="tv-section-title">Empresas registradas</div>', unsafe_allow_html=True)
    public_table = df[["__empresa__", "__fecha__", "__nivel__", "__score__"]].copy()
    public_table.columns = ["Empresa", "Fecha", "Nivel", "Puntaje"]
    public_table["Fecha"] = public_table["Fecha"].map(format_date)
    public_table["Puntaje"] = public_table["Puntaje"].map(format_score)
    st.markdown(html_table(public_table), unsafe_allow_html=True)
    st.caption("Esta vista es agregada. Para resultados individuales, cada empresa debe ingresar su código de acceso.")

# -----------------------------
# Página 2: consulta empresarial
# -----------------------------
elif page == "Consulta empresarial":
    st.markdown('<div class="tv-section-title">Acceso a resultados de empresa</div>', unsafe_allow_html=True)
    companies = sorted(df["__empresa__"].dropna().astype(str).unique().tolist())
    col_a, col_b = st.columns([1, 1])
    with col_a:
        company = st.selectbox("Nombre de empresa", companies, index=0 if companies else None)
    with col_b:
        code = st.text_input("Código de acceso", type="password", placeholder="Ingrese el código recibido")

    if not code:
        st.info("Seleccione la empresa e ingrese el código para ver la lectura del plan. No es necesario presionar ningún botón.")
        st.stop()

    candidates = df[df["__empresa__"].astype(str) == str(company)].copy()
    valid_rows = [(idx, row) for idx, row in candidates.iterrows() if validate_access(row, code)]
    if not valid_rows:
        st.error("El código no coincide con la empresa seleccionada. Verifique el nombre y el código recibido.")
        st.stop()

    row = pd.DataFrame([r[1] for r in valid_rows]).sort_values("__fecha__", ascending=False).iloc[0]
    score = row.get("__score__", np.nan)
    level = row.get("__nivel__", level_from_score(score))
    p_df = principle_scores(row, meta["indicator_cols"])
    o_df = objective_scores(row, meta["indicator_cols"], p_df)
    ind_df = build_indicator_table(row, meta["indicator_cols"])
    reading_text = row.get(meta["reading_col"]) if meta["reading_col"] else None
    if not reading_text or pd.isna(reading_text):
        reading_text = general_plan_reading(score, p_df, o_df, ind_df)

    principles_evaluated = int(p_df["Puntaje"].notna().sum()) if not p_df.empty else 0
    indicators_with_data = len(ind_df) if ind_df is not None else 0
    date_value = format_date(row.get("__fecha__"))

    kpis = "<div class='tv-grid'>" + "".join([
        render_kpi("Empresa", row["__empresa__"], "Registro validado"),
        render_kpi("Puntaje general", format_score(score), "Calificación consolidada"),
        render_kpi("Nivel de avance", level, "Lectura empresarial"),
        render_kpi("Fecha de envío", date_value, "Registro seleccionado"),
    ]) + "</div>"
    st.markdown(kpis, unsafe_allow_html=True)

    extra_kpis = "<div class='tv-grid'>" + "".join([
        render_kpi("Principios evaluados", f"{principles_evaluated}/7", "Estructura WEPs / Turismo Violeta"),
        render_kpi("Objetivos revisados", f"{len(o_df.dropna(subset=['Puntaje']))}/{len(OBJECTIVES)}", "Ruta del plan"),
        render_kpi("Indicadores priorizados", str(indicators_with_data), "Brechas con evidencia"),
        render_kpi("Personas en organización", str(row.get(meta["total_people_col"], "Sin dato")) if meta["total_people_col"] else "Sin dato", "Dato declarado"),
    ]) + "</div>"
    st.markdown(extra_kpis, unsafe_allow_html=True)

    st.markdown('<div class="tv-section-title">Calificación general</div>', unsafe_allow_html=True)
    pct = 0 if pd.isna(score) else max(0, min(100, float(score)))
    st.markdown(
        f"""
        <div class="tv-card tv-ring-row">
            <div class="tv-ring" style="--pct:{pct:.0f}%"><div class="tv-ring-inner">{format_score(score)}</div></div>
            <div>
                <div><span class="tv-pill">{html.escape(str(level))}</span></div>
                <div class="tv-progress-wrap" style="min-width:260px"><div class="tv-progress-bar" style="width:{pct:.0f}%"></div></div>
                <div class="tv-small">La calificación general sintetiza los avances detectados en los principios, objetivos e indicadores evaluables del instrumento.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="tv-section-title">Lectura para plan</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='tv-callout'><strong>Lectura ejecutiva.</strong> {html.escape(str(reading_text))}</div>", unsafe_allow_html=True)

    st.markdown('<div class="tv-section-title">Avance por principio</div>', unsafe_allow_html=True)
    chart_df = p_df.dropna(subset=["Puntaje"]).copy()
    if not chart_df.empty:
        fig = px.bar(chart_df, x="Puntaje", y="Principio", orientation="h", text="Puntaje", range_x=[0, 100])
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(height=max(300, 48 * len(chart_df)), margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Avance (%)", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No se detectaron puntajes por principio. Se mostrará la lectura por objetivos con los campos disponibles.")

    st.markdown('<div class="tv-section-title">Principios, objetivos e indicadores para el plan</div>', unsafe_allow_html=True)
    for _, prow in p_df.iterrows():
        st.markdown(render_principle_card(prow, o_df), unsafe_allow_html=True)

    st.markdown('<div class="tv-section-title">Prioridades sugeridas</div>', unsafe_allow_html=True)
    recs = recommended_actions(score, p_df, o_df)
    st.markdown(html_table(recs), unsafe_allow_html=True)

    st.markdown('<div class="tv-section-title">Indicadores críticos / brechas con mayor prioridad</div>', unsafe_allow_html=True)
    if not ind_df.empty:
        st.markdown(html_table(ind_df[["Indicador / evidencia", "Puntaje", "Estado", "Prioridad"]]), unsafe_allow_html=True)
    else:
        st.info("No se detectaron respuestas evaluables para construir la tabla de indicadores.")

# -----------------------------
# Página 3: diagnóstico técnico
# -----------------------------
else:
    st.markdown('<div class="tv-section-title">Diagnóstico técnico de la conexión</div>', unsafe_allow_html=True)
    admin_password = str(get_secret("ADMIN_PASSWORD", "")).strip()
    typed_admin_password = st.text_input("Clave de administrador", type="password", help="Necesaria para revisar códigos y diagnóstico en una app pública.")
    if not admin_password or typed_admin_password != admin_password:
        st.warning("Esta vista está protegida. Configura ADMIN_PASSWORD en los secretos de Streamlit y escribe la clave para continuar.")
        st.stop()

    diag = pd.DataFrame([
        ["Filas", len(df_raw)],
        ["Columnas", len(df_raw.columns)],
        ["Columna empresa", meta["company_col"]],
        ["Columna código", meta["access_col"] or "Código generado automáticamente"],
        ["Columna fecha", meta["date_col"] or "No detectada"],
        ["Columna puntaje", meta["score_col"] or "Cálculo automático"],
        ["Columna nivel", meta["level_col"] or "Cálculo automático"],
        ["Columna lectura", meta["reading_col"] or "Lectura automática"],
        ["Indicadores evaluables", len(meta["indicator_cols"])],
    ], columns=["Elemento", "Valor"])
    st.markdown(html_table(diag), unsafe_allow_html=True)

    st.markdown("#### Columnas detectadas como indicadores")
    st.markdown(html_table(pd.DataFrame({"Columna": meta["indicator_cols"]})), unsafe_allow_html=True)

    st.markdown("#### Códigos sugeridos para entrega")
    codes = df[["__empresa__", "__codigo_base__", "__codigo_dashboard__"]].copy()
    codes.columns = ["Empresa", "Código base detectado", "Código dashboard generado"]
    st.markdown(html_table(codes), unsafe_allow_html=True)
    st.download_button(
        "Descargar códigos sugeridos",
        data=codes.to_csv(index=False).encode("utf-8-sig"),
        file_name="codigos_empresas_turismo_violeta.csv",
        mime="text/csv",
        use_container_width=True,
    )
 
