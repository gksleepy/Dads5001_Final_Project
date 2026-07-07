"""
pages/3_Dashboard.py
Dashboard — Best Picks + Scoreboard + Price & Return + Risk + Decision Summary
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import DEFAULT_TICKERS, PALETTE, DEFAULT_PALETTE_COLOR

# 3 สีตัดกันชัดเจน เหมือนกับหน้า Stock Selection
CHART_COLORS = ["#00D4FF", "#76b900", "#f87171"]

def get_color(ticker, tickers_list):
    """ดึงสีตาม index ของ ticker ใน list"""
    try:
        idx = list(tickers_list).index(ticker)
        return CHART_COLORS[idx % len(CHART_COLORS)]
    except ValueError:
        return DEFAULT_PALETTE_COLOR
from src.data_pipeline import load_prices, duckdb_price_summary
from src.indicators import add_technical_indicators, latest_technical_scores
from src.storage import snowflake_status

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

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
  .rec-buy  { background:#064e3b;color:#34d399;padding:4px 16px;border-radius:20px;font-weight:700;font-size:0.88rem; }
  .rec-hold { background:#451a03;color:#f59e0b;padding:4px 16px;border-radius:20px;font-weight:700;font-size:0.88rem; }
  .rec-sell { background:#450a0a;color:#f87171;padding:4px 16px;border-radius:20px;font-weight:700;font-size:0.88rem; }
  .decision-card { background:#111827;border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:18px;margin-bottom:8px; }
  [data-testid="stSidebar"] { background: #0d1117 !important; }
</style>
""", unsafe_allow_html=True)

# ── Data ───────────────────────────────────────────────────────────────────────
ai_result = st.session_state.get("ai_result", pd.DataFrame())

st.markdown("## 📊 Stock Analytics Dashboard")

# เลือกหุ้นที่จะดู
all_tickers_db = st.session_state.get("selected_tickers", DEFAULT_TICKERS)
tickers = st.multiselect(
    "เลือกหุ้นที่ต้องการดู",
    options=all_tickers_db,
    default=all_tickers_db,
    key="dashboard_tickers",
)
if not tickers:
    st.warning("กรุณาเลือกหุ้นอย่างน้อย 1 ตัว")
    st.stop()

st.caption(f"เปรียบเทียบ **{', '.join(tickers)}** — ผลตอบแทน, ความเสี่ยง, Technical")

with st.spinner("กำลังโหลดข้อมูล..."):
    prices     = load_prices(tuple(tickers))
    summary    = duckdb_price_summary(prices)
    indicators = add_technical_indicators(prices)
    technical  = latest_technical_scores(indicators)

if prices.empty:
    st.error("❌ ไม่มีข้อมูล — กลับไปหน้า Stock Selection")
    st.stop()

# ── Build scoreboard ───────────────────────────────────────────────────────────
scoreboard = (
    summary[["ticker","latest_close","return_1m","return_3m","return_6m","return_1y","volatility"]]
    .merge(technical[["ticker","technical_score","technical_signal"]], on="ticker", how="left")
)

# Safety guard — ถ้ายังไม่มี AI result
if not ai_result.empty:
    scoreboard = scoreboard.merge(
        ai_result[["ticker","sentiment_label","recommendation","combined_score"]],
        on="ticker", how="left"
    )

if "recommendation" not in scoreboard.columns:
    scoreboard["recommendation"] = "N/A"
if "combined_score" not in scoreboard.columns:
    scoreboard["combined_score"] = None
if "sentiment_label" not in scoreboard.columns:
    scoreboard["sentiment_label"] = "N/A"

scoreboard["recommendation"] = scoreboard["recommendation"].fillna("N/A")
scoreboard["risk_adjusted"]  = (scoreboard["return_3m"] / scoreboard["volatility"].replace(0, np.nan)).round(2)

# ── Best Picks ─────────────────────────────────────────────────────────────────
best_return = scoreboard.sort_values("return_3m", ascending=False).iloc[0]
best_risk   = scoreboard.sort_values("risk_adjusted", ascending=False).iloc[0]
best_tech   = scoreboard.sort_values("technical_score", ascending=False).iloc[0]

