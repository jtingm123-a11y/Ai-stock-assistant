import pandas as pd

from src.analysis.rule_engine import build_technical_signals


def test_rule_engine_detects_golden_cross():
    data = pd.DataFrame({
        "trade_date": pd.date_range("2024-01-01", periods=2),
        "close": [10, 11], "ma20": [10, 10], "ma5": [9, 11],
        "dif": [-1, 1], "dea": [0, 0], "k": [10, 80], "d": [20, 30],
    })
    signals = build_technical_signals(data)
    assert any(item["result"] == "金叉" for item in signals)
