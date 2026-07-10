import re
import unicodedata
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

APP_VERSION = "v11 reconstruida limpia sin HTML"

DEFAULT_DATA_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1PSFsSwHAvXHCeoWO2DzBmZln67FxwE9SBuxb_ET5ufo/"
    "gviz/tq?tqx=out:csv&sheet=Externos"
)
DEFAULT_COMPANY_COLUMN = "1. Nombre legal de la organización"

PRINCIPLES = [
    {
        "id": 1,
        "title": "Principio WEPs 1: Promover la igualdad de género desde la dirección al más alto nivel",
        "objectives": [1, 2, 3],
        "keywords": ["direccion", "liderazgo", "gobernanza", "comite", "politica", "compromiso"],
        "documents": "Principios WEPs; Acuerdo MDT-2025-102; documentos WEPs 1 al 8.",
        "reading": "Reforzar el compromiso de alta dirección, gobernanza, Comité de Igualdad, políticas institucionales y seguimiento del plan.",
    },
    {
        "id": 2,
        "title": "Principio WEPs 2: Trato equitativo, derechos humanos y no discriminación en el trabajo",
        "objectives": [1, 2, 5, 7],
        "keywords": ["trato", "derechos", "discriminacion", "seleccion", "remuneracion", "condiciones", "equidad"],
        "documents": "Principios WEPs; Acuerdo MDT-2025-102; Protocolo Turismo Violeta y Tool Kit.",
        "reading": "Priorizar trato equitativo, no discriminación, igualdad en selección, promoción, formación, remuneración y condiciones laborales.",
    },
    {
        "id": 3,
        "title": "Principio WEPs 3: Salud, seguridad, bienestar y vida libre de violencia",
        "objectives": [4, 5, 7],
        "keywords": ["salud", "seguridad", "bienestar", "violencia", "acoso", "protocolo", "proteccion", "ruta"],
        "documents": "Protocolo Turismo Violeta; Tool Kit; Acuerdo MDT-2025-102; Manual ESNNA.",
        "reading": "Fortalecer prevención de violencia y acoso, rutas de atención, derivación, protección y condiciones de bienestar.",
    },
    {
        "id": 4,
        "title": "Principio WEPs 4: Educación, formación y desarrollo profesional de mujeres y grupos subrepresentados",
        "objectives": [6, 7],
        "keywords": ["educacion", "formacion", "capacitacion", "desarrollo", "profesional", "participacion"],
        "documents": "Principios WEPs; Tool Kit para capacitación y fortalecimiento de capacidades.",
        "reading": "Consolidar formación, desarrollo profesional y participación de mujeres y grupos subrepresentados.",
    },
    {
        "id": 5,
        "title": "Principio WEPs 5: Desarrollo empresarial, cadena de suministro y marketing a favor del empoderamiento de las mujeres",
        "objectives": [8, 9],
        "keywords": ["cadena", "suministro", "marketing", "proveedor", "compras", "empoderamiento", "responsable"],
        "documents": "Principios WEPs y Tool Kit para marketing responsable, proveedores y cadena de valor.",
        "reading": "Ajustar prácticas empresariales, marketing responsable, cadena de suministro, proveedores y compras con enfoque de igualdad.",
    },
    {
        "id": 6,
        "title": "Principio WEPs 6: Igualdad mediante iniciativas comunitarias y participación territorial",
        "objectives": [10, 11],
        "keywords": ["comunitaria", "territorial", "comunidad", "pago", "transparente", "alianza", "local"],
        "documents": "Principios WEPs; Plan Integral de Seguridad Turística y Protocolo Turismo Violeta.",
        "reading": "Fortalecer iniciativas comunitarias, participación territorial, pagos transparentes, alianzas locales y saberes ancestrales.",
    },
    {
        "id": 7,
        "title": "Principio WEPs 7: Medición, reporte y transparencia",
        "objectives": [12, 13],
        "keywords": ["medicion", "reporte", "transparencia", "indicador", "seguimiento", "rendicion", "datos"],
        "documents": "Principios WEPs; lineamientos de reporte, seguimiento y mejora continua.",
        "reading": "Fortalecer indicadores, seguimiento periódico, reporte interno y rendición de cuentas sobre avances del plan.",
    },
]