st.markdown('<div class="section-header">🏆 Best Picks</div>', unsafe_allow_html=True)
with st.expander("ℹ️ Best Picks คืออะไร?", expanded=False):
    st.markdown("""
    | Best Pick | วัดอะไร | สูตร | ยิ่งสูงยิ่ง |
    |---|---|---|---|
    | 📈 Best Momentum (3M) | ผลตอบแทนใน 3 เดือน | Return 3M% | ✅ ดี |
    | ⚖️ Best Risk-Adjusted | return เทียบกับความเสี่ยง | Return 3M / Volatility | ✅ ดี |
    | 📊 Best Technical Score | สัญญาณ Technical รวม | mean(RSI+MACD+MA score) | ✅ ดี |

    - **Best Momentum** — หุ้นที่ทำผลงานดีที่สุดใน 3 เดือนที่ผ่านมา
    - **Best Risk-Adjusted** — หุ้นที่คุ้มค่าที่สุดเมื่อเทียบกับความเสี่ยง (มาจาก Sharpe Ratio concept)
    - **Best Technical** — หุ้นที่มีสัญญาณ Technical indicator แข็งแกร่งที่สุด
    """)
c1, c2, c3 = st.columns(3)
c1.metric("📈 Best Momentum (3M)",   best_return["ticker"], f"{best_return['return_3m']:+.2f}%")
c2.metric("⚖️ Best Risk-Adjusted",   best_risk["ticker"],   f"{best_risk['risk_adjusted']:.2f}")
c3.metric("📊 Best Technical Score", best_tech["ticker"],   f"{best_tech['technical_score']:.1f}/100")

st.divider()

# ── Scoreboard ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📋 Scoreboard</div>', unsafe_allow_html=True)
has_1y  = "return_1y" in scoreboard.columns
has_ai  = "combined_score" in scoreboard.columns and scoreboard["combined_score"].notna().any()

cols_show = ["ticker","latest_close","return_1m","return_3m","return_6m"]
rename    = ["Ticker","ราคา ($)","1M%","3M%","6M%"]
if has_1y:
    cols_show.append("return_1y");  rename.append("1Y%")
cols_show += ["volatility","technical_score","technical_signal","risk_adjusted"]
rename    += ["Volatility%","Tech Score","Signal","Risk-Adj"]
if has_ai:
    cols_show += ["combined_score","recommendation"]
    rename    += ["AI Score","แนะนำ"]

