import pandas as pd

from src.analysis.scoring import calculate_stock_score
from src.data_sources.financial_data import fetch_financial_indicators


def get_stock_score(
    symbol: str, indicators: pd.DataFrame, refresh: bool = False
) -> tuple[dict, pd.DataFrame | None, str | None]:
    """Fetch optional financial data, then calculate an explainable composite score."""
    financials = None
    finance_error = None
    try:
        financials = fetch_financial_indicators(symbol, refresh=refresh)
    except Exception as exc:
        finance_error = str(exc)
    return calculate_stock_score(indicators, financials), financials, finance_error