OBJECTIVES = {
    1: {
        "title": "Objetivo 1: Compromiso institucional y liderazgo de alta dirección",
        "principles": "WEPs 1, WEPs 2",
        "indicators": "1, 2, 3",
        "keywords": ["compromiso", "direccion", "liderazgo", "gobernanza"],
        "reading": "Formalizar el compromiso de la dirección, comunicarlo internamente y convertirlo en responsabilidades concretas.",
    },
    2: {
        "title": "Objetivo 2: Política interna de igualdad y no discriminación",
        "principles": "WEPs 1, WEPs 2",
        "indicators": "4, 5, 6, 7",
        "keywords": ["politica", "igualdad", "discriminacion", "derechos"],
        "reading": "Revisar políticas internas para asegurar criterios explícitos de igualdad, no discriminación y derechos humanos.",
    },
    3: {
        "title": "Objetivo 3: Comité de Igualdad y gobernanza del plan",
        "principles": "WEPs 1",
        "indicators": "8, 9, 20, 21, 22",
        "keywords": ["comite", "gobernanza", "actas", "seguimiento"],
        "reading": "Formalizar el Comité de Igualdad, generar actas, capacitar integrantes y establecer seguimiento periódico.",
    },
    4: {
        "title": "Objetivo 4: Prevención y atención frente a violencia, acoso y discriminación",
        "principles": "WEPs 3",
        "indicators": "10, 11, 12, 13, 14",
        "keywords": ["violencia", "acoso", "prevencion", "atencion", "protocolo", "ruta"],
        "reading": "Definir rutas de actuación, responsables, canales de denuncia y medidas de protección frente a violencia y acoso.",
    },
    5: {
        "title": "Objetivo 5: Condiciones laborales equitativas, seguras y dignas",
        "principles": "WEPs 2, WEPs 3",
        "indicators": "15, 16, 17, 18, 19",
        "keywords": ["laboral", "condiciones", "segura", "digna", "equidad"],
        "reading": "Asegurar condiciones laborales equitativas, seguras y dignas, con mecanismos de seguimiento y mejora.",
    },
    6: {
        "title": "Objetivo 6: Formación, educación y desarrollo profesional",
        "principles": "WEPs 4",
        "indicators": "23, 24, 25, 26, 27, 28",
        "keywords": ["formacion", "educacion", "capacitacion", "desarrollo", "profesional"],
        "reading": "Diseñar rutas de formación y desarrollo profesional para mujeres y grupos subrepresentados.",
    },
    7: {
        "title": "Objetivo 7: Participación, corresponsabilidad y bienestar organizacional",
        "principles": "WEPs 2, WEPs 3, WEPs 4",
        "indicators": "29, 30, 31, 32, 33, 34",
        "keywords": ["participacion", "corresponsabilidad", "bienestar", "conciliacion"],
        "reading": "Promover participación, corresponsabilidad, bienestar y mecanismos de conciliación dentro de la organización.",
    },
    8: {
        "title": "Objetivo 8: Cadena de suministro y compras con enfoque de igualdad",
        "principles": "WEPs 5",
        "indicators": "35, 36, 37, 38",
        "keywords": ["cadena", "suministro", "compras", "proveedor"],
        "reading": "Incorporar criterios de igualdad en selección de proveedores, compras y relaciones de cadena de valor.",
    },
    9: {
        "title": "Objetivo 9: Marketing, comunicación y promoción responsable",
        "principles": "WEPs 5",
        "indicators": "39, 40, 41, 42",
        "keywords": ["marketing", "comunicacion", "promocion", "responsable"],
        "reading": "Revisar mensajes, piezas y campañas para evitar estereotipos y promover comunicación responsable.",
    },
    10: {
        "title": "Objetivo 10: Iniciativas comunitarias y participación territorial",
        "principles": "WEPs 6",
        "indicators": "43, 44, 45",
        "keywords": ["comunitaria", "territorial", "comunidad", "alianza"],
        "reading": "Vincular el plan con iniciativas comunitarias, participación territorial y alianzas locales.",
    },
    11: {
        "title": "Objetivo 11: Pagos transparentes, cultura local y saberes ancestrales",
        "principles": "WEPs 6",
        "indicators": "46, 47, 48",
        "keywords": ["pagos", "transparente", "cultura", "ancestral", "local"],
        "reading": "Asegurar pagos transparentes, reconocimiento cultural y respeto a saberes locales y ancestrales.",
    },
    12: {
        "title": "Objetivo 12: Medición, indicadores y seguimiento del plan",
        "principles": "WEPs 7",
        "indicators": "49, 50, 51",
        "keywords": ["medicion", "indicador", "seguimiento", "monitoreo"],
        "reading": "Definir indicadores de seguimiento, responsables, periodicidad y medios de verificación.",
    },
    13: {
        "title": "Objetivo 13: Reporte, transparencia y mejora continua",
        "principles": "WEPs 7",
        "indicators": "52, 53, 54",
        "keywords": ["reporte", "transparencia", "rendicion", "mejora"],
        "reading": "Establecer mecanismos de reporte, transparencia, rendición de cuentas y mejora continua.",
    },
}

