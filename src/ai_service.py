"""
src/ai_service.py
AI Analysis ด้วย Groq (Llama 3.3) — วิเคราะห์หุ้น, สรุปข่าว, คำแนะนำ
"""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st
import yfinance as yf
from groq import Groq

from src.config import GROQ_MODEL


# ─── Groq Client ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_groq_client() -> Groq | None:
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if not api_key or api_key == "YOUR_GROQ_API_KEY":
            return None
        return Groq(api_key=api_key)
    except Exception as e:
        st.error(f"Groq init error: {e}")
        return None


def _call_groq(prompt: str, max_tokens: int = 1500) -> str:
    client = get_groq_client()
    if client is None:
        return "⚠️ กรุณาตั้งค่า GROQ_API_KEY ใน .streamlit/secrets.toml"
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ Groq error: {e}"


# ─── ดึงข่าวจาก yfinance ──────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def get_news(ticker: str, limit: int = 5) -> list[dict]:
    """ดึงข่าวหุ้น คืนค่า list of dict: title, url, pub_date"""
    try:
        raw = yf.Ticker(ticker).news or []
        result = []
        for item in raw[:limit]:
            if not isinstance(item, dict):
                continue
            cnt   = item.get("content", item) if isinstance(item.get("content"), dict) else item
            title = cnt.get("title", item.get("title", "")) or ""
            url   = cnt.get("canonicalUrl", {}).get("url", "") or item.get("link", "") or ""
            pub   = str(cnt.get("pubDate", ""))[:10]
            if title:
                result.append({"title": title, "url": url, "pub_date": pub})
        return result
    except Exception:
        return []


# ─── AI Analysis ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def run_ai_analysis(
    technical: pd.DataFrame,
    tickers:   tuple[str, ...],
) -> pd.DataFrame:
    """
    วิเคราะห์หุ้นทุกตัวด้วย Groq AI
    Combined Score = Technical (60%) + AI Sentiment (40%)
    """
    rows = []

    for row in technical.to_dict("records"):
        ticker    = row["ticker"]
        headlines = get_news(ticker)
        result    = _analyze_one(row, headlines)
        result["ticker"]          = ticker
        result["news_headlines"]  = headlines
        rows.append(result)

    return pd.DataFrame(rows)


def _analyze_one(row: dict, headlines: list[str]) -> dict:
    """เรียก Groq วิเคราะห์หุ้น 1 ตัว"""
    news_text = "\n".join([f"- {h}" for h in headlines]) if headlines else "- ไม่มีข่าวล่าสุด"

    prompt = f"""
คุณเป็น AI นักวิเคราะห์หุ้นมืออาชีพ วิเคราะห์หุ้น {row['ticker']} โดยใช้ข้อมูลต่อไปนี้:

**Technical Analysis:**
- RSI: {row.get('rsi', 'N/A')} (Score: {row.get('rsi_score', 'N/A')}/100)
- MACD Score: {row.get('macd_score', 'N/A')}/100
- MA Score: {row.get('ma_score', 'N/A')}/100
- Technical Signal: {row.get('technical_signal', 'N/A')}
- Technical Score: {row.get('technical_score', 'N/A')}/100

**ข่าวล่าสุด:**
{news_text}

ตอบในรูปแบบ JSON เท่านั้น ไม่มี markdown หรือ backticks:
{{
  "ai_summary": "สรุปภาพรวมการวิเคราะห์ 3-4 ประโยค ภาษาไทย",
  "sentiment_label": "Positive หรือ Neutral หรือ Negative",
  "sentiment_score": <ตัวเลข 0-100>,
  "impact_revenue": "ผลกระทบต่อรายได้ 1-2 ประโยค",
  "impact_profit": "ผลกระทบต่อกำไร 1-2 ประโยค",
  "impact_competition": "ผลกระทบด้านการแข่งขัน 1-2 ประโยค",
  "impact_growth": "แนวโน้มการเติบโต 1-2 ประโยค",
  "recommendation": "Buy หรือ Hold หรือ Sell",
  "reason": "เหตุผลสั้น 1-2 ประโยค"
}}
"""

    raw = _call_groq(prompt, max_tokens=1000)

    # Parse JSON
    try:
        # clean markdown fences if any
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
    except Exception:
        result = {
            "ai_summary":          raw[:300] if len(raw) > 10 else "ไม่สามารถวิเคราะห์ได้",
            "sentiment_label":     "Neutral",
            "sentiment_score":     50,
            "impact_revenue":      "N/A",
            "impact_profit":       "N/A",
            "impact_competition":  "N/A",
            "impact_growth":       "N/A",
            "recommendation":      "Hold",
            "reason":              "ไม่สามารถ parse ผลลัพธ์ได้",
        }

    # Combined Score = Technical (60%) + AI Sentiment (40%)
    tech_score = row.get("technical_score", 50)
    sent_score = result.get("sentiment_score", 50)
    result["combined_score"] = round(tech_score * 0.60 + sent_score * 0.40, 1)

    return result