# กรองเฉพาะ columns ที่มีอยู่จริง
cols_show = [c for c in cols_show if c in scoreboard.columns]
disp = scoreboard[cols_show].copy()
disp.columns = rename[:len(cols_show)]
disp["ราคา ($)"] = disp["ราคา ($)"].map(lambda x: f"${x:,.2f}")
st.dataframe(disp, width='stretch', hide_index=True)

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_price, tab_risk, tab_decision = st.tabs(["📈 Price & Return", "⚖️ Risk Analysis", "🎯 Decision Summary"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — PRICE & RETURN
# ════════════════════════════════════════════════════════════════════════════
with tab_price:
    st.markdown('<div class="section-header">📈 Price Trend (Normalized Base=100)</div>', unsafe_allow_html=True)
    cb1, cb2 = st.columns(2)
    with cb1:
        show_ma20_db = st.checkbox("MA20", value=False, key="db_ma20")
    with cb2:
        show_ma50_db = st.checkbox("MA50", value=False, key="db_ma50")

    from src.indicators import add_technical_indicators
    indicators_db = add_technical_indicators(prices)

    fig1 = go.Figure()
    for ticker in tickers:
        df = prices[prices["ticker"]==ticker].sort_values("date")
        if df.empty: continue
        base  = df["close"].iloc[0]
        color = get_color(ticker, tickers)
        indexed = df["close"] / base * 100
        fig1.add_trace(go.Scatter(
            x=df["date"], y=indexed, name=ticker,
            line=dict(color=color, width=2),
            hovertemplate=f"{ticker}: %{{y:.1f}}<extra></extra>"))
        ticker_color = get_color(ticker, tickers)
        if show_ma20_db:
            df_ind = indicators_db[indicators_db["ticker"]==ticker].sort_values("date")
            fig1.add_trace(go.Scatter(
                x=df_ind["date"], y=df_ind["ma20"] / base * 100,
                name=f"{ticker} MA20", showlegend=False,
                line=dict(color=ticker_color, width=1.2, dash="dot"), opacity=0.6,
                hovertemplate=f"{ticker} MA20: %{{y:.1f}}<extra></extra>"))
        if show_ma50_db:
            df_ind = indicators_db[indicators_db["ticker"]==ticker].sort_values("date")
            fig1.add_trace(go.Scatter(
                x=df_ind["date"], y=df_ind["ma50"] / base * 100,
                name=f"{ticker} MA50", showlegend=False,
                line=dict(color=ticker_color, width=1.2, dash="dash"), opacity=0.6,
                hovertemplate=f"{ticker} MA50: %{{y:.1f}}<extra></extra>"))
    fig1.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.2)")
    fig1.update_layout(height=340, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569", title="Indexed (Base=100)"),
        xaxis=dict(showgrid=False, color="#475569"),
        legend=dict(font=dict(color="#94a3b8",size=12), orientation="h", y=1.08))
    st.plotly_chart(fig1, width='stretch')

    st.markdown('<div class="section-header">📊 Return Comparison (1M / 3M / 6M / 1Y)</div>', unsafe_allow_html=True)
    ret_cols = ["return_1m","return_3m","return_6m"]
    if "return_1y" in scoreboard.columns:
        ret_cols.append("return_1y")
    ret_long = scoreboard.melt(
        id_vars="ticker", value_vars=ret_cols,
        var_name="period", value_name="return_pct"
    )
    ret_long["period"] = ret_long["period"].map({
        "return_1m":"1M","return_3m":"3M","return_6m":"6M","return_1y":"1Y"
    })
    fig2 = go.Figure()
    for ticker in tickers:
        df = ret_long[ret_long["ticker"]==ticker]
        fig2.add_trace(go.Bar(
            x=df["period"], y=df["return_pct"], name=ticker,
            marker_color=get_color(ticker, tickers),
            text=df["return_pct"].map(lambda x: f"{x:+.1f}%"), textposition="outside"))
    fig2.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.2)")
    fig2.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569", ticksuffix="%"),
        xaxis=dict(color="#475569"), barmode="group",
        legend=dict(font=dict(color="#94a3b8",size=11), orientation="h", y=1.08))
    st.plotly_chart(fig2, width='stretch')


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — RISK ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
with tab_risk:
    left, right = st.columns(2, gap="large")

    with left:
        st.markdown('<div class="section-header">🎯 Risk vs Return</div>', unsafe_allow_html=True)
        st.caption("หุ้นที่ดีควรอยู่บน-ซ้าย (return สูง, risk ต่ำ)")
        fig3 = go.Figure()
        period_map = {
            "1 Month":  {"ret": "return_1m", "days": 21},
            "3 Months": {"ret": "return_3m", "days": 63},
            "6 Months": {"ret": "return_6m", "days": 126},
            "1 Year":   {"ret": "return_1y", "days": 252},
        }
        selected_period = st.selectbox(
            "ช่วงเวลา Return & Volatility",
            options=list(period_map.keys()),
            index=1,
            key="risk_return_period",
        )
        ret_col  = period_map[selected_period]["ret"]
        vol_days = period_map[selected_period]["days"]

        def period_vol(ticker, days):
            df = prices[prices["ticker"]==ticker].sort_values("date").tail(days)
            if len(df) < 5: return 0.0
            return round(df["close"].pct_change(fill_method=None).dropna().std() * np.sqrt(252) * 100, 2)

        fig3.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)",
                       annotation_text="0% return", annotation_position="right",
                       annotation_font=dict(color="#64748b", size=10))
        fig3.add_vline(x=30, line_dash="dash", line_color="rgba(255,255,255,0.3)",
                       annotation_text="30% risk", annotation_position="top",
                       annotation_font=dict(color="#64748b", size=10))
        for _, row in scoreboard.iterrows():
            ret_val = row.get(ret_col, 0)
            vol_val = period_vol(row["ticker"], vol_days)
            fig3.add_trace(go.Scatter(
                x=[vol_val], y=[ret_val],
                mode="markers+text", name=row["ticker"],
                text=[row["ticker"]], textposition="top center",
                marker=dict(size=20, color=get_color(row["ticker"], tickers))))
        fig3.add_hline(y=0, line_dash="solid", line_color="rgba(255,255,255,0.1)")
        fig3.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                       color="#475569", title=f"Risk: Volatility {selected_period} (%)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                       color="#475569", title=f"Return {selected_period} (%)", ticksuffix="%"),
            showlegend=False)
        st.plotly_chart(fig3, width='stretch')

    with right:
        st.markdown('<div class="section-header">⚡ Volatility</div>', unsafe_allow_html=True)
        st.caption("ความผันผวนรายปี — ยิ่งสูงยิ่งเสี่ยง")
        for _, row in scoreboard.iterrows():
            color = get_color(row["ticker"], tickers)
            vol   = row["volatility"]
            vol_color = "#f87171" if vol > 40 else "#f59e0b" if vol > 25 else "#34d399"
            st.markdown(f"""
            <div style="background:#111827;border:1px solid rgba(255,255,255,0.06);
                        border-radius:10px;padding:12px 16px;margin-bottom:8px;
                        display:flex;justify-content:space-between;align-items:center;">
              <span style="font-family:'Space Mono',monospace;color:{color};font-weight:600;">{row["ticker"]}</span>
              <span style="color:{vol_color};font-size:1.1rem;font-weight:700;">{vol:.1f}%</span>
            </div>""", unsafe_allow_html=True)
        st.caption("🟢 < 25% = ต่ำ | 🟡 25-40% = กลาง | 🔴 > 40% = สูง")




# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — DECISION SUMMARY
# ════════════════════════════════════════════════════════════════════════════
with tab_decision:
    st.markdown('<div class="section-header">🎯 Investment Decision Summary</div>', unsafe_allow_html=True)
    st.caption("สรุปคำแนะนำจากทุกมิติ — ช่วยตัดสินใจว่าควร ซื้อ / ถือ / ขาย")

    if ai_result.empty:
        st.warning("⚠️ ยังไม่มีผล AI Analysis — ไปที่หน้า **Analysis** เปิด AI Mode แล้วกด 'วิเคราะห์ด้วย AI' ก่อนครับ")
    else:
        for ticker in tickers:
            t_rows = scoreboard[scoreboard["ticker"]==ticker]
            a_rows = ai_result[ai_result["ticker"]==ticker]
            if t_rows.empty or a_rows.empty: continue
            t = t_rows.iloc[0]; a = a_rows.iloc[0]

            rec   = a.get("recommendation","Hold") or "Hold"
            color = get_color(ticker, tickers)
            cls   = "rec-buy" if rec=="Buy" else "rec-hold" if rec=="Hold" else "rec-sell"
            reason= a.get("reason","")

            st.markdown(f"""
            <div class="decision-card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <div>
                  <span style="font-family:'Space Mono',monospace;font-size:1.4rem;
                               font-weight:700;color:{color};">{ticker}</span>
                  <span style="color:#64748b;font-size:0.82rem;margin-left:10px;">
                    ${t.get('latest_close',0):,.2f}
                  </span>
                </div>
                <span class="{cls}" style="font-size:1rem;padding:6px 20px;">⚡ {rec}</span>
              </div>
              <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:14px;">
                <div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">
                  <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">Technical</div>
                  <div style="color:#e2e8f0;font-size:0.88rem;margin-top:4px;">{t.get("technical_signal","N/A")}</div>
                  <div style="color:#64748b;font-size:0.72rem;">{t.get("technical_score",0):.0f}/100</div>
                </div>
                <div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">
                  <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">AI Sentiment</div>
                  <div style="color:#e2e8f0;font-size:0.88rem;margin-top:4px;">{a.get("sentiment_label","N/A")}</div>
                  <div style="color:#64748b;font-size:0.72rem;">{a.get("sentiment_score",0):.0f}/100</div>
                </div>
                <div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">
                  <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">Combined</div>
                  <div style="color:{color};font-size:1.1rem;font-weight:700;margin-top:4px;">{a.get("combined_score",0):.1f}</div>
                  <div style="color:#64748b;font-size:0.72rem;">/100</div>
                </div>
              </div>
              <div style="background:#0d1117;border-radius:8px;padding:10px;
                          color:#94a3b8;font-size:0.82rem;line-height:1.6;">
                💡 {reason}
              </div>
            </div>
            """, unsafe_allow_html=True)

        # Combined Score bar chart
        st.markdown('<div class="section-header">📊 Combined Score เปรียบเทียบ</div>', unsafe_allow_html=True)
        merged_dec = scoreboard.copy()
        if "combined_score" not in merged_dec.columns:
            merged_dec["combined_score"] = 50.0
        if "recommendation" not in merged_dec.columns:
            merged_dec["recommendation"] = "Hold"
        merged_dec["combined_score"]  = merged_dec["combined_score"].fillna(50.0)
        merged_dec["recommendation"]  = merged_dec["recommendation"].fillna("Hold")

        colors_dec = [
            "#34d399" if r=="Buy" else "#f87171" if r=="Sell" else "#f59e0b"
            for r in merged_dec["recommendation"]
        ]
        fig_dec = go.Figure(go.Bar(
            x=merged_dec["ticker"], y=merged_dec["combined_score"],
            marker_color=colors_dec,
            text=merged_dec.apply(lambda r: f"{r['combined_score']:.1f} ({r['recommendation']})", axis=1),
            textposition="outside",
        ))
        fig_dec.add_hline(y=68, line_dash="dash", line_color="#34d399", opacity=0.5,
                          annotation_text="Buy zone (≥68)")
        fig_dec.add_hline(y=45, line_dash="dash", line_color="#f87171", opacity=0.5,
                          annotation_text="Sell zone (<45)")
        fig_dec.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                       color="#475569", range=[0,110], title="Combined Score"),
            xaxis=dict(color="#475569"), showlegend=False)
        st.plotly_chart(fig_dec, width='stretch')
        st.caption("Combined Score = Technical (60%) + AI Sentiment (40%) | ≥68 Buy | 45-67 Hold | <45 Sell")