SENSITIVE_TERMS = [
    "cedula", "cédula", "identidad", "telefono", "teléfono", "correo", "email",
    "ruc", "representante", "direccion", "dirección", "ip", "dispositivo",
]

NEGATIVE_TERMS = [
    "no cuenta", "no tiene", "no dispone", "no existe", "no aplica", "ninguno", "ninguna",
    "nunca", "sin evidencia", "sin documento", "inexistente", "pendiente", "no implementado",
]
MID_LOW_TERMS = [
    "en diseño", "borrador", "inicial", "informal", "parcial", "en proceso", "proceso",
    "en construccion", "en construcción", "ocasional", "algunas veces",
]
MID_HIGH_TERMS = [
    "aprobado", "definido", "documentado", "formalizado", "capacitado", "socializado",
    "difundido", "implementado parcialmente", "seguimiento", "monitoreo",
]
HIGH_TERMS = [
    "implementado", "evaluado", "medido", "revisado", "mejora continua", "rendición",
    "rendicion", "auditoria", "auditoría", "sistematizado", "evidencia", "cumplimiento",
]


def norm(text: Any) -> str:
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    value = str(text).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\s+", " ", value)
    return value


def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
        if value is None:
            return default
        return str(value)
    except Exception:
        return default


def first_existing_column(df: pd.DataFrame, preferred: Sequence[str], fuzzy_terms: Sequence[str] = ()) -> Optional[str]:
    if df.empty:
        return None
    col_norm_map = {norm(c): c for c in df.columns}
    for col in preferred:
        if not col:
            continue
        if col in df.columns:
            return col
        ncol = norm(col)
        if ncol in col_norm_map:
            return col_norm_map[ncol]
    for col in df.columns:
        ncol = norm(col)
        if all(term in ncol for term in fuzzy_terms):
            return col
    return None


def find_company_column(df: pd.DataFrame) -> Optional[str]:
    configured = get_secret("COMPANY_COLUMN", DEFAULT_COMPANY_COLUMN)
    return first_existing_column(
        df,
        [configured, DEFAULT_COMPANY_COLUMN, "Nombre legal de la organización", "nombre_empresa", "empresa", "organización"],
        ["nombre", "organizacion"],
    ) or first_existing_column(df, [], ["empresa"])


def find_code_columns(df: pd.DataFrame) -> List[str]:
    configured = get_secret("ACCESS_CODE_COLUMN", "")
    candidates: List[str] = []
    for col in [configured]:
        resolved = first_existing_column(df, [col])
        if resolved and resolved not in candidates:
            candidates.append(resolved)
    for col in df.columns:
        ncol = norm(col)
        if ("codigo" in ncol and "acceso" in ncol) or ("código" in str(col).lower() and "acceso" in str(col).lower()):
            if col not in candidates:
                candidates.append(col)
    for col in df.columns:
        ncol = norm(col)
        if "codigo" in ncol and col not in candidates:
            candidates.append(col)
    for fallback in ["codigo_acceso", "Código de acceso", "_id", "_uuid", "meta/instanceID"]:
        resolved = first_existing_column(df, [fallback])
        if resolved and resolved not in candidates:
            candidates.append(resolved)
    return candidates