# ─── Sector Screening ─────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def screen_sector(sector: str) -> pd.DataFrame:
    """
    ดึงข้อมูลหุ้น Top 10 ใน sector
    คืนค่า DataFrame พร้อม return, technical signal, pattern score, reason
    """
    from src.data_pipeline import load_prices, duckdb_price_summary
    from src.indicators import add_technical_indicators, latest_technical_scores
    from src.config import SECTORS as SECTOR_MAP

    tickers = SECTOR_MAP.get(sector, [])
    if not tickers:
        return pd.DataFrame()

    prices     = load_prices(tuple(tickers))
    summary    = duckdb_price_summary(prices)
    indicators = add_technical_indicators(prices)
    technical  = latest_technical_scores(indicators)

    merged = (
        summary[["ticker","latest_close","return_1m","return_3m","volatility"]]
        .merge(technical[["ticker","technical_score","technical_signal","rsi"]], on="ticker")
    )

    # แยกหุ้นที่มีข้อมูลครบ vs ไม่ครบ
    has_data = (
        merged["latest_close"].notna() & (merged["latest_close"] > 0) &
        merged["return_1m"].notna() &
        merged["technical_score"].notna()
    )
    excluded = merged[~has_data]["ticker"].tolist()
    merged   = merged[has_data].copy()

    if excluded:
        merged.attrs["excluded"] = excluded

    # Momentum Score = Return 1M (40%) + Technical Score (60%)
    merged["momentum_score"] = (
        merged["return_1m"].clip(-20,20) / 20 * 40 +
        merged["technical_score"] / 100 * 60
    ).round(1)

    # สร้างเหตุผลสั้นๆ ว่าทำไมมาแรง
    def make_reason(row):
        reasons = []
        if row["return_1m"] >= 5:        reasons.append(f"ผลตอบแทน 1 เดือนสูง ({row['return_1m']:+.1f}%)")
        elif row["return_3m"] >= 10:     reasons.append(f"ผลตอบแทน 3 เดือนดี ({row['return_3m']:+.1f}%)")
        elif row["return_1m"] < -5:      reasons.append(f"ราคาปรับตัวลง ({row['return_1m']:+.1f}%)")
        if row["technical_score"] >= 65: reasons.append("Technical signal แข็งแกร่ง")
        elif row["technical_score"] < 45:reasons.append("Technical signal อ่อนแอ")
        if row["rsi"] < 35:              reasons.append("RSI Oversold (โอกาสฟื้น)")
        elif row["rsi"] > 70:            reasons.append("RSI Overbought (ระวังปรับฐาน)")
        if row["volatility"] > 50:       reasons.append("ความผันผวนสูงมาก")
        return " • ".join(reasons) if reasons else "Momentum โดยรวมอยู่ในระดับกลาง"

    merged["reason"] = merged.apply(make_reason, axis=1)

    return merged.sort_values("momentum_score", ascending=False).head(10)


