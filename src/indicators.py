"""
src/indicators.py
คำนวณ Technical Indicators: MA, RSI, MACD, Bollinger Bands
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st


@st.cache_data(ttl=900, show_spinner=False)
def add_technical_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    """เพิ่ม Technical Indicators ลงใน DataFrame"""
    if prices.empty:
        return prices

    frames = []
    for ticker, group in prices.sort_values("date").groupby("ticker"):
        df    = group.copy()
        close = df["close"]

        df["daily_return"] = close.pct_change(fill_method=None)

        # Moving Averages
        df["ma20"] = close.rolling(20, min_periods=5).mean()
        df["ma50"] = close.rolling(50, min_periods=10).mean()

        # Bollinger Bands
        rolling_std  = close.rolling(20, min_periods=5).std()
        df["bb_upper"] = df["ma20"] + 2 * rolling_std
        df["bb_lower"] = df["ma20"] - 2 * rolling_std

        # RSI
        df["rsi"] = _rsi(close)

        # MACD
        ema12          = close.ewm(span=12, adjust=False).mean()
        ema26          = close.ewm(span=26, adjust=False).mean()
        df["macd"]        = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"]   = df["macd"] - df["macd_signal"]

        frames.append(df)

    return pd.concat(frames, ignore_index=True)


@st.cache_data(ttl=900, show_spinner=False)
def latest_technical_scores(indicators: pd.DataFrame) -> pd.DataFrame:
    """คำนวณ Technical Score สำหรับหุ้นแต่ละตัว"""
    if indicators.empty:
        return pd.DataFrame()

    rows = []
    for ticker, group in indicators.sort_values("date").groupby("ticker"):
        last = group.dropna(subset=["rsi", "macd", "macd_signal", "ma20", "ma50"]).iloc[-1]

        rsi_score  = _score_rsi(last["rsi"])
        macd_score = 70 if last["macd"] > last["macd_signal"] else 35
        ma_score   = 75 if last["close"] > last["ma20"] > last["ma50"] else 45

        total  = round(np.mean([rsi_score, macd_score, ma_score]), 1)
        signal = "Bullish 🟢" if total >= 65 else "Bearish 🔴" if total < 45 else "Neutral 🟡"

        rows.append({
            "ticker":           ticker,
            "rsi":              round(float(last["rsi"]), 1),
            "rsi_score":        rsi_score,
            "macd_score":       macd_score,
            "ma_score":         ma_score,
            "technical_score":  total,
            "technical_signal": signal,
            "close":            round(float(last["close"]), 2),
            "ma20":             round(float(last["ma20"]), 2),
            "ma50":             round(float(last["ma50"]), 2),
            "bb_upper":         round(float(last["bb_upper"]), 2),
            "bb_lower":         round(float(last["bb_lower"]), 2),
        })

    return pd.DataFrame(rows)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def _score_rsi(value: float) -> int:
    if 45 <= value <= 65:  return 70
    if 35 <= value < 45 or 65 < value <= 75: return 55
    return 35
