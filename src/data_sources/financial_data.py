import pandas as pd

from src.data_sources.market_data import normalize_symbol
from src.database.repositories import load_financial_cache, save_financial_cache


def fetch_financial_indicators(
    symbol: str, refresh: bool = False, max_age_hours: int = 24
) -> pd.DataFrame:
    """Fetch a compact financial-indicator table; provider availability may vary."""
    symbol = normalize_symbol(symbol)
    if not refresh:
        cached, fetched_at = load_financial_cache(symbol)
        if cached is not None and fetched_at:
            age = pd.Timestamp.now() - pd.Timestamp(fetched_at)
            if age <= pd.Timedelta(hours=max_age_hours):
                return cached
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("尚未安装 akshare，请先执行 pip install -r requirements.txt") from exc
    try:
        data = ak.stock_financial_analysis_indicator(symbol=symbol, start_year="2020")
    except Exception as exc:
        raise RuntimeError(f"财务数据获取失败：{exc}") from exc
    if data is None or data.empty:
        raise RuntimeError("未取得财务指标数据。")
    save_financial_cache(symbol, data)
    return data
