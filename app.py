"""
Main.py — AI Stock Decision Support System
หน้าแรก: Story + Flow + System Status
"""

import streamlit as st
from src.storage import setup_snowflake_tables, mongo_status, snowflake_status

st.set_page_config(
    page_title="AI Stock Decision Support",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .hero-title {
    font-family: 'Space Mono', monospace;
    font-size: 2.8rem; font-weight: 700;
    background: linear-gradient(90deg, #76b900, #00A4EF, #4285F4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    line-height: 1.2;
  }
  .hero-sub   { color: #94a3b8; font-size: 1.05rem; margin-top: 8px; }
  .persona-card {
    background: linear-gradient(135deg, #0f1b2d, #111827);
    border: 1px solid rgba(0,164,239,0.3);
    border-left: 4px solid #00A4EF;
    border-radius: 12px; padding: 18px 22px; margin: 16px 0;
  }
  .problem-card {
    background: #111827; border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; padding: 16px 20px;
  }
  .flow-card {
    background: #111827; border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; padding: 20px; text-align: center; height: 100%;
  }
  .flow-icon  { font-size: 2rem; margin-bottom: 8px; }
  .flow-title { font-weight: 600; color: #e2e8f0; font-size: 0.95rem; margin-bottom: 6px; }
  .flow-desc  { color: #64748b; font-size: 0.82rem; line-height: 1.5; }
  .status-row {
    background: #111827; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px; padding: 12px 16px; margin-bottom: 8px;
  }
  .section-header {
    font-size: 0.7rem; font-weight: 600; color: #00D4FF;
    text-transform: uppercase; letter-spacing: 0.12em;
    margin: 24px 0 12px; border-bottom: 1px solid rgba(0,212,255,0.2);
    padding-bottom: 6px;
  }
  .disclaimer-banner {
    background: linear-gradient(135deg, #1c1400, #2a1f00);
    border: 1px solid #f59e0b;
    border-left: 5px solid #f59e0b;
    border-radius: 12px; padding: 16px 20px; margin: 20px 0;
  }
  [data-testid="stSidebar"] { background: #0d1117 !important; }
</style>
""", unsafe_allow_html=True)

# ── Setup ──────────────────────────────────────────────────────────────────────
setup_snowflake_tables()

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">📈 AI Stock Decision<br>Support System</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">วิเคราะห์หุ้นด้วย Technical Analysis และ AI<br>เพื่อช่วยนักลงทุนตัดสินใจได้อย่างมั่นใจขึ้น</div>', unsafe_allow_html=True)

# ── Disclaimer Banner ──────────────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer-banner">
  <div style="font-weight:700;color:#f59e0b;font-size:0.95rem;margin-bottom:6px;">
    ⚠️ ข้อควรทราบก่อนใช้งาน
  </div>
  <div style="color:#fcd34d;font-size:0.85rem;line-height:1.7;">
    App นี้เป็น <strong>เครื่องมือช่วยตัดสินใจ</strong> ไม่ใช่คำแนะนำทางการเงิน
    <strong></strong><br>
    การลงทุนมีความเสี่ยง ผู้ลงทุนควรศึกษาข้อมูลเพิ่มเติมและตัดสินใจด้วยตนเอง
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Story / Persona ────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">👤 สร้างมาเพื่อใคร?</div>', unsafe_allow_html=True)

st.markdown("""
<div class="persona-card">
  <div style="font-size:1.1rem;font-weight:600;color:#e2e8f0;margin-bottom:10px;">
    🙋 สำหรับ <span style="color:#00A4EF;">นักลงทุนรายย่อย</span> ที่ไม่มีเวลาติดตามข่าวทุกวัน
  </div>
  <div style="color:#94a3b8;font-size:0.88rem;line-height:1.8;">
    คุณเป็นคนทำงาน มีเงินออมอยากลงทุน แต่ไม่มีเวลานั่งอ่านข่าว ไม่รู้ว่าหุ้นตัวไหนกำลังมาแรง
    และทุกครั้งที่จะซื้อหรือขายก็ไม่แน่ใจว่าตัดสินใจถูกไหม —
    <strong style="color:#e2e8f0;">AI Stock Decision Support</strong> ทำหน้าที่เป็นผู้ช่วยส่วนตัวที่
    ดึงข้อมูลล่าสุด วิเคราะห์ให้ แล้วสรุปเป็นคำแนะนำง่ายๆ ว่า <strong style="color:#34d399;">ซื้อ / ถือ / ขาย</strong>
  </div>
</div>
""", unsafe_allow_html=True)

# Problems
st.markdown('<div class="section-header">❗ ปัญหาที่ app นี้แก้</div>', unsafe_allow_html=True)
p1, p2, p3 = st.columns(3)
problems = [
    ("📰", "ข้อมูลกระจัดกระจาย", "ต้องเปิดหลาย website เพื่อดูข่าว ราคา และ technical indicators"),
    ("🤯", "วิเคราะห์เองไม่เป็น", "ไม่รู้ว่า RSI, MACD หมายความว่าอะไร หรือควรดูอะไรก่อน"),
    ("⏰", "ไม่มีเวลาติดตาม", "ตลาดเปลี่ยนเร็ว กว่าจะรู้ข่าวก็สายไปแล้ว"),
]
for col, (icon, title, desc) in zip([p1,p2,p3], problems):
    with col:
        st.markdown(f"""
        <div class="problem-card">
          <div style="font-size:1.6rem;margin-bottom:8px;">{icon}</div>
          <div style="font-weight:600;color:#e2e8f0;font-size:0.9rem;margin-bottom:6px;">{title}</div>
          <div style="color:#64748b;font-size:0.8rem;line-height:1.5;">{desc}</div>
        </div>""", unsafe_allow_html=True)

st.divider()

# ── Flow ───────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🗺️ วิธีที่ App แก้ปัญหา</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
    <div class="flow-card">
      <div class="flow-icon">1️⃣</div>
      <div class="flow-title">เลือกหุ้นที่สนใจ</div>
      <div class="flow-desc">เลือกได้สูงสุด 3 ตัว<br>ระบบดึงข้อมูลจริงจาก Yahoo Finance<br>บันทึก Watchlist ลง MongoDB</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class="flow-card">
      <div class="flow-icon">2️⃣</div>
      <div class="flow-title">AI วิเคราะห์ให้อัตโนมัติ</div>
      <div class="flow-desc">ดึงข่าวล่าสุด → วิเคราะห์ Sentiment<br>รวมกับ Technical + Pattern<br>สรุปเป็น Buy / Hold / Sell</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div class="flow-card">
      <div class="flow-icon">3️⃣</div>
      <div class="flow-title">ดู Dashboard + ตัดสินใจ</div>
      <div class="flow-desc">เปรียบเทียบหุ้นหลายตัว<br>scan หุ้นมาแรงในอุตสาหกรรม<br>Decision Summary ชัดเจนใน 1 หน้า</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── System Status ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🔌 สถานะระบบ</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div class="status-row">
      {mongo_status()}<br>
      <span style="color:#475569;font-size:0.75rem;">เก็บ Watchlist, Search History, Analysis History</span>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="status-row">
      {snowflake_status()}<br>
      <span style="color:#475569;font-size:0.75rem;">เก็บ Stock Prices, Indicators, Predictions, AI Sentiment</span>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── Tech Stack ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🛠️ Tech Stack</div>', unsafe_allow_html=True)
stack = {
    "📊 Streamlit":  "Multi-page Web App Framework",
    "📈 yfinance":   "ดึงข้อมูลราคาหุ้นจริง Real-time",
    "🦆 DuckDB":     "In-memory SQL query บน DataFrame",
    "🐼 Pandas":     "Data manipulation & processing",
    "🌿 MongoDB":    "Watchlist, History (NoSQL)",
    "❄️ Snowflake":  "Price, Indicators, AI Results (Cloud DW)",
    "🤖 Groq AI":    "LLM วิเคราะห์ข่าว + แนะนำ Buy/Hold/Sell",
    "📉 Plotly":     "Interactive charts — Price, Return, Risk vs Return",
}
cols = st.columns(4)
for i, (k, v) in enumerate(stack.items()):
    with cols[i % 4]:
        st.markdown(f"""
        <div style="background:#111827;border:1px solid rgba(255,255,255,0.06);
                    border-radius:10px;padding:12px;margin-bottom:8px;">
          <div style="font-weight:600;color:#e2e8f0;font-size:0.88rem;">{k}</div>
          <div style="color:#64748b;font-size:0.78rem;margin-top:3px;">{v}</div>
        </div>""", unsafe_allow_html=True)
