"""
TWAP Monitor — Mesa de Capitales
Fórmulas replicadas exactamente del Excel:

TWAP x MINUTOS
  C10 = (hora_meta - hora_orden) * 1440          → mins totales (float)
  C12 = HOUR(NOW-hora_orden)*60 + MINUTE(...)    → mins transcurridos (int)
  C13 = vol_original / C10 * C12                 → TWAP esperado ahora mismo
  C15 = C13 - asignado                           → Por Asignar  (neg=adelantado, pos=atrasado)

TWAP x PERIODOS
  F11 = C10  (mismo mins totales)
  F14 = F11 / mins_periodo                       → total periodos (float)
  F15 = vol_original / F14                       → vol por periodo
  F13 = C12  (mismos mins transcurridos)
  F16 = ROUNDUP(F13 / mins_periodo, 0)           → periodos transcurridos (escalón entero)
  F17 = F16 * F15                                → TWAP esperado (en escalones)
  F20 = F17 - asignado                           → Por Asignar periodos
"""

import streamlit as st
import json
from datetime import datetime, time, date, timedelta
import math

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TWAP Monitor",
    page_icon="▸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Persistent storage via st.query_params (survives refresh) ──────────────
# We use a dedicated "save/load" pattern with query_params as a lightweight
# persistence layer that survives Streamlit Cloud refreshes within the session.
# For true cross-session persistence the user would need a DB, but this handles
# the F5-refresh case cleanly.

DEFAULTS = [
    {
        "nombre": "VOLARA",
        "tipo": "COMPRA",
        "fondo": "FONDO A",
        "hora_orden": "11:35:59",
        "hora_meta": "13:55:00",
        "vol_original": 50550,
        "asignado": 39700,
        "mins_periodo": 10,
    }
]

def load_emisoras():
    """Load from session_state (already deserialized) or initialize from defaults."""
    if "emisoras" not in st.session_state:
        st.session_state.emisoras = json.loads(json.dumps(DEFAULTS))
    return st.session_state.emisoras

def save_emisoras(data):
    st.session_state.emisoras = data

def parse_time(t_str: str) -> time:
    h, m, s = (int(x) for x in t_str.split(":"))
    return time(h, m, s)

def time_to_str(t: time) -> str:
    return t.strftime("%H:%M:%S")

