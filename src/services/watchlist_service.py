import pandas as pd

from src.data_sources.market_data import normalize_symbol
from src.database.repositories import add_watchlist as _add_watchlist
from src.database.repositories import get_watchlist_snapshot, list_watchlist, remove_watchlist
from src.services.stock_service import get_quotes


def add_watchlist(symbol: str, note: str = "") -> None:
    _add_watchlist(normalize_symbol(symbol), note)


def refresh_watchlist() -> tuple[list[str], list[str]]:
    """Refresh all watchlist quotes one by one and return successes and failures."""
    symbols = list_watchlist()["symbol"].tolist()
    succeeded, failed = [], []
    for symbol in symbols:
        try:
            get_quotes(symbol, refresh=True)
            succeeded.append(symbol)
        except Exception as exc:
            failed.append(f"{symbol}：{exc}")
    return succeeded, failed

__all__ = ["add_watchlist", "list_watchlist", "remove_watchlist", "get_watchlist_snapshot", "refresh_watchlist"]
