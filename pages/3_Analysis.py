"""
pages/2_Analysis.py
Analysis — Non-AI (ฟรี) + AI Features (ต้อง toggle เปิด)
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time

from src.config import DEFAULT_TICKERS, PALETTE, DEFAULT_PALETTE_COLOR, SECTORS
from src.data_pipeline import load_prices
from src.indicators import add_technical_indicators, latest_technical_scores
from src.ai_service import (
    run_ai_analysis, get_news,
    get_market_news, summarize_market_news,
    screen_sector, ai_sector_commentary,
)
from src.storage import (
    save_analysis_to_snowflake,
    save_analysis_history, load_analysis_history,
)

st.set_page_config(page_title="Analysis", page_icon="🔬", layout="wide")

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
  .rec-buy  { background:#064e3b;color:#34d399;padding:4px 14px;border-radius:20px;font-weight:700;font-size:0.85rem; }
  .rec-hold { background:#451a03;color:#f59e0b;padding:4px 14px;border-radius:20px;font-weight:700;font-size:0.85rem; }
  .rec-sell { background:#450a0a;color:#f87171;padding:4px 14px;border-radius:20px;font-weight:700;font-size:0.85rem; }
  .ai-card  { background:linear-gradient(135deg,#0f0f1a,#111827);
    border:1px solid rgba(124,58,237,0.3);border-radius:12px;padding:18px;border-left:3px solid #7C3AED; }
  .decision-card { background:#111827;border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:20px;margin-bottom:8px; }
  .news-card { background:#111827;border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:14px 16px;margin-bottom:10px; }
  [data-testid="stSidebar"] { background: #0d1117 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🔬 Analysis")

# ── AI Mode Toggle ─────────────────────────────────────────────────────────────
st.divider()
col_t, col_i = st.columns([1, 3])
with col_t:
    ai_enabled = st.toggle(
        "🤖 AI Mode",
        value=st.session_state.get("ai_enabled", False),
        key="ai_enabled",
    )
with col_i:
    if not ai_enabled:
        st.markdown('<div style="padding-top:6px;color:#64748b;font-size:0.88rem;">🔒 เปิด AI Mode เพื่อใช้งาน: ข่าวตลาด · วิเคราะห์หุ้น AI · Sector Screening</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="padding-top:6px;color:#a78bfa;font-size:0.88rem;font-weight:600;">✅ AI Mode เปิดแล้ว — Powered by Groq (Llama 3.3)</div>', unsafe_allow_html=True)
st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
if not ai_enabled:
    (tab_nonai,) = st.tabs(["📊 Technical Analysis"])
else:
    tab_nonai, tab_analysis, tab_news, tab_sector = st.tabs([
        "📊 Technical Analysis",
        "🤖 AI Analysis",
        "📰 ข่าวตลาด",
        "🏭 Sector Screening",
    ])


# ════════════════════════════════════════════════════════════════════════════
# TAB 0 — TECHNICAL ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
with tab_nonai:

    all_tickers_na = st.session_state.get("selected_tickers", DEFAULT_TICKERS)

    selected_na = st.multiselect(
        "เลือกหุ้นที่ต้องการดู",
        options=all_tickers_na,
        default=all_tickers_na,
        key="nonai_tickers",
    )
    if not selected_na:
        st.warning("กรุณาเลือกหุ้นอย่างน้อย 1 ตัว")
        st.stop()

    with st.spinner("กำลังโหลดข้อมูล..."):
        prices_na     = load_prices(tuple(selected_na))
        indicators_na = add_technical_indicators(prices_na)
        technical_na  = latest_technical_scores(indicators_na)

    if prices_na.empty:
        st.error("❌ ไม่มีข้อมูลหุ้น — กลับไปหน้า Stock Selection")
    else:
        result_na = technical_na.copy()

        st.markdown('<div class="section-header">🎯 Technical Recommendation</div>', unsafe_allow_html=True)
        st.caption("คำแนะนำจาก Technical Indicators เท่านั้น — RSI + MACD + MA (ไม่ใช้ AI)")

        rec_cols = st.columns(len(selected_na))
        for i, ticker in enumerate(selected_na):
            row = result_na[result_na["ticker"]==ticker]
            if row.empty: continue
            r     = row.iloc[0]
            color = PALETTE.get(ticker, DEFAULT_PALETTE_COLOR)
            score = r.get("technical_score", 50)
            rsi   = r.get("rsi", 50)

            if score >= 65:
                rec, rec_cls, rec_reason = "Buy", "rec-buy", "Technical signal แข็งแกร่ง"
                conf_pct = min(50 + (score - 65) / 35 * 50, 95)
            elif score < 45:
                rec, rec_cls, rec_reason = "Sell", "rec-sell", "Technical signal อ่อนแอ"
                conf_pct = min(50 + (45 - score) / 45 * 50, 95)
            else:
                rec, rec_cls, rec_reason = "Hold", "rec-hold", "Technical signal ปานกลาง"
                conf_pct = min(50 + (1 - abs(score - 55) / 10) * 30, 85)

            conf_pct   = round(conf_pct)
            conf_label = "High" if conf_pct >= 70 else "Medium" if conf_pct >= 50 else "Low"
            conf_color = "#34d399" if conf_pct >= 70 else "#f59e0b" if conf_pct >= 50 else "#f87171"
            rsi_note   = "RSI Oversold — อาจฟื้นตัว ⬆️" if rsi < 30 else "RSI Overbought — ระวังปรับฐาน ⬇️" if rsi > 70 else ""

            with rec_cols[i]:
                st.markdown(f"""
                <div style="background:#111827;border:1px solid {color}44;
                            border-radius:14px;padding:18px;text-align:center;">
                  <div style="font-family:'Space Mono',monospace;font-size:1.2rem;
                              font-weight:700;color:{color};margin-bottom:12px;">{ticker}</div>
                  <div style="margin-bottom:10px;">
                    <span class="{rec_cls}" style="font-size:1rem;padding:6px 20px;">⚡ {rec}</span>
                  </div>
                  <div style="display:flex;justify-content:space-around;margin-bottom:10px;">
                    <div style="text-align:center;">
                      <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">Tech Score</div>
                      <div style="font-family:'Space Mono',monospace;color:#e2e8f0;font-size:1rem;font-weight:600;">{score:.0f}/100</div>
                    </div>
                    <div style="text-align:center;">
                      <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">Confidence</div>
                      <div style="font-family:'Space Mono',monospace;color:{conf_color};font-size:1rem;font-weight:600;">
                        {conf_label} ({conf_pct}%)
                      </div>
                    </div>
                  </div>
                  <div style="color:#94a3b8;font-size:0.78rem;line-height:1.5;margin-bottom:4px;">{rec_reason}</div>
                  <div style="color:#64748b;font-size:0.75rem;">{rsi_note}</div>
                </div>""", unsafe_allow_html=True)

        st.divider()

        with st.expander("📊 ดู Score Breakdown ละเอียด", expanded=False):
            disp_sel = result_na[result_na["ticker"].isin(selected_na)]
            disp_na  = disp_sel[["ticker","rsi","rsi_score","macd_score","ma_score","technical_score","technical_signal"]].copy()
            disp_na.columns = ["Ticker","RSI","RSI Score","MACD Score","MA Score","Tech Score","Signal"]
            st.dataframe(disp_na, width='stretch', hide_index=True)

        with st.expander("ℹ️ วิธีอ่าน Recommendation"):
            st.markdown("""
            **📊 Tech Score คำนวณยังไง:**
            ```
            Tech Score = mean(RSI Score + MACD Score + MA Score)
            ```
            | Indicator | เกณฑ์ | Score |
            |---|---|---|
            | RSI | 45-65 = 70 / 35-45 หรือ 65-75 = 55 / อื่นๆ = 35 | 0-100 |
            | MACD | MACD > Signal line = 70 / MACD < Signal line = 35 | 0-100 |
            | MA | ราคา > MA20 > MA50 = 75 / อื่นๆ = 45 | 0-100 |

            ---

            **🎯 เกณฑ์ Recommendation:**
            | Tech Score | คำแนะนำ | ความหมาย |
            |---|---|---|
            | ≥ 65 | **Buy** | สัญญาณ Technical แข็งแกร่ง |
            | 45–64 | **Hold** | สัญญาณปานกลาง รอดูก่อน |
            | < 45 | **Sell** | สัญญาณอ่อนแอ ควรระวัง |

            ---

            **📐 Confidence Score คำนวณยังไง:**
            ```
            Buy:  Confidence = 50 + (score - 65) / 35 × 50   [cap 95%]
            Sell: Confidence = 50 + (45 - score) / 45 × 50   [cap 95%]
            Hold: Confidence = 50 + (1 - |score - 55| / 10) × 30  [cap 85%]
            ```
            - ยิ่ง score ห่างจาก threshold มาก → Confidence ยิ่งสูง
            - **High ≥ 70%** — สัญญาณชัดเจน มั่นใจสูง
            - **Medium 50–69%** — score ใกล้เกณฑ์ ควรระวัง
            - **Low < 50%** — score อยู่ใกล้เส้นแบ่ง อาจเปลี่ยนแปลงได้

            ---
            ⚠️ นี่คือการวิเคราะห์เชิงสถิติเท่านั้น ไม่ใช่คำแนะนำทางการเงิน
            เปิด AI Mode เพื่อรับคำแนะนำที่รวมข่าวล่าสุดด้วย
            """)


# ════════════════════════════════════════════════════════════════════════════
# TAB 1-3 — AI FEATURES
# ════════════════════════════════════════════════════════════════════════════
if ai_enabled:

    # ── TAB: MARKET NEWS ─────────────────────────────────────────────────────
    with tab_news:
        st.markdown('<div class="section-header">📰 ข่าวตลาดหุ้นน่าสนใจ</div>', unsafe_allow_html=True)
        st.caption("ข่าวภาพรวมตลาด — AI สรุปให้อ่านเร็ว")

        fetch_btn = st.button("🔄 ดึงข่าวและสรุป", type="primary", width='stretch', key="fetch_news")

        if fetch_btn:
            with st.spinner("กำลังดึงข่าวตลาด..."):
                raw_news = get_market_news(limit_per_ticker=5)
            with st.spinner(f"AI กำลังสรุป {len(raw_news)} ข่าว..."):
                summarized = summarize_market_news(raw_news)
            st.session_state["market_news"] = summarized
            st.success(f"✅ ดึงและสรุป {len(summarized)} ข่าวเรียบร้อย")

        market_news = st.session_state.get("market_news", [])
        if market_news:
            st.caption(f"แสดง {len(market_news)} ข่าวล่าสุด")
            for i, n in enumerate(market_news):
                title   = n.get("title","")
                url     = n.get("url","")
                pub     = n.get("pub_date","")
                summary = n.get("summary","")
                st.markdown(f"""
                <div class="news-card">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                    <div style="font-weight:600;color:#e2e8f0;font-size:1rem;flex:1;line-height:1.4;">
                      {i+1}. {title}
                    </div>
                    <span style="color:#475569;font-size:0.72rem;margin-left:12px;white-space:nowrap;">{pub}</span>
                  </div>
                  <div style="color:#cbd5e1;font-size:0.92rem;line-height:1.7;margin-bottom:10px;">
                    {summary if summary else "<span style='color:#475569'>AI ไม่สามารถสรุปได้ — อาจเกิดจาก rate limit กรุณาลองใหม่</span>"}
                  </div>
                  {"" if not url else f'<a href="{url}" target="_blank" style="color:#00D4FF;font-size:0.78rem;text-decoration:none;">🔗 อ่านต้นฉบับ →</a>'}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("กด 'ดึงข่าวและสรุป' เพื่อดูข่าวตลาดล่าสุด")

    # ── TAB: AI ANALYSIS ─────────────────────────────────────────────────────
    with tab_analysis:
        st.markdown('<div class="section-header">🤖 วิเคราะห์หุ้นด้วย AI</div>', unsafe_allow_html=True)

        all_tickers = st.session_state.get("selected_tickers", DEFAULT_TICKERS)
        tickers_to_analyze = st.multiselect(
            "เลือกหุ้นที่ต้องการวิเคราะห์",
            options=all_tickers,
            default=all_tickers,
            key="analysis_tickers",
        )
        if not tickers_to_analyze:
            st.warning("กรุณาเลือกหุ้นอย่างน้อย 1 ตัว")
            st.stop()

        col_news, col_btn = st.columns([2, 1])
        with col_news:
            news_count = st.slider("จำนวนข่าวที่ใช้วิเคราะห์ต่อหุ้น", min_value=3, max_value=10, value=5, step=1)
            st.caption(f"จะดึง {news_count} ข่าวล่าสุดต่อหุ้น จาก Yahoo Finance")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            run_btn = st.button("🚀 วิเคราะห์ด้วย AI", type="primary", width='stretch')

        with st.spinner("กำลังโหลดข้อมูล..."):
            prices     = load_prices(tuple(tickers_to_analyze))
            indicators = add_technical_indicators(prices)
            technical  = latest_technical_scores(indicators)

        if prices.empty:
            st.error("❌ ไม่มีข้อมูลหุ้น")
            st.stop()

        merged_scores = technical.copy()

        if run_btn:
            progress_bar = st.progress(0)
            status_text  = st.empty()
            status_text.markdown(f"🔍 **กำลังดึงข่าวล่าสุด** ({news_count} ข่าวต่อหุ้น)...")
            progress_bar.progress(20); time.sleep(0.5)
            status_text.markdown("📊 **กำลังวิเคราะห์ Technical Indicators...**")
            progress_bar.progress(40); time.sleep(0.5)
            status_text.markdown("🤖 **AI กำลังวิเคราะห์ Sentiment ข่าว...**")
            progress_bar.progress(60)

            ai_result = run_ai_analysis(technical, tuple(tickers_to_analyze))
            st.session_state["ai_result"] = ai_result

            status_text.markdown("💾 **กำลังบันทึกผลลัพธ์...**")
            progress_bar.progress(80)
            results_for_mongo = ai_result[["ticker","recommendation","combined_score","sentiment_label"]].to_dict("records")
            msg = save_analysis_history(list(tickers_to_analyze), results_for_mongo)
            ok  = save_analysis_to_snowflake(technical, ai_result)
            progress_bar.progress(100)
            status_text.empty(); progress_bar.empty()
            st.success(f"✅ วิเคราะห์เสร็จแล้ว! | {msg} | {'Snowflake ✓' if ok else 'Snowflake ✗'}")

        ai_result = st.session_state.get("ai_result", pd.DataFrame())

        if not ai_result.empty:
            st.markdown('<div class="section-header">🎯 Investment Decision Summary</div>', unsafe_allow_html=True)

            for ticker in tickers_to_analyze:
                t_rows = merged_scores[merged_scores["ticker"]==ticker]
                a_rows = ai_result[ai_result["ticker"]==ticker]
                if t_rows.empty or a_rows.empty: continue
                t = t_rows.iloc[0]; a = a_rows.iloc[0]
                rec   = a.get("recommendation","Hold")
                color = PALETTE.get(ticker, DEFAULT_PALETTE_COLOR)
                cls   = "rec-buy" if rec=="Buy" else "rec-hold" if rec=="Hold" else "rec-sell"
                st.markdown(f"""
                <div class="decision-card">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                    <span style="font-family:'Space Mono',monospace;font-size:1.2rem;font-weight:700;color:{color};">{ticker}</span>
                    <span class="{cls}">⚡ {rec}</span>
                  </div>
                  <div style="display:flex;gap:24px;flex-wrap:wrap;margin-bottom:10px;">
                    <div><span style="color:#64748b;font-size:0.75rem;">TECHNICAL</span><br>
                         <span style="color:#e2e8f0;">{t.get("technical_signal","N/A")}</span></div>
                    <div><span style="color:#64748b;font-size:0.75rem;">AI SENTIMENT</span><br>
                         <span style="color:#e2e8f0;">{a.get("sentiment_label","N/A")}</span></div>
                    <div><span style="color:#64748b;font-size:0.75rem;">COMBINED SCORE</span><br>
                         <span style="color:#e2e8f0;">{a.get("combined_score",50):.1f}/100</span></div>
                  </div>
                  <div style="color:#94a3b8;font-size:0.82rem;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
                    💡 {a.get("reason","")}
                  </div>
                </div>
                """, unsafe_allow_html=True)

            with st.expander("📊 ดู Score Breakdown — Combined Score มาจากไหน?", expanded=False):
                st.caption("Combined Score = Technical (60%) + AI Sentiment (40%)")
                for ticker in tickers_to_analyze:
                    t_rows = merged_scores[merged_scores["ticker"]==ticker]
                    a_rows = ai_result[ai_result["ticker"]==ticker]
                    if t_rows.empty or a_rows.empty: continue
                    t = t_rows.iloc[0]; a = a_rows.iloc[0]
                    color    = PALETTE.get(ticker, DEFAULT_PALETTE_COLOR)
                    tech     = t.get("technical_score", 0)
                    rsi_s    = t.get("rsi_score", 0)
                    macd_s   = t.get("macd_score", 0)
                    ma_s     = t.get("ma_score", 0)
                    sent     = a.get("sentiment_score", 0)
                    combined = a.get("combined_score", 0)
                    st.markdown(f"""
                    <div style="background:#111827;border:1px solid {color}33;border-radius:12px;padding:16px;margin-bottom:10px;">
                      <div style="font-family:'Space Mono',monospace;font-weight:700;color:{color};margin-bottom:12px;">{ticker}</div>
                      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
                        <div style="background:#0d1117;border-radius:8px;padding:10px;">
                          <div style="color:#64748b;font-size:0.72rem;text-transform:uppercase;margin-bottom:6px;">Technical Score (60%)</div>
                          <div style="font-family:'Space Mono',monospace;color:#e2e8f0;font-size:1.1rem;font-weight:600;">{tech:.1f}/100</div>
                          <div style="color:#64748b;font-size:0.78rem;margin-top:6px;line-height:1.6;">
                            RSI Score: {rsi_s:.0f}/100<br>MACD Score: {macd_s:.0f}/100<br>MA Score: {ma_s:.0f}/100
                          </div>
                        </div>
                        <div style="background:#0d1117;border-radius:8px;padding:10px;">
                          <div style="color:#64748b;font-size:0.72rem;text-transform:uppercase;margin-bottom:6px;">AI Sentiment (40%)</div>
                          <div style="font-family:'Space Mono',monospace;color:#e2e8f0;font-size:1.1rem;font-weight:600;">{sent:.0f}/100</div>
                          <div style="color:#64748b;font-size:0.78rem;margin-top:6px;line-height:1.6;">จาก Groq วิเคราะห์ข่าวล่าสุด</div>
                        </div>
                      </div>
                      <div style="background:#0d1117;border-radius:8px;padding:10px;display:flex;justify-content:space-between;align-items:center;">
                        <div style="color:#64748b;font-size:0.82rem;">Combined Score</div>
                        <div style="font-family:'Space Mono',monospace;color:{color};font-size:1.2rem;font-weight:700;">{combined:.1f}/100</div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()

            for ticker in tickers_to_analyze:
                a_rows = ai_result[ai_result["ticker"]==ticker]
                if a_rows.empty: continue
                a = a_rows.iloc[0]
                with st.expander(f"📊 {ticker} — รายละเอียด", expanded=False):
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Sentiment",       a.get("sentiment_label","N/A"))
                    c2.metric("Sentiment Score",  f"{a.get('sentiment_score',0):.0f}/100")
                    c3.metric("Combined Score",   f"{a.get('combined_score',0):.1f}/100")

                    st.markdown('<div class="section-header">💬 AI Summary</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="ai-card">{a.get("ai_summary","")}</div>', unsafe_allow_html=True)

                    st.markdown('<div class="section-header">📈 Impact Analysis</div>', unsafe_allow_html=True)
                    ia1, ia2 = st.columns(2)
                    with ia1:
                        st.markdown(f"**Revenue:** {a.get('impact_revenue','N/A')}")
                        st.markdown(f"**Profit:** {a.get('impact_profit','N/A')}")
                    with ia2:
                        st.markdown(f"**Competition:** {a.get('impact_competition','N/A')}")
                        st.markdown(f"**Growth:** {a.get('impact_growth','N/A')}")

                    st.markdown('<div class="section-header">📰 ข่าวที่ใช้วิเคราะห์</div>', unsafe_allow_html=True)
                    raw_news = get_news(ticker, limit=news_count)
                    if raw_news:
                        st.caption(f"ดึงมา {len(raw_news)} ข่าวล่าสุดจาก Yahoo Finance")
                        for n in raw_news:
                            title    = n.get("title","")
                            url      = n.get("url","")
                            pub_date = n.get("pub_date","")
                            if not title: continue
                            from src.ai_service import _call_groq
                            try:
                                news_summary = _call_groq(f"สรุปข่าวนี้เป็นภาษาไทย 2 ประโยค: {title}", max_tokens=150).strip()
                            except Exception:
                                news_summary = ""
                            summary_html = f'<div style="color:#94a3b8;font-size:0.88rem;line-height:1.65;margin-bottom:8px;">{news_summary}</div>' if news_summary else ''
                            link_html    = f'<a href="{url}" target="_blank" style="color:#00D4FF;font-size:0.78rem;text-decoration:none;">🔗 อ่านต้นฉบับ →</a>' if url else ''
                            st.markdown(f"""
                            <div class="news-card">
                              <div style="font-weight:600;color:#e2e8f0;font-size:0.92rem;margin-bottom:8px;">📰 {title}</div>
                              {summary_html}
                              <div style="display:flex;justify-content:space-between;">
                                {link_html}
                                <span style="color:#475569;font-size:0.72rem;">{pub_date}</span>
                              </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("ไม่พบข่าวล่าสุด")

            st.divider()
            with st.expander("🕐 ประวัติการวิเคราะห์ (MongoDB)", expanded=False):
                history = load_analysis_history(5)
                if history:
                    for h in history:
                        tickers_str = ", ".join(h.get("tickers",[]))
                        time_str    = h["analyzed_at"].strftime("%d/%m/%Y %H:%M") if hasattr(h.get("analyzed_at"), "strftime") else str(h.get("analyzed_at",""))
                        results     = h.get("results",[])
                        recs        = " | ".join([f"{r['ticker']}: {r.get('recommendation','N/A')}" for r in results])
                        st.markdown(f"""
                        <div style="background:#111827;border:1px solid rgba(255,255,255,0.06);
                                    border-radius:8px;padding:10px 14px;margin-bottom:6px;">
                          <div style="display:flex;justify-content:space-between;">
                            <span style="color:#e2e8f0;font-size:0.85rem;">📋 {tickers_str}</span>
                            <span style="color:#475569;font-size:0.75rem;">{time_str}</span>
                          </div>
                          <div style="color:#64748b;font-size:0.78rem;margin-top:4px;">{recs}</div>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.caption("ยังไม่มีประวัติ")
        else:
            st.info("กด '🚀 วิเคราะห์ด้วย AI' เพื่อรับการวิเคราะห์และคำแนะนำ")

    # ── TAB: SECTOR SCREENING ────────────────────────────────────────────────
    with tab_sector:
        st.markdown('<div class="section-header">🏆 Top 10 หุ้นที่ดีที่สุดในอุตสาหกรรม</div>', unsafe_allow_html=True)
        st.caption("จัดอันดับหุ้นในอุตสาหกรรมที่เลือกจาก Momentum Score พร้อมเหตุผล")

        sector_list = list(SECTORS.keys())
        col_sec, col_run = st.columns([2, 1])
        with col_sec:
            selected_sector = st.selectbox("เลือกอุตสาหกรรม", sector_list)
        with col_run:
            st.markdown("<br>", unsafe_allow_html=True)
            screen_btn = st.button("🔍 Scan Sector", type="primary", width='stretch')

        if screen_btn:
            with st.spinner(f"กำลัง scan {selected_sector}..."):
                screen_df = screen_sector(selected_sector)
            st.session_state["screen_df"]     = screen_df
            st.session_state["screen_sector"] = selected_sector
            with st.spinner("AI กำลังสรุป sector..."):
                commentary = ai_sector_commentary(selected_sector, screen_df)
            st.session_state["sector_commentary"] = commentary

        screen_df  = st.session_state.get("screen_df", pd.DataFrame())
        commentary = st.session_state.get("sector_commentary", "")

        if not screen_df.empty:
            excluded = screen_df.attrs.get("excluded", [])
            if excluded:
                st.warning(f"⚠️ ตัดหุ้นออก {len(excluded)} ตัวเพราะข้อมูลไม่ครบ: **{', '.join(excluded)}**")

            # ℹ️ คำอธิบายการคำนวณ
            with st.expander("ℹ️ วิธีคำนวณ Momentum Score, Technical Score และ Signal", expanded=False):
                st.markdown("""
                **🚀 Momentum Score** — วัดว่าหุ้นกำลัง "มาแรง" แค่ไหน
                ```
                Momentum Score = Return 1M (40%) + Technical Score (60%)
                ```
                - **Return 1M** — ผลตอบแทนใน 1 เดือนที่ผ่านมา (clip ที่ ±20%)
                - **Technical Score** — สัญญาณ Technical indicator รวม
                - ยิ่งสูงยิ่งดี — หุ้นที่ขึ้นแรงและมี technical signal ดีจะอยู่อันดับต้น

                ---

                **📊 Technical Score** — วัดความแข็งแกร่งของสัญญาณ Technical
                ```
                Technical Score = mean(RSI Score + MACD Score + MA Score)
                ```
                | Indicator | วิธีคำนวณ Score |
                |---|---|
                | RSI Score | RSI 45-65 = 70 / RSI 35-45 หรือ 65-75 = 55 / อื่นๆ = 35 |
                | MACD Score | MACD > Signal line = 70 / MACD < Signal line = 35 |
                | MA Score | ราคา > MA20 > MA50 = 75 / อื่นๆ = 45 |

                ---

                **🎯 Signal** — สรุปภาพรวม Technical
                | Signal | เกณฑ์ | ความหมาย |
                |---|---|---|
                | Bullish 🟢 | Tech Score ≥ 65 | สัญญาณแข็งแกร่ง น่าสนใจ |
                | Neutral 🟡 | Tech Score 45-64 | สัญญาณกลางๆ รอดูก่อน |
                | Bearish 🔴 | Tech Score < 45 | สัญญาณอ่อนแอ ควรระวัง |
                """)

            st.markdown('<div class="section-header">🚀 Momentum Ranking</div>', unsafe_allow_html=True)
            medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
            top10  = screen_df.head(10)

            rows_list = list(top10.iterrows())
            for idx in range(0, len(rows_list), 2):
                col_a, col_b = st.columns(2)
                pair = rows_list[idx:idx+2]
                for col_w, (_, row) in zip([col_a, col_b], pair):
                    rank      = list(top10.index).index(row.name)
                    medal     = medals[rank] if rank < len(medals) else str(rank+1)
                    color     = PALETTE.get(row["ticker"], DEFAULT_PALETTE_COLOR)
                    ret_color = "#34d399" if row["return_1m"] >= 0 else "#f87171"
                    sig       = str(row.get("technical_signal","")).replace(" 🟢","").replace(" 🔴","").replace(" 🟡","")
                    reason    = row.get("reason","Momentum โดยรวมอยู่ในระดับกลาง")
                    with col_w:
                        st.markdown(f"""
                        <div style="background:#111827;border:1px solid {color}44;border-radius:12px;padding:18px;margin-bottom:10px;">
                          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                            <span style="font-size:1.4rem;">{medal}</span>
                            <span style="font-family:'Space Mono',monospace;font-size:1.1rem;font-weight:700;color:{color};">{row['ticker']}</span>
                            <span style="color:{ret_color};font-size:0.88rem;font-weight:600;">{row['return_1m']:+.1f}% 1M</span>
                          </div>
                          <div style="display:flex;gap:16px;margin-bottom:10px;">
                            <div><span style="color:#64748b;font-size:0.72rem;">MOMENTUM</span><br>
                                 <span style="color:#e2e8f0;font-weight:600;">{row['momentum_score']:.1f}</span></div>
                            <div><span style="color:#64748b;font-size:0.72rem;">TECHNICAL</span><br>
                                 <span style="color:#e2e8f0;font-weight:600;">{row['technical_score']:.0f}/100</span></div>
                            <div><span style="color:#64748b;font-size:0.72rem;">SIGNAL</span><br>
                                 <span style="color:#e2e8f0;font-weight:600;">{sig}</span></div>
                          </div>
                          <div style="color:#94a3b8;font-size:0.8rem;line-height:1.5;
                                      border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
                            💡 {reason}
                          </div>
                        </div>""", unsafe_allow_html=True)

            if commentary:
                st.markdown('<div class="section-header">🤖 AI สรุป Sector</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="ai-card">{commentary}</div>', unsafe_allow_html=True)
        else:
            st.info("กด 'Scan Sector' เพื่อดูหุ้นที่กำลังมาแรง")
