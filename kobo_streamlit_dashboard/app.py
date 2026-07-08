import io
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(
    page_title="Dashboard empresarial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# CONFIGURACIÓN VISUAL
# =========================================================
APP_TITLE = "Dashboard empresarial"
APP_SUBTITLE = "Consulta de resultados por empresa"
BRAND_NOTE = "Resultados generados a partir de la encuesta empresarial."

CSS = """
<style>
    .main .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px;}
    .hero {
        padding: 2rem 2.2rem; border-radius: 26px;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 58%, #334155 100%);
        color: white; margin-bottom: 1.3rem;
        box-shadow: 0 18px 45px rgba(15, 23, 42, .18);
    }
    .hero h1 {font-size: 2.15rem; margin: 0 0 .4rem 0; font-weight: 750;}
    .hero p {font-size: 1.02rem; color: #dbeafe; margin: 0; max-width: 850px;}
    .soft-card {
        background: #ffffff; border: 1px solid #e5e7eb; border-radius: 22px;
        padding: 1.1rem 1.25rem; box-shadow: 0 6px 18px rgba(15, 23, 42, .055);
    }
    .section-title {font-weight: 760; font-size: 1.25rem; margin: .3rem 0 .9rem 0; color: #0f172a;}
    .small-muted {font-size: .86rem; color: #64748b;}
    .metric-label {font-size:.82rem; color:#64748b; margin-bottom:.25rem;}
    .metric-value {font-size:1.65rem; font-weight:760; color:#0f172a; line-height:1.15;}
    .pill {display:inline-block; padding:.28rem .65rem; border-radius:999px; font-weight:650; font-size:.84rem;}
    .pill-green {background:#dcfce7; color:#166534;}
    .pill-yellow {background:#fef9c3; color:#854d0e;}
    .pill-orange {background:#ffedd5; color:#9a3412;}
    .pill-red {background:#fee2e2; color:#991b1b;}
    .divider {height:1px; background:#e5e7eb; margin:1.3rem 0;}
    div[data-testid="stMetricValue"] {font-weight: 760;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =========================================================
# UTILIDADES
# =========================================================
def get_secret(name: str, default: str = "") -> str:
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def pretty_label(col: str) -> str:
    label = str(col)
    label = label.replace("/", " · ").replace("_", " ")
    label = re.sub(r"\s+", " ", label).strip()
    return label[:1].upper() + label[1:]


def pick_column(df: pd.DataFrame, explicit_secret: str, candidates: List[str]) -> Optional[str]:
    if explicit_secret and explicit_secret in df.columns:
        return explicit_secret
    norm_map = {normalize_text(c): c for c in df.columns}
    for candidate in candidates:
        nc = normalize_text(candidate)
        if nc in norm_map:
            return norm_map[nc]
    for candidate in candidates:
        nc = normalize_text(candidate)
        for ncol, original in norm_map.items():
            if nc and (nc in ncol or ncol in nc):
                return original
    return None


def first_non_empty(row: pd.Series, columns: List[str]) -> str:
    for col in columns:
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip() != "":
            return str(row[col]).strip()
    return ""


def parse_percent(value: Any) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        raw = value.strip().replace(",", ".")
        raw = raw.replace("%", "")
        match = re.search(r"-?\d+(\.\d+)?", raw)
        if not match:
            return None
        value = float(match.group())
    try:
        value = float(value)
    except Exception:
        return None
    if -1 <= value <= 1:
        value *= 100
    if value < 0:
        return 0.0
    if value > 100:
        # Si una columna contiene un conteo y no un porcentaje, se descarta.
        return None
    return round(value, 2)


def score_level(score: Optional[float]) -> Tuple[str, str]:
    if score is None:
        return "No detectado", "pill-orange"
    if score >= 80:
        return "Avance alto", "pill-green"
    if score >= 60:
        return "Avance medio", "pill-yellow"
    if score >= 40:
        return "Avance inicial", "pill-orange"
    return "Brecha crítica", "pill-red"


def yes_no_score(value: Any) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    text = normalize_text(value)
    yes_values = {"si", "sí", "yes", "cumple", "completo", "implementado", "alto"}
    partial_values = {"parcial", "en_proceso", "medio", "medianamente", "algunas_veces"}
    no_values = {"no", "none", "ninguno", "no_cumple", "bajo", "sin_implementar"}
    na_values = {"no_aplica", "na", "n_a", "no_corresponde"}
    if text in yes_values:
        return 100.0
    if text in partial_values:
        return 50.0
    if text in no_values:
        return 0.0
    if text in na_values:
        return None
    return None


# =========================================================
# CARGA DE DATOS
# =========================================================
def read_excel_bytes(content: bytes) -> pd.DataFrame:
    sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, dtype=object)
    # Kobo suele traer una hoja principal y, a veces, hojas auxiliares. Se toma la de mayor tamaño.
    best_name, best_df = max(sheets.items(), key=lambda item: item[1].shape[0] * max(item[1].shape[1], 1))
    best_df.columns = [str(c).strip() for c in best_df.columns]
    best_df = best_df.dropna(how="all")
    return best_df


def read_csv_bytes(content: bytes) -> pd.DataFrame:
    for enc in ["utf-8", "utf-8-sig", "latin1"]:
        try:
            df = pd.read_csv(io.BytesIO(content), dtype=object, encoding=enc)
            df.columns = [str(c).strip() for c in df.columns]
            return df.dropna(how="all")
        except Exception:
            continue
    raise ValueError("No fue posible leer el CSV. Revise el formato o la codificación del archivo.")


@st.cache_data(ttl=600, show_spinner=False)
def fetch_from_url(url: str, token: str = "") -> pd.DataFrame:
    headers = {}
    if token:
        headers["Authorization"] = f"Token {token}"
    response = requests.get(url, headers=headers, timeout=45)
    response.raise_for_status()
    content = response.content
    ctype = response.headers.get("content-type", "").lower()
    if url.lower().endswith(".csv") or "csv" in ctype:
        return read_csv_bytes(content)
    return read_excel_bytes(content)


def load_data() -> Tuple[Optional[pd.DataFrame], str]:
    data_url = get_secret("KOBO_DATA_URL", "").strip()
    kobo_token = get_secret("KOBO_TOKEN", "").strip()

    uploaded = st.sidebar.file_uploader(
        "Cargar Excel/CSV manualmente",
        type=["xlsx", "xls", "csv"],
        help="Útil para pruebas locales o si el enlace de KOBO aún no tiene acceso público/API.",
    )

    if uploaded is not None:
        content = uploaded.getvalue()
        if uploaded.name.lower().endswith(".csv"):
            return read_csv_bytes(content), "Archivo cargado manualmente"
        return read_excel_bytes(content), "Archivo cargado manualmente"

    if data_url:
        try:
            return fetch_from_url(data_url, kobo_token), "KOBO / URL configurada"
        except Exception as exc:
            st.error(f"No fue posible cargar la URL configurada. Detalle técnico: {exc}")
            return None, "Error al cargar URL"

    return None, "Sin fuente configurada"


# =========================================================
# DETECCIÓN DE COLUMNAS Y CÁLCULOS
# =========================================================
def detect_schema(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    company_col = pick_column(
        df,
        get_secret("COMPANY_COLUMN", ""),
        [
            "empresa", "nombre_empresa", "nombre_de_la_empresa", "razon_social", "razón_social",
            "organizacion", "organización", "nombre_organizacion", "nombre_organización", "company", "organization",
        ],
    )
    access_col = pick_column(
        df,
        get_secret("ACCESS_CODE_COLUMN", ""),
        [
            "codigo_acceso", "código_acceso", "codigo", "código", "access_code", "token_empresa",
            "id_empresa", "_id", "_uuid", "meta/instanceID", "instanceID",
        ],
    )
    date_col = pick_column(
        df,
        get_secret("DATE_COLUMN", ""),
        ["_submission_time", "submission_time", "fecha_envio", "fecha_de_envio", "end", "today", "fecha"],
    )
    level_col = pick_column(
        df,
        get_secret("LEVEL_COLUMN", ""),
        ["nivel_avance", "nivel_de_avance", "nivel", "estado_avance", "clasificacion", "clasificación"],
    )
    reading_col = pick_column(
        df,
        get_secret("READING_COLUMN", ""),
        ["lectura_para_plan", "lectura_plan", "lectura", "recomendacion", "recomendación", "plan"],
    )
    return {
        "company": company_col,
        "access": access_col,
        "date": date_col,
        "level": level_col,
        "reading": reading_col,
    }


def candidate_score_columns(df: pd.DataFrame) -> List[str]:
    explicit = get_secret("SCORE_COLUMNS", "").strip()
    if explicit:
        cols = [c.strip() for c in explicit.split(",") if c.strip() in df.columns]
        if cols:
            return cols

    include_terms = [
        "puntaje", "score", "avance", "calificacion", "calificación", "cumplimiento", "porcentaje", "resultado",
    ]
    exclude_terms = [
        "nivel", "lectura", "comentario", "observacion", "observación", "nota", "fecha", "hora", "empresa",
    ]
    cols = []
    for col in df.columns:
        norm = normalize_text(col)
        if any(term in norm for term in include_terms) and not any(term in norm for term in exclude_terms):
            # Al menos una fila debe poder leerse como porcentaje.
            valid_values = df[col].map(parse_percent).dropna()
            if len(valid_values) > 0:
                cols.append(col)
    return cols


def pick_general_score(row: pd.Series, df: pd.DataFrame) -> Tuple[Optional[float], Optional[str]]:
    explicit = get_secret("GENERAL_SCORE_COLUMN", "").strip()
    if explicit and explicit in row.index:
        score = parse_percent(row[explicit])
        if score is not None:
            return score, explicit

    score_cols = candidate_score_columns(df)
    general_terms = ["general", "total", "resumen", "global", "final"]
    for col in score_cols:
        norm = normalize_text(col)
        if any(term in norm for term in general_terms):
            score = parse_percent(row[col])
            if score is not None:
                return score, col

    values = [parse_percent(row[col]) for col in score_cols if col in row.index]
    values = [v for v in values if v is not None]
    if values:
        return round(sum(values) / len(values), 2), "Promedio de columnas de avance detectadas"

    # Último recurso: mapear respuestas sí/no/parcial, evitando metadatos y textos largos.
    excluded = {detect_schema(df).get(k) for k in ["company", "access", "date", "level", "reading"]}
    derived = []
    for col in df.columns:
        if col in excluded:
            continue
        val = row[col]
        mapped = yes_no_score(val)
        if mapped is not None:
            derived.append(mapped)
    if derived:
        return round(sum(derived) / len(derived), 2), "Promedio derivado de respuestas Sí/No/Parcial"
    return None, None


def dimension_scores(row: pd.Series, df: pd.DataFrame, general_col: Optional[str]) -> pd.DataFrame:
    cols = candidate_score_columns(df)
    data = []
    for col in cols:
        if general_col and col == general_col:
            continue
        value = parse_percent(row.get(col))
        if value is not None:
            label = pretty_label(col)
            label = re.sub(r"(?i)puntaje|score|avance|calificacion|calificación|porcentaje|cumplimiento", "", label).strip(" -_·")
            data.append({"Dimensión": label or pretty_label(col), "Puntaje": value, "Columna": col})
    return pd.DataFrame(data).sort_values("Puntaje", ascending=True) if data else pd.DataFrame(columns=["Dimensión", "Puntaje", "Columna"])


def info_fields(row: pd.Series, schema: Dict[str, Optional[str]]) -> List[Tuple[str, str]]:
    desired_terms = [
        "sector", "actividad", "provincia", "canton", "cantón", "parroquia", "ciudad", "direccion", "dirección",
        "total_area", "trabajadores", "personal", "empleados", "fecha", "submission", "end", "start",
    ]
    fields = []
    used = set()
    for key, col in schema.items():
        if col and col in row.index and col not in used:
            val = row[col]
            if pd.notna(val) and str(val).strip():
                label = {
                    "company": "Empresa",
                    "access": "Código / ID interno",
                    "date": "Fecha de envío",
                    "level": "Nivel de avance",
                    "reading": "Lectura para plan",
                }.get(key, pretty_label(col))
                fields.append((label, str(val)))
                used.add(col)
    for col in row.index:
        if col in used:
            continue
        norm = normalize_text(col)
        if any(normalize_text(t) in norm for t in desired_terms):
            val = row[col]
            if pd.notna(val) and str(val).strip():
                fields.append((pretty_label(col), str(val)))
                used.add(col)
        if len(fields) >= 14:
            break
    return fields


def plan_reading(score: Optional[float], dims: pd.DataFrame, explicit_reading: str = "") -> str:
    if explicit_reading:
        return explicit_reading
    if score is None:
        return "No se detectó una columna de calificación. Configure GENERAL_SCORE_COLUMN o SCORE_COLUMNS en los secretos para activar una lectura automática más precisa."
    if not dims.empty:
        lowest = dims.head(3)["Dimensión"].tolist()
        focus = ", ".join(lowest)
    else:
        focus = "los indicadores con respuesta negativa o parcial"
    if score >= 80:
        return f"La empresa muestra un avance alto. La prioridad debe ser consolidar evidencia, mantener seguimiento periódico y cerrar brechas puntuales en {focus}."
    if score >= 60:
        return f"La empresa cuenta con una base de implementación, pero requiere formalizar acciones, responsables y evidencia. Se recomienda priorizar {focus}."
    if score >= 40:
        return f"La implementación es inicial. El plan debería concentrarse en acciones de corto plazo, responsables claros, cronograma y cierre de brechas en {focus}."
    return f"La empresa presenta brechas críticas. El plan debe iniciar con medidas básicas de gobernanza, prevención, capacitación y documentación, priorizando {focus}."


# =========================================================
# COMPONENTES VISUALES
# =========================================================
def hero():
    st.markdown(
        f"""
        <div class="hero">
            <h1>{APP_TITLE}</h1>
            <p>{APP_SUBTITLE}. {BRAND_NOTE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: Any, help_text: str = ""):
    st.markdown(
        f"""
        <div class="soft-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="small-muted">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def gauge(score: Optional[float]):
    value = 0 if score is None else score
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "%", "font": {"size": 42}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"thickness": 0.28},
            "steps": [
                {"range": [0, 40], "color": "#fee2e2"},
                {"range": [40, 60], "color": "#ffedd5"},
                {"range": [60, 80], "color": "#fef9c3"},
                {"range": [80, 100], "color": "#dcfce7"},
            ],
        },
        title={"text": "Calificación general"},
    ))
    fig.update_layout(height=330, margin=dict(l=20, r=20, t=55, b=20))
    st.plotly_chart(fig, use_container_width=True)


def bar_dimensions(dims: pd.DataFrame):
    if dims.empty:
        st.info("Aún no se detectaron columnas de puntaje por principio/dimensión. Configure SCORE_COLUMNS o revise los nombres de columnas exportadas.")
        return
    chart_df = dims.copy().tail(12)
    fig = px.bar(chart_df, x="Puntaje", y="Dimensión", orientation="h", text="Puntaje")
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=max(360, 42 * len(chart_df)),
        xaxis_range=[0, 105],
        xaxis_title="Puntaje (%)",
        yaxis_title="",
        margin=dict(l=10, r=20, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def public_summary(df: pd.DataFrame, schema: Dict[str, Optional[str]]):
    st.markdown('<div class="section-title">Información general pública</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Encuestas registradas", f"{len(df):,}".replace(",", "."), "Total de formularios en la fuente")
    with c2:
        if schema.get("company"):
            n_emp = df[schema["company"]].dropna().astype(str).str.strip().replace("", pd.NA).dropna().nunique()
        else:
            n_emp = "N/D"
        metric_card("Empresas", n_emp, "Empresas únicas detectadas")
    with c3:
        score_values = []
        for _, r in df.iterrows():
            s, _ = pick_general_score(r, df)
            if s is not None:
                score_values.append(s)
        avg = f"{sum(score_values) / len(score_values):.1f}%" if score_values else "N/D"
        metric_card("Promedio general", avg, "Calculado solo con puntajes detectados")
    with c4:
        if schema.get("date"):
            latest = pd.to_datetime(df[schema["date"]], errors="coerce").max()
            latest_txt = latest.strftime("%d/%m/%Y") if pd.notna(latest) else "N/D"
        else:
            latest_txt = "N/D"
        metric_card("Última actualización", latest_txt, "Según fecha de envío detectada")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.caption("Esta vista pública muestra solo información agregada. Para ver resultados por empresa se requiere nombre de empresa y código de acceso.")


def company_access_form(df: pd.DataFrame, schema: Dict[str, Optional[str]]) -> Optional[pd.Series]:
    st.markdown('<div class="section-title">Consulta por empresa</div>', unsafe_allow_html=True)
    if not schema.get("access"):
        st.warning("No se detectó una columna de código de acceso. Configure ACCESS_CODE_COLUMN o agregue una columna codigo_acceso en la base.")
        return None
    if not schema.get("company"):
        st.warning("No se detectó una columna de empresa. Configure COMPANY_COLUMN o agregue una columna nombre_empresa en la base.")
        return None

    with st.form("access_form", clear_on_submit=False):
        c1, c2, c3 = st.columns([1.2, 1, .42])
        with c1:
            company_input = st.text_input("Nombre de empresa", placeholder="Ej.: Empresa Turística S.A.")
        with c2:
            code_input = st.text_input("Código de acceso", type="password", placeholder="Ej.: EMP-8K42-RM91")
        with c3:
            st.write("")
            submitted = st.form_submit_button("Ver resultados", use_container_width=True)

    if not submitted:
        st.info("Ingrese el nombre de la empresa y el código recibido para consultar los resultados.")
        return None

    company_norm = normalize_text(company_input)
    code_norm = normalize_text(code_input)
    if not company_norm or not code_norm:
        st.error("Complete el nombre de empresa y el código de acceso.")
        return None

    company_col = schema["company"]
    access_col = schema["access"]
    filtered = df[
        (df[company_col].astype(str).map(normalize_text) == company_norm)
        & (df[access_col].astype(str).map(normalize_text) == code_norm)
    ].copy()

    if filtered.empty:
        st.error("No encontramos resultados asociados a esa combinación de empresa y código.")
        return None

    if schema.get("date"):
        filtered["__date__"] = pd.to_datetime(filtered[schema["date"]], errors="coerce")
        filtered = filtered.sort_values("__date__", ascending=False)
    return filtered.iloc[0]


def render_company_dashboard(row: pd.Series, df: pd.DataFrame, schema: Dict[str, Optional[str]]):
    company_name = str(row[schema["company"]]) if schema.get("company") else "Empresa"
    score, score_source = pick_general_score(row, df)
    level, pill_class = score_level(score)
    explicit_level = str(row[schema["level"]]).strip() if schema.get("level") and pd.notna(row[schema["level"]]) else ""
    final_level = explicit_level or level
    dims = dimension_scores(row, df, score_source if score_source in df.columns else None)
    explicit_reading = str(row[schema["reading"]]).strip() if schema.get("reading") and pd.notna(row[schema["reading"]]) else ""

    st.markdown(f"### {company_name}")
    st.markdown(f'<span class="pill {pill_class}">{final_level}</span>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Calificación general", f"{score:.1f}%" if score is not None else "N/D", score_source or "No detectado")
    with c2:
        metric_card("Nivel de avance", final_level, "Lectura sintética del resultado")
    with c3:
        if schema.get("date") and pd.notna(row.get(schema["date"])):
            try:
                date_txt = pd.to_datetime(row[schema["date"]]).strftime("%d/%m/%Y")
            except Exception:
                date_txt = str(row[schema["date"]])
        else:
            date_txt = "N/D"
        metric_card("Fecha de envío", date_txt, "Registro seleccionado")
    with c4:
        metric_card("Dimensiones detectadas", len(dims), "Principios / indicadores de avance")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["Resumen", "Calificación", "Lectura para plan", "Datos de la encuesta"])

    with tab1:
        left, right = st.columns([1.05, 1])
        with left:
            gauge(score)
        with right:
            st.markdown('<div class="section-title">Información general</div>', unsafe_allow_html=True)
            fields = info_fields(row, schema)
            if fields:
                display_df = pd.DataFrame(fields, columns=["Campo", "Valor"])
                st.dataframe(display_df, hide_index=True, use_container_width=True)
            else:
                st.info("No se detectaron campos generales adicionales.")

    with tab2:
        st.markdown('<div class="section-title">Avance por principio / dimensión</div>', unsafe_allow_html=True)
        bar_dimensions(dims)
        if not dims.empty:
            table = dims.sort_values("Puntaje", ascending=False)[["Dimensión", "Puntaje"]].copy()
            table["Puntaje"] = table["Puntaje"].map(lambda x: f"{x:.1f}%")
            st.dataframe(table, hide_index=True, use_container_width=True)

    with tab3:
        st.markdown('<div class="section-title">Lectura para plan</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="soft-card">
                {plan_reading(score, dims, explicit_reading)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not dims.empty:
            st.markdown("#### Prioridades sugeridas")
            priorities = dims.head(5).copy()
            priorities["Prioridad"] = priorities["Puntaje"].apply(lambda x: "Alta" if x < 50 else ("Media" if x < 70 else "Baja"))
            priorities["Acción sugerida"] = priorities["Puntaje"].apply(
                lambda x: "Intervención prioritaria y evidencia mínima" if x < 50 else (
                    "Fortalecer procedimientos y seguimiento" if x < 70 else "Mantener y documentar evidencia"
                )
            )
            st.dataframe(priorities[["Dimensión", "Puntaje", "Prioridad", "Acción sugerida"]], hide_index=True, use_container_width=True)

    with tab4:
        st.markdown('<div class="section-title">Registro filtrado</div>', unsafe_allow_html=True)
        safe = row.drop(labels=[schema["access"]], errors="ignore").to_frame("Valor")
        safe.index.name = "Campo"
        st.dataframe(safe.reset_index(), hide_index=True, use_container_width=True)
        st.caption("Por seguridad, la columna de código no se muestra en esta vista.")


# =========================================================
# APP
# =========================================================
def main():
    hero()
    df, source_label = load_data()

    with st.sidebar:
        st.markdown("### Fuente de datos")
        st.caption(source_label)
        st.markdown("### Vista")
        view = st.radio("Seleccione", ["Consulta por empresa", "Resumen general público"], label_visibility="collapsed")
        st.markdown("### Configuración detectada")

    if df is None or df.empty:
        st.warning("No hay datos cargados todavía.")
        st.markdown(
            """
            Para activar la app, configure los secretos en Streamlit Cloud o cargue un Excel/CSV desde la barra lateral.

            Secretos mínimos recomendados:
            ```toml
            KOBO_DATA_URL = "https://eu.kobotoolbox.org/api/v2/assets/.../data.xlsx"
            KOBO_TOKEN = "PEGUE_AQUI_SU_TOKEN"
            COMPANY_COLUMN = "nombre_empresa"
            ACCESS_CODE_COLUMN = "codigo_acceso"
            GENERAL_SCORE_COLUMN = "puntaje_general"
            SCORE_COLUMNS = "principio_1,principio_2,principio_3"
            ```
            """
        )
        return

    schema = detect_schema(df)
    with st.sidebar:
        st.json({k: v for k, v in schema.items()})
        st.caption(f"Filas: {len(df)} · Columnas: {len(df.columns)}")

    if view == "Resumen general público":
        public_summary(df, schema)
    else:
        selected = company_access_form(df, schema)
        if selected is not None:
            render_company_dashboard(selected, df, schema)


if __name__ == "__main__":
    main()
