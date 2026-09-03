import pandas as pd

from src.analysis.technical_indicators import add_technical_indicators


def test_indicators_add_expected_columns():
    dates = pd.date_range("2024-01-01", periods=80)
    data = pd.DataFrame({"trade_date": dates, "close": range(10, 90), "high": range(11, 91), "low": range(9, 89)})
    result = add_technical_indicators(data)
    assert {"ma5", "dif", "dea", "macd", "k", "d", "j", "rsi14"}.issubset(result.columns)
    assert pd.notna(result.iloc[-1]["ma20"])
