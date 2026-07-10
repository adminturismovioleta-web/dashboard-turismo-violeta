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

APP_VERSION = "v12 KOBO directo limpio"

st.set_page_config(
    page_title="Dashboard Turismo Violeta",
    page_icon="📊",
    layout="wide",
)

PRINCIPLES = [
    {
        "id": 1,
        "title": "Promover la igualdad de género desde la dirección al más alto nivel",
        "objectives": [1, 2, 3],
        "documents": "Principios WEPs; Acuerdo MDT-2025-102; documentos WEPs 1 al 8.",
        "reading": "Reforzar compromiso de alta dirección, gobernanza, Comité de Igualdad, políticas institucionales y seguimiento del plan.",
    },
    {
        "id": 2,
        "title": "Trato equitativo, derechos humanos y no discriminación en el trabajo",
        "objectives": [1, 2, 5, 7],
        "documents": "Principios WEPs; Acuerdo MDT-2025-102; Protocolo Turismo Violeta y Tool Kit.",
        "reading": "Priorizar trato equitativo, no discriminación, igualdad en selección, promoción, formación, remuneración y condiciones laborales.",
    },
    {
        "id": 3,
        "title": "Salud, seguridad, bienestar y vida libre de violencia",
        "objectives": [4, 5, 7],
        "documents": "Protocolo Turismo Violeta; Tool Kit; Acuerdo MDT-2025-102 y Manual ESNNA.",
        "reading": "Fortalecer seguridad, salud, bienestar, prevención de violencia y acoso, rutas de atención, derivación y protección.",
    },
    {
        "id": 4,
        "title": "Educación, formación y desarrollo profesional de mujeres y grupos subrepresentados",
        "objectives": [6, 7],
        "documents": "Principios WEPs y Tool Kit para capacitación y fortalecimiento de capacidades.",
        "reading": "Consolidar educación, formación, desarrollo profesional y participación de mujeres y grupos subrepresentados.",
    },
    {
        "id": 5,
        "title": "Desarrollo empresarial, cadena de suministro y marketing a favor del empoderamiento de las mujeres",
        "objectives": [8, 9],
        "documents": "Principios WEPs y Tool Kit para marketing, proveedores y cadena de valor.",
        "reading": "Ajustar prácticas empresariales, marketing responsable, cadena de suministro, proveedores y compras con enfoque de igualdad.",
    },
    {
        "id": 6,
        "title": "Igualdad mediante iniciativas comunitarias y participación territorial",
        "objectives": [10, 11],
        "documents": "Principios WEPs; Plan Integral de Seguridad Turística y Protocolo Turismo Violeta.",
        "reading": "Fortalecer iniciativas comunitarias, participación territorial, pagos transparentes, alianzas locales y saberes ancestrales.",
    },
]

OBJECTIVES = {
    1: {
        "title": "Compromiso institucional y liderazgo de alta dirección",
        "indicators": "1, 2, 3",
        "reading": "Formalizar el compromiso de la dirección, comunicarlo internamente y convertirlo en responsabilidades concretas.",
        "keywords": ["objetivo 1", "compromiso institucional", "liderazgo", "alta direccion", "alta dirección"],
    },
    2: {
        "title": "Política interna de igualdad y no discriminación",
        "indicators": "4, 5, 6, 7",
        "reading": "Revisar políticas internas para asegurar criterios explícitos de igualdad, no discriminación y derechos humanos.",
        "keywords": ["objetivo 2", "politica interna", "política interna", "no discriminacion", "no discriminación"],
    },
    3: {
        "title": "Comité de Igualdad y gobernanza del plan",
        "indicators": "8, 9, 20, 21, 22",
        "reading": "Formalizar el Comité de Igualdad, generar actas, capacitar integrantes y establecer seguimiento periódico.",
        "keywords": ["objetivo 3", "comite", "comité", "gobernanza"],
    },
    4: {
        "title": "Prevención de violencia, acoso y rutas de atención",
        "indicators": "10, 11, 12, 13, 14",
        "reading": "Implementar o actualizar rutas de prevención, atención, derivación y protección frente a violencia y acoso.",
        "keywords": ["objetivo 4", "violencia", "acoso", "rutas de atencion", "rutas de atención"],
    },
    5: {
        "title": "Derechos laborales, conciliación y condiciones de trabajo",
        "indicators": "15, 16, 17, 18, 19",
        "reading": "Fortalecer condiciones laborales, conciliación, remuneración, selección y promoción con enfoque de igualdad.",
        "keywords": ["objetivo 5", "derechos laborales", "conciliacion", "conciliación", "condiciones de trabajo"],
    },
    6: {
        "title": "Educación, formación y desarrollo profesional",
        "indicators": "23, 24, 25, 26, 27",
        "reading": "Planificar capacitación periódica, desarrollo profesional y fortalecimiento de capacidades con enfoque de igualdad.",
        "keywords": ["objetivo 6", "educacion", "educación", "formacion", "formación", "desarrollo profesional"],
    },
    7: {
        "title": "Participación de mujeres y grupos subrepresentados",
        "indicators": "28, 29, 30, 31, 32, 33, 34",
        "reading": "Reducir brechas de participación, representación y oportunidades para mujeres y grupos subrepresentados.",
        "keywords": ["objetivo 7", "participacion", "participación", "grupos subrepresentados", "mujeres"],
    },
    8: {
        "title": "Cadena de suministro, proveedores y compras responsables",
        "indicators": "35, 36, 37, 38",
        "reading": "Incorporar criterios de igualdad en proveedores, compras, contratación y relaciones con la cadena de valor.",
        "keywords": ["objetivo 8", "cadena de suministro", "proveedores", "compras"],
    },
    9: {
        "title": "Marketing, comunicación y promoción responsable",
        "indicators": "39, 40, 41, 42",
        "reading": "Revisar comunicación, marketing y promoción para evitar estereotipos y fortalecer mensajes de igualdad.",
        "keywords": ["objetivo 9", "marketing", "comunicacion", "comunicación", "promocion", "promoción"],
    },
    10: {
        "title": "Iniciativas comunitarias y articulación territorial",
        "indicators": "43, 44, 45",
        "reading": "Fortalecer alianzas locales, participación territorial e iniciativas comunitarias con enfoque de igualdad.",
        "keywords": ["objetivo 10", "comunitarias", "territorial", "alianzas locales"],
    },
    11: {
        "title": "Transparencia, seguimiento y rendición de cuentas",
        "indicators": "46, 47, 48",
        "reading": "Definir responsables, metas, evidencia y seguimiento periódico para sostener el plan de igualdad.",
        "keywords": ["objetivo 11", "transparencia", "seguimiento", "rendicion", "rendición"],
    },
}

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
    "implementado": 4,
    "difundido": 5,
    "evaluado": 5,
    "rendicion": 5,
    "rendición": 5,
    "seguimiento": 5,
}