@st.cache_data(ttl=3600, show_spinner=False)
def ai_sector_commentary(sector: str, screening_df: pd.DataFrame) -> str:
    """AI สรุปภาพรวม sector และหุ้นที่น่าสนใจ"""
    if screening_df.empty:
        return "ไม่มีข้อมูล"

    rows_text = "\n".join([
        f"- {r['ticker']}: Return 1M {r['return_1m']:+.1f}%, "
        f"Technical {r['technical_score']:.0f}/100, "
        f"Signal: {r['technical_signal']}"
        for _, r in screening_df.iterrows()
    ])

    prompt = f"""
คุณเป็น AI นักวิเคราะห์หุ้นมืออาชีพ วิเคราะห์ Top 10 หุ้นใน sector {sector} ต่อไปนี้:

{rows_text}

สรุปในรูปแบบ:

## 🏭 ภาพรวม {sector} Sector
(2-3 ประโยค สรุปภาพรวม)

## 🚀 หุ้นที่กำลังมาแรง
- (ระบุชื่อหุ้นและเหตุผลสั้นๆ)

## ⚠️ หุ้นที่ควรระวัง
- (ระบุชื่อหุ้นและเหตุผลสั้นๆ)

## 💡 สรุปคำแนะนำ
(1-2 ประโยค)

ตอบภาษาไทย กระชับ อ่านง่าย
"""
    return _call_groq(prompt, max_tokens=800)


# ─── Market News Feed (Tab 1) ──────────────────────────────────────────────────
MARKET_TICKERS = ["SPY", "QQQ"]  # ดึงข่าวตลาดภาพรวม

@st.cache_data(ttl=1800, show_spinner=False)
def get_market_news(limit_per_ticker: int = 5) -> list[dict]:
    """
    ดึงข่าวตลาดภาพรวมจาก SPY + QQQ
    คืนค่า list of dict: title, url, pub_date
    """
    all_news = []
    seen_titles = set()
    for ticker in MARKET_TICKERS:
        try:
            raw = yf.Ticker(ticker).news or []
            for item in raw[:limit_per_ticker]:
                if not isinstance(item, dict):
                    continue
                cnt   = item.get("content", item) if isinstance(item.get("content"), dict) else item
                title = cnt.get("title", item.get("title", "")) or ""
                url   = cnt.get("canonicalUrl", {}).get("url", "") or item.get("link", "") or ""
                pub   = str(cnt.get("pubDate", ""))[:10]
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    all_news.append({"title": title, "url": url, "pub_date": pub})
        except Exception:
            continue
    return all_news


@st.cache_data(ttl=3600, show_spinner=False)
def summarize_market_news(news_list: list[dict]) -> list[dict]:
    """
    ให้ AI สรุปแต่ละข่าวตลาดเป็น 2-3 ประโยค
    คืนค่า list of dict เดิม + เพิ่ม summary
    """
    if not news_list:
        return []

    headlines_text = "\n".join([
        f"{i+1}. {n['title']}" for i, n in enumerate(news_list)
    ])

    prompt = f"""
คุณเป็น AI นักวิเคราะห์ตลาดหุ้น สรุปข่าวตลาดต่อไปนี้แต่ละข่าวเป็นภาษาไทย

{headlines_text}

ตอบในรูปแบบ JSON array เท่านั้น ไม่มี markdown หรือ backticks:
[
  {{
    "index": 1,
    "summary": "สรุปข่าวนี้ 3-4 ประโยค: (1) เกิดอะไรขึ้น (2) ทำไมถึงสำคัญ (3) ผลกระทบต่อตลาดหรือนักลงทุน (4) แนวโน้มที่คาด"
  }}
]

กฎ:
- สรุปทุกข่าว ครบตามจำนวน
- แต่ละข่าวสรุป 2-3 ประโยค ไม่สั้นหรือยาวเกินไป
- ตอบ JSON เท่านั้น
"""
    raw = _call_groq(prompt, max_tokens=2000)
    try:
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        summaries = json.loads(text)
        # map summary กลับเข้า news_list
        summary_map = {s["index"]: s["summary"] for s in summaries if "index" in s}
        result = []
        for i, n in enumerate(news_list):
            n_copy = dict(n)
            n_copy["summary"] = summary_map.get(i+1, "ไม่สามารถสรุปได้")
            result.append(n_copy)
        return result
    except Exception:
        # fallback — ไม่มี summary
        return [{**n, "summary": ""} for n in news_list]