def find_date_column(df: pd.DataFrame) -> Optional[str]:
    return first_existing_column(
        df,
        ["_submission_time", "SubmissionDate", "start", "end", "Fecha de envío", "fecha_envio", "fecha"],
    ) or first_existing_column(df, [], ["submission"])


def excel_serial_to_datetime(value: Any) -> Optional[pd.Timestamp]:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float, np.number)) and 20000 < float(value) < 80000:
            return pd.to_datetime("1899-12-30") + pd.to_timedelta(float(value), unit="D")
        s = str(value).strip()
        if re.fullmatch(r"\d+(\.\d+)?", s) and 20000 < float(s) < 80000:
            return pd.to_datetime("1899-12-30") + pd.to_timedelta(float(s), unit="D")
        parsed = pd.to_datetime(s, errors="coerce", dayfirst=False)
        if pd.notna(parsed):
            return parsed
    except Exception:
        return None
    return None


def format_date(value: Any) -> str:
    parsed = excel_serial_to_datetime(value)
    if parsed is None or pd.isna(parsed):
        return "Sin fecha"
    return parsed.strftime("%d/%m/%Y")


def load_data() -> pd.DataFrame:
    url = get_secret("KOBO_DATA_URL", DEFAULT_DATA_URL) or DEFAULT_DATA_URL
    uploaded = st.sidebar.file_uploader("Cargar Excel o CSV alternativo", type=["xlsx", "xls", "csv"])
    if uploaded is not None:
        name = uploaded.name.lower()
        if name.endswith(".csv"):
            return pd.read_csv(uploaded)
        return pd.read_excel(uploaded)
    try:
        if url.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(url)
        return pd.read_csv(url)
    except Exception as exc:
        st.error("No se pudo cargar la fuente de datos. Revise que la hoja esté publicada o que la URL de datos sea correcta.")
        st.caption(str(exc))
        return pd.DataFrame()


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")
    df = df.loc[:, ~pd.Series(df.columns).duplicated().values]
    return df


def value_to_score(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (int, float, np.number)):
        v = float(value)
        if 0 <= v <= 5:
            return v * 20
        if 0 <= v <= 100:
            return v
        return None
    text = str(value).strip()
    if not text:
        return None
    ntext = norm(text)
    numeric = re.findall(r"[-+]?\d+[\.,]?\d*", ntext)
    if numeric:
        try:
            val = float(numeric[0].replace(",", "."))
            if "0 a 5" in ntext or "0-5" in ntext or val <= 5:
                if 0 <= val <= 5:
                    return val * 20
            if 0 <= val <= 100:
                return val
        except Exception:
            pass
    if any(term in ntext for term in HIGH_TERMS):
        return 85.0
    if any(term in ntext for term in MID_HIGH_TERMS):
        return 65.0
    if any(term in ntext for term in MID_LOW_TERMS):
        return 35.0
    if any(term in ntext for term in NEGATIVE_TERMS):
        return 0.0
    if ntext in ["si", "sí", "yes", "true", "verdadero"]:
        return 80.0
    if ntext in ["no", "false", "falso"]:
        return 0.0
    return None


def is_sensitive_col(col: str) -> bool:
    ncol = norm(col)
    return any(term in ncol for term in [norm(t) for t in SENSITIVE_TERMS])


def is_likely_scoring_col(col: str, sample_values: Iterable[Any]) -> bool:
    ncol = norm(col)
    if is_sensitive_col(col):
        return False
    positive_column_terms = [
        "weps", "wep", "indicador", "objetivo", "principio", "calculo", "cálculo",
        "avance", "accion", "acción", "documento", "politica", "comite", "protocolo",
        "capacitacion", "formacion", "violencia", "acoso", "seguimiento", "reporte",
    ]
    if any(term in ncol for term in [norm(t) for t in positive_column_terms]):
        return True
    scores = [value_to_score(v) for v in sample_values]
    scores = [s for s in scores if s is not None]
    return len(scores) >= 1


