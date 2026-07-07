"""
src/storage.py
MongoDB — เก็บ Watchlist, Search History
Snowflake — เก็บ Indicators, AI Sentiment, Market Snapshots
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.config import USER_ID


# ════════════════════════════════════════════════════════════════════════════
# MongoDB
# ════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_mongo_client():
    try:
        from pymongo import MongoClient
        uri = st.secrets.get("MONGO_URI", "")
        if not uri:
            return None
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return client
    except Exception as e:
        st.warning(f"MongoDB: {e}")
        return None


def _get_mongo_db():
    client = get_mongo_client()
    if client is None:
        return None
    return client[st.secrets.get("MONGO_DB", "ai_stock_db")]


def save_watchlist(tickers: list[str]) -> str:
    db = _get_mongo_db()
    if db is None:
        return "⚠️ Demo mode: MongoDB ไม่ได้เชื่อมต่อ"
    now = datetime.now(timezone.utc)
    db.watchlists.update_one(
        {"user_id": USER_ID},
        {"$set": {"tickers": tickers, "updated_at": now}},
        upsert=True,
    )
    db.search_history.insert_one({
        "user_id":     USER_ID,
        "tickers":     tickers,
        "searched_at": now,
    })
    return f"✅ บันทึก Watchlist {tickers} ลง MongoDB แล้ว"


def load_watchlist() -> list[str]:
    db = _get_mongo_db()
    if db is None:
        return []
    doc = db.watchlists.find_one({"user_id": USER_ID})
    return doc.get("tickers", []) if doc else []


def load_search_history(limit: int = 10) -> list[dict]:
    db = _get_mongo_db()
    if db is None:
        return []
    cursor = db.search_history.find(
        {"user_id": USER_ID},
        sort=[("searched_at", -1)],
        limit=limit
    )
    return [{"tickers": d["tickers"], "time": d["searched_at"]} for d in cursor]


# ════════════════════════════════════════════════════════════════════════════
# Snowflake — Auto-reconnect via session_state
# ════════════════════════════════════════════════════════════════════════════

def _new_sf_conn():
    """สร้าง Snowflake connection ใหม่"""
    try:
        import snowflake.connector
        sf = st.secrets["snowflake"]
        return snowflake.connector.connect(
            account   = sf["account"],
            user      = sf["user"],
            password  = sf["password"],
            warehouse = sf["warehouse"],
            database  = sf["database"],
            schema    = sf["schema"],
        )
    except Exception as e:
        st.warning(f"Snowflake connect error: {e}")
        return None


def _get_sf_conn():
    """
    ดึง Snowflake connection พร้อม auto-reconnect
    เก็บใน session_state แทน cache_resource เพื่อให้ clear แล้ว reconnect ได้ทันที
    """
    conn = st.session_state.get("_sf_conn")

    # ยังไม่มี connection → สร้างใหม่
    if conn is None:
        conn = _new_sf_conn()
        st.session_state["_sf_conn"] = conn
        return conn

    # ทดสอบว่า token ยังใช้ได้ไหม
    try:
        conn.cursor().execute("SELECT 1")
        return conn
    except Exception as e:
        err = str(e)
        if "390114" in err or "Authentication token" in err or "08001" in err:
            # Token หมดอายุ → ปิด connection เก่า แล้ว reconnect
            try:
                conn.close()
            except Exception:
                pass
            new_conn = _new_sf_conn()
            st.session_state["_sf_conn"] = new_conn
            return new_conn
        return None


# alias สำหรับ backward compatibility (app.py เรียก snowflake_status ผ่าน _get_sf_conn อยู่แล้ว)
def get_snowflake_conn():
    return _get_sf_conn()


def _sf_execute(sql: str, params: list | None = None) -> bool:
    conn = _get_sf_conn()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.warning(f"Snowflake execute: {e}")
        return False


def _sf_query(sql: str, params: list | None = None) -> pd.DataFrame:
    conn = _get_sf_conn()
    if conn is None:
        return pd.DataFrame()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        df = cur.fetch_pandas_all()
        cur.close()
        return df
    except Exception as e:
        st.warning(f"Snowflake query: {e}")
        return pd.DataFrame()


def setup_snowflake_tables() -> None:
    _sf_execute("""
        CREATE TABLE IF NOT EXISTS technical_metrics (
            id               STRING DEFAULT UUID_STRING(),
            ticker           STRING,
            metric_date      DATE,
            ma20             FLOAT,
            ma50             FLOAT,
            rsi              FLOAT,
            macd             FLOAT,
            macd_signal      FLOAT,
            bb_upper         FLOAT,
            bb_lower         FLOAT,
            technical_score  FLOAT,
            technical_signal STRING,
            saved_at         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)
    _sf_execute("""
        CREATE TABLE IF NOT EXISTS ai_sentiment (
            id               STRING DEFAULT UUID_STRING(),
            ticker           STRING,
            analysis_date    DATE DEFAULT CURRENT_DATE(),
            sentiment_label  STRING,
            sentiment_score  FLOAT,
            recommendation   STRING,
            combined_score   FLOAT,
            ai_summary       STRING,
            saved_at         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)


def save_analysis_to_snowflake(
    technical: pd.DataFrame,
    ai_result: pd.DataFrame,
) -> bool:
    conn = _get_sf_conn()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        for _, row in technical.iterrows():
            cur.execute("""
                INSERT INTO technical_metrics
                    (ticker, metric_date, ma20, ma50, rsi, macd_signal, bb_upper, bb_lower, technical_score, technical_signal)
                VALUES (%s, CURRENT_DATE(), %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                row["ticker"], row.get("ma20"), row.get("ma50"),
                row.get("rsi"), row.get("macd_score"), row.get("bb_upper"),
                row.get("bb_lower"), row.get("technical_score"), row.get("technical_signal"),
            ])
        if not ai_result.empty:
            for _, row in ai_result.iterrows():
                cur.execute("""
                    INSERT INTO ai_sentiment (ticker, sentiment_label, sentiment_score, recommendation, combined_score, ai_summary)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [
                    row["ticker"], row.get("sentiment_label"), row.get("sentiment_score"),
                    row.get("recommendation"), row.get("combined_score"),
                    str(row.get("ai_summary", ""))[:500],
                ])
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.warning(f"Save analysis error: {e}")
        return False


def mongo_status() -> str:
    client = get_mongo_client()
    return "✅ MongoDB เชื่อมต่อแล้ว" if client else "⚠️ MongoDB ไม่ได้เชื่อมต่อ"


def snowflake_status() -> str:
    conn = _get_sf_conn()
    return "✅ Snowflake เชื่อมต่อแล้ว" if conn else "⚠️ Snowflake ไม่ได้เชื่อมต่อ"


# ════════════════════════════════════════════════════════════════════════════
# Analysis History (MongoDB)
# ════════════════════════════════════════════════════════════════════════════

def save_analysis_history(tickers: list[str], results: list[dict]) -> str:
    db = _get_mongo_db()
    if db is None:
        return "⚠️ MongoDB ไม่ได้เชื่อมต่อ"
    now = datetime.now(timezone.utc)
    db.analysis_history.insert_one({
        "user_id":     USER_ID,
        "tickers":     tickers,
        "results":     results,
        "analyzed_at": now,
    })
    return f"✅ บันทึกประวัติการวิเคราะห์ {tickers} ลง MongoDB แล้ว"


def load_analysis_history(limit: int = 5) -> list[dict]:
    db = _get_mongo_db()
    if db is None:
        return []
    cursor = db.analysis_history.find(
        {"user_id": USER_ID},
        sort=[("analyzed_at", -1)],
        limit=limit
    )
    return list(cursor)


def save_market_snapshot(index_data: dict) -> bool:
    conn = _get_sf_conn()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_snapshots (
                snapshot_date  DATE DEFAULT CONVERT_TIMEZONE('Asia/Bangkok', CURRENT_TIMESTAMP())::DATE,
                sp500          FLOAT,
                nasdaq         FLOAT,
                dow_jones      FLOAT,
                vix            FLOAT,
                sp500_chg_pct  FLOAT,
                nasdaq_chg_pct FLOAT,
                dow_chg_pct    FLOAT,
                vix_chg_pct    FLOAT,
                saved_at       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
            )
        """)
        cur.execute("SELECT COUNT(*) FROM market_snapshots WHERE snapshot_date = CONVERT_TIMEZONE('Asia/Bangkok', CURRENT_TIMESTAMP())::DATE")
        if cur.fetchone()[0] > 0:
            cur.close()
            return False
        cur.execute("""
            INSERT INTO market_snapshots
                (snapshot_date, sp500, nasdaq, dow_jones, vix,
                 sp500_chg_pct, nasdaq_chg_pct, dow_chg_pct, vix_chg_pct)
            VALUES (CONVERT_TIMEZONE('Asia/Bangkok', CURRENT_TIMESTAMP())::DATE,
                    %s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            index_data.get("^GSPC", {}).get("price", 0),
            index_data.get("^IXIC", {}).get("price", 0),
            index_data.get("^DJI",  {}).get("price", 0),
            index_data.get("^VIX",  {}).get("price", 0),
            index_data.get("^GSPC", {}).get("chg_pct", 0),
            index_data.get("^IXIC", {}).get("chg_pct", 0),
            index_data.get("^DJI",  {}).get("chg_pct", 0),
            index_data.get("^VIX",  {}).get("chg_pct", 0),
        ])
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.warning(f"Market snapshot save error: {e}")
        return False
