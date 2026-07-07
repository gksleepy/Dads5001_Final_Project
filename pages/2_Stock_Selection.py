"""
pages/1_Stock_Selection.py
เลือกหุ้น + บันทึก Watchlist ลง MongoDB + แสดง snapshot
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime as dt

from src.config import SUPPORTED_TICKERS, DEFAULT_TICKERS, PALETTE, DEFAULT_PALETTE_COLOR
from src.data_pipeline import load_prices, duckdb_price_summary, get_current_price
from src.storage import save_watchlist, load_watchlist, mongo_status

# 3 สีตัดกันชัดเจน สำหรับหุ้นตัวที่ 1, 2, 3
CHART_COLORS = ["#00D4FF", "#76b900", "#f87171"]

st.set_page_config(page_title="Stock Selection", page_icon="🎯", layout="wide")

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
  [data-testid="stSidebar"] { background: #0d1117 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🎯 เลือกหุ้น")
st.caption("เลือกหุ้นสูงสุด 3 ตัวสำหรับการวิเคราะห์ — ระบบจะดึงข้อมูลจริงจาก Yahoo Finance")

# ── Session init ───────────────────────────────────────────────────────────────
# โหลด watchlist จาก MongoDB ครั้งแรกเท่านั้น
if "selected_tickers" not in st.session_state:
    saved = load_watchlist()
    st.session_state["selected_tickers"] = saved if saved else DEFAULT_TICKERS.copy()

# ── Select ─────────────────────────────────────────────────────────────────────
# วิธีที่ถูกต้อง: sync _ticker_select กับ selected_tickers ก่อน render widget
# เพื่อไม่ให้ default= reset ค่าที่ user เลือกไว้
if "_ticker_select" not in st.session_state:
    st.session_state["_ticker_select"] = st.session_state["selected_tickers"]

def on_ticker_change():
    """เรียกตอน user เปลี่ยนการเลือก — save ลง selected_tickers ทันที"""
    val = st.session_state.get("_ticker_select", [])
    st.session_state["selected_tickers"] = val if val else DEFAULT_TICKERS.copy()

st.multiselect(
    "หุ้นที่ต้องการวิเคราะห์ (สูงสุด 3 ตัว)",
    options=SUPPORTED_TICKERS,
    max_selections=3,
    key="_ticker_select",
    on_change=on_ticker_change,
)

selected = st.session_state["_ticker_select"]
if not selected:
    selected = st.session_state["selected_tickers"]
if not selected:
    selected = DEFAULT_TICKERS.copy()
    st.session_state["selected_tickers"] = selected
    st.session_state["_ticker_select"]   = selected

# ── Save to MongoDB ────────────────────────────────────────────────────────────
col_save, col_status = st.columns([1, 3])
with col_save:
    if st.button("💾 บันทึก Watchlist → MongoDB", width='stretch', type="primary"):
        msg = save_watchlist(selected)
        st.success(msg)
with col_status:
    st.markdown(f'<div style="padding-top:8px;color:#64748b;font-size:0.82rem;">{mongo_status()}</div>',
                unsafe_allow_html=True)

st.divider()

# ── Load data ──────────────────────────────────────────────────────────────────
with st.spinner("กำลังดึงข้อมูลจาก Yahoo Finance..."):
    prices  = load_prices(tuple(selected))
    summary = duckdb_price_summary(prices)

if prices.empty:
    st.error("❌ ไม่สามารถดึงข้อมูลได้ กรุณาตรวจสอบ internet connection")
    st.stop()

# ── Current Price Cards ────────────────────────────────────────────────────────
st.markdown('<div class="section-header">💲 ราคาปัจจุบัน</div>', unsafe_allow_html=True)
cols = st.columns(len(selected))
for i, ticker in enumerate(selected):
    info = get_current_price(ticker)
    chg  = info["change_pct"]
    with cols[i]:
        st.metric(
            label=ticker,
            value=f"${info['price']:,.2f}",
            delta=f"{chg:+.2f}%",
            delta_color="normal" if chg >= 0 else "inverse",
        )

st.divider()

# ── DuckDB Summary Table ───────────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 สรุปข้อมูล </div>', unsafe_allow_html=True)
if not summary.empty:
    disp = summary[[
        "ticker","latest_close",
        "return_1m","return_3m","return_6m","return_1y",
        "volatility","avg_volume","latest_volume"
    ]].copy()
    disp.columns = [
        "Ticker","Latest Close ($)",
        "Return 1M%","Return 3M%","Return 6M%","Return 1Y%",
        "Volatility%","Avg Volume","Latest Volume"
    ]
    disp["Latest Close ($)"] = disp["Latest Close ($)"].map(lambda x: f"${x:,.2f}")
    disp["Avg Volume"]       = disp["Avg Volume"].map(lambda x: f"{int(x):,}")
    disp["Latest Volume"]    = disp["Latest Volume"].map(lambda x: f"{int(x):,}")
    st.dataframe(disp, width='stretch', hide_index=True)

# ── Price Chart ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📈 กราฟราคาย้อนหลัง (Normalized Base=100)</div>', unsafe_allow_html=True)

ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1.5, 1.5, 1, 1])
with ctrl1:
    chart_date_from = st.date_input(
        "ตั้งแต่", value=dt.date.today() - dt.timedelta(days=365),
        max_value=dt.date.today(), key="chart_date_from",
    )
with ctrl2:
    chart_date_to = st.date_input(
        "ถึง", value=dt.date.today(),
        max_value=dt.date.today(), key="chart_date_to",
    )
with ctrl3:
    show_ma20 = st.checkbox("MA20", value=False, key="chart_ma20")
with ctrl4:
    show_ma50 = st.checkbox("MA50", value=False, key="chart_ma50")

if chart_date_from > chart_date_to:
    st.error("❌ วันเริ่มต้นต้องไม่เกินวันสิ้นสุด")
else:
    fig = go.Figure()
    for i, ticker in enumerate(selected):
        df = prices[prices["ticker"] == ticker].sort_values("date").copy()
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        df = df[
            (df["date"] >= pd.Timestamp(chart_date_from)) &
            (df["date"] <= pd.Timestamp(chart_date_to))
        ]
        if df.empty:
            continue

        base  = df["close"].iloc[0]
        color = CHART_COLORS[i % len(CHART_COLORS)]

        fig.add_trace(go.Scatter(
            x=df["date"], y=df["close"] / base * 100,
            name=ticker, line=dict(color=color, width=2),
            hovertemplate=f"{ticker}: %{{y:.1f}}<extra></extra>",
        ))

        if show_ma20:
            ma20 = df["close"].rolling(20, min_periods=5).mean()
            fig.add_trace(go.Scatter(
                x=df["date"], y=ma20 / base * 100,
                name=f"{ticker} MA20",
                line=dict(color=color, width=1.2, dash="dot"),
                opacity=0.6,
                hovertemplate=f"{ticker} MA20: %{{y:.1f}}<extra></extra>",
            ))

        if show_ma50:
            ma50 = df["close"].rolling(50, min_periods=10).mean()
            fig.add_trace(go.Scatter(
                x=df["date"], y=ma50 / base * 100,
                name=f"{ticker} MA50",
                line=dict(color=color, width=1.2, dash="dash"),
                opacity=0.6,
                hovertemplate=f"{ticker} MA50: %{{y:.1f}}<extra></extra>",
            ))

    fig.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.2)")
    fig.update_layout(
        height=380, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#475569", title="Indexed (Base=100)"),
        xaxis=dict(showgrid=False, color="#475569"),
        legend=dict(font=dict(color="#94a3b8", size=11), orientation="h", y=1.08),
    )
    st.plotly_chart(fig, width='stretch')

# ── Historical Data ────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📋 Historical Data</div>', unsafe_allow_html=True)
st.caption("เลือกดูข้อมูลราคาย้อนหลังทีละหุ้น")

col_hist_sym, col_date_from, col_date_to = st.columns([2, 1, 1])
with col_hist_sym:
    hist_ticker = st.selectbox(
        "เลือกหุ้นที่ต้องการดู",
        options=selected,
        key="hist_ticker_select",
    )
with col_date_from:
    date_from = st.date_input(
        "ตั้งแต่",
        value=dt.date.today() - dt.timedelta(days=365),
        max_value=dt.date.today(),
        key="hist_date_from",
    )
with col_date_to:
    date_to = st.date_input(
        "ถึง",
        value=dt.date.today(),
        max_value=dt.date.today(),
        key="hist_date_to",
    )

if date_from > date_to:
    st.error("❌ วันเริ่มต้นต้องไม่เกินวันสิ้นสุด")
    st.stop()

df_all  = prices[prices["ticker"] == hist_ticker].copy()
df_all["date"] = pd.to_datetime(df_all["date"]).dt.normalize()

today_utc = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)
df_hist = df_all[
    (df_all["date"] >= pd.Timestamp(date_from)) &
    (df_all["date"] <= min(pd.Timestamp(date_to), today_utc - pd.Timedelta(days=1)))
].sort_values("date", ascending=False)

if not df_hist.empty:
    latest_close  = df_hist["close"].dropna().iloc[0]
    oldest_close  = df_hist["close"].dropna().iloc[-1]
    period_return = (latest_close / oldest_close - 1) * 100
    avg_volume    = df_hist["volume"].mean()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ราคาล่าสุด",     f"${latest_close:,.2f}")
    m2.metric("ราคาต้นช่วง",    f"${oldest_close:,.2f}")
    m3.metric("Return ช่วงนี้", f"{period_return:+.2f}%",
              delta_color="normal" if period_return >= 0 else "inverse")
    m4.metric("Avg Volume",      f"{avg_volume:,.0f}")

    df_display = df_hist[["date","open","high","low","close","volume"]].copy()
    df_display.columns = ["Date","Open ($)","High ($)","Low ($)","Close ($)","Volume"]
    df_display["Date"]      = pd.to_datetime(df_display["Date"]).dt.strftime("%Y-%m-%d")
    df_display["Open ($)"]  = df_display["Open ($)"].map(lambda x: f"${x:,.2f}")
    df_display["High ($)"]  = df_display["High ($)"].map(lambda x: f"${x:,.2f}")
    df_display["Low ($)"]   = df_display["Low ($)"].map(lambda x: f"${x:,.2f}")
    df_display["Close ($)"] = df_display["Close ($)"].map(lambda x: f"${x:,.2f}")
    df_display["Volume"]    = df_display["Volume"].map(lambda x: f"{int(x):,}")

    st.markdown(
        f'<div style="color:#94a3b8;font-size:0.82rem;margin-bottom:6px;">'
        f'แสดง <strong style="color:#e2e8f0;">{len(df_display)} วัน</strong> '
        f'({date_from.strftime("%d %b %Y")} — {date_to.strftime("%d %b %Y")}) — {hist_ticker}'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(df_display, width='stretch', hide_index=True, height=320)

    csv = df_hist[["date","open","high","low","close","volume"]].to_csv(index=False)
    st.download_button(
        label=f"⬇️ Download {hist_ticker} CSV",
        data=csv,
        file_name=f"{hist_ticker}_{date_from}_{date_to}.csv",
        mime="text/csv",
    )
else:
    st.info(f"ไม่มีข้อมูล {hist_ticker} ในช่วงวันที่ที่เลือก")

st.divider()