def scoring_columns_for_row(row: pd.Series, df_columns: Sequence[str]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for col in df_columns:
        if is_likely_scoring_col(col, [row.get(col)]):
            score = value_to_score(row.get(col))
            if score is not None:
                scores[col] = max(0.0, min(100.0, float(score)))
    return scores


def scores_by_keywords(scores: Dict[str, float], keywords: Sequence[str]) -> List[float]:
    selected: List[float] = []
    key_norms = [norm(k) for k in keywords]
    for col, score in scores.items():
        ncol = norm(col)
        nval = norm(score)
        if any(k in ncol for k in key_norms):
            selected.append(score)
    return selected


def mean_or_fallback(values: Sequence[float], fallback: Optional[float]) -> Optional[float]:
    clean = [v for v in values if v is not None and not np.isnan(v)]
    if clean:
        return float(np.mean(clean))
    return fallback


def level_from_score(score: Optional[float]) -> str:
    if score is None or np.isnan(score):
        return "Sin cálculo"
    if score < 25:
        return "Crítico"
    if score < 50:
        return "Inicial"
    if score < 75:
        return "En construcción"
    return "Avanzado"


def recommendation_from_score(score: Optional[float]) -> str:
    if score is None or np.isnan(score):
        return "No se identificaron suficientes campos calculables; revise que los campos de cálculo estén exportándose desde Kobo."
    if score < 25:
        return "Intervención prioritaria: formalizar evidencia mínima, responsables, documentos base y medidas de cumplimiento."
    if score < 50:
        return "Fortalecer la estructura inicial: pasar de acciones parciales a procedimientos documentados y verificables."
    if score < 75:
        return "Consolidar implementación: asegurar seguimiento periódico, evidencias y responsabilidades claras."
    return "Mantener y mejorar: sistematizar aprendizajes, reportar avances y sostener mejora continua."


def metric_text(score: Optional[float]) -> str:
    if score is None or np.isnan(score):
        return "Sin cálculo"
    return f"{score:.1f}%"


def donut(score: Optional[float], title: str = "Avance", height: int = 190) -> go.Figure:
    val = 0 if score is None or np.isnan(score) else max(0, min(100, float(score)))
    remainder = 100 - val
    if val < 25:
        color = "#c0392b"
    elif val < 50:
        color = "#e67e22"
    elif val < 75:
        color = "#7e57c2"
    else:
        color = "#2e7d32"
    fig = go.Figure(
        data=[
            go.Pie(
                values=[val, remainder],
                hole=0.72,
                sort=False,
                direction="clockwise",
                marker=dict(colors=[color, "#eceff4"]),
                textinfo="none",
                hoverinfo="skip",
                showlegend=False,
            )
        ]
    )
    label = "S/C" if score is None or np.isnan(score) else f"{val:.0f}%"
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center", font=dict(size=13)),
        annotations=[dict(text=label, x=0.5, y=0.5, font=dict(size=20), showarrow=False)],
        margin=dict(l=10, r=10, t=35, b=10),
        height=height,
    )
    return fig


def progress_bar(score: Optional[float]) -> None:
    if score is None or np.isnan(score):
        st.progress(0, text="Sin cálculo")
    else:
        st.progress(int(max(0, min(100, score))), text=f"{score:.1f}%")


def compute_result(row: pd.Series, columns: Sequence[str]) -> Dict[str, Any]:
    all_scores = scoring_columns_for_row(row, columns)
    overall_fallback = float(np.mean(list(all_scores.values()))) if all_scores else None

    principle_results = []
    for p in PRINCIPLES:
        vals = scores_by_keywords(all_scores, p["keywords"] + [f"weps {p['id']}", f"weps-{p['id']}", f"principio {p['id']}"])
        p_score = mean_or_fallback(vals, overall_fallback)
        principle_results.append({**p, "score": p_score, "level": level_from_score(p_score)})

    objective_results = []
    for oid, obj in OBJECTIVES.items():
        vals = scores_by_keywords(all_scores, obj["keywords"] + [f"objetivo {oid}"])
        linked_scores = [p["score"] for p in principle_results if oid in p["objectives"]]
        fallback = mean_or_fallback(linked_scores, overall_fallback)
        o_score = mean_or_fallback(vals, fallback)
        objective_results.append({"id": oid, **obj, "score": o_score, "level": level_from_score(o_score)})

    global_score = mean_or_fallback([p["score"] for p in principle_results], overall_fallback)
    return {
        "all_scores": all_scores,
        "global_score": global_score,
        "global_level": level_from_score(global_score),
        "principles": principle_results,
        "objectives": objective_results,
    }


