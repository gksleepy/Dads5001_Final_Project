"""
src/data_pipeline.py
ดึงข้อมูลหุ้นจริงจาก Yahoo Finance ผ่าน yfinance
ใช้ DuckDB สำหรับ SQL summary
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from src.config import PRICE_PERIOD


# ─── yfinance — ดึงข้อมูลจริง ─────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def load_prices(tickers: tuple[str, ...]) -> pd.DataFrame:
    """
    ดึงราคาหุ้นจริงจาก Yahoo Finance
    คืนค่า DataFrame columns: date, ticker, open, high, low, close, volume
    """
    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        try:
            raw = yf.Ticker(ticker).history(period=PRICE_PERIOD)
            if raw.empty:
                continue
            # normalize timezone
            raw.index = raw.index.tz_localize(None) if raw.index.tz is None else raw.index.tz_convert(None)
            df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
            df = df.dropna(subset=["Open", "High", "Low", "Close"])
            df.columns = ["open", "high", "low", "close", "volume"]
            df["date"]   = df.index.normalize()
            df["ticker"] = ticker
            df = df.reset_index(drop=True)
            frames.append(df[["date", "ticker", "open", "high", "low", "close", "volume"]])
        except Exception as e:
            st.warning(f"⚠️ ดึงข้อมูล {ticker} ไม่สำเร็จ: {e}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


@st.cache_data(ttl=900, show_spinner=False)
def get_current_price(ticker: str) -> dict:
    """ดึงราคาปัจจุบัน + ข้อมูลพื้นฐาน"""
    try:
        t    = yf.Ticker(ticker)
        info = t.info
        fast = t.fast_info
        price     = fast.last_price or info.get("currentPrice", 0)
        prev      = fast.previous_close or info.get("previousClose", price)
        change    = price - prev
        change_pct= (change / prev * 100) if prev else 0
        return {
            "price":      round(price, 2),
            "change":     round(change, 2),
            "change_pct": round(change_pct, 2),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio":   info.get("trailingPE"),
            "name":       info.get("longName", ticker),
        }
    except Exception:
        return {"price": 0, "change": 0, "change_pct": 0, "market_cap": 0, "pe_ratio": None, "name": ticker}


# ─── DuckDB SQL summary ────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def duckdb_price_summary(prices: pd.DataFrame) -> pd.DataFrame:
    """
    คำนวณ summary สถิติด้วย DuckDB SQL
    คืนค่า: ticker, latest_close, latest_volume, return_1m, return_3m, return_6m, volatility
    """
    if prices.empty:
        return pd.DataFrame()

    con = duckdb.connect(database=":memory:")
    con.register("prices", prices)

    latest = con.execute("""
        WITH ranked AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
            FROM prices
        )
        SELECT ticker, date AS latest_date, close AS latest_close, volume AS latest_volume
        FROM ranked WHERE rn = 1
        ORDER BY ticker
    """).df()

    avg_vol = con.execute("""
        SELECT ticker, AVG(volume) AS avg_volume
        FROM prices
        GROUP BY ticker
        ORDER BY ticker
    """).df()

    returns = []
    for ticker, group in prices.sort_values("date").groupby("ticker"):
        close = group["close"].reset_index(drop=True)
        returns.append({
            "ticker":     ticker,
            "return_1m":  _period_return(close, 21),
            "return_3m":  _period_return(close, 63),
            "return_6m":  _period_return(close, 126),
            "return_1y":  _period_return(close, 252),
            "volatility": round(close.pct_change(fill_method=None).dropna().std() * np.sqrt(252) * 100, 2),
        })
    con.close()

    return latest.merge(avg_vol, on="ticker").merge(pd.DataFrame(returns), on="ticker")


def _period_return(close: pd.Series, days: int) -> float:
    if len(close) <= days:
        days = len(close) - 1
    if days <= 0:
        return 0.0
    return round((close.iloc[-1] / close.iloc[-days] - 1) * 100, 2)
