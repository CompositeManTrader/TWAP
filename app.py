import streamlit as st
import pandas as pd
from datetime import datetime, time, date, timedelta
import math

st.set_page_config(
    page_title="TWAP Operaciones",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styles ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0d1117; color: #e6edf3; }
  [data-testid="stSidebar"] { background: #161b22; }
  .metric-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    padding: 16px 20px; margin: 6px 0;
  }
  .metric-label { font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: .5px; }
  .metric-value { font-size: 26px; font-weight: 700; margin-top: 4px; }
  .metric-sub   { font-size: 13px; color: #8b949e; margin-top: 2px; }
  .ahead  { color: #3fb950; }
  .behind { color: #f85149; }
  .ontk   { color: #d29922; }
  .emisora-header {
    background: #21262d; border: 1px solid #30363d; border-radius: 8px;
    padding: 10px 16px; margin-bottom: 12px;
    font-size: 18px; font-weight: 700; letter-spacing: .5px;
  }
  .confirm-table th {
    background: #21262d; color: #8b949e; font-size: 12px;
    padding: 10px 12px; text-align: left; border-bottom: 1px solid #30363d;
  }
  .confirm-table td {
    padding: 10px 12px; border-bottom: 1px solid #21262d;
    font-size: 14px; color: #e6edf3;
  }
  .confirm-table tr:hover td { background: #21262d; }
  .tag-ahead  { background:#1a4731; color:#3fb950; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
  .tag-behind { background:#3d1a1a; color:#f85149; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
  .tag-ok     { background:#3d2f0a; color:#d29922; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
  div[data-testid="stNumberInput"] label,
  div[data-testid="stTextInput"]  label,
  div[data-testid="stTimeInput"]  label,
  div[data-testid="stSelectbox"] label { color: #c9d1d9 !important; font-size: 13px; }
  div[data-testid="stTabs"] button { color: #8b949e; font-size: 14px; }
  div[data-testid="stTabs"] button[aria-selected="true"] { color: #58a6ff; border-bottom: 2px solid #58a6ff; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────
if "emisoras" not in st.session_state:
    st.session_state.emisoras = [
        {
            "nombre": "VOLARA",
            "tipo": "Compra",
            "fondo": "Fondo A",
            "hora_orden": time(11, 35, 59),
            "hora_meta": time(13, 55, 0),
            "vol_original": 50550,
            "asignado": 39700,
            "mins_periodo": 10,
        }
    ]

# ── TWAP Calculations ──────────────────────────────────────────────────────
def calc_twap(e: dict, ahora: datetime):
    ho = datetime.combine(ahora.date(), e["hora_orden"])
    hm = datetime.combine(ahora.date(), e["hora_meta"])
    if hm <= ho:
        hm += timedelta(days=1)

    tiempo_total = (hm - ho).total_seconds() / 60          # minutos totales
    transcurridos_raw = (ahora - ho).total_seconds() / 60  # minutos transcurridos
    transcurridos = max(0, min(transcurridos_raw, tiempo_total))
    pct_tiempo = transcurridos / tiempo_total if tiempo_total > 0 else 0

    # ── TWAP x Minutos ──
    twap_min = e["vol_original"] * pct_tiempo
    por_asignar_min = twap_min - e["asignado"]

    # ── TWAP x Periodos ──
    mp = e["mins_periodo"]
    total_periodos = tiempo_total / mp if mp > 0 else 0
    vol_por_periodo = e["vol_original"] / total_periodos if total_periodos > 0 else 0
    transcurridos_periodos = transcurridos / mp if mp > 0 else 0
    twap_per = vol_por_periodo * transcurridos_periodos
    por_asignar_per = twap_per - e["asignado"]
    periodos_en_asignado = e["asignado"] / vol_por_periodo if vol_por_periodo > 0 else 0

    return {
        "tiempo_total_min": tiempo_total,
        "transcurridos_min": transcurridos,
        "pct_tiempo": pct_tiempo,
        # minutos
        "twap_min": twap_min,
        "por_asignar_min": por_asignar_min,
        # periodos
        "total_periodos": total_periodos,
        "vol_por_periodo": vol_por_periodo,
        "transcurridos_periodos": transcurridos_periodos,
        "twap_per": twap_per,
        "por_asignar_per": por_asignar_per,
        "periodos_en_asignado": periodos_en_asignado,
    }

def status_label(por_asignar: float):
    if por_asignar < -200:
        return "ADELANTADO", "ahead"
    elif por_asignar > 200:
        return "ATRASADO", "behind"
    else:
        return "EN LÍNEA", "ontk"

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    hora_actual = st.time_input("Hora de referencia", value=datetime.now().time(), step=60)
    fecha_actual = st.date_input("Fecha", value=date.today())
    ahora = datetime.combine(fecha_actual, hora_actual)
    st.markdown("---")
    st.markdown("### ➕ Nueva Emisora")
    with st.form("add_emisora", clear_on_submit=True):
        new_nombre    = st.text_input("Ticker", placeholder="AMXL")
        new_fondo     = st.text_input("Fondo", placeholder="Fondo A")
        new_tipo      = st.selectbox("Tipo", ["Compra", "Venta"])
        new_ho        = st.time_input("Hora Orden", value=time(9, 30), step=60)
        new_hm        = st.time_input("Hora Meta",  value=time(14, 0), step=60)
        new_vol       = st.number_input("Vol. Original", min_value=1, value=10000, step=100)
        new_asignado  = st.number_input("Asignado",      min_value=0, value=0,     step=100)
        new_mp        = st.number_input("Mins x Periodo", min_value=1, value=10,   step=1)
        submitted = st.form_submit_button("Agregar Emisora", use_container_width=True)
        if submitted and new_nombre:
            st.session_state.emisoras.append({
                "nombre": new_nombre.upper(),
                "fondo": new_fondo,
                "tipo": new_tipo,
                "hora_orden": new_ho,
                "hora_meta": new_hm,
                "vol_original": int(new_vol),
                "asignado": int(new_asignado),
                "mins_periodo": int(new_mp),
            })
            st.success(f"✅ {new_nombre.upper()} agregada")

# ── Main Tabs ──────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 TWAP Monitor", "🗂️ Dashboard", "📋 Confirmación"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 – TWAP Monitor
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown(f"## 📈 TWAP Monitor  <span style='font-size:14px;color:#8b949e;'>— {ahora.strftime('%d/%m/%Y %H:%M')}</span>", unsafe_allow_html=True)

    if not st.session_state.emisoras:
        st.info("No hay emisoras. Agrega una desde la barra lateral.")
    else:
        for idx, e in enumerate(st.session_state.emisoras):
            r = calc_twap(e, ahora)
            lbl, cls = status_label(r["por_asignar_min"])
            pct_asig = e["asignado"] / e["vol_original"] * 100 if e["vol_original"] > 0 else 0

            with st.expander(f"{'🟢' if cls=='ahead' else '🔴' if cls=='behind' else '🟡'}  {e['nombre']}  ·  {e['fondo']}  ·  {e['tipo'].upper()}", expanded=True):

                # ── Header row ────────────────────────────────────────────
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                with c1:
                    st.markdown(f"""
                    <div class='metric-card'>
                      <div class='metric-label'>Volumen Original</div>
                      <div class='metric-value'>{e['vol_original']:,.0f}</div>
                      <div class='metric-sub'>títulos totales</div>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div class='metric-card'>
                      <div class='metric-label'>Asignado</div>
                      <div class='metric-value {cls}'>{e['asignado']:,.0f}</div>
                      <div class='metric-sub'>{pct_asig:.1f}% del total</div>
                    </div>""", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"""
                    <div class='metric-card'>
                      <div class='metric-label'>Tiempo Transcurrido</div>
                      <div class='metric-value'>{r['pct_tiempo']*100:.1f}%</div>
                      <div class='metric-sub'>{r['transcurridos_min']:.0f} / {r['tiempo_total_min']:.0f} min</div>
                    </div>""", unsafe_allow_html=True)
                with c4:
                    st.markdown(f"""
                    <div class='metric-card' style='text-align:center;'>
                      <div class='metric-label'>Estado</div>
                      <div class='metric-value {cls}' style='font-size:18px;margin-top:8px;'>{lbl}</div>
                    </div>""", unsafe_allow_html=True)

                # ── Progress bar ───────────────────────────────────────────
                bar_color = "#3fb950" if cls == "ahead" else "#f85149" if cls == "behind" else "#d29922"
                st.markdown(f"""
                <div style='background:#21262d;border-radius:6px;height:10px;margin:12px 0 6px;'>
                  <div style='background:{bar_color};width:{min(pct_asig,100):.1f}%;height:10px;border-radius:6px;'></div>
                </div>
                <div style='display:flex;justify-content:space-between;font-size:11px;color:#8b949e;'>
                  <span>Asignado: {pct_asig:.1f}%</span>
                  <span>Tiempo: {r['pct_tiempo']*100:.1f}%</span>
                </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Two TWAP columns ───────────────────────────────────────
                col_min, col_per = st.columns(2)

                with col_min:
                    st.markdown("#### ⏱ TWAP x Minutos")
                    sign_m = "+" if r["por_asignar_min"] >= 0 else ""
                    color_m = "#3fb950" if r["por_asignar_min"] <= 0 else "#f85149"
                    st.markdown(f"""
                    <table style='width:100%;border-collapse:collapse;'>
                      <tr><td style='color:#8b949e;padding:5px 0;font-size:13px;'>TWAP Esperado</td>
                          <td style='text-align:right;font-weight:600;color:#e6edf3;'>{r['twap_min']:,.1f}</td></tr>
                      <tr><td style='color:#8b949e;padding:5px 0;font-size:13px;'>Asignado</td>
                          <td style='text-align:right;font-weight:600;color:#e6edf3;'>{e['asignado']:,}</td></tr>
                      <tr style='border-top:1px solid #30363d;'>
                          <td style='color:#8b949e;padding:8px 0 0;font-size:13px;'>Por Asignar</td>
                          <td style='text-align:right;font-weight:700;font-size:16px;color:{color_m};padding-top:8px;'>
                            {sign_m}{r['por_asignar_min']:,.1f}</td></tr>
                    </table>""", unsafe_allow_html=True)

                with col_per:
                    st.markdown(f"#### 📦 TWAP x Periodos  ({e['mins_periodo']} min)")
                    sign_p = "+" if r["por_asignar_per"] >= 0 else ""
                    color_p = "#3fb950" if r["por_asignar_per"] <= 0 else "#f85149"
                    st.markdown(f"""
                    <table style='width:100%;border-collapse:collapse;'>
                      <tr><td style='color:#8b949e;padding:5px 0;font-size:13px;'>Total Periodos</td>
                          <td style='text-align:right;font-weight:600;color:#e6edf3;'>{r['total_periodos']:.2f}</td></tr>
                      <tr><td style='color:#8b949e;padding:5px 0;font-size:13px;'>Vol por Periodo</td>
                          <td style='text-align:right;font-weight:600;color:#e6edf3;'>{r['vol_por_periodo']:,.1f}</td></tr>
                      <tr><td style='color:#8b949e;padding:5px 0;font-size:13px;'>Periodos Transcurridos</td>
                          <td style='text-align:right;font-weight:600;color:#e6edf3;'>{r['transcurridos_periodos']:.2f}</td></tr>
                      <tr><td style='color:#8b949e;padding:5px 0;font-size:13px;'>TWAP Esperado</td>
                          <td style='text-align:right;font-weight:600;color:#e6edf3;'>{r['twap_per']:,.1f}</td></tr>
                      <tr><td style='color:#8b949e;padding:5px 0;font-size:13px;'>Asignado (periodos)</td>
                          <td style='text-align:right;font-weight:600;color:#e6edf3;'>{r['periodos_en_asignado']:.2f}</td></tr>
                      <tr style='border-top:1px solid #30363d;'>
                          <td style='color:#8b949e;padding:8px 0 0;font-size:13px;'>Por Asignar</td>
                          <td style='text-align:right;font-weight:700;font-size:16px;color:{color_p};padding-top:8px;'>
                            {sign_p}{r['por_asignar_per']:,.1f}</td></tr>
                    </table>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Edit Asignado ──────────────────────────────────────────
                col_edit, col_del = st.columns([4, 1])
                with col_edit:
                    new_val = st.number_input(
                        f"✏️ Actualizar Asignado — {e['nombre']}",
                        min_value=0, max_value=e["vol_original"],
                        value=e["asignado"], step=100, key=f"asig_{idx}"
                    )
                    if new_val != e["asignado"]:
                        st.session_state.emisoras[idx]["asignado"] = new_val
                        st.rerun()
                with col_del:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ Eliminar", key=f"del_{idx}"):
                        st.session_state.emisoras.pop(idx)
                        st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 – Dashboard
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("## 🗂️ Dashboard de Operaciones")

    if not st.session_state.emisoras:
        st.info("No hay emisoras cargadas.")
    else:
        results = []
        for e in st.session_state.emisoras:
            r = calc_twap(e, ahora)
            lbl, cls = status_label(r["por_asignar_min"])
            pct_asig = e["asignado"] / e["vol_original"] * 100 if e["vol_original"] > 0 else 0
            results.append({**e, **r, "lbl": lbl, "cls": cls, "pct_asig": pct_asig})

        # ── KPI Row ────────────────────────────────────────────────────────
        tot = len(results)
        adelantados = sum(1 for r in results if r["cls"] == "ahead")
        atrasados   = sum(1 for r in results if r["cls"] == "behind")
        en_linea    = sum(1 for r in results if r["cls"] == "ontk")

        k1, k2, k3, k4 = st.columns(4)
        for col, label, val, color in [
            (k1, "Total Emisoras",  tot,         "#58a6ff"),
            (k2, "Adelantadas",     adelantados, "#3fb950"),
            (k3, "Atrasadas",       atrasados,   "#f85149"),
            (k4, "En Línea",        en_linea,    "#d29922"),
        ]:
            col.markdown(f"""
            <div class='metric-card' style='text-align:center;'>
              <div class='metric-label'>{label}</div>
              <div class='metric-value' style='color:{color};'>{val}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Summary Table ──────────────────────────────────────────────────
        st.markdown("### 📋 Resumen por Emisora")
        rows_html = ""
        for r in results:
            tag_map = {"ahead": "tag-ahead", "behind": "tag-behind", "ontk": "tag-ok"}
            tag_cls = tag_map[r["cls"]]
            sign = "+" if r["por_asignar_min"] >= 0 else ""
            rows_html += f"""
            <tr>
              <td><b>{r['nombre']}</b></td>
              <td>{r['fondo']}</td>
              <td>{r['tipo']}</td>
              <td>{r['vol_original']:,}</td>
              <td>{r['asignado']:,}</td>
              <td>{r['pct_asig']:.1f}%</td>
              <td>{r['pct_tiempo']*100:.1f}%</td>
              <td style='color:{"#3fb950" if r["por_asignar_min"]<=0 else "#f85149"};font-weight:600;'>{sign}{r['por_asignar_min']:,.0f}</td>
              <td><span class='{tag_cls}'>{r['lbl']}</span></td>
            </tr>"""

        st.markdown(f"""
        <table class='confirm-table' style='width:100%;border-collapse:collapse;'>
          <thead>
            <tr>
              <th>Emisora</th><th>Fondo</th><th>Tipo</th>
              <th>Vol. Original</th><th>Asignado</th>
              <th>% Asignado</th><th>% Tiempo</th>
              <th>Por Asignar</th><th>Estado</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Mini progress bars ─────────────────────────────────────────────
        st.markdown("### 📊 Avance por Emisora")
        for r in results:
            color_map = {"ahead": "#3fb950", "behind": "#f85149", "ontk": "#d29922"}
            bar_c = color_map[r["cls"]]
            pct_t = r["pct_tiempo"] * 100
            pct_a = r["pct_asig"]
            st.markdown(f"""
            <div style='margin-bottom:18px;'>
              <div style='display:flex;justify-content:space-between;margin-bottom:4px;'>
                <span style='font-weight:600;color:#e6edf3;'>{r['nombre']}</span>
                <span style='font-size:12px;color:#8b949e;'>Asig: {pct_a:.1f}%  ·  Tiempo: {pct_t:.1f}%</span>
              </div>
              <div style='background:#21262d;border-radius:4px;height:8px;position:relative;'>
                <div style='background:#30363d;width:{min(pct_t,100):.1f}%;height:8px;border-radius:4px;position:absolute;'></div>
                <div style='background:{bar_c};width:{min(pct_a,100):.1f}%;height:8px;border-radius:4px;position:absolute;opacity:.85;'></div>
              </div>
              <div style='font-size:11px;color:#8b949e;margin-top:3px;'>
                🟫 Tiempo transcurrido &nbsp;&nbsp; <span style='color:{bar_c};'>■</span> Asignado
              </div>
            </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – Confirmación
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("## 📋 Formato de Confirmación al Cliente")
    st.markdown("Configura el precio de cada emisora para generar la tabla de confirmación.")

    if not st.session_state.emisoras:
        st.info("No hay emisoras cargadas.")
    else:
        st.markdown("### 💰 Precios de Ejecución")
        precios = {}
        cols = st.columns(min(len(st.session_state.emisoras), 4))
        for i, e in enumerate(st.session_state.emisoras):
            with cols[i % 4]:
                precios[e["nombre"]] = st.number_input(
                    f"{e['nombre']}",
                    min_value=0.0, value=0.0, step=0.01,
                    format="%.4f", key=f"precio_{i}"
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📄 Tabla de Confirmación")

        rows_conf = ""
        total_nocional = 0.0
        for e in st.session_state.emisoras:
            precio = precios.get(e["nombre"], 0.0)
            nocional = e["asignado"] * precio
            total_nocional += nocional
            rows_conf += f"""
            <tr>
              <td>{e['fondo']}</td>
              <td>{'🟢 ' if e['tipo']=='Compra' else '🔴 '}{e['tipo']}</td>
              <td><b>{e['nombre']}</b></td>
              <td style='text-align:right;'>{e['asignado']:,}</td>
              <td style='text-align:right;'>{precio:,.4f}</td>
              <td style='text-align:right;font-weight:600;color:#58a6ff;'>${nocional:,.2f}</td>
            </tr>"""

        st.markdown(f"""
        <table class='confirm-table' style='width:100%;border-collapse:collapse;'>
          <thead>
            <tr>
              <th>Fondo</th>
              <th>Operación</th>
              <th>Emisora</th>
              <th style='text-align:right;'>Títulos</th>
              <th style='text-align:right;'>Precio</th>
              <th style='text-align:right;'>Nocional</th>
            </tr>
          </thead>
          <tbody>
            {rows_conf}
            <tr style='border-top:2px solid #58a6ff;'>
              <td colspan='5' style='text-align:right;color:#8b949e;font-weight:600;padding-top:12px;'>Total Nocional</td>
              <td style='text-align:right;font-weight:700;font-size:16px;color:#58a6ff;padding-top:12px;'>${total_nocional:,.2f}</td>
            </tr>
          </tbody>
        </table>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Copy-friendly plain text ───────────────────────────────────────
        with st.expander("📨 Texto plano para copiar al cliente"):
            lineas = [f"CONFIRMACIÓN DE OPERACIONES — {ahora.strftime('%d/%m/%Y %H:%M')}", ""]
            lineas.append(f"{'Fondo':<20} {'Op':<8} {'Emisora':<10} {'Títulos':>10} {'Precio':>12} {'Nocional':>16}")
            lineas.append("-" * 78)
            for e in st.session_state.emisoras:
                precio = precios.get(e["nombre"], 0.0)
                nocional = e["asignado"] * precio
                lineas.append(f"{e['fondo']:<20} {e['tipo']:<8} {e['nombre']:<10} {e['asignado']:>10,} {precio:>12.4f} ${nocional:>14,.2f}")
            lineas.append("-" * 78)
            lineas.append(f"{'Total Nocional':>60} ${total_nocional:>14,.2f}")
            st.code("\n".join(lineas), language=None)