def validate_access(df: pd.DataFrame, company_col: Optional[str], code_cols: List[str], company: str, code: str) -> Optional[pd.Series]:
    if not company_col or not code_cols or not company or not code:
        return None
    company_norm = norm(company)
    code_norm = norm(code)
    company_matches = df[df[company_col].map(norm) == company_norm]
    if company_matches.empty:
        company_matches = df[df[company_col].map(norm).str.contains(re.escape(company_norm), na=False)]
    for _, row in company_matches.iterrows():
        for c in code_cols:
            if norm(row.get(c)) == code_norm:
                return row
    return None


def section_header() -> None:
    st.title("Dashboard empresarial | Turismo Violeta")
    st.write(
        "Consulta pública de resultados agregados y acceso individual por empresa mediante código. "
        "La lectura se organiza por principios WEPs, objetivos, indicadores y acciones sugeridas para el plan."
    )
    st.caption(f"Versión: {APP_VERSION}")


def render_login(df: pd.DataFrame, company_col: Optional[str], code_cols: List[str]) -> Optional[pd.Series]:
    st.subheader("Acceso a resultados de empresa")
    if not company_col:
        st.error("No se encontró la columna de nombre de empresa. Revise COMPANY_COLUMN en Secrets.")
        return None
    if not code_cols:
        st.error("No se encontró una columna de código de acceso. Revise que exista una pregunta de código en la hoja.")
        return None
    companies = sorted([x for x in df[company_col].dropna().astype(str).unique() if x.strip()])
    c1, c2 = st.columns([1, 1])
    with c1:
        company = st.selectbox("Nombre de empresa", companies, index=0 if companies else None)
    with c2:
        code = st.text_input("Código de acceso", type="password", help="Use el código creado al final del formulario.")
    st.caption("El código se valida contra la columna de Código de acceso creada por la empresa. Como respaldo, también se revisan identificadores técnicos si existen.")
    if not code:
        st.info("Seleccione la empresa e ingrese el código de acceso para consultar el resultado individual.")
        return None
    row = validate_access(df, company_col, code_cols, company, code)
    if row is None:
        st.error("No se encontró un registro con esa combinación de empresa y código. Revise mayúsculas, números y signos del código.")
        with st.expander("Ayuda técnica"):
            st.write("Columnas usadas para validar el código:")
            st.write(code_cols)
        return None
    st.success("Registro validado correctamente.")
    return row