def norm_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()


def clean_col(col: Any) -> str:
    return re.sub(r"\s+", " ", str(col).replace("\n", " ")).strip()


def get_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default


@st.cache_data(ttl=300, show_spinner=False)
def load_data_from_source(url: str, token: str) -> pd.DataFrame:
    if not url:
        return pd.DataFrame()

    headers = {}
    if token:
        headers["Authorization"] = f"Token {token}"

    response = requests.get(url, headers=headers, timeout=90)
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
    # Priorizar el nuevo campo creado por la empresa.
    auto = find_column(
        df,
        "",
        [
            "codigo de acceso",
            "código de acceso",
            "cree un codigo de acceso",
            "cree un código de acceso",
            "ingresar luego",
            "codigo para poder ingresar",
            "código para poder ingresar",
        ],
    )
    if auto:
        return auto
    return find_column(df, preferred, ["codigo", "código", "_id", "uuid", "instanceid"])


def parse_date(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Sin fecha"
    text = str(value).strip()
    if not text:
        return "Sin fecha"
    # Excel serial date.
    try:
        number = float(text)
        if 20000 <= number <= 60000:
            date = datetime(1899, 12, 30) + timedelta(days=number)
            return date.strftime("%d/%m/%Y")
    except Exception:
        pass
    # ISO-ish date.
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

    # Text like "Avance calculado: 50%".
    percent_match = re.search(r"(-?\d+(?:[\.,]\d+)?)\s*%", raw)
    if percent_match:
        try:
            return max(0.0, min(100.0, float(percent_match.group(1).replace(",", "."))))
        except Exception:
            pass

    # Numbers inside 0-5 or 0-100.
    numeric = re.findall(r"-?\d+(?:[\.,]\d+)?", raw)
    if numeric:
        try:
            n = float(numeric[0].replace(",", "."))
            if 0 <= n <= 5:
                return n * 20.0
            if 0 <= n <= 100:
                return n
        except Exception:
            pass

    for phrase, score_0_5 in SCORE_WORDS.items():
        if phrase in lowered:
            return score_0_5 * 20.0
    return None


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


def score_by_keywords(row: pd.Series, df: pd.DataFrame, keywords: Iterable[str]) -> float | None:
    cols = relevant_cols(df, keywords)
    return average_scores_from_cols(row, cols)


def objective_score(row: pd.Series, df: pd.DataFrame, objective_id: int) -> float | None:
    meta = OBJECTIVES[objective_id]
    direct = score_by_keywords(row, df, meta["keywords"])
    if direct is not None:
        return direct

    # Fallback by indicator numbers in column labels.
    indicator_tokens = re.findall(r"\d+", meta["indicators"])
    indicator_keywords = []
    for token in indicator_tokens:
        indicator_keywords.extend([f"indicador {token}", f"indicadores {token}", f"weps-tv {token.zfill(2)}", f"weps {token.zfill(2)}"])
    return score_by_keywords(row, df, indicator_keywords)


def principle_score(row: pd.Series, df: pd.DataFrame, principle_id: int, objective_scores: dict[int, float | None]) -> float | None:
    direct = score_by_keywords(
        row,
        df,
        [
            f"principio weps {principle_id}",
            f"resultado del principio weps {principle_id}",
            f"weps {principle_id}",
            f"weps 0{principle_id}",
        ],
    )
    if direct is not None:
        return direct

    objective_ids = next((p["objectives"] for p in PRINCIPLES if p["id"] == principle_id), [])
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
        "La lectura se organiza por principios WEPs, objetivos, indicadores y acciones sugeridas para el plan."
    )


