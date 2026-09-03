import pandas as pd

from src.data_sources.market_data import normalize_symbol


def fetch_financial_indicators(symbol: str) -> pd.DataFrame:
    """Fetch a compact financial-indicator table; provider availability may vary."""
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("尚未安装 akshare，请先执行 pip install -r requirements.txt") from exc
    symbol = normalize_symbol(symbol)
    try:
        data = ak.stock_financial_analysis_indicator(symbol=symbol, start_year="2020")
    except Exception as exc:
        raise RuntimeError(f"财务数据获取失败：{exc}") from exc
    if data is None or data.empty:
        raise RuntimeError("未取得财务指标数据。")
    return data