# ── Snowflake Tables (expander) ────────────────────────────────────────────────
st.divider()
with st.expander("❄️ Snowflake Data Tables", expanded=False):
    st.caption("ข้อมูลที่บันทึกลง Snowflake — ใช้ verify ว่า pipeline ทำงานถูกต้อง")
    inner_tabs = st.tabs(["Stock Prices", "Technical Metrics", "AI Sentiment"])
    with inner_tabs[0]:
        price_show = prices.sort_values(["ticker","date"], ascending=[True,False]).groupby("ticker").head(10)
        st.dataframe(price_show, width='stretch', hide_index=True)
    with inner_tabs[1]:
        tech_show = indicators.sort_values(["ticker","date"], ascending=[True,False]).groupby("ticker").head(5)
        show_cols = ["date","ticker","ma20","ma50","rsi","macd","macd_signal","bb_upper","bb_lower"]
        st.dataframe(tech_show[[c for c in show_cols if c in tech_show.columns]], width='stretch', hide_index=True)
    with inner_tabs[2]:
        if not ai_result.empty:
            st.dataframe(ai_result, width='stretch', hide_index=True)
        else:
            st.info("ยังไม่มีผล AI Analysis — ไปวิเคราะห์ในหน้า Analysis ก่อนครับ")

st.caption("Educational demo only. This is not financial advice.")
