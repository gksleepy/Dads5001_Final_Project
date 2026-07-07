"""
src/ml_model.py
ML Pattern Analysis — ใช้ Random Forest เป็น Pattern Recognition Tool
(ไม่ใช่การทำนายทิศทาง แต่ช่วยดู pattern ทางสถิติ)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st


FEATURES = ["daily_return", "rsi", "macd", "macd_signal", "ma20", "ma50", "volume"]


@st.cache_data(ttl=3600, show_spinner=False)
def train_prediction_models(indicators: pd.DataFrame) -> pd.DataFrame:
    """
    วิเคราะห์ Pattern ด้วย Random Forest
    ผลลัพธ์คือ Pattern Score (0-100) ไม่ใช่การทำนายทิศทาง
    """
    if indicators.empty:
        return pd.DataFrame()

    rows = []
    for ticker, group in indicators.sort_values("date").groupby("ticker"):
        df = group.copy()
        df["target_up"] = (df["close"].shift(-1) > df["close"]).astype(int)
        model_df = df.dropna(subset=FEATURES + ["target_up"])

        if len(model_df) < 40:
            pattern_score = _heuristic_pattern_score(df)
            accuracy      = None
            model_name    = "Heuristic Pattern"
        else:
            pattern_score, accuracy, model_name = _random_forest_pattern(model_df)

        # Pattern interpretation
        if pattern_score >= 65:
            pattern_label = "Strong Pattern 📈"
            pattern_desc  = "ข้อมูลย้อนหลังแสดง pattern ที่มักตามด้วยราคาขึ้น"
        elif pattern_score >= 50:
            pattern_label = "Moderate Pattern 🔄"
            pattern_desc  = "ข้อมูลย้อนหลังแสดง pattern ที่ไม่ชัดเจน"
        else:
            pattern_label = "Weak Pattern 📉"
            pattern_desc  = "ข้อมูลย้อนหลังแสดง pattern ที่มักตามด้วยราคาลง"

        rows.append({
            "ticker":         ticker,
            "pattern_score":  round(float(pattern_score), 1),
            "pattern_label":  pattern_label,
            "pattern_desc":   pattern_desc,
            "model_name":     model_name,
            "backtest_accuracy": accuracy,
            # ยังคง field เดิมไว้เพื่อ compatibility
            "prediction_score":  round(float(pattern_score), 1),
            "predicted_label":   pattern_label,
            "probability_up":    round(float(pattern_score) / 100, 3),
        })

    return pd.DataFrame(rows)


def _random_forest_pattern(model_df: pd.DataFrame) -> tuple[float, float | None, str]:
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score
    except ImportError:
        return _heuristic_pattern_score(model_df), None, "Heuristic Pattern"

    split  = max(int(len(model_df) * 0.75), 30)
    train  = model_df.iloc[:split]
    test   = model_df.iloc[split:-1]
    latest = model_df.iloc[[-1]]

    clf = RandomForestClassifier(n_estimators=150, max_depth=4, random_state=42)
    clf.fit(train[FEATURES], train["target_up"])

    # Pattern score = probability จาก model (บอกความแข็งแกร่งของ pattern เท่านั้น)
    pattern_score = clf.predict_proba(latest[FEATURES])[0][1] * 100
    accuracy = (
        round(accuracy_score(test["target_up"], clf.predict(test[FEATURES])), 3)
        if len(test) > 0 else None
    )
    return pattern_score, accuracy, "Random Forest Pattern"


def _heuristic_pattern_score(df: pd.DataFrame) -> float:
    last  = df.dropna(subset=["rsi","macd","macd_signal","ma20","ma50"]).iloc[-1]
    score = 50.0
    score += 8 if last["close"] > last["ma20"] else -4
    score += 8 if last["ma20"]  > last["ma50"] else -4
    score += 8 if last["macd"]  > last["macd_signal"] else -5
    score += 4 if 45 <= last["rsi"] <= 65 else -3
    return float(np.clip(score, 15, 85))
