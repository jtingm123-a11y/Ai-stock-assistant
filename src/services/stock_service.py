from datetime import datetime
import logging

import pandas as pd

from src.analysis.technical_indicators import add_technical_indicators
from src.data_sources.market_data import fetch_daily_quotes, get_last_source, normalize_symbol
from src.data_sources.stock_info import fetch_stock_profile
from src.database.repositories import load_quotes, save_quotes


logger = logging.getLogger(__name__)


def get_quotes(symbol: str, refresh: bool = False) -> pd.DataFrame:
    symbol = normalize_symbol(symbol)
    cached = load_quotes(symbol)
    # Daily data should be checked again on a new calendar day so a stale
    # cache does not make a newly available trading day invisible.
    cache_is_stale = (
        not cached.empty
        and pd.to_datetime(cached["trade_date"]).max().date() < datetime.now().date()
    )
    if refresh or cached.empty or cache_is_stale:
        try:
            quotes = fetch_daily_quotes(symbol)
        except Exception:
            if not cached.empty:
                from src.data_sources.market_data import set_last_source

                set_last_source("本地缓存（刷新失败）")
                logger.warning("刷新 %s 失败，继续使用本地缓存数据。", symbol, exc_info=True)
                return cached
            raise
        save_quotes(symbol, quotes)
        return quotes
    from src.data_sources.market_data import set_last_source

    set_last_source("本地缓存")
    return cached


def get_quote_source() -> str:
    return get_last_source()


def get_analysis(symbol: str, refresh: bool = False) -> tuple[dict, pd.DataFrame]:
    symbol = normalize_symbol(symbol)
    quotes = get_quotes(symbol, refresh=refresh)
    return fetch_stock_profile(symbol), add_technical_indicators(quotes)
