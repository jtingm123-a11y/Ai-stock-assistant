import json

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


def save_financial_cache(symbol: str, data: pd.DataFrame) -> None:
    payload = data.to_json(orient="split", date_format="iso")
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO financial_cache(symbol, payload, fetched_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)""",
            (symbol, payload),
        )


def load_financial_cache(symbol: str) -> tuple[pd.DataFrame | None, str | None]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT payload, fetched_at FROM financial_cache WHERE symbol = ?",
            (symbol,),
        ).fetchone()
    if row is None:
        return None, None
    try:
        return pd.read_json(row["payload"], orient="split"), row["fetched_at"]
    except (ValueError, TypeError, json.JSONDecodeError):
        return None, None


def save_score_history(symbol: str, trade_date: object, score: dict) -> None:
    sections = score["sections"]
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO score_history
               (symbol, trade_date, total, technical, financial, trend, risk, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, str(trade_date)[:10], score["total"],
             sections["技术面"]["score"], sections["财务面"]["score"],
             sections["趋势强度"]["score"], sections["风险指标"]["score"],
             score.get("confidence", "低")),
        )


def load_score_history(symbol: str, limit: int = 10) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM score_history WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
            conn, params=(symbol, limit),
        )


def save_signal_history(symbol: str, trade_date: object, signals: list[dict]) -> None:
    if not signals:
        return
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO technical_signal_history
               (symbol, trade_date, category, result, detail)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (symbol, str(trade_date)[:10], item["category"], item["result"], item.get("detail", ""))
                for item in signals
            ],
        )


def load_signal_history(symbol: str, limit: int = 50) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(
            """SELECT trade_date, category, result, detail, created_at
               FROM technical_signal_history
               WHERE symbol = ? ORDER BY trade_date DESC, created_at DESC LIMIT ?""",
            conn, params=(symbol, limit),
        )


def save_research_report(
    symbol: str, name: str, trade_date: object, score: dict, report: str
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO research_reports
               (symbol, name, trade_date, total_score, confidence, report)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (symbol, name, str(trade_date)[:10], score.get("total"),
             score.get("confidence", "低"), report),
        )
        return int(cursor.lastrowid)


def list_research_reports(symbol: str | None = None, limit: int = 50) -> pd.DataFrame:
    query = """SELECT id, symbol, name, trade_date, total_score, confidence, created_at
               FROM research_reports"""
    params: tuple[object, ...] = ()
    if symbol:
        query += " WHERE symbol = ?"
        params = (symbol,)
    query += " ORDER BY created_at DESC LIMIT ?"
    params += (limit,)
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def get_research_report(report_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM research_reports WHERE id = ?", (report_id,)
        ).fetchone()
    return dict(row) if row else None


def save_research_alerts(alerts: list[dict]) -> None:
    if not alerts:
        return
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO research_alerts
               (symbol, trade_date, category, level, message)
               VALUES (?, ?, ?, ?, ?)""",
            [(item["symbol"], item["trade_date"], item["category"], item["level"], item["message"])
             for item in alerts],
        )


def list_research_alerts(symbol: str | None = None, limit: int = 100) -> pd.DataFrame:
    query = "SELECT * FROM research_alerts"
    params: tuple[object, ...] = ()
    if symbol:
        query += " WHERE symbol = ?"
        params = (symbol,)
    query += " ORDER BY created_at DESC LIMIT ?"
    params += (limit,)
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


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