def render_company_dashboard(row: pd.Series, columns: Sequence[str], company_col: Optional[str], date_col: Optional[str]) -> None:
    result = compute_result(row, columns)
    company_name = str(row.get(company_col, "Empresa")) if company_col else "Empresa"
    date_value = format_date(row.get(date_col)) if date_col else "Sin fecha"

    st.subheader(company_name)
    a, b, c, d = st.columns([1.1, 1, 1, 1])
    with a:
        st.plotly_chart(donut(result["global_score"], "Avance general", 210), use_container_width=True, config={"displayModeBar": False})
    with b:
        st.metric("Puntaje general", metric_text(result["global_score"]))
    with c:
        st.metric("Nivel", result["global_level"])
    with d:
        st.metric("Fecha de envío", date_value)

    st.subheader("Resultado por principios WEPs")
    principle_chart_data = pd.DataFrame(
        [{"Principio": f"WEPs {p['id']}", "Avance": 0 if p["score"] is None else p["score"]} for p in result["principles"]]
    )
    if not principle_chart_data.empty:
        st.bar_chart(principle_chart_data.set_index("Principio"), height=260)

    st.subheader("Principios, objetivos e indicadores para el plan")
    obj_by_id = {o["id"]: o for o in result["objectives"]}
    for p in result["principles"]:
        with st.expander(f"» » E.1.{p['id']}. {p['title']}", expanded=True):
            pc1, pc2, pc3 = st.columns([1, 1.5, 2])
            with pc1:
                st.plotly_chart(donut(p["score"], "Avance", 170), use_container_width=True, config={"displayModeBar": False})
            with pc2:
                st.metric("Avance calculado", metric_text(p["score"]))
                st.metric("Nivel", p["level"])
            with pc3:
                st.write("Documentos de apoyo:")
                st.write(p["documents"])
            st.write("Lectura para plan:")
            st.info(p["reading"])
            progress_bar(p["score"])

            for oid in p["objectives"]:
                obj = obj_by_id.get(oid)
                if not obj:
                    continue
                with st.container(border=True):
                    oc1, oc2 = st.columns([0.8, 3])
                    with oc1:
                        st.plotly_chart(donut(obj["score"], "Objetivo", 145), use_container_width=True, config={"displayModeBar": False})
                    with oc2:
                        st.markdown(f"### » » E.2.{oid}. {obj['title']}")
                        st.write(f"Principios WEPs/TV vinculados: {obj['principles']}")
                        st.write(f"Avance calculado: {metric_text(obj['score'])}")
                        st.write(f"Nivel: {obj['level']}")
                        st.write("Lectura para plan:")
                        st.write(obj["reading"])
                        st.caption(f"Indicadores que sustentan este objetivo: {obj['indicators']}")
                        st.warning(recommendation_from_score(obj["score"]))

    with st.expander("Diagnóstico de cálculo", expanded=False):
        st.write("Campos detectados para cálculo:", len(result["all_scores"]))
        if result["all_scores"]:
            diag = pd.DataFrame(
                [{"Campo": k, "Puntaje interpretado": v} for k, v in result["all_scores"].items()]
            ).sort_values("Puntaje interpretado")
            st.dataframe(diag, use_container_width=True, hide_index=True)
        else:
            st.warning("No se detectaron campos con respuestas convertibles a puntaje. Revise que Kobo exporte los campos calculate o respuestas de indicadores.")


def render_public_summary(df: pd.DataFrame, company_col: Optional[str], date_col: Optional[str]) -> None:
    st.subheader("Resumen público agregado")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Encuestas", len(df))
    with c2:
        companies = df[company_col].nunique() if company_col else 0
        st.metric("Empresas", companies)
    with c3:
        if date_col:
            dates = [excel_serial_to_datetime(v) for v in df[date_col].dropna().tolist()]
            dates = [d for d in dates if d is not None and pd.notna(d)]
            latest = max(dates).strftime("%d/%m/%Y") if dates else "Sin fecha"
        else:
            latest = "Sin fecha"
        st.metric("Última actualización", latest)
    st.info("La vista pública muestra información agregada. Para ver resultados individuales se requiere empresa y código de acceso.")


def render_technical(df: pd.DataFrame, company_col: Optional[str], code_cols: List[str]) -> None:
    st.subheader("Diagnóstico técnico")
    password = st.text_input("Clave de administrador", type="password")
    admin_password = get_secret("ADMIN_PASSWORD", "TurismoVioleta2026")
    if password != admin_password:
        st.info("Ingrese la clave de administrador para ver el diagnóstico.")
        return
    st.success("Acceso de administrador validado.")
    st.write("Filas cargadas:", len(df))
    st.write("Columna de empresa:", company_col or "No detectada")
    st.write("Columnas de código detectadas:", code_cols)
    st.write("Columnas disponibles:")
    st.dataframe(pd.DataFrame({"columnas": list(df.columns)}), use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Dashboard Turismo Violeta", layout="wide")
    st.sidebar.caption(f"Versión: {APP_VERSION}")
    st.sidebar.write("Fuente de datos: Google Sheets / Kobo")
    section_header()

    df = clean_dataframe(load_data())
    if df.empty:
        st.stop()

    company_col = find_company_column(df)
    code_cols = find_code_columns(df)
    date_col = find_date_column(df)

    tab_company, tab_public, tab_tech = st.tabs(["Consulta por empresa", "Resumen público", "Diagnóstico técnico"])
    with tab_company:
        row = render_login(df, company_col, code_cols)
        if row is not None:
            render_company_dashboard(row, df.columns, company_col, date_col)
    with tab_public:
        render_public_summary(df, company_col, date_col)
    with tab_tech:
        render_technical(df, company_col, code_cols)


if __name__ == "__main__":
    main()
