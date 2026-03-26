"""
TWAP Monitor — Mesa de Capitales
Fórmulas EXACTAS del Excel (verificadas):
  C10 = (hora_meta - hora_orden) * 1440             -> Mins totales
  C11 = NOW() - hora_orden                          -> Tiempo transcurrido
  C12 = HOUR(C11)*60 + MINUTE(C11)                  -> Mins transcurridos (int)
  C13 = vol_original / C10 * C12                     -> TWAP esperado
  C15 = C13 - asignado                              -> Por Asignar
  F5  = mins_periodo                                 -> input
  F14 = C10 / F5                                     -> Total periodos
  F15 = vol_original / F14                           -> Vol por periodo
  F16 = ROUNDUP(C12 / F5, 0)                        -> Periodos transcurridos
  F17 = F16 * F15                                    -> TWAP periodos
  F18 = asignado                                     -> Asignado
  F19 = F18 / F15                                    -> Asignado en periodos
  F20 = F17 - F18                                    -> Por Asignar periodos
"""

import streamlit as st
from datetime import datetime, time, date, timedelta, timezone
import math, json, os

# ── Zona horaria CDMX (UTC-6, sin DST desde 2023) ─────────────────────────
CDMX_TZ = timezone(timedelta(hours=-6))
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "twap_data.json")

