import pandas as pd

from src.database.connection import get_connection


QUOTE_COLUMNS = ["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount", "turnover", "amplitude", "change_pct", "change_amount"]


def save_quotes(symbol: str, quotes: pd.DataFrame) -> None:
    if quotes.empty:
        return
    payload = quotes.copy()
    payload["symbol"] = symbol
    payload["trade_date"] = pd.to_datetime(payload["trade_date"]).dt.strftime("%Y-%m-%d")
    payload = payload.reindex(columns=QUOTE_COLUMNS)
    with get_connection() as conn:
        payload.to_sql("_quotes_staging", conn, if_exists="replace", index=False)
        conn.execute(
            """INSERT OR REPLACE INTO daily_quotes
               (symbol, trade_date, open, high, low, close, volume, amount, turnover, amplitude, change_pct, change_amount)
               SELECT symbol, trade_date, open, high, low, close, volume, amount, turnover, amplitude, change_pct, change_amount
               FROM _quotes_staging"""
        )
        conn.execute("DROP TABLE _quotes_staging")


def load_quotes(symbol: str) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM daily_quotes WHERE symbol = ? ORDER BY trade_date", conn, params=(symbol,), parse_dates=["trade_date"]
        )


def add_watchlist(symbol: str, note: str = "") -> None:
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO watchlist(symbol, note) VALUES (?, ?)", (symbol, note))


def remove_watchlist(symbol: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))


def list_watchlist() -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query("SELECT symbol, note, created_at FROM watchlist ORDER BY created_at DESC", conn)


def get_watchlist_snapshot() -> pd.DataFrame:
    """Return the newest cached quote for every watchlist stock."""
    query = """
        SELECT w.symbol, w.note, w.created_at,
               q.trade_date, q.close, q.change_pct, q.volume, q.amount, q.updated_at
        FROM watchlist AS w
        LEFT JOIN daily_quotes AS q
          ON q.symbol = w.symbol
         AND q.trade_date = (SELECT MAX(trade_date) FROM daily_quotes WHERE symbol = w.symbol)
        ORDER BY w.created_at DESC
    """
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


def get_local_market_overview() -> dict:
    """Summarize cache and the latest available watchlist changes."""
    query = """
        SELECT
            (SELECT COUNT(DISTINCT symbol) FROM daily_quotes) AS cached_symbols,
            MAX(q.trade_date) AS latest_date,
            AVG(q.change_pct) AS average_change,
            SUM(CASE WHEN q.change_pct > 0 THEN 1 ELSE 0 END) AS rising_count,
            SUM(CASE WHEN q.change_pct < 0 THEN 1 ELSE 0 END) AS falling_count,
            SUM(CASE WHEN q.change_pct = 0 THEN 1 ELSE 0 END) AS flat_count
        FROM watchlist AS w
        LEFT JOIN daily_quotes AS q
          ON q.symbol = w.symbol
         AND q.trade_date = (
             SELECT MAX(q2.trade_date) FROM daily_quotes AS q2 WHERE q2.symbol = w.symbol
         )
    """
    with get_connection() as conn:
        row = conn.execute(query).fetchone()
    return {
        "cached_symbols": int(row["cached_symbols"] or 0),
        "latest_date": row["latest_date"],
        "average_change": row["average_change"],
        "rising_count": int(row["rising_count"] or 0),
        "falling_count": int(row["falling_count"] or 0),
        "flat_count": int(row["flat_count"] or 0),
    }


def list_recent_research(limit: int = 6) -> pd.DataFrame:
    query = """
        SELECT q.symbol, q.trade_date, q.close, q.change_pct, q.updated_at
        FROM daily_quotes AS q
        WHERE q.trade_date = (
            SELECT MAX(q2.trade_date) FROM daily_quotes AS q2 WHERE q2.symbol = q.symbol
        )
        AND q.updated_at = (
            SELECT MAX(q3.updated_at) FROM daily_quotes AS q3
            WHERE q3.symbol = q.symbol AND q3.trade_date = q.trade_date
        )
        GROUP BY symbol
        ORDER BY q.updated_at DESC
        LIMIT ?
    """
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=(limit,))