def render_company_view(df: pd.DataFrame, company_col: str | None, code_col: str | None) -> None:
    st.subheader("Acceso a resultados de empresa")

    if not company_col:
        st.error("No se detectó la columna de nombre de empresa. Revise COMPANY_COLUMN en Secrets.")
        return
    if not code_col:
        st.error("No se detectó la columna de código de acceso. Revise que el formulario exporte el campo 'Código de acceso'.")
        return

    companies = sorted([c for c in df[company_col].dropna().astype(str).unique() if c.strip()])
    if not companies:
        st.warning("No hay empresas disponibles en la fuente de datos.")
        return

    col1, col2 = st.columns([1.2, 1])
    with col1:
        selected_company = st.selectbox("Nombre de empresa", companies)
    with col2:
        typed_code = st.text_input("Código de acceso", type="password")

    company_records = df[df[company_col].astype(str).str.strip() == selected_company]
    if not typed_code:
        st.info("Seleccione la empresa y escriba el código de acceso creado al final de la encuesta.")
        return

    code_series = company_records[code_col].fillna("").astype(str).str.strip()
    valid_records = company_records[code_series == typed_code.strip()]

    if valid_records.empty:
        st.error("No se encontró una encuesta con esa combinación de empresa y código. Verifique mayúsculas, números, signos y espacios.")
        with st.expander("Ayuda rápida"):
            st.write(f"Columna usada como empresa: {company_col}")
            st.write(f"Columna usada como código: {code_col}")
            st.write("El código se compara sin espacios al inicio o final, pero respetando el contenido escrito por la empresa.")
        return

    row = latest_row(valid_records)
    render_result(row, df, selected_company)


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
        st.plotly_chart(donut(total, "Avance general", height=250), use_container_width=True, config={"displayModeBar": False})
    with right:
        p_data = pd.DataFrame(
            {
                "Principio": [f"WEPs {pid}" for pid in principle_scores],
                "Avance": [0 if score is None else score for score in principle_scores.values()],
            }
        )
        fig = go.Figure(go.Bar(x=p_data["Avance"], y=p_data["Principio"], orientation="h", marker_color=[color_from_score(v) for v in p_data["Avance"]], text=[f"{v:.1f}%" for v in p_data["Avance"]], textposition="auto"))
        fig.update_layout(height=280, margin=dict(l=10, r=10, t=20, b=20), xaxis=dict(range=[0, 100], title="Avance (%)"), yaxis=dict(autorange="reversed"), showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.subheader("Principios, objetivos e indicadores para el plan")
    for p in PRINCIPLES:
        pid = p["id"]
        p_score = principle_scores.get(pid)
        with st.expander(f"» » E.1.{pid}. Principio WEPs {pid}: {p['title']}", expanded=True):
            col_a, col_b, col_c = st.columns([0.75, 1, 1.3])
            with col_a:
                st.plotly_chart(donut(p_score, "Avance del principio", height=210), use_container_width=True, config={"displayModeBar": False})
            with col_b:
                st.metric("Avance calculado", score_display(p_score))
                st.metric("Nivel", level_from_score(p_score))
                st.progress(0 if p_score is None else int(max(0, min(100, p_score))))
            with col_c:
                st.write("Documentos de apoyo:")
                st.write(p["documents"])
                st.write("Lectura para plan:")
                st.info(p["reading"])

            for objective_id in p["objectives"]:
                meta = OBJECTIVES[objective_id]
                o_score = objective_scores.get(objective_id)
                with st.container(border=True):
                    oc1, oc2 = st.columns([0.23, 1])
                    with oc1:
                        st.plotly_chart(donut(o_score, "", height=150), use_container_width=True, config={"displayModeBar": False})
                    with oc2:
                        st.markdown(f"### » » E.2.{objective_id}. Objetivo {objective_id}: {meta['title']}")
                        st.write(f"Principios WEPs/TV vinculados: {', '.join([f'WEPs {x}' for x in [pid]])}")
                        cc1, cc2 = st.columns(2)
                        cc1.metric("Avance calculado", score_display(o_score))
                        cc2.metric("Nivel", level_from_score(o_score))
                        st.write("Lectura para plan:")
                        st.success(meta["reading"])
                        st.caption(f"Indicadores que sustentan este objetivo: {meta['indicators']}")


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
    st.write(f"Columna código detectada: {code_col}")
    st.write("Primeras columnas detectadas:")
    st.dataframe(pd.DataFrame({"columna": list(df.columns)[:80]}), use_container_width=True, hide_index=True)


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
