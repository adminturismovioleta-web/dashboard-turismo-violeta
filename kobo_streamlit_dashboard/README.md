# Dashboard Turismo Violeta v16

Cambios principales:
- Incluye los 7 principios WEPs.
- Organiza los objetivos según el orden lógico del XLSForm.
- Muestra los 48 indicadores en tabla dentro de cada objetivo.
- Usa campos directos de cálculo exportados por KOBO cuando existen (`score_wep_7_pct`, `inf_obj_12_pct`, `inf_ind_046_score`, etc.).
- El gráfico de WEPs queda estático: sin zoom, sin barra de herramientas y sin arrastre.
- Mantiene la validación robusta del código de acceso.

Reemplazar en GitHub:
- `kobo_streamlit_dashboard/app.py`
- `kobo_streamlit_dashboard/requirements.txt`

Luego en Streamlit:
Manage app → Reboot app → Clear cache → Ctrl + F5.
