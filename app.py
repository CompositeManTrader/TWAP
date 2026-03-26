"""
TWAP Monitor — Mesa de Capitales
Fórmulas exactas del Excel:
  C10 = (hora_meta - hora_orden) * 1440
  C12 = HOUR(NOW-hora_orden)*60 + MINUTE(...)   -> int
  C13 = vol_original / C10 * C12               -> TWAP esperado
  C15 = C13 - asignado                         -> Por Asignar (neg=adelantado)
  F14 = C10 / mins_periodo
  F15 = vol_original / F14
  F16 = ROUNDUP(C12 / mins_periodo, 0)
  F17 = F16 * F15
  F20 = F17 - asignado
"""

import streamlit as st
from datetime import datetime, time, date, timedelta
import math, json

st.set_page_config(
    page_title="TWAP Monitor",
    page_icon="▸",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

def load_emisoras():
    if "emisoras" not in st.session_state:
        st.session_state.emisoras = json.loads(json.dumps(DEFAULTS))
    return st.session_state.emisoras

def save_emisoras(data):
    st.session_state.emisoras = data

def parse_time(s: str) -> time:
    parts = s.split(":")
    return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)

def fmt_time(t: time) -> str:
    return t.strftime("%H:%M:%S")

def calc_twap(e: dict, ahora: datetime) -> dict:
    ho = datetime.combine(ahora.date(), parse_time(e["hora_orden"]))
    hm = datetime.combine(ahora.date(), parse_time(e["hora_meta"]))
    if hm <= ho:
        hm += timedelta(days=1)
    vol  = float(e["vol_original"])
    asig = float(e["asignado"])
    mp   = int(e["mins_periodo"])
    mins_total = (hm - ho).total_seconds() / 60.0
    diff_s = max(0.0, min((ahora - ho).total_seconds(), mins_total * 60))
    total_sec = int(diff_s)
    c12 = (total_sec // 3600) * 60 + (total_sec % 3600) // 60
    twap_min = (vol / mins_total * c12) if mins_total > 0 else 0.0
    por_asignar_min = twap_min - asig
    total_periodos   = mins_total / mp if mp > 0 else 0.0
    vol_por_periodo  = vol / total_periodos if total_periodos > 0 else 0.0
    periodos_trans   = math.ceil(c12 / mp) if (mp > 0 and c12 > 0) else 0
    twap_per         = periodos_trans * vol_por_periodo
    asig_en_periodos = asig / vol_por_periodo if vol_por_periodo > 0 else 0.0
    por_asignar_per  = twap_per - asig
    pct_tiempo = c12 / mins_total if mins_total > 0 else 0.0
    pct_asig   = asig / vol if vol > 0 else 0.0
    return dict(
        mins_total=mins_total, c12=c12,
        pct_tiempo=pct_tiempo, pct_asig=pct_asig,
        twap_min=twap_min, por_asignar_min=por_asignar_min,
        total_periodos=total_periodos, vol_por_periodo=vol_por_periodo,
        periodos_trans=periodos_trans, twap_per=twap_per,
        asig_en_periodos=asig_en_periodos, por_asignar_per=por_asignar_per,
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
}
[data-testid="stSidebar"] * {
  font-family: 'Space Grotesk', sans-serif !important;
}
#MainMenu, footer, header, [data-testid="stDecoration"] { display: none !important; }

/* Sidebar text colors fix */
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

/* Tabs */
[data-testid="stTabs"] { border-bottom: 1px solid var(--bdr) !important; }
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

/* Main inputs */
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

/* Buttons */
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

/* ── Page header ── */
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

/* ── Ticker card ── */
.ecard {
  background: var(--bg1); border: 1px solid var(--bdr);
  border-radius: 18px; padding: 28px 32px; margin-bottom: 24px;
  position: relative; overflow: hidden;
}
.ecard::before {
  content: ''; position: absolute; top: 0; left: 0;
  width: 5px; height: 100%; border-radius: 18px 0 0 18px;
}
.ecard.green::before { background: var(--grn); }
.ecard.red::before   { background: var(--red); }
.ecard.yellow::before { background: var(--yel); }

.ec-head { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 24px; }
.ec-name { font-size: 36px; font-weight: 700; color: #fff; letter-spacing: 2px; }
.ec-meta { font-size: 14px; color: var(--muted); margin-top: 6px; font-weight: 500; }

/* ── Badge ── */
.bdg { font-size: 12px; font-weight: 700; letter-spacing: .5px; padding: 7px 16px; border-radius: 8px; text-transform: uppercase; }
.bdg.green  { background: rgba(34,197,94,.12);  color: var(--grn); border: 1px solid rgba(34,197,94,.35); }
.bdg.red    { background: rgba(239,68,68,.12);   color: var(--red); border: 1px solid rgba(239,68,68,.35); }
.bdg.yellow { background: rgba(234,179,8,.12);   color: var(--yel); border: 1px solid rgba(234,179,8,.35); }

/* ── Metric row ── */
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

/* ── Progress bar ── */
.pbar { margin-bottom: 24px; }
.pbar-track { height: 10px; background: var(--bg3); border-radius: 999px; position: relative; overflow: hidden; }
.pbar-t { position: absolute; height: 10px; top: 0; left: 0; border-radius: 999px; background: var(--bg3); }
.pbar-a { position: absolute; height: 10px; top: 0; left: 0; border-radius: 999px; opacity: .9; }
.pbar-lbl { display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; color: var(--muted); margin-top: 8px; }

/* ── TWAP panels ── */
.tpanels { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.tpanel { background: var(--bg2); border: 1px solid var(--bdr); border-radius: 14px; padding: 22px 24px; }
.tp-title { font-size: 11px; font-weight: 700; letter-spacing: 1px; color: var(--acc); text-transform: uppercase; margin-bottom: 16px; }
.trow { display: flex; justify-content: space-between; align-items: center; padding: 9px 0; border-bottom: 1px solid var(--bg3); }
.trow:last-child { border-bottom: none; padding-top: 14px; margin-top: 6px; }
.tk { font-size: 14px; color: var(--muted); }
.tv { font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 600; color: var(--text); }
.tv.big { font-size: 26px; font-weight: 700; }

/* ── KPI strip ── */
.kstrip { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 28px; }
.kc { background: var(--bg1); border: 1px solid var(--bdr); border-radius: 16px; padding: 22px 24px; text-align: center; }
.kc-lbl { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: var(--muted); }
.kc-val { font-size: 48px; font-weight: 700; margin-top: 8px; font-family: 'JetBrains Mono', monospace; }

/* ── Dashboard table ── */
.dtbl { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 14px; border: 1px solid var(--bdr); border-radius: 14px; overflow: hidden; }
.dtbl thead th { padding: 14px 18px; font-size: 11px; font-weight: 700; letter-spacing: .5px; color: var(--muted); text-transform: uppercase; background: var(--bg2); border-bottom: 1px solid var(--bdr); text-align: right; white-space: nowrap; }
.dtbl thead th.tl { text-align: left; }
.dtbl tbody tr:hover td { background: var(--bg2); }
.dtbl tbody td { padding: 14px 18px; color: var(--text); text-align: right; border-bottom: 1px solid var(--bg3); white-space: nowrap; }
.dtbl tbody td.tl { text-align: left; font-weight: 700; }
.dtbl tbody tr:last-child td { border-bottom: none; }
.dtbl tfoot td { padding: 14px 18px; text-align: right; font-weight: 700; font-size: 16px; border-top: 1px solid var(--bdr); background: var(--bg2); }

/* ── Asignado input label ── */
.inp-label {
  font-size: 12px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .5px; color: var(--muted); margin-bottom: 6px;
}
.inp-hint { color: var(--acc); font-weight: 400; font-size: 11px; }

[data-testid="stInfo"] { font-size: 14px !important; border-radius: 12px !important; }
pre, code { font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Load data ────────────────────────────────────────────────────────────────
emisoras = load_emisoras()
ahora_real = datetime.now()

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='font-size:22px;font-weight:700;color:var(--text);padding:4px 0 2px;'>
      ▸ TWAP <span style='color:#f97316;'>Monitor</span>
    </div>
    <div style='font-size:13px;color:#7b85a0;margin-bottom:20px;'>Mesa de Capitales</div>
    """, unsafe_allow_html=True)

    st.divider()

    usar_hora_real = st.checkbox("⏱ Usar hora del sistema", value=True)
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
    <div style='font-family:JetBrains Mono,monospace;font-size:24px;font-weight:700;
        color:#f97316;background:#1c2030;border:1px solid #2e3348;
        border-radius:10px;padding:10px 16px;text-align:center;margin:8px 0;
        letter-spacing:2px;'>
      {ahora.strftime('%H:%M:%S')}
    </div>
    <div style='text-align:center;font-size:13px;color:#7b85a0;margin-bottom:4px;'>
      {ahora.strftime('%d/%m/%Y')}
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
  <div class='ph-clock'>{ahora.strftime('%H:%M:%S')}</div>
</div>
""", unsafe_allow_html=True)

# Auto-refresh
st.markdown("<script>setTimeout(()=>window.location.reload(),30000);</script>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊  MONITOR", "📈  DASHBOARD", "📋  CONFIRMACIÓN"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — MONITOR
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    if not emisoras:
        st.info("Sin emisoras. Agrega una desde el panel izquierdo.")

    color_hex = {"green": "#22c55e", "red": "#ef4444", "yellow": "#eab308"}

    for idx, e in enumerate(emisoras):
        r = calc_twap(e, ahora)
        lbl, cls   = get_status(r["por_asignar_min"])
        _,   clsp  = get_status(r["por_asignar_per"])
        bc  = color_hex[cls]
        bcp = color_hex[clsp]

        pct_t = min(r["pct_tiempo"] * 100, 100)
        pct_a = min(r["pct_asig"]   * 100, 100)
        faltante = e["vol_original"] - e["asignado"]

        st.markdown(f"""
        <div class='ecard {cls}'>
          <div class='ec-head'>
            <div>
              <div class='ec-name'>{e['nombre']}</div>
              <div class='ec-meta'>
                {e['fondo']} &nbsp;·&nbsp; {e['tipo']}
                &nbsp;·&nbsp; {e['hora_orden'][:5]} → {e['hora_meta'][:5]}
                &nbsp;·&nbsp; Periodo {e['mins_periodo']} min
              </div>
            </div>
            <span class='bdg {cls}'>{lbl}</span>
          </div>

          <div class='mrow'>
            <div class='mc'>
              <div class='mc-lbl'>Vol. Original</div>
              <div class='mc-val cw'>{e['vol_original']:,}</div>
              <div class='mc-sub'>títulos totales</div>
            </div>
            <div class='mc'>
              <div class='mc-lbl'>Asignado</div>
              <div class='mc-val' style='color:{bc};'>{e['asignado']:,}</div>
              <div class='mc-sub'>{pct_a:.1f}% del total</div>
            </div>
            <div class='mc'>
              <div class='mc-lbl'>TWAP Esperado</div>
              <div class='mc-val ca'>{r['twap_min']:,.0f}</div>
              <div class='mc-sub'>deberías llevar</div>
            </div>
            <div class='mc'>
              <div class='mc-lbl'>Tiempo Trans.</div>
              <div class='mc-val cw'>{pct_t:.1f}%</div>
              <div class='mc-sub'>{r['c12']} / {r['mins_total']:.0f} min</div>
            </div>
            <div class='mc'>
              <div class='mc-lbl'>Sin Asignar</div>
              <div class='mc-val {"cg" if faltante == 0 else "cr"}'>{faltante:,}</div>
              <div class='mc-sub'>títulos restantes</div>
            </div>
          </div>

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

          <div class='tpanels'>
            <div class='tpanel'>
              <div class='tp-title'>⏱ TWAP × Minutos</div>
              <div class='trow'><span class='tk'>Mins totales (C10)</span><span class='tv'>{r['mins_total']:.2f}</span></div>
              <div class='trow'><span class='tk'>Mins transcurridos (C12)</span><span class='tv'>{r['c12']}</span></div>
              <div class='trow'><span class='tk'>TWAP esperado (C13)</span><span class='tv'>{r['twap_min']:,.0f}</span></div>
              <div class='trow'><span class='tk'>Asignado (C14)</span><span class='tv'>{e['asignado']:,}</span></div>
              <div class='trow'>
                <span class='tk' style='color:#eef0f8;font-size:16px;font-weight:700;'>Por Asignar (C15)</span>
                <span class='tv big' style='color:{bc};'>{signed(r["por_asignar_min"])}</span>
              </div>
            </div>
            <div class='tpanel'>
              <div class='tp-title'>📦 TWAP × Periodos — {e['mins_periodo']} min</div>
              <div class='trow'><span class='tk'>Total periodos (F14)</span><span class='tv'>{r['total_periodos']:.2f}</span></div>
              <div class='trow'><span class='tk'>Vol por periodo (F15)</span><span class='tv'>{r['vol_por_periodo']:,.0f}</span></div>
              <div class='trow'><span class='tk'>Periodos ROUNDUP (F16)</span><span class='tv'>{r['periodos_trans']}</span></div>
              <div class='trow'><span class='tk'>TWAP esperado (F17)</span><span class='tv'>{r['twap_per']:,.0f}</span></div>
              <div class='trow'><span class='tk'>Asignado en periodos (F19)</span><span class='tv'>{r['asig_en_periodos']:.2f}</span></div>
              <div class='trow'>
                <span class='tk' style='color:#eef0f8;font-size:16px;font-weight:700;'>Por Asignar (F20)</span>
                <span class='tv big' style='color:{bcp};'>{signed(r["por_asignar_per"])}</span>
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Actualizar Asignado — Enter guarda automáticamente ─────────────
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
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


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
        st.info("Selecciona todo → **Ctrl+A** → **Ctrl+C** → pega en **Bloomberg MSG** o **Excel**. Los tabuladores lo convierten en tabla automáticamente.", icon="ℹ️")

        header = "\t".join(["FONDO", "OPERACION", "EMISORA", "TITULOS", "PRECIO", "NOCIONAL"])
        lines = []
        for e in emisoras:
            px  = precios.get(e["nombre"], 0.0)
            noc = e["asignado"] * px
            lines.append("\t".join([e["fondo"], e["tipo"], e["nombre"], f"{e['asignado']:,}", f"{px:.4f}", f"{noc:.2f}"]))
        tsv = "\n".join([header] + lines + ["\t".join(["","","","","TOTAL",f"{total_noc:.2f}"])])

        st.code(tsv, language=None)
        st.download_button("⬇  Descargar .TSV (Excel / Bloomberg)",
            data=tsv.encode("utf-8"),
            file_name=f"confirmacion_{ahora.strftime('%Y%m%d_%H%M')}.tsv",
            mime="text/tab-separated-values")
