"""
pages/4_Market_Overview.py
ภาพรวมตลาดหุ้นโลก — ดัชนีหลัก, VIX, YTD Chart
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf

from src.data_pipeline import load_prices, get_current_price
from src.storage import save_market_snapshot, snowflake_status

st.set_page_config(page_title="Market Overview", page_icon="🌍", layout="wide")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  [data-testid="metric-container"] {
    background: #111827; border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 14px 18px;
  }
  [data-testid="metric-container"] label { color: #64748b !important; font-size: 0.72rem !important; text-transform: uppercase; }
  [data-testid="stMetricValue"] { font-family: 'Space Mono', monospace !important; color: #e2e8f0 !important; }
  .section-header { font-size:0.7rem;font-weight:600;color:#00D4FF;text-transform:uppercase;
    letter-spacing:0.12em;margin:20px 0 10px;border-bottom:1px solid rgba(0,212,255,0.2);padding-bottom:6px; }
  .ai-card { background:linear-gradient(135deg,#0f0f1a,#111827);
    border:1px solid rgba(124,58,237,0.3);border-radius:12px;padding:18px;border-left:3px solid #7C3AED; }
  .index-card { background:#111827;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px; }
  [data-testid="stSidebar"] { background: #0d1117 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🌍 Market Overview")
st.caption("ภาพรวมตลาดหุ้นโลก — อัปเดตล่าสุดจาก Yahoo Finance")

# ── ดัชนีหลัก ──────────────────────────────────────────────────────────────────
INDICES = {
    "^GSPC":  {"name": "S&P 500",    "desc": "หุ้นใหญ่ 500 ตัวสหรัฐ"},
    "^IXIC":  {"name": "Nasdaq",     "desc": "หุ้น Tech สหรัฐ"},
    "^DJI":   {"name": "Dow Jones",  "desc": "หุ้นอุตสาหกรรม 30 ตัว"},
    "^VIX":   {"name": "VIX",        "desc": "ดัชนีความกลัวตลาด"},
}



# ── Load index data ────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def load_index_data():
    result = {}
    for ticker, meta in INDICES.items():
        try:
            t    = yf.Ticker(ticker)
            fast = t.fast_info
            info = t.info
            price     = fast.last_price or 0
            prev      = fast.previous_close or price
            chg_pct   = ((price - prev) / prev * 100) if prev else 0
            result[ticker] = {
                "name":     meta["name"],
                "desc":     meta["desc"],
                "price":    round(price, 2),
                "chg_pct":  round(chg_pct, 2),
            }
        except Exception:
            result[ticker] = {"name": meta["name"], "desc": meta["desc"],
                              "price": 0, "chg_pct": 0}
    return result



@st.cache_data(ttl=1800, show_spinner=False)
def load_index_chart():
    """ดึงกราฟ YTD ของดัชนีหลัก"""
    tickers = ["^GSPC", "^IXIC", "^DJI"]
    frames  = {}
    for t in tickers:
        try:
            df = yf.Ticker(t).history(period="ytd")
            if not df.empty:
                df.index = df.index.tz_localize(None) if df.index.tz is None else df.index.tz_convert(None)
                frames[INDICES[t]["name"]] = df["Close"]
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames)

with st.spinner("กำลังดึงข้อมูลตลาด..."):
    index_data = load_index_data()

# Auto-save รายวัน — บันทึกแค่ครั้งแรกของวัน
from datetime import date
today_str = date.today().isoformat()
if st.session_state.get("market_saved_date") != today_str:
    saved = save_market_snapshot(index_data)
    if saved:
        st.session_state["market_saved_date"] = today_str

# ── Section 1: ดัชนีหลัก ────────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 ดัชนีตลาดหลัก</div>', unsafe_allow_html=True)
cols = st.columns(4)
for i, (ticker, data) in enumerate(index_data.items()):
    chg   = data["chg_pct"]
    color = "normal" if chg >= 0 else "inverse"
    arrow = "▲" if chg >= 0 else "▼"
    with cols[i]:
        st.metric(
            label=f"{data['name']}",
            value=f"{data['price']:,.2f}",  # metric value auto-sized
            delta=f"{chg:+.2f}%",
            delta_color=color,
        )
        st.markdown(f'<div style="color:#64748b;font-size:0.82rem;margin-top:2px;">{data["desc"]}</div>', unsafe_allow_html=True)

st.divider()

# ── Section 2: VIX Gauge ──────────────────────────────────────────────────────
left_col, right_col = st.columns([1, 2], gap="large")

with left_col:
    st.markdown('<div class="section-header">😨 VIX — ดัชนีความกลัวตลาด</div>', unsafe_allow_html=True)
    vix_val = index_data.get("^VIX", {}).get("price", 0)

    if vix_val < 20:
        vix_label = "ตลาดสงบ 😌"
        vix_color = "#34d399"
        vix_bg    = "#064e3b"
    elif vix_val < 30:
        vix_label = "ระวัง ⚠️"
        vix_color = "#f59e0b"
        vix_bg    = "#451a03"
    else:
        vix_label = "ตลาดกลัวมาก 😱"
        vix_color = "#f87171"
        vix_bg    = "#450a0a"

    st.markdown(f"""
    <div style="background:{vix_bg};border:1px solid {vix_color}44;border-radius:14px;
                padding:20px;text-align:center;margin-bottom:12px;">
      <div style="font-family:'Space Mono',monospace;font-size:3rem;font-weight:700;
                  color:{vix_color};">{vix_val:.1f}</div>
      <div style="color:{vix_color};font-size:1.05rem;font-weight:600;margin-top:6px;">
        {vix_label}
      </div>
    </div>
    <div style="display:flex;gap:0;border-radius:8px;overflow:hidden;height:10px;margin-bottom:8px;">
      <div style="flex:2;background:#34d399;"></div>
      <div style="flex:1;background:#f59e0b;"></div>
      <div style="flex:1;background:#f87171;"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:#475569;">
      <span>0 สงบ</span><span>20</span><span>30</span><span>40+ กลัวมาก</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#111827;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:12px;margin-top:8px;">
      <div style="font-size:0.88rem;color:#94a3b8;line-height:1.7;">
        <div>🟢 <strong>ต่ำกว่า 20</strong> — นักลงทุนมั่นใจ ตลาดสงบ</div>
        <div>🟡 <strong>20–30</strong> — เริ่มมีความกังวล ควรระวัง</div>
        <div>🔴 <strong>สูงกว่า 30</strong> — ตลาดกลัวมาก มักเป็นจุดซื้อที่ดี</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="section-header">📈 YTD Performance (Normalized)</div>', unsafe_allow_html=True)
    with st.spinner("โหลดกราฟ..."):
        chart_df = load_index_chart()

    if not chart_df.empty:
        colors_chart = {"S&P 500": "#00D4FF", "Nasdaq": "#7C3AED", "Dow Jones": "#f59e0b"}
        # Checkboxes เลือกดัชนี
        available = list(chart_df.columns)
        cb_cols   = st.columns(len(available))
        selected_indices = []
        for i, name in enumerate(available):
            with cb_cols[i]:
                if st.checkbox(name, value=True, key=f"idx_{name}"):
                    selected_indices.append(name)

        if selected_indices:
            fig = go.Figure()
            for col in selected_indices:
                norm = chart_df[col] / chart_df[col].iloc[0] * 100
                fig.add_trace(go.Scatter(
                    x=chart_df.index, y=norm, name=col,
                    line=dict(color=colors_chart.get(col,"#94a3b8"), width=2),
                    hovertemplate=f"{col}: %{{y:.1f}}<extra></extra>",
                ))
            fig.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.2)")
            fig.update_layout(
                height=300, margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                           color="#475569", title="Indexed (Base=100)"),
                xaxis=dict(showgrid=False, color="#475569"),
                legend=dict(font=dict(color="#94a3b8",size=12), orientation="h", y=1.08))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("เลือกอย่างน้อย 1 ดัชนีครับ")
    else:
        st.info("ไม่สามารถดึงข้อมูลกราฟได้")