st.set_page_config(
    page_title="TWAP Monitor",
    page_icon="▸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════════════════════
# FIX 1: PERSISTENCIA — Guardar/Cargar de archivo JSON
# ════════════════════════════════════════════════════════════════════════════
DEFAULTS = [{
    "nombre": "VOLARA",
    "tipo": "COMPRA",
    "fondo": "FONDO A",
    "hora_orden": "11:35:59",
    "hora_meta": "13:55:00",
    "vol_original": 50550,
    "asignado": 39700,
    "mins_periodo": 10,
}]

def _load_from_disk():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def _save_to_disk(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_emisoras():
    if "emisoras" not in st.session_state:
        disk = _load_from_disk()
        st.session_state.emisoras = disk if disk is not None else json.loads(json.dumps(DEFAULTS))
    return st.session_state.emisoras

def save_emisoras(data):
    st.session_state.emisoras = data
    _save_to_disk(data)

# ════════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ════════════════════════════════════════════════════════════════════════════
def parse_time(s: str) -> time:
    parts = s.split(":")
    return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)

def fmt_time(t: time) -> str:
    return t.strftime("%H:%M:%S")

def now_cdmx() -> datetime:
    return datetime.now(CDMX_TZ).replace(tzinfo=None)

def calc_twap(e: dict, ahora: datetime) -> dict:
    """Replica EXACTA de las fórmulas del Excel."""
    ho = datetime.combine(ahora.date(), parse_time(e["hora_orden"]))
    hm = datetime.combine(ahora.date(), parse_time(e["hora_meta"]))
    if hm <= ho:
        hm += timedelta(days=1)

    vol  = float(e["vol_original"])
    asig = float(e["asignado"])
    mp   = int(e["mins_periodo"])

    # C9:  Tiempo Total = hora_meta - hora_orden
    tiempo_total_sec = (hm - ho).total_seconds()
    # C10: Mins = (hora_meta - hora_orden) * 1440
    c10 = tiempo_total_sec / 60.0

    # C11: Tiempo Transcurrido = NOW() - hora_orden
    c11_sec = (ahora - ho).total_seconds()

    # CLAMP: si aún no empieza o ya terminó
    if c11_sec < 0:
        c11_sec = 0.0
    elif c11_sec > tiempo_total_sec:
        c11_sec = tiempo_total_sec

    # C12: = HOUR(C11)*60 + MINUTE(C11)   (Excel trunca segundos)
    c11_hours = int(c11_sec // 3600)
    c11_mins  = int((c11_sec % 3600) // 60)
    c12 = c11_hours * 60 + c11_mins

    # C13: TWAP = vol / C10 * C12
    c13 = (vol / c10 * c12) if c10 > 0 else 0.0
    c13 = min(c13, vol)  # CAP

    # C15: Por Asignar = C13 - Asignado
    c15 = c13 - asig

    # ── Periodos ──
    f14 = c10 / mp if mp > 0 else 0.0
    f15 = vol / f14 if f14 > 0 else 0.0
    f16 = math.ceil(c12 / mp) if (mp > 0 and c12 > 0) else 0
    f17 = min(f16 * f15, vol)  # CAP
    f18 = asig
    f19 = f18 / f15 if f15 > 0 else 0.0
    f20 = f17 - f18

    pct_tiempo = c12 / c10 if c10 > 0 else 0.0
    pct_asig   = asig / vol if vol > 0 else 0.0

    def sec_to_hms(s):
        s = int(abs(s))
        return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

    return dict(
        c10=c10, c12=c12, c13=c13, c15=c15,
        f14=f14, f15=f15, f16=f16, f17=f17, f18=f18, f19=f19, f20=f20,
        pct_tiempo=pct_tiempo, pct_asig=pct_asig,
        tiempo_total_hms=sec_to_hms(tiempo_total_sec),
        tiempo_trans_hms=sec_to_hms(c11_sec),
        mins_total=c10, twap_min=c13, por_asignar_min=c15,
        total_periodos=f14, vol_por_periodo=f15,
        periodos_trans=f16, twap_per=f17,
        asig_en_periodos=f19, por_asignar_per=f20,
    )

def get_status(v: float):
    if v < -200: return "ADELANTADO", "green"
    if v >  200: return "ATRASADO",   "red"
    return "EN LINEA", "yellow"

def signed(v):
    return f"+{v:,.0f}" if v >= 0 else f"{v:,.0f}"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --bg:     #0e1015;
  --bg1:    #14171f;
  --bg2:    #1c2030;
  --bg3:    #252a3a;
  --bdr:    #2e3348;
  --text:   #eef0f8;
  --muted:  #7b85a0;
  --acc:    #f97316;
  --grn:    #22c55e;
  --red:    #ef4444;
  --yel:    #eab308;
}

*, *::before, *::after { box-sizing: border-box; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Space Grotesk', sans-serif !important;
}

[data-testid="stSidebar"] {
  background: var(--bg1) !important;
  border-right: 1px solid var(--bdr) !important;
  min-width: 340px !important;
  width: 340px !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
  min-width: 340px !important; width: 340px !important;
  margin-left: 0 !important; transform: none !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1rem !important; }
[data-testid="stSidebar"] * { font-family: 'Space Grotesk', sans-serif !important; }
#MainMenu, footer, header, [data-testid="stDecoration"] { display: none !important; }

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div { color: var(--text) !important; }
[data-testid="stSidebar"] label {
  font-size: 11px !important; font-weight: 700 !important;
  text-transform: uppercase !important; letter-spacing: .5px !important;
  color: var(--muted) !important;
}
[data-testid="stSidebar"] input {
  background: var(--bg2) !important; border: 1px solid var(--bdr) !important;
  color: var(--text) !important; border-radius: 8px !important; font-size: 15px !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
  background: var(--bg2) !important; border: 1px solid var(--bdr) !important;
  color: var(--text) !important; border-radius: 8px !important;
}

button[data-baseweb="tab"] {
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: 14px !important; font-weight: 600 !important;
  color: var(--muted) !important; background: transparent !important;
  border: none !important; padding: 12px 24px !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--acc) !important;
  border-bottom: 2px solid var(--acc) !important;
}

/* Expander styling for collapsible cards */
[data-testid="stExpander"] {
  background: var(--bg1) !important;
  border: 1px solid var(--bdr) !important;
  border-radius: 18px !important;
  margin-bottom: 16px !important;
  overflow: hidden !important;
}
[data-testid="stExpander"] details {
  border: none !important;
}
[data-testid="stExpander"] summary {
  padding: 18px 24px !important;
  font-family: 'Space Grotesk', sans-serif !important;
}
[data-testid="stExpander"] summary span p {
  font-size: 15px !important; font-weight: 700 !important;
  color: var(--text) !important;
}
[data-testid="stExpander"] > div > div {
  padding: 0 24px 24px !important;
}

div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input {
  background: var(--bg2) !important; border: 1px solid var(--bdr) !important;
  color: var(--text) !important; border-radius: 10px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 18px !important; font-weight: 600 !important; padding: 12px 16px !important;
}
div[data-testid="stNumberInput"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stTimeInput"] label,
div[data-testid="stSelectbox"] label {
  font-size: 11px !important; font-weight: 700 !important;
  letter-spacing: .5px !important; text-transform: uppercase !important;
  color: var(--muted) !important;
}

.stButton > button {
  background: var(--bg2) !important; border: 1px solid var(--bdr) !important;
  color: var(--text) !important; font-family: 'Space Grotesk', sans-serif !important;
  font-size: 14px !important; font-weight: 600 !important;
  border-radius: 10px !important; padding: 10px 20px !important;
  transition: all .15s ease !important;
}
.stButton > button:hover {
  border-color: var(--acc) !important; color: var(--acc) !important;
  background: rgba(249,115,22,.08) !important;
}
.stDownloadButton > button {
  background: rgba(249,115,22,.1) !important; border: 1px solid var(--acc) !important;
  color: var(--acc) !important; font-size: 14px !important; font-weight: 600 !important;
  border-radius: 10px !important; font-family: 'Space Grotesk', sans-serif !important;
}

.ph {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 0 24px; border-bottom: 1px solid var(--bdr); margin-bottom: 28px;
}
.ph-title { font-size: 26px; font-weight: 700; color: var(--text); letter-spacing: -.3px; }
.ph-title em { color: var(--acc); font-style: normal; }
.ph-clock {
  font-family: 'JetBrains Mono', monospace;
  font-size: 20px; font-weight: 700; color: var(--acc);
  background: var(--bg2); border: 1px solid var(--bdr);
  padding: 10px 20px; border-radius: 10px; letter-spacing: 2px;
}

.ec-head { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 24px; }
.ec-meta { font-size: 14px; color: var(--muted); margin-top: 2px; font-weight: 500; }

.bdg { font-size: 12px; font-weight: 700; letter-spacing: .5px; padding: 7px 16px; border-radius: 8px; text-transform: uppercase; display: inline-block; }
.bdg.green  { background: rgba(34,197,94,.12);  color: var(--grn); border: 1px solid rgba(34,197,94,.35); }
.bdg.red    { background: rgba(239,68,68,.12);   color: var(--red); border: 1px solid rgba(239,68,68,.35); }
.bdg.yellow { background: rgba(234,179,8,.12);   color: var(--yel); border: 1px solid rgba(234,179,8,.35); }

.mrow { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 24px; }
.mc { background: var(--bg2); border: 1px solid var(--bdr); border-radius: 14px; padding: 18px 20px; }
.mc-lbl { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: var(--muted); }
.mc-val { font-size: 28px; font-weight: 700; margin-top: 8px; line-height: 1; color: var(--text); font-family: 'JetBrains Mono', monospace; }
.mc-sub { font-size: 12px; color: var(--muted); margin-top: 6px; }
.cw { color: #ffffff !important; }
.cg { color: var(--grn) !important; }
.cr { color: var(--red) !important; }
.cy { color: var(--yel) !important; }
.ca { color: var(--acc) !important; }

.pbar { margin-bottom: 24px; }
.pbar-track { height: 10px; background: var(--bg3); border-radius: 999px; position: relative; overflow: hidden; }
.pbar-t { position: absolute; height: 10px; top: 0; left: 0; border-radius: 999px; background: var(--bg3); }
.pbar-a { position: absolute; height: 10px; top: 0; left: 0; border-radius: 999px; opacity: .9; }
.pbar-lbl { display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; color: var(--muted); margin-top: 8px; }

/* Excel table */
.xtbl { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; border: 1px solid var(--bdr); border-radius: 12px; overflow: hidden; margin-bottom: 16px; }
.xtbl caption { caption-side: top; text-align: left; font-size: 11px; font-weight: 700; letter-spacing: 1px; color: var(--acc); text-transform: uppercase; padding: 0 0 10px 4px; }
.xtbl th { padding: 10px 14px; font-size: 11px; font-weight: 700; letter-spacing: .5px; color: var(--muted); text-transform: uppercase; background: var(--bg2); border-bottom: 1px solid var(--bdr); text-align: left; white-space: nowrap; }
.xtbl td { padding: 10px 14px; color: var(--text); border-bottom: 1px solid var(--bg3); white-space: nowrap; }
.xtbl tr:last-child td { border-bottom: none; }
.xtbl .xref { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); font-weight: 600; }
.xtbl .xval { font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 600; color: var(--text); text-align: right; }
.xtbl .xbig { font-size: 18px; font-weight: 700; }
.xtbl .xform { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #7b85a0; }
.xtbl tr.xhigh td { background: rgba(249,115,22,.06); border-top: 1px solid var(--bdr); }

.tpanels { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

.kstrip { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 28px; }
.kc { background: var(--bg1); border: 1px solid var(--bdr); border-radius: 16px; padding: 22px 24px; text-align: center; }
.kc-lbl { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: var(--muted); }
.kc-val { font-size: 48px; font-weight: 700; margin-top: 8px; font-family: 'JetBrains Mono', monospace; }

.dtbl { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 14px; border: 1px solid var(--bdr); border-radius: 14px; overflow: hidden; }
.dtbl thead th { padding: 14px 18px; font-size: 11px; font-weight: 700; letter-spacing: .5px; color: var(--muted); text-transform: uppercase; background: var(--bg2); border-bottom: 1px solid var(--bdr); text-align: right; white-space: nowrap; }
.dtbl thead th.tl { text-align: left; }
.dtbl tbody tr:hover td { background: var(--bg2); }
.dtbl tbody td { padding: 14px 18px; color: var(--text); text-align: right; border-bottom: 1px solid var(--bg3); white-space: nowrap; }
.dtbl tbody td.tl { text-align: left; font-weight: 700; }
.dtbl tbody tr:last-child td { border-bottom: none; }
.dtbl tfoot td { padding: 14px 18px; text-align: right; font-weight: 700; font-size: 16px; border-top: 1px solid var(--bdr); background: var(--bg2); }

.inp-label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: var(--muted); margin-bottom: 6px; }
.inp-hint { color: var(--acc); font-weight: 400; font-size: 11px; }

[data-testid="stInfo"] { font-size: 14px !important; border-radius: 12px !important; }
pre, code { font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Load data ────────────────────────────────────────────────────────────────
emisoras = load_emisoras()
ahora_real = now_cdmx()

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='font-size:22px;font-weight:700;color:var(--text);padding:4px 0 2px;'>
      ▸ TWAP <span style='color:#f97316;'>Monitor</span>
    </div>
    <div style='font-size:13px;color:#7b85a0;margin-bottom:20px;'>Mesa de Capitales</div>
    """, unsafe_allow_html=True)

    st.divider()

    usar_hora_real = st.checkbox("⏱ Usar hora del sistema (CDMX)", value=True)
    if usar_hora_real:
        ahora = ahora_real
    else:
        col_h, col_f = st.columns(2)
        with col_h:
            hora_ref = st.time_input("Hora", value=ahora_real.time(), step=60)
        with col_f:
            fecha_ref = st.date_input("Fecha", value=ahora_real.date(), label_visibility="collapsed")
        ahora = datetime.combine(fecha_ref, hora_ref)

    st.markdown(f"""
    <div id='sidebar-clock' style='font-family:JetBrains Mono,monospace;font-size:24px;font-weight:700;
        color:#f97316;background:#1c2030;border:1px solid #2e3348;
        border-radius:10px;padding:10px 16px;text-align:center;margin:8px 0;
        letter-spacing:2px;'>
      {ahora.strftime('%H:%M:%S')}
    </div>
    <div style='text-align:center;font-size:13px;color:#7b85a0;margin-bottom:4px;'>
      {ahora.strftime('%d/%m/%Y')} · CDMX (UTC-6)
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("<div style='font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#7b85a0;margin-bottom:12px;'>➕ Nueva Emisora</div>", unsafe_allow_html=True)

    with st.form("add_form", clear_on_submit=True):
        nn  = st.text_input("Ticker", placeholder="AMXL")
        nf  = st.text_input("Fondo",  placeholder="FONDO A")
        nt  = st.selectbox("Operación", ["COMPRA", "VENTA"])
        c1, c2 = st.columns(2)
        with c1:
            nho = st.time_input("Hora Orden", value=time(9, 30), step=60)
        with c2:
            nhm = st.time_input("Hora Meta",  value=time(14, 0), step=60)
        nv  = st.number_input("Vol. Original",  min_value=1, value=10000, step=100)
        na  = st.number_input("Asignado",        min_value=0, value=0,    step=100)
        nmp = st.number_input("Mins × Periodo",  min_value=1, value=10,   step=1)

        if st.form_submit_button("➕ Agregar Emisora", use_container_width=True) and nn.strip():
            emisoras.append({
                "nombre":       nn.upper().strip(),
                "fondo":        nf.upper().strip() or "—",
                "tipo":         nt,
                "hora_orden":   fmt_time(nho),
                "hora_meta":    fmt_time(nhm),
                "vol_original": int(nv),
                "asignado":     int(na),
                "mins_periodo": int(nmp),
            })
            save_emisoras(emisoras)
            st.rerun()

    if emisoras:
        st.divider()
        st.markdown("<div style='font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#7b85a0;margin-bottom:8px;'>🗑 Eliminar</div>", unsafe_allow_html=True)
        to_del = st.selectbox("Emisora", [e["nombre"] for e in emisoras], label_visibility="collapsed")
        if st.button("Eliminar seleccionada", use_container_width=True):
            emisoras = [e for e in emisoras if e["nombre"] != to_del]
            save_emisoras(emisoras)
            st.rerun()

# ─── Page header ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class='ph'>
  <div class='ph-title'>TWAP <em>Monitor</em> &nbsp;<span style='font-size:16px;color:#7b85a0;font-weight:500;'>Mesa de Capitales</span></div>
  <div class='ph-clock' id='header-clock'>{ahora.strftime('%H:%M:%S')}</div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# FIX 3: RELOJ EN TIEMPO REAL cada segundo + page refresh cada 60s
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<script>
(function() {
  function getCDMXTime() {
    var now = new Date();
    var utc = now.getTime() + now.getTimezoneOffset() * 60000;
    return new Date(utc - 6 * 3600000);
  }
  function pad(n) { return String(n).padStart(2, '0'); }
  function updateClocks() {
    var cdmx = getCDMXTime();
    var t = pad(cdmx.getHours()) + ':' + pad(cdmx.getMinutes()) + ':' + pad(cdmx.getSeconds());
    var hc = document.getElementById('header-clock');
    if (hc) hc.textContent = t;
    var sc = document.getElementById('sidebar-clock');
    if (sc) sc.textContent = t;
  }
  if (!window._twapClock) {
    window._twapClock = setInterval(updateClocks, 1000);
    updateClocks();
  }
  // Refresh completo cada 60s para recalcular TWAP
  if (!window._twapRefresh) {
    window._twapRefresh = true;
    setTimeout(function(){ window.location.reload(); }, 60000);
  }
})();
</script>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊  MONITOR", "📈  DASHBOARD", "📋  CONFIRMACIÓN"])

color_hex = {"green": "#22c55e", "red": "#ef4444", "yellow": "#eab308"}

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — MONITOR (FIX 2: pestañas colapsables)
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    if not emisoras:
        st.info("Sin emisoras. Agrega una desde el panel izquierdo ← (sidebar).")

    for idx, e in enumerate(emisoras):
        r = calc_twap(e, ahora)
        lbl, cls   = get_status(r["por_asignar_min"])
        _,   clsp  = get_status(r["por_asignar_per"])
        bc  = color_hex[cls]
        bcp = color_hex[clsp]

        pct_t = min(r["pct_tiempo"] * 100, 100)
        pct_a = min(r["pct_asig"]   * 100, 100)
        faltante = e["vol_original"] - e["asignado"]

        tipo_icon = "🟢" if e["tipo"] == "COMPRA" else "🔴"
        status_icon = {"green": "✅", "red": "🔻", "yellow": "🟡"}[cls]

        expander_title = f"{tipo_icon}  **{e['nombre']}**  ·  {e['tipo']}  ·  {lbl}  {status_icon}  ·  Por Asignar: **{signed(r['por_asignar_min'])}**"

        with st.expander(expander_title, expanded=False):
            st.markdown(f"""
            <div class='ec-head'>
              <div>
                <div class='ec-meta'>
                  {e['fondo']} &nbsp;·&nbsp;
                  {e['hora_orden'][:5]} → {e['hora_meta'][:5]}
                  &nbsp;·&nbsp; Periodo {e['mins_periodo']} min
                </div>
              </div>
              <span class='bdg {cls}'>{lbl}</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class='mrow'>
              <div class='mc'><div class='mc-lbl'>Vol. Original</div><div class='mc-val cw'>{e['vol_original']:,}</div><div class='mc-sub'>títulos totales</div></div>
              <div class='mc'><div class='mc-lbl'>Asignado</div><div class='mc-val' style='color:{bc};'>{e['asignado']:,}</div><div class='mc-sub'>{pct_a:.1f}% del total</div></div>
              <div class='mc'><div class='mc-lbl'>TWAP Esperado</div><div class='mc-val ca'>{r['twap_min']:,.0f}</div><div class='mc-sub'>deberías llevar</div></div>
              <div class='mc'><div class='mc-lbl'>Tiempo Trans.</div><div class='mc-val cw'>{pct_t:.1f}%</div><div class='mc-sub'>{r['c12']} / {r['mins_total']:.0f} min</div></div>
              <div class='mc'><div class='mc-lbl'>Sin Asignar</div><div class='mc-val {"cg" if faltante == 0 else "cr"}'>{faltante:,}</div><div class='mc-sub'>títulos restantes</div></div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class='pbar'>
              <div class='pbar-track'>
                <div class='pbar-t' style='width:{pct_t:.2f}%;background:#252a3a;'></div>
                <div class='pbar-a' style='width:{pct_a:.2f}%;background:{bc};'></div>
              </div>
              <div class='pbar-lbl'>
                <span>⬛ Tiempo {pct_t:.1f}%</span>
                <span style='color:{bc};'>● Asignado {pct_a:.1f}%</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ══ FIX 4: TABLAS EXACTAS DEL EXCEL ══
            st.markdown(f"""
            <div class='tpanels'>
              <table class='xtbl'>
                <caption>⏱ TWAP × MINUTOS</caption>
                <thead><tr><th>Celda</th><th>Concepto</th><th>Fórmula Excel</th><th style='text-align:right;'>Valor</th></tr></thead>
                <tbody>
                  <tr><td class='xref'>B5</td><td>Emisora</td><td class='xform'></td><td class='xval'>{e['nombre']}</td></tr>
                  <tr><td class='xref'>C6</td><td>Hora Orden</td><td class='xform'></td><td class='xval'>{e['hora_orden']}</td></tr>
                  <tr><td class='xref'>C7</td><td>Vol. Original</td><td class='xform'></td><td class='xval'>{e['vol_original']:,}</td></tr>
                  <tr><td class='xref'>C8</td><td>Hora Meta</td><td class='xform'></td><td class='xval'>{e['hora_meta']}</td></tr>
                  <tr><td class='xref'>C9</td><td>Tiempo Total</td><td class='xform'>=C8-C6</td><td class='xval'>{r['tiempo_total_hms']}</td></tr>
                  <tr><td class='xref'>C10</td><td>Mins</td><td class='xform'>=(C8-C6)*1440</td><td class='xval'>{r['c10']:.4f}</td></tr>
                  <tr><td class='xref'>C11</td><td>Tiempo Trans.</td><td class='xform'>=NOW()-C6</td><td class='xval'>{r['tiempo_trans_hms']}</td></tr>
                  <tr><td class='xref'>C12</td><td>Mins</td><td class='xform'>=HOUR(C11)*60+MIN(C11)</td><td class='xval'>{r['c12']}</td></tr>
                  <tr><td class='xref'>C13</td><td>TWAP</td><td class='xform'>=C7/C10*C12</td><td class='xval' style='color:var(--acc);'>{r['c13']:,.2f}</td></tr>
                  <tr><td class='xref'>C14</td><td>Asignado</td><td class='xform'></td><td class='xval'>{e['asignado']:,}</td></tr>
                  <tr class='xhigh'><td class='xref'>C15</td><td><b>Por Asignar</b></td><td class='xform'>=C13-C14</td><td class='xval xbig' style='color:{bc};'>{signed(r['c15'])}</td></tr>
                </tbody>
              </table>

              <table class='xtbl'>
                <caption>📦 TWAP × PERIODOS — {e['mins_periodo']} min</caption>
                <thead><tr><th>Celda</th><th>Concepto</th><th>Fórmula Excel</th><th style='text-align:right;'>Valor</th></tr></thead>
                <tbody>
                  <tr><td class='xref'>F5</td><td>Mins × Periodo</td><td class='xform'></td><td class='xval'>{e['mins_periodo']}</td></tr>
                  <tr><td class='xref'>F7</td><td>Hora Orden</td><td class='xform'>=C6</td><td class='xval'>{e['hora_orden']}</td></tr>
                  <tr><td class='xref'>F8</td><td>Vol. Original</td><td class='xform'>=C7</td><td class='xval'>{e['vol_original']:,}</td></tr>
                  <tr><td class='xref'>F9</td><td>Hora Meta</td><td class='xform'>=C8</td><td class='xval'>{e['hora_meta']}</td></tr>
                  <tr><td class='xref'>F10</td><td>Tiempo Total</td><td class='xform'>=F9-F7</td><td class='xval'>{r['tiempo_total_hms']}</td></tr>
                  <tr><td class='xref'>F11</td><td>Mins</td><td class='xform'>=(F9-F7)*1440</td><td class='xval'>{r['c10']:.4f}</td></tr>
                  <tr><td class='xref'>F12</td><td>Tiempo Trans.</td><td class='xform'>=NOW()-F7</td><td class='xval'>{r['tiempo_trans_hms']}</td></tr>
                  <tr><td class='xref'>F13</td><td>Mins</td><td class='xform'>=HOUR(F12)*60+MIN(F12)</td><td class='xval'>{r['c12']}</td></tr>
                  <tr><td class='xref'>F14</td><td>Total Periodos</td><td class='xform'>=F11/F5</td><td class='xval'>{r['f14']:.4f}</td></tr>
                  <tr><td class='xref'>F15</td><td>Vol por Periodo</td><td class='xform'>=F8/F14</td><td class='xval'>{r['f15']:,.2f}</td></tr>
                  <tr><td class='xref'>F16</td><td>Transcurridos</td><td class='xform'>=ROUNDUP(F13/F5,0)</td><td class='xval'>{r['f16']}</td></tr>
                  <tr><td class='xref'>F17</td><td>TWAP</td><td class='xform'>=F16*F15</td><td class='xval' style='color:var(--acc);'>{r['f17']:,.2f}</td></tr>
                  <tr><td class='xref'>F18</td><td>Asignado</td><td class='xform'>=C14</td><td class='xval'>{e['asignado']:,}</td></tr>
                  <tr><td class='xref'>F19</td><td>(en periodos)</td><td class='xform'>=F18/F15</td><td class='xval'>{r['f19']:.4f}</td></tr>
                  <tr class='xhigh'><td class='xref'>F20</td><td><b>Por Asignar</b></td><td class='xform'>=F17-F18</td><td class='xval xbig' style='color:{bcp};'>{signed(r['f20'])}</td></tr>
                </tbody>
              </table>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class='inp-label'>
              ✏️ Actualizar Asignado — {e['nombre']}
              <span class='inp-hint'>&nbsp; Presiona Enter para guardar</span>
            </div>
            """, unsafe_allow_html=True)

            def make_cb(i):
                def _cb():
                    emisoras[i]["asignado"] = int(st.session_state[f"ai_{i}"])
                    save_emisoras(emisoras)
                return _cb

            st.number_input(
                f"_asig_{idx}",
                min_value=0,
                max_value=e["vol_original"],
                value=e["asignado"],
                step=100,
                key=f"ai_{idx}",
                on_change=make_cb(idx),
                label_visibility="collapsed",
            )


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    if not emisoras:
        st.info("Sin emisoras cargadas.")
    else:
        rows = []
        for e in emisoras:
            r = calc_twap(e, ahora)
            lbl, cls = get_status(r["por_asignar_min"])
            rows.append({**e, **r, "lbl": lbl, "cls": cls})

        adel = sum(1 for x in rows if x["cls"] == "green")
        atra = sum(1 for x in rows if x["cls"] == "red")
        onli = sum(1 for x in rows if x["cls"] == "yellow")

        st.markdown(f"""
        <div class='kstrip'>
          <div class='kc'><div class='kc-lbl'>Emisoras Activas</div><div class='kc-val cw'>{len(rows)}</div></div>
          <div class='kc'><div class='kc-lbl'>Adelantadas</div><div class='kc-val cg'>{adel}</div></div>
          <div class='kc'><div class='kc-lbl'>Atrasadas</div><div class='kc-val cr'>{atra}</div></div>
          <div class='kc'><div class='kc-lbl'>En Línea</div><div class='kc-val cy'>{onli}</div></div>
        </div>
        """, unsafe_allow_html=True)

        tbody = ""
        for r in rows:
            bc  = color_hex[r["cls"]]
            _, clsp = get_status(r["por_asignar_per"])
            bcp = color_hex[clsp]
            pct_a = min(r["pct_asig"] * 100, 100)
            pct_t = min(r["pct_tiempo"] * 100, 100)
            sm = "+" if r["por_asignar_min"] >= 0 else ""
            sp = "+" if r["por_asignar_per"] >= 0 else ""

            bar = f"""
            <div style='background:#252a3a;height:7px;border-radius:999px;position:relative;min-width:100px;'>
              <div style='position:absolute;height:7px;border-radius:999px;background:#2e3348;width:{pct_t:.1f}%;'></div>
              <div style='position:absolute;height:7px;border-radius:999px;background:{bc};width:{pct_a:.1f}%;opacity:.9;'></div>
            </div>
            <div style='display:flex;justify-content:space-between;font-size:11px;color:#7b85a0;margin-top:4px;font-weight:600;'>
              <span>T:{pct_t:.0f}%</span><span style='color:{bc};'>A:{pct_a:.0f}%</span>
            </div>"""

            tbody += f"""<tr>
              <td class='tl' style='font-size:16px;'>{r['nombre']}</td>
              <td class='tl' style='font-weight:500;color:#7b85a0;'>{r['fondo']}</td>
              <td class='tl' style='font-weight:700;color:{"#22c55e" if r["tipo"]=="COMPRA" else "#ef4444"};'>{r['tipo']}</td>
              <td style='font-family:JetBrains Mono,monospace;'>{r['vol_original']:,}</td>
              <td style='font-family:JetBrains Mono,monospace;font-weight:700;color:#fff;'>{r['asignado']:,}</td>
              <td style='font-family:JetBrains Mono,monospace;color:#f97316;'>{r['twap_min']:,.0f}</td>
              <td style='min-width:130px;'>{bar}</td>
              <td style='font-family:JetBrains Mono,monospace;font-weight:700;color:{bc};font-size:16px;'>{sm}{r['por_asignar_min']:,.0f}</td>
              <td style='font-family:JetBrains Mono,monospace;font-weight:700;color:{bcp};font-size:16px;'>{sp}{r['por_asignar_per']:,.0f}</td>
              <td><span class='bdg {r["cls"]}'>{r['lbl']}</span></td>
            </tr>"""

        st.markdown(f"""
        <table class='dtbl'>
          <thead><tr>
            <th class='tl'>TICKER</th><th class='tl'>FONDO</th><th class='tl'>OP</th>
            <th>VOL ORIG</th><th>ASIGNADO</th><th>TWAP ESPERADO</th>
            <th>PROGRESO</th><th>POR ASIG (MIN)</th><th>POR ASIG (PER)</th><th>ESTADO</th>
          </tr></thead>
          <tbody>{tbody}</tbody>
        </table>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — CONFIRMACIÓN
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    if not emisoras:
        st.info("Sin emisoras cargadas.")
    else:
        st.markdown("<div style='font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#7b85a0;margin-bottom:16px;'>Precios de Ejecución</div>", unsafe_allow_html=True)

        precios = {}
        cols = st.columns(min(len(emisoras), 5))
        for i, e in enumerate(emisoras):
            with cols[i % 5]:
                precios[e["nombre"]] = st.number_input(
                    e["nombre"], min_value=0.0, value=0.0,
                    step=0.01, format="%.4f", key=f"px_{i}"
                )

        st.markdown("<div style='font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#7b85a0;margin:28px 0 16px;'>Tabla de Confirmación</div>", unsafe_allow_html=True)

        conf_rows = ""
        total_noc = 0.0
        for e in emisoras:
            px  = precios.get(e["nombre"], 0.0)
            noc = e["asignado"] * px
            total_noc += noc
            opc = "#22c55e" if e["tipo"] == "COMPRA" else "#ef4444"
            conf_rows += f"""<tr>
              <td class='tl'>{e['fondo']}</td>
              <td class='tl' style='color:{opc};font-weight:700;'>{e['tipo']}</td>
              <td style='font-family:JetBrains Mono,monospace;font-weight:700;'>{e['nombre']}</td>
              <td style='font-family:JetBrains Mono,monospace;'>{e['asignado']:,}</td>
              <td style='font-family:JetBrains Mono,monospace;'>{px:,.4f}</td>
              <td style='font-family:JetBrains Mono,monospace;color:#f97316;font-weight:700;'>${noc:,.2f}</td>
            </tr>"""

        st.markdown(f"""
        <table class='dtbl'>
          <thead><tr>
            <th class='tl'>FONDO</th><th class='tl'>OPERACIÓN</th>
            <th>EMISORA</th><th>TÍTULOS</th><th>PRECIO</th><th>NOCIONAL</th>
          </tr></thead>
          <tbody>{conf_rows}</tbody>
          <tfoot><tr>
            <td colspan='5' style='text-align:right;color:#7b85a0;font-size:13px;letter-spacing:.5px;'>TOTAL NOCIONAL</td>
            <td style='color:#f97316;font-family:JetBrains Mono,monospace;'>${total_noc:,.2f}</td>
          </tr></tfoot>
        </table>
        """, unsafe_allow_html=True)

        st.markdown("<div style='font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#7b85a0;margin:28px 0 10px;'>Formato Bloomberg (Tab-separated)</div>", unsafe_allow_html=True)
        st.info("Selecciona todo → **Ctrl+A** → **Ctrl+C** → pega en **Bloomberg MSG** o **Excel**.", icon="ℹ️")

        header_tsv = "\t".join(["FONDO", "OPERACION", "EMISORA", "TITULOS", "PRECIO", "NOCIONAL"])
        lines = []
        for e in emisoras:
            px  = precios.get(e["nombre"], 0.0)
            noc = e["asignado"] * px
            lines.append("\t".join([e["fondo"], e["tipo"], e["nombre"], f"{e['asignado']:,}", f"{px:.4f}", f"{noc:.2f}"]))
        tsv = "\n".join([header_tsv] + lines + ["\t".join(["","","","","TOTAL",f"{total_noc:.2f}"])])

        st.code(tsv, language=None)
        st.download_button("⬇  Descargar .TSV (Excel / Bloomberg)",
            data=tsv.encode("utf-8"),
            file_name=f"confirmacion_{ahora.strftime('%Y%m%d_%H%M')}.tsv",
            mime="text/tab-separated-values")
