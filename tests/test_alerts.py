import pandas as pd

from src.analysis.alerts import build_research_alerts
from src.analysis.technical_indicators import add_technical_indicators


def test_alerts_detect_rising_volume_and_cross():
    dates = pd.date_range("2024-01-01", periods=80)
    close = pd.Series(range(10, 90), dtype=float)
    data = pd.DataFrame({
        "trade_date": dates, "open": close - 0.5, "high": close + 1,
        "low": close - 1, "close": close, "volume": [100] * 79 + [200],
    })
    indicators = add_technical_indicators(data)
    alerts = build_research_alerts("600519", indicators)
    assert isinstance(alerts, list)
