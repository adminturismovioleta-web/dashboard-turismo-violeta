import hashlib
import re
from datetime import datetime
from urllib.parse import quote

import numpy as np
import pandas as pd
import streamlit as st

APP_VERSION = "v8 limpia funcional SIN HTML"
DEFAULT_GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1PSFsSwHAvXHCeoWO2DzBmZln67FxwE9SBuxb_ET5ufo/edit?usp=sharing"
DEFAULT_GOOGLE_SHEET_ID = "1PSFsSwHAvXHCeoWO2DzBmZln67FxwE9SBuxb_ET5ufo"
DEFAULT_SHEET_NAME = "Externos"

st.set_page_config(
    page_title="Turismo Violeta | Dashboard empresarial",
    page_icon="🟣",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PRINCIPLES = {
    1: {
        "code": "E.1.1",
        "title": "Promover la igualdad de género desde la dirección al más alto nivel",
        "objectives": [1, 2, 3],
        "focus": "Reforzar compromiso de alta dirección, gobernanza, Comité de Igualdad, políticas institucionales y seguimiento del plan.",
        "docs": "Principios WEPs; Acuerdo MDT-2025-102; documentos WEPs 1 al 8.",
    },
    2: {
        "code": "E.1.2",
        "title": "Trato equitativo, derechos humanos y no discriminación en el trabajo",
        "objectives": [1, 2, 5, 7],
        "focus": "Priorizar trato equitativo, no discriminación, igualdad en selección, promoción, formación, remuneración y condiciones laborales.",
        "docs": "Principios WEPs; Acuerdo MDT-2025-102; Protocolo Turismo Violeta; Tool Kit; documentos WEPs 1 al 10.",
    },
    3: {
        "code": "E.1.3",
        "title": "Salud, seguridad, bienestar y vida libre de violencia",
        "objectives": [4, 5, 7],
        "focus": "Fortalecer prevención de violencia y acoso, rutas de atención, confidencialidad, protección, derivación y bienestar laboral.",
        "docs": "Protocolo Turismo Violeta; Tool Kit; Acuerdo MDT-2025-102; Manual ESNNA; documentos WEPs 9 al 17.",
    },
    4: {
        "code": "E.1.4",
        "title": "Educación, formación y desarrollo profesional de mujeres y grupos subrepresentados",
        "objectives": [6, 7],
        "focus": "Consolidar educación, formación, desarrollo profesional y participación de mujeres y grupos subrepresentados.",
        "docs": "Principios WEPs; Tool Kit para capacitación y fortalecimiento de capacidades; documentos WEPs 18 al 21.",
    },
    5: {
        "code": "E.1.5",
        "title": "Desarrollo empresarial, cadena de suministro y marketing a favor del empoderamiento de las mujeres",
        "objectives": [8, 9],
        "focus": "Ajustar prácticas empresariales, marketing responsable, cadena de suministro, proveedores y compras con enfoque de igualdad.",
        "docs": "Principios WEPs; Tool Kit para marketing, proveedores y cadena de valor; documentos WEPs 22 al 24.",
    },
    6: {
        "code": "E.1.6",
        "title": "Igualdad mediante iniciativas comunitarias y participación territorial",
        "objectives": [10, 11],
        "focus": "Fortalecer iniciativas comunitarias, participación territorial, pagos transparentes, alianzas locales y saberes ancestrales.",
        "docs": "Principios WEPs; Plan Integral de Seguridad Turística; Protocolo Turismo Violeta; documentos WEPs 25 al 27.",
    },
    7: {
        "code": "E.1.7",
        "title": "Medición, reporte y mejora continua",
        "objectives": [11],
        "focus": "Definir indicadores, levantar evidencias, revisar avances y actualizar periódicamente el plan.",
        "docs": "Matriz de indicadores, reportes internos, evidencias de seguimiento y actualización anual del plan.",
    },
}

OBJECTIVES = {
    1: {"code": "E.2.1", "title": "Compromiso institucional y liderazgo de alta dirección", "principles": [1, 2], "indicators": [1, 2, 3], "reading": "Formalizar el compromiso de la dirección, comunicarlo internamente y convertirlo en responsabilidades concretas."},
    2: {"code": "E.2.2", "title": "Política interna de igualdad y no discriminación", "principles": [1, 2], "indicators": [4, 5, 6, 7], "reading": "Revisar políticas internas para asegurar criterios explícitos de igualdad, no discriminación y derechos humanos."},
    3: {"code": "E.2.3", "title": "Comité de Igualdad y gobernanza del plan", "principles": [1], "indicators": [8, 9, 20, 21, 22], "reading": "Formalizar el Comité de Igualdad, generar actas, capacitar integrantes y establecer seguimiento periódico."},
    4: {"code": "E.2.4", "title": "Prevención de violencia, acoso y discriminación", "principles": [3], "indicators": [10, 11, 12, 13, 14, 15, 16, 17], "reading": "Consolidar rutas de prevención, atención y derivación; reforzar confidencialidad, protección y cero represalias."},
    5: {"code": "E.2.5", "title": "Condiciones laborales, bienestar y vida libre de violencia", "principles": [2, 3], "indicators": [18, 19, 23, 24, 25, 26], "reading": "Alinear condiciones laborales, bienestar, seguridad y mecanismos de respuesta frente a riesgos psicosociales y violencia."},
    6: {"code": "E.2.6", "title": "Educación, formación y desarrollo profesional", "principles": [4], "indicators": [27, 28, 29, 30], "reading": "Planificar formación periódica, fortalecer capacidades y crear oportunidades de desarrollo profesional."},
    7: {"code": "E.2.7", "title": "Selección, promoción, remuneración y participación laboral", "principles": [2, 3, 4], "indicators": [31, 32, 33, 34, 35, 36], "reading": "Revisar procesos de selección, promoción y remuneración para reducir brechas y asegurar criterios transparentes."},
    8: {"code": "E.2.8", "title": "Cadena de suministro y compras con enfoque de igualdad", "principles": [5], "indicators": [35, 36, 37, 38], "reading": "Incorporar criterios de igualdad en compras, proveedores, contratación y relaciones con la cadena de valor."},
    9: {"code": "E.2.9", "title": "Marketing, comunicación y servicios turísticos responsables", "principles": [5], "indicators": [40, 41, 42], "reading": "Ajustar comunicación, marketing y servicios para evitar estereotipos y fortalecer el empoderamiento de las mujeres."},
    10: {"code": "E.2.10", "title": "Participación territorial e iniciativas comunitarias", "principles": [6], "indicators": [39, 43, 44, 45], "reading": "Fortalecer alianzas locales, participación comunitaria, pagos transparentes y articulación territorial."},
    11: {"code": "E.2.11", "title": "Seguimiento, indicadores, evidencias y mejora continua", "principles": [6, 7], "indicators": [46, 47, 48, 49, 50], "reading": "Definir indicadores, levantar evidencias, revisar avances periódicamente y actualizar el plan con base en resultados."},
}

SENSITIVE_WORDS = [
    "representante", "identidad", "cedula", "cédula", "ruc", "telefono", "teléfono", "correo", "email", "direccion", "dirección",
    "georeferenciacion", "geo-referenciacion", "georreferenciacion", "lat", "lon", "altitude", "precision", "audit", "uuid",
]


def get_secret(name, default=""):
    try:
        value = st.secrets.get(name, default)
        return default if value is None else value
    except Exception:
        return default


def normalize_text(value) -> str:
    value = "" if value is None else str(value)
    value = value.strip().lower()
    for a, b in {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}.items():
        value = value.replace(a, b)
    return re.sub(r"\s+", " ", value)


def clean_code(value) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    txt = str(value).strip()
    if re.fullmatch(r"\d+\.0", txt):
        return txt[:-2]
    return txt


def extract_sheet_id(url_or_id: str) -> str:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", str(url_or_id or ""))
    if match:
        return match.group(1)
    return str(url_or_id or DEFAULT_GOOGLE_SHEET_ID).strip()


def google_csv_url(sheet_url=None, sheet_id=None, sheet_name=DEFAULT_SHEET_NAME):
    sid = sheet_id or extract_sheet_id(sheet_url or DEFAULT_GOOGLE_SHEET_URL)
    return f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={quote(sheet_name)}"


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", str(c).strip()) for c in df.columns]
    df = df.drop(columns=[c for c in df.columns if str(c).startswith("Unnamed:") or df[c].isna().all()], errors="ignore")
    return df.dropna(how="all")


@st.cache_data(ttl=300, show_spinner=False)
def load_from_url(url: str) -> pd.DataFrame:
    if str(url).lower().endswith(".xlsx"):
        return clean_dataframe(pd.read_excel(url))
    return clean_dataframe(pd.read_csv(url))


def load_data() -> pd.DataFrame:
    direct_url = get_secret("KOBO_DATA_URL", "")
    sheet_url = get_secret("GOOGLE_SHEET_URL", DEFAULT_GOOGLE_SHEET_URL)
    sheet_id = get_secret("GOOGLE_SHEET_ID", extract_sheet_id(sheet_url))
    sheet_name = get_secret("GOOGLE_SHEET_NAME", DEFAULT_SHEET_NAME)
    source_url = direct_url or google_csv_url(sheet_url=sheet_url, sheet_id=sheet_id, sheet_name=sheet_name)
    try:
        return load_from_url(source_url)
    except Exception as exc:
        st.error("No fue posible leer la fuente de datos. Verifica que la hoja esté pública o que el enlace CSV esté disponible.")
        st.exception(exc)
        st.stop()


def find_col(df: pd.DataFrame, candidates=None, contains=None, secret_name=None):
    forced = get_secret(secret_name, "") if secret_name else ""
    if forced and forced in df.columns:
        return forced
    candidates = candidates or []
    contains = contains or []
    normalized = {normalize_text(c): c for c in df.columns}
    for candidate in candidates:
        if normalize_text(candidate) in normalized:
            return normalized[normalize_text(candidate)]
    for col in df.columns:
        n = normalize_text(col)
        if any(token in n for token in contains):
            return col
    return None


def find_company_col(df):
    return find_col(df, candidates=["1. Nombre legal de la organización", "Nombre legal de la organización", "Empresa", "organización", "organizacion"], contains=["nombre legal de la organizacion", "empresa", "organizacion"], secret_name="COMPANY_COLUMN")


def find_access_col(df):
    return find_col(df, candidates=["codigo_acceso", "código de acceso", "codigo", "_id", "id", "_uuid", "uuid", "meta/instanceID", "instanceID", "_submission__id"], contains=["codigo_acceso", "codigo de acceso", "_id", "uuid", "instanceid", "submission"], secret_name="ACCESS_CODE_COLUMN")


def find_date_col(df):
    return find_col(df, candidates=["_submission_time", "submission_time", "end", "fecha_envio", "Fecha de envío", "today", "start"], contains=["submission", "fecha de envio", "fecha_envio", "end", "today", "start", "fecha"], secret_name="DATE_COLUMN")


def find_total_people_col(df):
    return find_col(df, candidates=["total_area", "Total de personas en la organización"], contains=["total_area", "total de personas"])


def find_general_score_col(df):
    return find_col(df, candidates=["puntaje_general", "calificacion_general", "calificación general", "avance_general", "score_total", "total_score", "porcentaje_general"], contains=["puntaje general", "calificacion general", "calificación general", "avance general", "score total", "porcentaje general"], secret_name="GENERAL_SCORE_COLUMN")


def find_level_col(df):
    return find_col(df, candidates=["nivel_avance", "nivel de avance", "nivel_general"], contains=["nivel de avance", "nivel general"], secret_name="LEVEL_COLUMN")


def parse_date_series(series: pd.Series) -> pd.Series:
    raw = series.copy()
    parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    numeric = pd.to_numeric(raw, errors="coerce")
    excel_mask = parsed.isna() & numeric.between(20000, 70000)
    if excel_mask.any():
        parsed.loc[excel_mask] = pd.to_datetime(numeric.loc[excel_mask], unit="D", origin="1899-12-30", errors="coerce")
    return parsed


def format_date(value) -> str:
    if value is None or pd.isna(value):
        return "Sin fecha"
    try:
        return pd.to_datetime(value).strftime("%d/%m/%Y")
    except Exception:
        return "Sin fecha"


def parse_score(value, col_name=""):
    if value is None or pd.isna(value):
        return np.nan
    original = str(value).strip()
    text = normalize_text(original)
    if text in {"", "nan", "none", "no aplica", "n/a", "na", "no sabe", "no responde"}:
        return np.nan
    percent = re.search(r"(-?\d+(?:[\.,]\d+)?)\s*%", original)
    if percent:
        return float(percent.group(1).replace(",", "."))
    numeric_text = original.replace("%", "").strip()
    if re.search(r"\d+\.\d{3}", numeric_text) and "," in numeric_text:
        numeric_text = numeric_text.replace(".", "").replace(",", ".")
    elif "," in numeric_text and "." not in numeric_text:
        numeric_text = numeric_text.replace(",", ".")
    try:
        num = float(numeric_text)
        col_n = normalize_text(col_name)
        if any(token in col_n for token in ["0 a 5", "0-5", "weps-tv", "accion", "acción"]):
            if 0 <= num <= 5:
                return num / 5 * 100
        if "0 a 10" in col_n or "0-10" in col_n:
            if 0 <= num <= 10:
                return num / 10 * 100
        if 0 <= num <= 1:
            return num * 100
        if 0 <= num <= 100:
            return num
        return np.nan
    except Exception:
        pass
    if any(p in text for p in ["parcial", "en proceso", "medio", "algunas", "algunos", "a veces", "limitado", "en construccion", "en construcción"]):
        return 50
    if text in {"true", "verdadero", "si", "sí", "cumple", "implementado", "alto", "existe", "formalizado", "aprobado"}:
        return 100
    if text in {"false", "falso", "no", "bajo", "no cumple", "no existe", "pendiente", "inicial", "ninguno", "ninguna"}:
        return 0
    return np.nan


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


def format_score(score):
    if pd.isna(score):
        return "Sin cálculo"
    return f"{float(score):.1f}%"


def progress_value(score):
    if pd.isna(score):
        return 0.0
    return max(0.0, min(1.0, float(score) / 100.0))


def extract_principle_id(col: str):
    n = normalize_text(col)
    for pattern in [r"principio\s*weps?\s*(\d{1,2})", r"resultado\s+del\s+principio\s+weps?\s*(\d{1,2})", r"calculo\s+interno\s*:?\s*weps?\s*0?(\d{1,2})", r"cálculo\s+interno\s*:?\s*weps?\s*0?(\d{1,2})"]:
        match = re.search(pattern, n)
        if match:
            pid = int(match.group(1))
            if 1 <= pid <= 7:
                return pid
    return None


def extract_objective_id(col: str):
    n = normalize_text(col)
    match = re.search(r"objetivo\s*0?(\d{1,2})", n)
    if match:
        oid = int(match.group(1))
        if oid in OBJECTIVES:
            return oid
    return None


def extract_indicator_numbers(col: str):
    n = normalize_text(col)
    nums = []
    for pattern in [r"indicador(?:es)?\s*0?(\d{1,2})", r"weps-tv\s*0?(\d{1,2})", r"accion\s*weps-tv\s*0?(\d{1,2})", r"acción\s*weps-tv\s*0?(\d{1,2})"]:
        nums.extend([int(x) for x in re.findall(pattern, n)])
    return nums


def identify_score_columns(df: pd.DataFrame):
    forced = get_secret("SCORE_COLUMNS", "")
    if forced:
        forced_cols = [c.strip() for c in str(forced).split(",") if c.strip() in df.columns]
        if forced_cols:
            return forced_cols
    cols = []
    for col in df.columns:
        n = normalize_text(col)
        if any(word in n for word in SENSITIVE_WORDS):
            continue
        if any(word in n for word in ["nombre legal", "red social", "nacionalidad", "edad", "discapacidad", "numero de", "número de", "total_area", "total de personas"]):
            continue
        score_like = bool(extract_principle_id(col) or extract_objective_id(col) or extract_indicator_numbers(col) or "avance calculado" in n or "puntaje" in n or "score" in n or "0 a 5" in n or "0-5" in n)
        if score_like:
            sample = df[col].head(100).map(lambda x: parse_score(x, col))
            if sample.notna().any():
                cols.append(col)
    return cols


def generate_access_code(row: pd.Series, company_col: str, date_col: str = None):
    company = clean_code(row.get(company_col, "empresa"))
    date_value = clean_code(row.get(date_col, "")) if date_col else ""
    raw = f"{company}|{date_value}|turismo-violeta"
    return "TV-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8].upper()


def principle_scores(row: pd.Series, score_cols):
    records = []
    for pid, meta in PRINCIPLES.items():
        values = []
        sources = []
        for col in score_cols:
            if extract_principle_id(col) == pid:
                val = parse_score(row.get(col), col)
                if pd.notna(val):
                    values.append(val)
                    sources.append(col)
        if not values:
            indicator_targets = set()
            for oid in meta["objectives"]:
                indicator_targets.update(OBJECTIVES[oid]["indicators"])
            for col in score_cols:
                if set(extract_indicator_numbers(col)) & indicator_targets:
                    val = parse_score(row.get(col), col)
                    if pd.notna(val):
                        values.append(val)
                        sources.append(col)
        score = float(np.mean(values)) if values else np.nan
        records.append({"pid": pid, "Código": meta["code"], "Principio": f"Principio WEPs {pid}", "Título": meta["title"], "Puntaje": round(score, 1) if pd.notna(score) else np.nan, "Nivel": level_from_score(score), "Fuentes": sources})
    return pd.DataFrame(records)


def objective_scores(row: pd.Series, score_cols, p_df: pd.DataFrame):
    records = []
    for oid, obj in OBJECTIVES.items():
        values = []
        sources = []
        for col in score_cols:
            if extract_objective_id(col) == oid:
                val = parse_score(row.get(col), col)
                if pd.notna(val):
                    values.append(val)
                    sources.append(col)
        if not values:
            targets = set(obj["indicators"])
            for col in score_cols:
                if set(extract_indicator_numbers(col)) & targets:
                    val = parse_score(row.get(col), col)
                    if pd.notna(val):
                        values.append(val)
                        sources.append(col)
        if not values and p_df is not None and not p_df.empty:
            linked = p_df[p_df["pid"].isin(obj["principles"])]
            values = linked["Puntaje"].dropna().tolist()
        score = float(np.mean(values)) if values else np.nan
        records.append({"oid": oid, "Código": obj["code"], "Objetivo": f"Objetivo {oid}: {obj['title']}", "Principios vinculados": ", ".join([f"WEPs {p}" for p in obj["principles"]]), "Indicadores": ", ".join(map(str, obj["indicators"])), "Puntaje": round(score, 1) if pd.notna(score) else np.nan, "Nivel": level_from_score(score), "Lectura para plan": obj["reading"], "Fuentes": sources})
    return pd.DataFrame(records)


def build_indicator_table(row: pd.Series, score_cols, max_rows=35):
    records = []
    for col in score_cols:
        val = parse_score(row.get(col), col)
        if pd.isna(val):
            continue
        nums = extract_indicator_numbers(col)
        records.append({"Indicador / documento": col, "Indicadores vinculados": ", ".join(map(str, nums)) if nums else "", "Puntaje": round(float(val), 1), "Estado": "Cumplido" if val >= 80 else ("Parcial" if val >= 50 else "Pendiente"), "Prioridad": "Alta" if val < 50 else ("Media" if val < 80 else "Baja"), "Acción sugerida": "Generar evidencia mínima y responsable" if val < 50 else ("Completar documentación y seguimiento" if val < 80 else "Mantener evidencia y reporte")})
    out = pd.DataFrame(records)
    if out.empty:
        return out
    order = {"Alta": 0, "Media": 1, "Baja": 2}
    out["_orden"] = out["Prioridad"].map(order)
    return out.sort_values(["_orden", "Puntaje", "Indicador / documento"]).drop(columns="_orden").head(max_rows)


def prepare_data(df_raw: pd.DataFrame):
    company_col = find_company_col(df_raw)
    access_col = find_access_col(df_raw)
    date_col = find_date_col(df_raw)
    total_people_col = find_total_people_col(df_raw)
    general_score_col = find_general_score_col(df_raw)
    level_col = find_level_col(df_raw)
    score_cols = identify_score_columns(df_raw)
    if not company_col:
        st.error("No encontré la columna de empresa. Configura COMPANY_COLUMN en Secrets con el nombre exacto de la columna.")
        st.stop()
    df = df_raw.copy()
    df["__empresa__"] = df[company_col].astype(str).str.strip()
    df = df[df["__empresa__"].str.len() > 0].copy()
    df["__fecha__"] = parse_date_series(df[date_col]) if date_col else pd.NaT
    if general_score_col:
        df["__score__"] = df[general_score_col].map(lambda x: parse_score(x, general_score_col))
        score_source = general_score_col
    else:
        rows = []
        for _, row in df.iterrows():
            p_df = principle_scores(row, score_cols)
            p_values = p_df["Puntaje"].dropna().tolist()
            rows.append(float(np.mean(p_values)) if p_values else np.nan)
        df["__score__"] = rows
        score_source = "promedio de principios WEPs detectados"
    if level_col:
        df["__nivel__"] = df[level_col].fillna("").astype(str).replace("", np.nan).fillna(df["__score__"].map(level_from_score))
    else:
        df["__nivel__"] = df["__score__"].map(level_from_score)
    if access_col:
        df["__codigo_base__"] = df[access_col].map(clean_code)
    else:
        df["__codigo_base__"] = ""
    df["__codigo_dashboard__"] = df.apply(lambda r: generate_access_code(r, company_col, date_col), axis=1)
    meta = {"company_col": company_col, "access_col": access_col, "date_col": date_col, "total_people_col": total_people_col, "general_score_col": general_score_col, "level_col": level_col, "score_cols": score_cols, "score_source": score_source}
    return df, meta


def validate_access(row: pd.Series, code: str):
    code_clean = clean_code(code)
    if not code_clean:
        return False
    valid_codes = {clean_code(row.get("__codigo_base__", "")), clean_code(row.get("__codigo_dashboard__", ""))}
    return code_clean in valid_codes


def general_reading(score, p_df, o_df):
    if pd.isna(score):
        opening = "No hay suficiente información para calcular una calificación general. Revise columnas de principios, objetivos e indicadores."
    elif score >= 80:
        opening = "La empresa presenta un nivel avanzado. El plan debe concentrarse en sostener evidencias, medir resultados y documentar buenas prácticas."
    elif score >= 60:
        opening = "La empresa muestra una base sólida, pero todavía debe convertir avances en procedimientos, responsables y evidencias periódicas."
    elif score >= 40:
        opening = "La empresa se encuentra en construcción. El plan debe priorizar formalización, capacitación, protocolos y seguimiento."
    elif score >= 20:
        opening = "La empresa está en fase inicial. El plan debe partir de compromisos básicos, responsables, protocolos, capacitación y evidencias mínimas."
    else:
        opening = "La empresa presenta brechas críticas. El plan debe iniciar con acciones fundacionales de corto plazo antes de avanzar hacia procesos complejos de medición."
    parts = [opening]
    if p_df is not None and not p_df.empty:
        low_p = p_df.dropna(subset=["Puntaje"]).sort_values("Puntaje").head(2)
        if not low_p.empty:
            parts.append("Principios prioritarios: " + "; ".join([f"{r['Principio']} ({format_score(r['Puntaje'])})" for _, r in low_p.iterrows()]) + ".")
    if o_df is not None and not o_df.empty:
        low_o = o_df.dropna(subset=["Puntaje"]).sort_values("Puntaje").head(3)
        if not low_o.empty:
            parts.append("Objetivos iniciales del plan: " + "; ".join([f"{r['Código']} {r['Objetivo'].split(': ', 1)[-1]}" for _, r in low_o.iterrows()]) + ".")
    return " ".join(parts)


def recommended_actions(score, o_df):
    rows = []
    if pd.isna(score) or score < 40:
        rows.extend([["Alta", "Formalizar compromiso interno de igualdad, prevención de violencia y no acoso.", "30 días"], ["Alta", "Designar Comité o responsable del plan con funciones, actas y calendario de seguimiento.", "30 días"], ["Alta", "Definir ruta mínima de actuación ante acoso, discriminación o violencia.", "45 días"]])
    elif score < 70:
        rows.extend([["Alta", "Convertir brechas en actividades, responsables, plazos e indicadores.", "30 días"], ["Media", "Planificar capacitación periódica para directivos y equipos operativos.", "60 días"], ["Media", "Consolidar evidencias documentales de cumplimiento y seguimiento.", "90 días"]])
    else:
        rows.extend([["Media", "Fortalecer medición periódica y revisión anual del plan.", "60 días"], ["Media", "Documentar buenas prácticas para replicarlas en áreas con menor avance.", "90 días"], ["Baja", "Preparar reporte de resultados y actualización de indicadores.", "12 meses"]])
    if o_df is not None and not o_df.empty:
        for _, row in o_df.dropna(subset=["Puntaje"]).sort_values("Puntaje").head(2).iterrows():
            if row["Puntaje"] < 60:
                rows.append(["Alta", f"Priorizar {row['Código']} - {row['Objetivo'].split(': ', 1)[-1]}", "60 días"])
    return pd.DataFrame(rows, columns=["Prioridad", "Acción sugerida", "Plazo"])


def public_table(df: pd.DataFrame):
    out = df[["__empresa__", "__fecha__", "__nivel__", "__score__"]].copy()
    out.columns = ["Empresa", "Fecha", "Nivel", "Puntaje"]
    out["Fecha"] = out["Fecha"].map(format_date)
    out["Puntaje"] = out["Puntaje"].map(format_score)
    return out


# ============================
# APP PRINCIPAL - SIN HTML
# ============================
st.title("Dashboard empresarial | Turismo Violeta")
st.caption(f"Versión: {APP_VERSION}")
st.write("Consulta pública agregada y acceso individual por empresa mediante código. La lectura se organiza por principios WEPs, objetivos, indicadores y acciones sugeridas para el plan.")

raw = load_data()
df, meta = prepare_data(raw)

tab_empresa, tab_publico, tab_diag = st.tabs(["Consulta por empresa", "Resumen público", "Diagnóstico técnico"])

with tab_empresa:
    st.header("Acceso a resultados de empresa")
    companies = sorted(df["__empresa__"].dropna().astype(str).unique().tolist())
    col_a, col_b = st.columns([1.2, 1])
    with col_a:
        company = st.selectbox("Nombre de empresa", companies, index=0 if companies else None)
    with col_b:
        code = st.text_input("Código de acceso", type="password", placeholder="Ingrese el _id o código TV")

    if not code:
        st.info("Ingrese el código de acceso para visualizar la calificación, principios, objetivos, indicadores y acciones sugeridas.")
    else:
        candidates = df[df["__empresa__"].astype(str) == str(company)].copy()
        valid_rows = [row for _, row in candidates.iterrows() if validate_access(row, code)]
        if not valid_rows:
            st.error("El código no coincide con la empresa seleccionada. Revise el nombre de empresa y el código recibido.")
        else:
            selected = pd.DataFrame(valid_rows).sort_values("__fecha__", ascending=False).iloc[0]
            score = selected.get("__score__", np.nan)
            level = selected.get("__nivel__", level_from_score(score))
            p_df = principle_scores(selected, meta["score_cols"])
            o_df = objective_scores(selected, meta["score_cols"], p_df)
            i_df = build_indicator_table(selected, meta["score_cols"])
            total_people = selected.get(meta["total_people_col"], "Sin dato") if meta["total_people_col"] else "Sin dato"

            st.success("Registro validado")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Empresa", selected["__empresa__"])
            m2.metric("Puntaje general", format_score(score))
            m3.metric("Nivel de avance", level)
            m4.metric("Fecha de envío", format_date(selected.get("__fecha__")))

            m5, m6, m7, m8 = st.columns(4)
            m5.metric("Principios evaluados", f"{int(p_df['Puntaje'].notna().sum())}/7")
            m6.metric("Objetivos revisados", f"{int(o_df['Puntaje'].notna().sum())}/{len(OBJECTIVES)}")
            m7.metric("Indicadores priorizados", str(len(i_df)))
            m8.metric("Personas en organización", clean_code(total_people) or "Sin dato")

            st.header("Lectura general para plan")
            st.progress(progress_value(score), text=f"{format_score(score)} · {level}")
            st.info(general_reading(score, p_df, o_df))

            st.header("Avance por principios WEPs")
            chart_df = p_df[["Principio", "Puntaje"]].dropna().set_index("Principio")
            if not chart_df.empty:
                st.bar_chart(chart_df)
            else:
                st.warning("No se detectaron puntajes por principio. Revise las columnas evaluables en Diagnóstico técnico.")

            st.header("Principios, objetivos e indicadores para el plan")
            for _, prow in p_df.iterrows():
                meta_p = PRINCIPLES[int(prow["pid"])]
                with st.expander(f"» » {prow['Código']}. {prow['Principio']}: {prow['Título']}", expanded=True):
                    a, b, c = st.columns([1, 1, 2])
                    a.metric("Avance calculado", format_score(prow["Puntaje"]))
                    b.metric("Nivel", prow["Nivel"])
                    c.write("Documentos de apoyo:")
                    c.write(meta_p["docs"])
                    st.write("Lectura para plan:")
                    st.write(meta_p["focus"])

                    obj_rows = o_df[o_df["oid"].isin(meta_p["objectives"])]
                    for _, obj in obj_rows.iterrows():
                        with st.container(border=True):
                            st.subheader(f"» » {obj['Código']}. {obj['Objetivo']}")
                            st.write(f"Principios WEPs/TV vinculados: {obj['Principios vinculados']}")
                            st.write(f"Avance calculado: {format_score(obj['Puntaje'])}")
                            st.write(f"Nivel: {obj['Nivel']}")
                            st.write("Lectura para plan:")
                            st.write(obj["Lectura para plan"])
                            st.caption(f"Indicadores que sustentan este objetivo: {obj['Indicadores']}")

            st.header("Indicadores priorizados")
            if i_df.empty:
                st.info("No se detectaron indicadores/documentos con puntaje suficiente para priorizar.")
            else:
                st.dataframe(i_df, use_container_width=True, hide_index=True)

            st.header("Acciones sugeridas para el plan")
            st.dataframe(recommended_actions(score, o_df), use_container_width=True, hide_index=True)

with tab_publico:
    st.header("Resumen público agregado")
    total_records = len(df)
    total_companies = df["__empresa__"].nunique()
    avg_score = df["__score__"].mean()
    last_date = df["__fecha__"].max()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Encuestas", f"{total_records:,}".replace(",", "."))
    c2.metric("Empresas", f"{total_companies:,}".replace(",", "."))
    c3.metric("Promedio general", format_score(avg_score))
    c4.metric("Última actualización", format_date(last_date))

    st.header("Distribución por nivel")
    levels = df["__nivel__"].fillna("Sin cálculo").value_counts().rename_axis("Nivel").reset_index(name="Encuestas")
    st.bar_chart(levels.set_index("Nivel"))

    st.header("Empresas registradas")
    st.dataframe(public_table(df), use_container_width=True, hide_index=True)

with tab_diag:
    st.header("Diagnóstico técnico")
    admin_password = get_secret("ADMIN_PASSWORD", "")
    typed_password = st.text_input("Clave de administrador", type="password")
    if not admin_password or typed_password != admin_password:
        st.warning("Ingrese la clave de administrador para ver columnas y códigos.")
    else:
        st.success(f"App ejecutando: {APP_VERSION}")
        st.write("Filas:", len(raw))
        st.write("Columnas:", len(raw.columns))
        st.write("Columna empresa:", meta["company_col"])
        st.write("Columna código:", meta["access_col"] or "código generado")
        st.write("Columna fecha:", meta["date_col"] or "no detectada")
        st.write("Fuente puntaje:", meta["score_source"])
        st.write("Columnas evaluables detectadas:", len(meta["score_cols"]))

        with st.expander("Columnas evaluables detectadas"):
            st.dataframe(pd.DataFrame({"Columnas": meta["score_cols"]}), use_container_width=True, hide_index=True)

        codes = df[["__empresa__", "__fecha__", "__codigo_base__", "__codigo_dashboard__"]].copy()
        codes.columns = ["Empresa", "Fecha", "Código base", "Código sugerido"]
        codes["Fecha"] = codes["Fecha"].map(format_date)
        st.dataframe(codes, use_container_width=True, hide_index=True)
        st.download_button("Descargar códigos", codes.to_csv(index=False).encode("utf-8-sig"), "codigos_acceso_turismo_violeta.csv", "text/csv")
