import pandas as pd

from src.analysis.research_signals import (
    build_risk_metrics, build_support_resistance, build_trend_signal, build_volume_signal,
)


def _data(periods=80):
    dates = pd.date_range("2024-01-01", periods=periods)
    close = pd.Series(range(10, 10 + periods), dtype=float)
    return pd.DataFrame({
        "trade_date": dates,
        "close": close,
        "volume": [100] * (periods - 1) + [200],
        "ma20": close.rolling(20, min_periods=20).mean(),
        "ma60": close.rolling(60, min_periods=60).mean(),
    })


def test_trend_signal_detects_rising_market():
    result = build_trend_signal(_data())
    assert result["status"] == "上升趋势"


def test_risk_metrics_are_percentage_values():
    result = build_risk_metrics(_data())
    assert result["return_20d"] > 0
    assert result["drawdown_60d"] <= 0


def test_volume_signal_detects_rising_volume():
    assert build_volume_signal(_data())["status"] == "上涨放量"


def test_support_and_resistance_use_recent_extremes():
    result = build_support_resistance(_data())
    assert result["support_20"] < result["resistance_20"]
    assert result["distance_support"] > 0