# ─── TWAP Engine ─────────────────────────────────────────────────────────────
def calc_twap(e: dict, ahora: datetime) -> dict:
    """
    Replica exacta de las fórmulas del Excel.
    e['hora_orden'] y e['hora_meta'] vienen como strings "HH:MM:SS"
    """
    ho = datetime.combine(ahora.date(), parse_time(e["hora_orden"]))
    hm = datetime.combine(ahora.date(), parse_time(e["hora_meta"]))
    if hm <= ho:
        hm += timedelta(days=1)

    vol = e["vol_original"]
    asig = e["asignado"]
    mp = e["mins_periodo"]

    # ── C10: mins totales (float, como Excel) ──────────────────────────────
    mins_total = (hm - ho).total_seconds() / 60.0          # (C8-C6)*1440

    # ── C11: tiempo transcurrido desde hora_orden ─────────────────────────
    diff_secs = (ahora - ho).total_seconds()
    diff_secs = max(0.0, min(diff_secs, mins_total * 60.0))  # clamp [0, total]

    # ── C12: HOUR(C11)*60 + MINUTE(C11) — minutos enteros (int) ───────────
    # Excel HOUR() y MINUTE() truncan, no redondean
    diff_td   = timedelta(seconds=diff_secs)
    total_sec = int(diff_td.total_seconds())
    c12 = (total_sec // 3600) * 60 + (total_sec % 3600) // 60   # int

    # ── C13: TWAP x minutos ───────────────────────────────────────────────
    # = vol_original / mins_total * c12
    twap_min = (vol / mins_total * c12) if mins_total > 0 else 0.0

    # ── C15: Por Asignar x minutos ────────────────────────────────────────
    # NEGATIVO = ya asignaste MÁS de lo que el TWAP pide → vas ADELANTADO
    # POSITIVO = debes asignar más → vas ATRASADO
    por_asignar_min = twap_min - asig   # C13 - C14

    # ── PERIODOS ──────────────────────────────────────────────────────────
    # F14 = F11 / F5  (F11 = C10 = mins_total, F5 = mins_periodo)
    total_periodos  = mins_total / mp if mp > 0 else 0.0

    # F15 = F8 / F14  (F8 = vol_original)
    vol_por_periodo = vol / total_periodos if total_periodos > 0 else 0.0

    # F16 = ROUNDUP(F13 / F5, 0)  donde F13 = C12 = c12 (mins enteros)
    periodos_trans  = math.ceil(c12 / mp) if (mp > 0 and c12 > 0) else 0

    # F17 = F16 * F15
    twap_per = periodos_trans * vol_por_periodo

    # F19 = F18 / F15  (F18 = asignado)
    asig_en_periodos = asig / vol_por_periodo if vol_por_periodo > 0 else 0.0

    # F20 = F17 - F18
    por_asignar_per = twap_per - asig

    pct_tiempo = c12 / mins_total if mins_total > 0 else 0.0
    pct_asig   = asig / vol if vol > 0 else 0.0

    return {
        "mins_total": mins_total,
        "c12": c12,
        "pct_tiempo": pct_tiempo,
        "pct_asig":   pct_asig,
        # minutos
        "twap_min":         twap_min,
        "por_asignar_min":  por_asignar_min,
        # periodos
        "total_periodos":   total_periodos,
        "vol_por_periodo":  vol_por_periodo,
        "periodos_trans":   periodos_trans,
        "twap_per":         twap_per,
        "asig_en_periodos": asig_en_periodos,
        "por_asignar_per":  por_asignar_per,
    }


# ── Validation: reproduce Excel values ──────────────────────────────────────
# ahora = 12:23:17, hora_orden = 11:35:59
# Expected: C12=47, C13=17090.40, C15=-22609.60, F16=5, F17=18181.27, F20=-21518.73
_test_e = DEFAULTS[0].copy()
_test_now = datetime(2026, 3, 25, 12, 23, 17)
_t = calc_twap(_test_e, _test_now)
assert _t["c12"] == 47,               f"C12 wrong: {_t['c12']}"
assert abs(_t["twap_min"] - 17090.40)  < 1, f"C13 wrong: {_t['twap_min']}"
assert abs(_t["por_asignar_min"] - (-22609.60)) < 1, f"C15 wrong: {_t['por_asignar_min']}"
assert _t["periodos_trans"] == 5,     f"F16 wrong: {_t['periodos_trans']}"
assert abs(_t["twap_per"] - 18181.27)  < 1, f"F17 wrong: {_t['twap_per']}"
assert abs(_t["por_asignar_per"] - (-21518.73)) < 1, f"F20 wrong: {_t['por_asignar_per']}"


def badge(por_asignar: float):
    """Returns (label, css_class_suffix) based on Por Asignar value."""
    if por_asignar < -200:
        return "ADELANTADO", "green"
    elif por_asignar > 200:
        return "ATRASADO", "red"
    else:
        return "EN LÍNEA", "orange"


# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #111318 !important;
    color: #e8eaf0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
[data-testid="stAppViewContainer"] > .main { background: #111318 !important; }
[data-testid="stSidebar"] { background: #0d0f13 !important; border-right: 1px solid #2a2d35; }
[data-testid="stSidebar"] * { font-family: 'IBM Plex Mono', monospace !important; color: #c8cad4 !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* ── Tabs ── */
[data-testid="stTabs"] { border-bottom: 1px solid #2a2d35 !important; }
button[data-baseweb="tab"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; font-weight: 600 !important;
    letter-spacing: 1.5px !important; text-transform: uppercase !important;
    color: #6b7080 !important; background: transparent !important;
    border: none !important; padding: 10px 20px !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #ff6b00 !important;
    border-bottom: 2px solid #ff6b00 !important;
}

/* ── Top bar ── */
.topbar {
    background: linear-gradient(90deg, #ff6b00, #e55a00);
    padding: 8px 24px; display: flex;
    justify-content: space-between; align-items: center;
    font-size: 11px; font-weight: 700;
    color: #000; letter-spacing: 2px;
    margin-bottom: 20px;
}

/* ── Section label ── */
.slabel {
    font-size: 9px; font-weight: 700; letter-spacing: 2.5px;
    color: #ff6b00; text-transform: uppercase;
    border-bottom: 1px solid #2a2d35; padding-bottom: 6px;
    margin: 24px 0 16px;
}

/* ── Ticker card ── */
.card {
    background: #161920; border: 1px solid #2a2d35;
    border-left: 4px solid #444;
    padding: 18px 22px; margin-bottom: 14px;
}
.card.green  { border-left-color: #2dd87a; }
.card.red    { border-left-color: #ff4560; }
.card.orange { border-left-color: #ff6b00; }

.card-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.card-title { font-size: 22px; font-weight: 700; letter-spacing: 3px; color: #ffffff; }
.card-sub { font-size: 10px; color: #6b7080; letter-spacing: 1px; margin-top: 3px; }

/* ── Status badge ── */
.bdg { font-size: 9px; font-weight: 700; letter-spacing: 1.5px; padding: 4px 10px; text-transform: uppercase; }
.bdg.green  { background: #0d2b1a; color: #2dd87a; border: 1px solid #2dd87a; }
.bdg.red    { background: #2b0d12; color: #ff4560; border: 1px solid #ff4560; }
.bdg.orange { background: #2b1a0d; color: #ff6b00; border: 1px solid #ff6b00; }

/* ── Metric grid ── */
.mgrid {
    display: grid; grid-template-columns: repeat(5, 1fr);
    gap: 1px; background: #2a2d35;
    border: 1px solid #2a2d35; margin: 0 0 14px;
}
.mcell { background: #161920; padding: 12px 16px; }
.mlabel { font-size: 9px; color: #6b7080; letter-spacing: 1.5px; text-transform: uppercase; }
.mval { font-size: 22px; font-weight: 700; margin-top: 4px; }
.msub { font-size: 10px; color: #6b7080; margin-top: 2px; }
.cw { color: #ffffff !important; }
.cg { color: #2dd87a !important; }
.cr { color: #ff4560 !important; }
.co { color: #ff6b00 !important; }

/* ── Progress bar ── */
.pbar-wrap { margin: 0 0 14px; }
.pbar-track { height: 6px; background: #1e2028; position: relative; border-radius: 2px; }
.pbar-fill { position: absolute; height: 6px; border-radius: 2px; top: 0; left: 0; }
.pbar-labels { display: flex; justify-content: space-between; font-size: 9px; color: #6b7080; margin-top: 5px; letter-spacing: .5px; }

/* ── TWAP panels ── */
.tpanels { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: #2a2d35; }
.tpanel { background: #13161d; padding: 16px 18px; }
.tptitle { font-size: 9px; font-weight: 700; letter-spacing: 2px; color: #ff6b00; text-transform: uppercase; margin-bottom: 12px; }
.trow { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #1e2028; font-size: 12px; }
.trow:last-child { border-bottom: none; margin-top: 4px; padding-top: 10px; }
.tkey { color: #8890a0; }
.tval { color: #e8eaf0; font-weight: 500; }
.tval.big { font-size: 20px; font-weight: 700; }

/* ── Por Asignar highlight ── */
.por-asignar-box {
    display: flex; justify-content: space-between; align-items: center;
    background: #1a1d24; border: 1px solid #2a2d35;
    padding: 10px 16px; margin-top: 1px;
}
.pa-label { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; color: #c8cad4; text-transform: uppercase; }
.pa-val { font-size: 24px; font-weight: 700; }

/* ── Dashboard table ── */
.dbtable { width: 100%; border-collapse: collapse; font-size: 12px; }
.dbtable thead th {
    padding: 9px 14px; font-size: 9px; letter-spacing: 1.5px;
    color: #ff6b00; font-weight: 700; text-transform: uppercase;
    border-bottom: 1px solid #ff6b00; background: #13161d;
    text-align: right; white-space: nowrap;
}
.dbtable thead th.tl { text-align: left; }
.dbtable tbody tr { border-bottom: 1px solid #1e2028; }
.dbtable tbody tr:hover td { background: #161920; }
.dbtable tbody td { padding: 9px 14px; color: #c8cad4; text-align: right; white-space: nowrap; }
.dbtable tbody td.tl { text-align: left; color: #ffffff; font-weight: 600; }
.dbtable tfoot td { padding: 9px 14px; border-top: 1px solid #ff6b00; text-align: right; font-weight: 700; font-size: 14px; }

/* ── KPI strip ── */
.kstrip { display: grid; grid-template-columns: repeat(4,1fr); gap: 1px; background: #2a2d35; border: 1px solid #2a2d35; margin-bottom: 24px; }
.kcell { background: #161920; padding: 18px 20px; text-align: center; }
.klabel { font-size: 9px; color: #6b7080; letter-spacing: 1.5px; text-transform: uppercase; }
.kval { font-size: 34px; font-weight: 700; margin-top: 6px; }

/* ── Streamlit inputs ── */
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input {
    background: #1a1d24 !important; border: 1px solid #2a2d35 !important;
    color: #e8eaf0 !important; border-radius: 2px !important;
    font-family: 'IBM Plex Mono', monospace !important; font-size: 13px !important;
}
div[data-testid="stNumberInput"] label,
div[data-testid="stTextInput"]  label,
div[data-testid="stTimeInput"]  label,
div[data-testid="stSelectbox"]  label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important; color: #8890a0 !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
}
div[data-testid="stSelectbox"] > div > div {
    background: #1a1d24 !important; border: 1px solid #2a2d35 !important;
    color: #e8eaf0 !important; border-radius: 2px !important;
}
.stButton > button {
    background: #1a1d24 !important; border: 1px solid #2a2d35 !important;
    color: #8890a0 !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important; letter-spacing: 1px !important;
    text-transform: uppercase !important; border-radius: 2px !important;
    padding: 8px 14px !important;
}
.stButton > button:hover {
    border-color: #ff6b00 !important; color: #ff6b00 !important;
    background: #1f1610 !important;
}
.stDownloadButton > button {
    background: #1f1610 !important; border: 1px solid #ff6b00 !important;
    color: #ff6b00 !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important; letter-spacing: 1px !important; border-radius: 2px !important;
}
[data-testid="stSidebar"] label { color: #8890a0 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Load data ────────────────────────────────────────────────────────────────
emisoras = load_emisoras()

# ─── TOP BAR ─────────────────────────────────────────────────────────────────
ahora_real = datetime.now()
st.markdown(f"""
<div class='topbar'>
  <span>▸ TWAP MONITOR — MESA DE CAPITALES</span>
  <span>{ahora_real.strftime('%d/%m/%Y  %H:%M:%S')}</span>
</div>""", unsafe_allow_html=True)

# ─── Auto-refresh every 30 seconds ───────────────────────────────────────────
st.markdown("""
<script>
setTimeout(function(){ window.location.reload(); }, 30000);
</script>""", unsafe_allow_html=True)

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### TWAP Monitor")
    st.caption("Mesa de Capitales")
    st.divider()

    # Hora de referencia — por defecto usa la hora real
    usar_hora_real = st.checkbox("Usar hora actual del sistema", value=True)
    if usar_hora_real:
        ahora = ahora_real
        st.caption(f"⏱ {ahora.strftime('%H:%M:%S')}")
    else:
        hora_ref  = st.time_input("Hora de referencia", value=ahora_real.time(), step=1)
        fecha_ref = st.date_input("Fecha", value=ahora_real.date())
        ahora = datetime.combine(fecha_ref, hora_ref)

    st.divider()
    st.markdown("**NUEVA EMISORA**")

    with st.form("add_form", clear_on_submit=True):
        nn = st.text_input("Ticker",    placeholder="AMXL")
        nf = st.text_input("Fondo",     placeholder="FONDO A")
        nt = st.selectbox("Operación",  ["COMPRA", "VENTA"])
        nho = st.time_input("Hora Orden", value=time(9, 30),  step=60)
        nhm = st.time_input("Hora Meta",  value=time(14, 0), step=60)
        nv  = st.number_input("Vol. Original",  min_value=1,     value=10000, step=100)
        na  = st.number_input("Asignado",       min_value=0,     value=0,     step=100)
        nmp = st.number_input("Mins x Periodo", min_value=1,     value=10,    step=1)

        if st.form_submit_button("▸ AGREGAR", use_container_width=True) and nn:
            emisoras.append({
                "nombre":      nn.upper().strip(),
                "fondo":       nf.upper().strip() or "—",
                "tipo":        nt,
                "hora_orden":  time_to_str(nho),
                "hora_meta":   time_to_str(nhm),
                "vol_original": int(nv),
                "asignado":     int(na),
                "mins_periodo": int(nmp),
            })
            save_emisoras(emisoras)
            st.rerun()


# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["  TWAP MONITOR  ", "  DASHBOARD  ", "  CONFIRMACIÓN  "])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — TWAP MONITOR
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if not emisoras:
        st.info("Sin emisoras. Agrega una desde la barra lateral.")

    for idx, e in enumerate(emisoras):
        r = calc_twap(e, ahora)
        lbl, cls = badge(r["por_asignar_min"])

        pct_t = min(r["pct_tiempo"] * 100, 100)
        pct_a = min(r["pct_asig"]   * 100, 100)
        bar_hex = {"green": "#2dd87a", "red": "#ff4560", "orange": "#ff6b00"}[cls]

        # Color de "Por Asignar"
        def pa_color(val):
            if val > 200:  return "#ff4560"
            if val < -200: return "#2dd87a"
            return "#ff6b00"

        cm = pa_color(r["por_asignar_min"])
        cp = pa_color(r["por_asignar_per"])

        sign_m = "+" if r["por_asignar_min"] >= 0 else ""
        sign_p = "+" if r["por_asignar_per"] >= 0 else ""

        st.markdown(f"""
        <div class='card {cls}'>
          <div class='card-head'>
            <div>
              <div class='card-title'>{e['nombre']}</div>
              <div class='card-sub'>
                {e['fondo']} &nbsp;·&nbsp; {e['tipo']}
                &nbsp;·&nbsp; {e['hora_orden'][:5]} → {e['hora_meta'][:5]}
                &nbsp;·&nbsp; {e['mins_periodo']} min/periodo
              </div>
            </div>
            <span class='bdg {cls}'>{lbl}</span>
          </div>

          <div class='mgrid'>
            <div class='mcell'>
              <div class='mlabel'>Vol. Original</div>
              <div class='mval cw'>{e['vol_original']:,}</div>
              <div class='msub'>títulos</div>
            </div>
            <div class='mcell'>
              <div class='mlabel'>Asignado</div>
              <div class='mval' style='color:{bar_hex};'>{e['asignado']:,}</div>
              <div class='msub'>{pct_a:.1f}% del total</div>
            </div>
            <div class='mcell'>
              <div class='mlabel'>TWAP Esperado</div>
              <div class='mval cw'>{r['twap_min']:,.0f}</div>
              <div class='msub'>deberías llevar</div>
            </div>
            <div class='mcell'>
              <div class='mlabel'>Tiempo Trans.</div>
              <div class='mval cw'>{pct_t:.1f}%</div>
              <div class='msub'>{r['c12']} / {r['mins_total']:.0f} min</div>
            </div>
            <div class='mcell'>
              <div class='mlabel'>Por Asignar</div>
              <div class='mval' style='color:{cm};'>{sign_m}{r['por_asignar_min']:,.0f}</div>
              <div class='msub'>x minutos</div>
            </div>
          </div>

          <div class='pbar-wrap'>
            <div class='pbar-track'>
              <div class='pbar-fill' style='width:{pct_t:.2f}%;background:#2a2d35;'></div>
              <div class='pbar-fill' style='width:{pct_a:.2f}%;background:{bar_hex};opacity:.8;'></div>
            </div>
            <div class='pbar-labels'>
              <span>⬜ TIEMPO TRANSCURRIDO {pct_t:.1f}%</span>
              <span style='color:{bar_hex};'>■ ASIGNADO {pct_a:.1f}%</span>
            </div>
          </div>

          <div class='tpanels'>
            <div class='tpanel'>
              <div class='tptitle'>⏱ TWAP x Minutos</div>
              <div class='trow'><span class='tkey'>Mins totales (C10)</span><span class='tval'>{r['mins_total']:.2f}</span></div>
              <div class='trow'><span class='tkey'>Mins transcurridos (C12)</span><span class='tval'>{r['c12']}</span></div>
              <div class='trow'><span class='tkey'>TWAP esperado (C13)</span><span class='tval'>{r['twap_min']:,.2f}</span></div>
              <div class='trow'><span class='tkey'>Asignado (C14)</span><span class='tval'>{e['asignado']:,}</span></div>
              <div class='trow'>
                <span class='tkey' style='color:#e8eaf0;font-weight:700;'>POR ASIGNAR (C15)</span>
                <span class='tval big' style='color:{cm};'>{sign_m}{r['por_asignar_min']:,.0f}</span>
              </div>
            </div>
            <div class='tpanel'>
              <div class='tptitle'>📦 TWAP x Periodos ({e['mins_periodo']} min)</div>
              <div class='trow'><span class='tkey'>Total periodos (F14)</span><span class='tval'>{r['total_periodos']:.2f}</span></div>
              <div class='trow'><span class='tkey'>Vol por periodo (F15)</span><span class='tval'>{r['vol_por_periodo']:,.2f}</span></div>
              <div class='trow'><span class='tkey'>Periodos trans. ROUNDUP (F16)</span><span class='tval'>{r['periodos_trans']}</span></div>
              <div class='trow'><span class='tkey'>TWAP esperado (F17)</span><span class='tval'>{r['twap_per']:,.2f}</span></div>
              <div class='trow'><span class='tkey'>Asignado en periodos (F19)</span><span class='tval'>{r['asig_en_periodos']:.2f}</span></div>
              <div class='trow'>
                <span class='tkey' style='color:#e8eaf0;font-weight:700;'>POR ASIGNAR (F20)</span>
                <span class='tval big' style='color:{cp};'>{sign_p}{r['por_asignar_per']:,.0f}</span>
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Actualizar Asignado ──────────────────────────────────────────────
        col_inp, col_btn = st.columns([5, 1])
        with col_inp:
            new_asig = st.number_input(
                f"ACTUALIZAR ASIGNADO — {e['nombre']}",
                min_value=0, max_value=e["vol_original"],
                value=e["asignado"], step=100, key=f"asig_{idx}"
            )
        with col_btn:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("GUARDAR", key=f"save_{idx}"):
                emisoras[idx]["asignado"] = int(new_asig)
                save_emisoras(emisoras)
                st.rerun()
            if st.button("✕ BORRAR", key=f"del_{idx}"):
                emisoras.pop(idx)
                save_emisoras(emisoras)
                st.rerun()

        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    if not emisoras:
        st.info("Sin emisoras cargadas.")
    else:
        rows = []
        for e in emisoras:
            r   = calc_twap(e, ahora)
            lbl, cls = badge(r["por_asignar_min"])
            rows.append({**e, **r, "lbl": lbl, "cls": cls})

        adel = sum(1 for x in rows if x["cls"] == "green")
        atra = sum(1 for x in rows if x["cls"] == "red")
        onli = sum(1 for x in rows if x["cls"] == "orange")

        st.markdown(f"""
        <div class='kstrip'>
          <div class='kcell'><div class='klabel'>Emisoras activas</div><div class='kval cw'>{len(rows)}</div></div>
          <div class='kcell'><div class='klabel'>Adelantadas</div><div class='kval cg'>{adel}</div></div>
          <div class='kcell'><div class='klabel'>Atrasadas</div><div class='kval cr'>{atra}</div></div>
          <div class='kcell'><div class='klabel'>En línea</div><div class='kval co'>{onli}</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<div class='slabel'>Resumen de posiciones</div>", unsafe_allow_html=True)

        tbody = ""
        for r in rows:
            bar_hex = {"green": "#2dd87a", "red": "#ff4560", "orange": "#ff6b00"}[r["cls"]]
            pct_a = min(r["pct_asig"]   * 100, 100)
            pct_t = min(r["pct_tiempo"] * 100, 100)
            sm = "+" if r["por_asignar_min"] >= 0 else ""
            sp = "+" if r["por_asignar_per"] >= 0 else ""
            cm = "#ff4560" if r["por_asignar_min"] > 200 else ("#2dd87a" if r["por_asignar_min"] < -200 else "#ff6b00")
            cp = "#ff4560" if r["por_asignar_per"] > 200 else ("#2dd87a" if r["por_asignar_per"] < -200 else "#ff6b00")
            bar = f"""<div style='background:#1e2028;height:4px;position:relative;border-radius:2px;'>
              <div style='position:absolute;height:4px;background:#2a2d35;width:{pct_t:.1f}%;border-radius:2px;'></div>
              <div style='position:absolute;height:4px;background:{bar_hex};width:{pct_a:.1f}%;border-radius:2px;opacity:.85;'></div>
            </div>
            <div style='display:flex;justify-content:space-between;font-size:9px;color:#4a4d55;margin-top:3px;'>
              <span>T:{pct_t:.0f}%</span><span style='color:{bar_hex};'>A:{pct_a:.0f}%</span></div>"""
            tbody += f"""<tr>
              <td class='tl'>{r['nombre']}</td>
              <td class='tl' style='color:#8890a0;font-weight:400;'>{r['fondo']}</td>
              <td class='tl' style='color:#8890a0;font-weight:400;'>{r['tipo']}</td>
              <td>{r['vol_original']:,}</td>
              <td style='color:#fff;'>{r['asignado']:,}</td>
              <td>{r['twap_min']:,.0f}</td>
              <td style='min-width:110px;'>{bar}</td>
              <td style='color:{cm};font-weight:700;'>{sm}{r['por_asignar_min']:,.0f}</td>
              <td style='color:{cp};font-weight:700;'>{sp}{r['por_asignar_per']:,.0f}</td>
              <td><span class='bdg {r["cls"]}'>{r['lbl']}</span></td>
            </tr>"""

        st.markdown(f"""
        <table class='dbtable'>
          <thead><tr>
            <th class='tl'>TICKER</th><th class='tl'>FONDO</th><th class='tl'>OP</th>
            <th>VOL ORIG</th><th>ASIGNADO</th><th>TWAP ESPERADO</th>
            <th>PROGRESO</th>
            <th>POR ASIG (MIN)</th><th>POR ASIG (PER)</th><th>ESTADO</th>
          </tr></thead>
          <tbody>{tbody}</tbody>
        </table>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CONFIRMACIÓN
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    if not emisoras:
        st.info("Sin emisoras cargadas.")
    else:
        st.markdown("<div class='slabel'>Precios de ejecución</div>", unsafe_allow_html=True)

        precios = {}
        cols = st.columns(min(len(emisoras), 5))
        for i, e in enumerate(emisoras):
            with cols[i % 5]:
                precios[e["nombre"]] = st.number_input(
                    e["nombre"], min_value=0.0, value=0.0,
                    step=0.01, format="%.4f", key=f"px_{i}"
                )

        st.markdown("<div class='slabel'>Tabla de confirmación</div>", unsafe_allow_html=True)

        conf_rows = ""
        total_noc = 0.0
        for e in emisoras:
            px  = precios.get(e["nombre"], 0.0)
            noc = e["asignado"] * px
            total_noc += noc
            op_c = "#2dd87a" if e["tipo"] == "COMPRA" else "#ff4560"
            conf_rows += f"""<tr>
              <td class='tl'>{e['fondo']}</td>
              <td class='tl' style='color:{op_c};font-weight:700;'>{e['tipo']}</td>
              <td>{e['nombre']}</td>
              <td>{e['asignado']:,}</td>
              <td>{px:,.4f}</td>
              <td style='color:#ff6b00;font-weight:700;'>${noc:,.2f}</td>
            </tr>"""

        st.markdown(f"""
        <table class='dbtable'>
          <thead><tr>
            <th class='tl'>FONDO</th><th class='tl'>OPERACIÓN</th>
            <th>EMISORA</th><th>TÍTULOS</th><th>PRECIO</th><th>NOCIONAL</th>
          </tr></thead>
          <tbody>{conf_rows}</tbody>
          <tfoot><tr>
            <td colspan='5' style='text-align:right;color:#6b7080;font-size:9px;letter-spacing:1px;'>TOTAL NOCIONAL</td>
            <td style='color:#ff6b00;'>${total_noc:,.2f}</td>
          </tr></tfoot>
        </table>""", unsafe_allow_html=True)

        st.markdown("<div class='slabel'>Formato Bloomberg — copiar y pegar</div>", unsafe_allow_html=True)
        st.info(
            "Selecciona todo → **Ctrl+A** → **Ctrl+C** → pega en **Bloomberg MSG** o **Excel**. "
            "Los tabuladores hacen que se formatee automáticamente como tabla.",
            icon="ℹ️"
        )

        # Tab-separated → Bloomberg MSG / Excel pega como tabla nativa
        header = "\t".join(["FONDO", "OPERACIÓN", "EMISORA", "TÍTULOS", "PRECIO", "NOCIONAL"])
        data_lines = []
        for e in emisoras:
            px  = precios.get(e["nombre"], 0.0)
            noc = e["asignado"] * px
            data_lines.append("\t".join([
                e["fondo"], e["tipo"], e["nombre"],
                f"{e['asignado']:,}", f"{px:.4f}", f"{noc:.2f}"
            ]))
        footer_line = "\t".join(["", "", "", "", "TOTAL", f"{total_noc:.2f}"])
        tsv = "\n".join([header] + data_lines + [footer_line])

        st.code(tsv, language=None)

        st.download_button(
            "⬇  DESCARGAR .TSV",
            data=tsv.encode("utf-8"),
            file_name=f"confirmacion_{ahora.strftime('%Y%m%d_%H%M')}.tsv",
            mime="text/tab-separated-values",
        )
