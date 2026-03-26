import streamlit as st
import pandas as pd
from datetime import datetime, time, date, timedelta
import math

st.set_page_config(
    page_title="TWAP | Mesa de Capitales",
    page_icon="▸",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
    background-color: #0a0a0a !important;
    color: #d4d4d4;
    font-family: 'IBM Plex Mono', monospace;
}
[data-testid="stAppViewContainer"] > .main { background: #0a0a0a !important; }
[data-testid="stSidebar"] {
    background: #0f0f0f !important;
    border-right: 1px solid #1e1e1e;
}
[data-testid="stSidebar"] * { font-family: 'IBM Plex Mono', monospace !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

.top-bar {
    background: #ff6600;
    padding: 6px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    font-weight: 600;
    color: #000;
    letter-spacing: 1.5px;
    margin-bottom: 18px;
}

[data-testid="stTabs"] { border-bottom: 1px solid #222; }
[data-testid="stTabs"] button {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    letter-spacing: 1px !important;
    color: #555 !important;
    padding: 8px 16px !important;
    border: none !important;
    background: transparent !important;
    text-transform: uppercase;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #ff6600 !important;
    border-bottom: 2px solid #ff6600 !important;
}

.sec-header {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
    color: #ff6600;
    text-transform: uppercase;
    border-bottom: 1px solid #1e1e1e;
    padding-bottom: 6px;
    margin: 20px 0 14px;
}

.ticker-block {
    border: 1px solid #1e1e1e;
    border-left: 3px solid #555;
    background: #0d0d0d;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.ticker-block.ahead  { border-left-color: #00c853; }
.ticker-block.behind { border-left-color: #ff1744; }
.ticker-block.ontk   { border-left-color: #ff6600; }

.ticker-name { font-size: 18px; font-weight: 600; letter-spacing: 2px; color: #fff; }
.ticker-meta { font-size: 10px; color: #555; letter-spacing: 1px; margin-top: 2px; }

.m-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 1px;
    background: #1a1a1a;
    border: 1px solid #1a1a1a;
    margin: 12px 0;
}
.m-cell { background: #0d0d0d; padding: 10px 14px; }
.m-label { font-size: 9px; color: #444; letter-spacing: 1.5px; text-transform: uppercase; }
.m-val   { font-size: 20px; font-weight: 600; color: #d4d4d4; margin-top: 3px; }
.m-sub   { font-size: 10px; color: #444; margin-top: 2px; }
.cg  { color: #00c853 !important; }
.cr  { color: #ff1744 !important; }
.co  { color: #ff6600 !important; }
.cw  { color: #ffffff !important; }

.track-bg {
    height: 4px;
    background: #1a1a1a;
    position: relative;
    margin: 8px 0 4px;
}
.track-labels { display: flex; justify-content: space-between; font-size: 9px; color: #444; letter-spacing: .5px; }

.twap-panel { border: 1px solid #1a1a1a; padding: 14px 16px; background: #0a0a0a; }
.twap-title { font-size: 9px; letter-spacing: 2px; color: #ff6600; text-transform: uppercase; margin-bottom: 10px; font-weight: 600; }
.twap-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; border-bottom: 1px solid #111; font-size: 12px; }
.twap-row:last-child { border-bottom: none; }
.twap-key { color: #444; }
.twap-val { color: #d4d4d4; font-weight: 500; }
.twap-val.big { font-size: 16px; font-weight: 600; }

.badge { font-size: 9px; font-weight: 600; letter-spacing: 1.5px; padding: 2px 8px; text-transform: uppercase; }
.bg { background: #001a08; color: #00c853; border: 1px solid #00c853; }
.br { background: #1a0004; color: #ff1744; border: 1px solid #ff1744; }
.bo { background: #1a0900; color: #ff6600; border: 1px solid #ff6600; }

.bb-table { width: 100%; border-collapse: collapse; font-family: 'IBM Plex Mono', monospace; font-size: 12px; }
.bb-table thead tr { background: #111; }
.bb-table thead th { padding: 8px 12px; text-align: right; font-size: 9px; letter-spacing: 1.5px; color: #ff6600; font-weight: 600; text-transform: uppercase; border-bottom: 1px solid #ff6600; white-space: nowrap; }
.bb-table thead th.tl { text-align: left; }
.bb-table tbody tr { border-bottom: 1px solid #111; }
.bb-table tbody tr:hover td { background: #0f0f0f; }
.bb-table tbody td { padding: 8px 12px; color: #d4d4d4; text-align: right; white-space: nowrap; }
.bb-table tbody td.tl { text-align: left; color: #fff; font-weight: 600; }
.bb-table tfoot td { padding: 8px 12px; text-align: right; border-top: 1px solid #ff6600; font-weight: 600; font-size: 13px; }

.kpi-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: #1a1a1a; border: 1px solid #1a1a1a; margin-bottom: 20px; }
.kpi-cell { background: #0d0d0d; padding: 14px 18px; text-align: center; }
.kpi-label { font-size: 9px; color: #444; letter-spacing: 1.5px; text-transform: uppercase; }
.kpi-val   { font-size: 28px; font-weight: 600; margin-top: 4px; }

.sidebar-section { font-size: 9px; letter-spacing: 2px; color: #ff6600; text-transform: uppercase; font-weight: 600; border-bottom: 1px solid #1e1e1e; padding-bottom: 5px; margin: 16px 0 12px; }

[data-testid="stSidebar"] label { font-size: 10px !important; color: #555 !important; letter-spacing: 1px !important; text-transform: uppercase !important; }

.stButton > button {
    background: transparent !important;
    border: 1px solid #333 !important;
    color: #555 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    border-radius: 0 !important;
    padding: 6px 12px !important;
}
.stButton > button:hover { border-color: #ff6600 !important; color: #ff6600 !important; background: #1a0900 !important; }

div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input {
    background: #0f0f0f !important;
    border: 1px solid #222 !important;
    color: #d4d4d4 !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important;
}
div[data-testid="stNumberInput"] label,
div[data-testid="stTextInput"]  label,
div[data-testid="stTimeInput"]  label,
div[data-testid="stSelectbox"]  label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    color: #555 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────
if "emisoras" not in st.session_state:
    st.session_state.emisoras = [
        {
            "nombre": "VOLARA",
            "tipo": "COMPRA",
            "fondo": "FONDO A",
            "hora_orden": time(11, 35, 59),
            "hora_meta": time(13, 55, 0),
            "vol_original": 50550,
            "asignado": 39700,
            "mins_periodo": 10,
        }
    ]


# ── TWAP FORMULAS — exact Excel replication ────────────────────────────────
#
# TWAP x MINUTOS (columna C del Excel)
#   C10 = (C8-C6)*1440                    → Mins totales
#   C12 = HOUR(NOW()-C6)*60 + MINUTE(...)  → Mins transcurridos (entero)
#   C13 = C7 / C10 * C12                  → TWAP: cuánto DEBERÍA llevar asignado
#   C15 = C13 - C14                       → Por asignar (neg=adelantado, pos=atrasado)
#
# TWAP x PERIODOS (columna F del Excel)
#   F14 = F11 / F5   → Total periodos = mins_total / mins_periodo
#   F15 = F8 / F14   → Vol por periodo
#   F16 = ROUNDUP(C12 / F5, 0)  → Periodos transcurridos (escalón)
#   F17 = F16 * F15  → TWAP esperado en escalones
#   F20 = F17 - F18  → Por asignar
#
def calc_twap(e: dict, ahora: datetime):
    ho = datetime.combine(ahora.date(), e["hora_orden"])
    hm = datetime.combine(ahora.date(), e["hora_meta"])
    if hm <= ho:
        hm += timedelta(days=1)

    # C10 — mins totales
    mins_total = (hm - ho).total_seconds() / 60.0

    # C11 — tiempo transcurrido desde hora_orden, clamped a [0, mins_total]
    raw_secs = (ahora - ho).total_seconds()
    raw_secs = max(0.0, min(raw_secs, mins_total * 60.0))

    # C12 — HOUR(C11)*60 + MINUTE(C11) → minutos enteros transcurridos
    mins_trans = int(raw_secs // 60)

    # C13 — TWAP x minutos: cuánto debería ir asignado en este momento
    twap_min = (e["vol_original"] / mins_total * mins_trans) if mins_total > 0 else 0.0

    # C15 — por asignar: negativo = vas adelantado, positivo = vas atrasado
    por_asignar_min = twap_min - e["asignado"]

    # PERIODOS
    mp = e["mins_periodo"]
    total_periodos   = mins_total / mp if mp > 0 else 0.0                          # F14
    vol_por_periodo  = e["vol_original"] / total_periodos if total_periodos > 0 else 0.0  # F15
    periodos_trans   = math.ceil(mins_trans / mp) if mp > 0 else 0                 # F16 ROUNDUP
    twap_per         = periodos_trans * vol_por_periodo                             # F17
    asig_en_periodos = e["asignado"] / vol_por_periodo if vol_por_periodo > 0 else 0.0  # F19
    por_asignar_per  = twap_per - e["asignado"]                                     # F20

    pct_tiempo = mins_trans / mins_total if mins_total > 0 else 0.0
    pct_asig   = e["asignado"] / e["vol_original"] if e["vol_original"] > 0 else 0.0

    return dict(
        mins_total=mins_total, mins_trans=mins_trans,
        pct_tiempo=pct_tiempo, pct_asig=pct_asig,
        twap_min=twap_min, por_asignar_min=por_asignar_min,
        total_periodos=total_periodos, vol_por_periodo=vol_por_periodo,
        periodos_trans=periodos_trans, twap_per=twap_per,
        asig_en_periodos=asig_en_periodos, por_asignar_per=por_asignar_per,
    )


def get_status(por_asignar: float):
    if por_asignar < -200:
        return "ADELANTADO", "ahead",  "bg", "cg"
    elif por_asignar > 200:
        return "ATRASADO",   "behind", "br", "cr"
    else:
        return "EN LÍNEA",   "ontk",   "bo", "co"


# ── TOP BAR ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class='top-bar'>
  <span>▸ MESA DE CAPITALES — TWAP MONITOR</span>
  <span>SISTEMA INTERNO · {datetime.now().strftime('%d/%m/%Y')}</span>
</div>""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div class='sidebar-section'>Referencia de tiempo</div>", unsafe_allow_html=True)
    hora_actual  = st.time_input("Hora actual", value=datetime.now().time(), step=60)
    fecha_actual = st.date_input("Fecha", value=date.today(), label_visibility="collapsed")
    ahora = datetime.combine(fecha_actual, hora_actual)
    st.caption(f"⏱ {ahora.strftime('%H:%M')}  ·  {ahora.strftime('%d/%m/%Y')}")

    st.markdown("<div class='sidebar-section'>Nueva emisora</div>", unsafe_allow_html=True)
    with st.form("add_emisora", clear_on_submit=True):
        new_nombre = st.text_input("Ticker", placeholder="AMXL")
        new_fondo  = st.text_input("Fondo",  placeholder="FONDO A")
        new_tipo   = st.selectbox("Operación", ["COMPRA", "VENTA"])
        new_ho     = st.time_input("Hora Orden", value=time(9, 30),  step=60)
        new_hm     = st.time_input("Hora Meta",  value=time(14, 0), step=60)
        new_vol    = st.number_input("Vol. Original",  min_value=1, value=10000, step=100)
        new_asig   = st.number_input("Asignado",       min_value=0, value=0,     step=100)
        new_mp     = st.number_input("Mins x Periodo", min_value=1, value=10,    step=1)
        if st.form_submit_button("▸ AGREGAR", use_container_width=True) and new_nombre:
            st.session_state.emisoras.append({
                "nombre": new_nombre.upper().strip(),
                "fondo":  new_fondo.upper().strip() or "—",
                "tipo":   new_tipo,
                "hora_orden":   new_ho,
                "hora_meta":    new_hm,
                "vol_original": int(new_vol),
                "asignado":     int(new_asig),
                "mins_periodo": int(new_mp),
            })
            st.rerun()


# ── TABS ──────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["TWAP MONITOR", "DASHBOARD", "CONFIRMACIÓN"])


# ══════════════════════════════════════════════════════════════════════════
# TAB 1 – TWAP MONITOR
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    if not st.session_state.emisoras:
        st.info("Sin emisoras. Agrega una desde la barra lateral.")

    for idx, e in enumerate(st.session_state.emisoras):
        r = calc_twap(e, ahora)
        lbl, blk_cls, badge_cls, val_cls = get_status(r["por_asignar_min"])

        pct_t = min(r["pct_tiempo"] * 100, 100)
        pct_a = min(r["pct_asig"]   * 100, 100)
        bar_color = {"ahead": "#00c853", "behind": "#ff1744", "ontk": "#ff6600"}[blk_cls]

        sign_m  = "+" if r["por_asignar_min"] >= 0 else ""
        sign_p  = "+" if r["por_asignar_per"] >= 0 else ""
        color_m = "#ff1744" if r["por_asignar_min"] > 200 else ("#00c853" if r["por_asignar_min"] < -200 else "#ff6600")
        color_p = "#ff1744" if r["por_asignar_per"] > 200 else ("#00c853" if r["por_asignar_per"] < -200 else "#ff6600")

        st.markdown(f"""
        <div class='ticker-block {blk_cls}'>
          <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
            <div>
              <div class='ticker-name'>{e['nombre']}</div>
              <div class='ticker-meta'>{e['fondo']} &nbsp;·&nbsp; {e['tipo']} &nbsp;·&nbsp; {e['hora_orden'].strftime('%H:%M')} → {e['hora_meta'].strftime('%H:%M')}</div>
            </div>
            <span class='badge {badge_cls}'>{lbl}</span>
          </div>

          <div class='m-grid'>
            <div class='m-cell'>
              <div class='m-label'>Vol. Original</div>
              <div class='m-val cw'>{e['vol_original']:,}</div>
              <div class='m-sub'>títulos</div>
            </div>
            <div class='m-cell'>
              <div class='m-label'>Asignado</div>
              <div class='m-val {val_cls}'>{e['asignado']:,}</div>
              <div class='m-sub'>{pct_a:.1f}% del total</div>
            </div>
            <div class='m-cell'>
              <div class='m-label'>TWAP Esperado</div>
              <div class='m-val cw'>{r['twap_min']:,.0f}</div>
              <div class='m-sub'>deberías llevar</div>
            </div>
            <div class='m-cell'>
              <div class='m-label'>Por Asignar</div>
              <div class='m-val' style='color:{color_m};'>{sign_m}{r['por_asignar_min']:,.0f}</div>
              <div class='m-sub'>x minutos</div>
            </div>
            <div class='m-cell'>
              <div class='m-label'>Tiempo Trans.</div>
              <div class='m-val cw'>{pct_t:.1f}%</div>
              <div class='m-sub'>{r['mins_trans']} / {r['mins_total']:.0f} min</div>
            </div>
          </div>

          <div class='track-bg'>
            <div style='position:absolute;height:4px;background:#2a2a2a;width:{pct_t:.2f}%;top:0;left:0;'></div>
            <div style='position:absolute;height:4px;background:{bar_color};width:{pct_a:.2f}%;top:0;left:0;opacity:.75;'></div>
          </div>
          <div class='track-labels'>
            <span>TIEMPO TRANS. {pct_t:.1f}%</span>
            <span>ASIGNADO {pct_a:.1f}%</span>
          </div>

          <div style='display:grid;grid-template-columns:1fr 1fr;gap:1px;margin-top:12px;background:#1a1a1a;'>
            <div class='twap-panel'>
              <div class='twap-title'>⏱ TWAP x Minutos</div>
              <div class='twap-row'><span class='twap-key'>Mins totales</span><span class='twap-val'>{r['mins_total']:.1f}</span></div>
              <div class='twap-row'><span class='twap-key'>Mins transcurridos</span><span class='twap-val'>{r['mins_trans']}</span></div>
              <div class='twap-row'><span class='twap-key'>TWAP esperado</span><span class='twap-val'>{r['twap_min']:,.1f}</span></div>
              <div class='twap-row'><span class='twap-key'>Asignado</span><span class='twap-val'>{e['asignado']:,}</span></div>
              <div class='twap-row'>
                <span class='twap-key' style='color:#ccc;font-weight:600;'>Por Asignar</span>
                <span class='twap-val big' style='color:{color_m};'>{sign_m}{r['por_asignar_min']:,.0f}</span>
              </div>
            </div>
            <div class='twap-panel'>
              <div class='twap-title'>📦 TWAP x Periodos ({e['mins_periodo']} min)</div>
              <div class='twap-row'><span class='twap-key'>Total periodos</span><span class='twap-val'>{r['total_periodos']:.2f}</span></div>
              <div class='twap-row'><span class='twap-key'>Vol por periodo</span><span class='twap-val'>{r['vol_por_periodo']:,.1f}</span></div>
              <div class='twap-row'><span class='twap-key'>Periodos trans. (ROUNDUP)</span><span class='twap-val'>{r['periodos_trans']}</span></div>
              <div class='twap-row'><span class='twap-key'>TWAP esperado</span><span class='twap-val'>{r['twap_per']:,.1f}</span></div>
              <div class='twap-row'><span class='twap-key'>Asignado (periodos)</span><span class='twap-val'>{r['asig_en_periodos']:.2f}</span></div>
              <div class='twap-row'>
                <span class='twap-key' style='color:#ccc;font-weight:600;'>Por Asignar</span>
                <span class='twap-val big' style='color:{color_p};'>{sign_p}{r['por_asignar_per']:,.0f}</span>
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        col_a, col_b = st.columns([5, 1])
        with col_a:
            new_val = st.number_input(
                f"ACTUALIZAR ASIGNADO — {e['nombre']}",
                min_value=0, max_value=e["vol_original"],
                value=e["asignado"], step=100, key=f"asig_{idx}"
            )
            if new_val != e["asignado"]:
                st.session_state.emisoras[idx]["asignado"] = new_val
                st.rerun()
        with col_b:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✕ ELIMINAR", key=f"del_{idx}"):
                st.session_state.emisoras.pop(idx)
                st.rerun()
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# TAB 2 – DASHBOARD
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    if not st.session_state.emisoras:
        st.info("Sin emisoras cargadas.")
    else:
        results = []
        for e in st.session_state.emisoras:
            r = calc_twap(e, ahora)
            lbl, blk_cls, badge_cls, val_cls = get_status(r["por_asignar_min"])
            results.append({**e, **r, "lbl": lbl, "blk_cls": blk_cls, "badge_cls": badge_cls})

        tot  = len(results)
        adel = sum(1 for x in results if x["blk_cls"] == "ahead")
        atra = sum(1 for x in results if x["blk_cls"] == "behind")
        onli = sum(1 for x in results if x["blk_cls"] == "ontk")

        st.markdown(f"""
        <div class='kpi-strip'>
          <div class='kpi-cell'><div class='kpi-label'>Emisoras activas</div><div class='kpi-val cw'>{tot}</div></div>
          <div class='kpi-cell'><div class='kpi-label'>Adelantadas</div><div class='kpi-val cg'>{adel}</div></div>
          <div class='kpi-cell'><div class='kpi-label'>Atrasadas</div><div class='kpi-val cr'>{atra}</div></div>
          <div class='kpi-cell'><div class='kpi-label'>En línea</div><div class='kpi-val co'>{onli}</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<div class='sec-header'>Resumen de posiciones</div>", unsafe_allow_html=True)

        rows_html = ""
        for r in results:
            sign = "+" if r["por_asignar_min"] >= 0 else ""
            cm = "#ff1744" if r["por_asignar_min"] > 200 else ("#00c853" if r["por_asignar_min"] < -200 else "#ff6600")
            cp = "#ff1744" if r["por_asignar_per"] > 200 else ("#00c853" if r["por_asignar_per"] < -200 else "#ff6600")
            pct_a = r["pct_asig"]   * 100
            pct_t = r["pct_tiempo"] * 100
            bar_c = {"ahead": "#00c853", "behind": "#ff1744", "ontk": "#ff6600"}[r["blk_cls"]]
            sign_p = "+" if r["por_asignar_per"] >= 0 else ""
            bar_html = f"""<div style='width:100%;background:#1a1a1a;height:3px;position:relative;'>
              <div style='position:absolute;height:3px;background:#2a2a2a;width:{min(pct_t,100):.1f}%;'></div>
              <div style='position:absolute;height:3px;background:{bar_c};width:{min(pct_a,100):.1f}%;opacity:.8;'></div>
            </div>
            <div style='display:flex;justify-content:space-between;font-size:9px;color:#333;margin-top:2px;'><span>T:{pct_t:.0f}%</span><span>A:{pct_a:.0f}%</span></div>"""

            rows_html += f"""<tr>
              <td class='tl'>{r['nombre']}</td>
              <td class='tl' style='color:#555;font-weight:400;'>{r['fondo']}</td>
              <td class='tl' style='color:#555;font-weight:400;'>{r['tipo']}</td>
              <td>{r['vol_original']:,}</td>
              <td style='color:#fff;'>{r['asignado']:,}</td>
              <td>{pct_a:.1f}%</td>
              <td style='min-width:100px;'>{bar_html}</td>
              <td style='color:{cm};font-weight:600;'>{sign}{r['por_asignar_min']:,.0f}</td>
              <td style='color:{cp};font-weight:600;'>{sign_p}{r['por_asignar_per']:,.0f}</td>
              <td><span class='badge {r["badge_cls"]}'>{r['lbl']}</span></td>
            </tr>"""

        st.markdown(f"""
        <table class='bb-table'>
          <thead><tr>
            <th class='tl'>TICKER</th>
            <th class='tl'>FONDO</th>
            <th class='tl'>OP</th>
            <th>VOL ORIG</th>
            <th>ASIGNADO</th>
            <th>% ASIG</th>
            <th>PROGRESO</th>
            <th>POR ASIG (MIN)</th>
            <th>POR ASIG (PER)</th>
            <th>ESTADO</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# TAB 3 – CONFIRMACIÓN Bloomberg-pasteable
# ══════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("<div class='sec-header'>Precios de ejecución</div>", unsafe_allow_html=True)

    precios = {}
    n = len(st.session_state.emisoras)
    if n == 0:
        st.info("Sin emisoras cargadas.")
    else:
        cols = st.columns(min(n, 5))
        for i, e in enumerate(st.session_state.emisoras):
            with cols[i % 5]:
                precios[e["nombre"]] = st.number_input(
                    e["nombre"], min_value=0.0, value=0.0,
                    step=0.01, format="%.4f", key=f"px_{i}"
                )

        st.markdown("<div class='sec-header'>Tabla de confirmación</div>", unsafe_allow_html=True)

        rows_conf = ""
        total_noc = 0.0
        for e in st.session_state.emisoras:
            px  = precios.get(e["nombre"], 0.0)
            noc = e["asignado"] * px
            total_noc += noc
            op_color = "#00c853" if e["tipo"] == "COMPRA" else "#ff1744"
            rows_conf += f"""<tr>
              <td class='tl'>{e['fondo']}</td>
              <td class='tl' style='color:{op_color};font-weight:600;'>{e['tipo']}</td>
              <td>{e['nombre']}</td>
              <td>{e['asignado']:,}</td>
              <td>{px:,.4f}</td>
              <td style='color:#ff6600;font-weight:600;'>${noc:,.2f}</td>
            </tr>"""

        st.markdown(f"""
        <table class='bb-table'>
          <thead><tr>
            <th class='tl'>FONDO</th>
            <th class='tl'>OPERACIÓN</th>
            <th>EMISORA</th>
            <th>TÍTULOS</th>
            <th>PRECIO</th>
            <th>NOCIONAL</th>
          </tr></thead>
          <tbody>{rows_conf}</tbody>
          <tfoot><tr>
            <td colspan='5' style='text-align:right;color:#555;font-size:10px;letter-spacing:1px;'>TOTAL NOCIONAL</td>
            <td style='color:#ff6600;'>${total_noc:,.2f}</td>
          </tr></tfoot>
        </table>""", unsafe_allow_html=True)

        st.markdown("<div class='sec-header'>Formato Bloomberg — copiar y pegar</div>", unsafe_allow_html=True)

        # ── Tab-separated values → Bloomberg MSG / Excel pega como tabla ──
        header = "\t".join(["FONDO", "OPERACIÓN", "EMISORA", "TÍTULOS", "PRECIO", "NOCIONAL"])
        data_rows = []
        for e in st.session_state.emisoras:
            px  = precios.get(e["nombre"], 0.0)
            noc = e["asignado"] * px
            data_rows.append("\t".join([
                e["fondo"], e["tipo"], e["nombre"],
                str(e["asignado"]), f"{px:.4f}", f"{noc:.2f}"
            ]))
        footer = "\t".join(["", "", "", "", "TOTAL", f"{total_noc:.2f}"])
        bbg_tsv = "\n".join([header] + data_rows + [footer])

        st.info(
            "Selecciona todo el texto de abajo → **Ctrl+A** → **Ctrl+C** → pégalo en **Bloomberg MSG** o **Excel**. "
            "Al estar separado por tabuladores, se convierte automáticamente en tabla.",
            icon="ℹ️"
        )
        st.code(bbg_tsv, language=None)

        st.download_button(
            label="⬇  DESCARGAR .TSV (Excel / Bloomberg)",
            data=bbg_tsv.encode("utf-8"),
            file_name=f"confirmacion_{ahora.strftime('%Y%m%d_%H%M')}.tsv",
            mime="text/tab-separated-values",
        )
