from datetime import datetime
import logging
import json
import re

import pandas as pd
import requests

from config.settings import DEFAULT_ADJUST, DEFAULT_HISTORY_START


logger = logging.getLogger(__name__)
_last_source = "本地缓存"


def get_last_source() -> str:
    return _last_source


def normalize_symbol(symbol: str) -> str:
    value = str(symbol).strip()
    if not value.isdigit() or len(value) != 6:
        raise ValueError("请输入 6 位 A 股代码，例如 600519 或 000001。")
    return value


def fetch_daily_quotes(symbol: str, start_date: str = DEFAULT_HISTORY_START) -> pd.DataFrame:
    global _last_source
    symbol = normalize_symbol(symbol)
    end_date = datetime.now().strftime("%Y%m%d")
    errors: list[str] = []
    for source_name, source in (
        ("AkShare", lambda: _fetch_akshare(symbol, start_date, end_date)),
        ("腾讯财经", lambda: _fetch_tencent(symbol, start_date, end_date)),
        ("新浪财经", lambda: _fetch_sina(symbol, start_date, end_date)),
    ):
        try:
            result = source()
            if not result.empty:
                logger.info("股票 %s 使用%s行情源，获取 %s 条数据。", symbol, source_name, len(result))
                _last_source = source_name
                return result
        except Exception as exc:
            errors.append(f"{source_name}: {exc}")
            logger.warning("%s 获取 %s 失败：%s", source_name, symbol, exc)
    raise RuntimeError("行情获取失败，已尝试 AkShare、腾讯财经和新浪财经。请检查网络后重试。")


def _finalize_quotes(data: pd.DataFrame) -> pd.DataFrame:
    columns = ["trade_date", "open", "high", "low", "close", "volume", "amount",
               "turnover", "amplitude", "change_pct", "change_amount"]
    result = data.copy()
    for column in columns:
        if column not in result:
            result[column] = None
    result["trade_date"] = pd.to_datetime(result["trade_date"], errors="coerce")
    for column in columns[1:]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=["trade_date", "close"])
    result = result.sort_values("trade_date").drop_duplicates("trade_date")
    if result.empty:
        raise ValueError("数据源返回了空行情。")
    if result["change_pct"].isna().all():
        result["change_pct"] = result["close"].pct_change().mul(100)
    if result["change_amount"].isna().all():
        result["change_amount"] = result["close"].diff()
    return result[columns]


def _fetch_akshare(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    import akshare as ak

    raw = ak.stock_zh_a_hist(
        symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust=DEFAULT_ADJUST
    )
    mapping = {"日期": "trade_date", "开盘": "open", "最高": "high", "最低": "low",
               "收盘": "close", "成交量": "volume", "成交额": "amount", "换手率": "turnover",
               "振幅": "amplitude", "涨跌幅": "change_pct", "涨跌额": "change_amount"}
    return _finalize_quotes(raw.rename(columns=mapping))


def _market_prefix(symbol: str) -> str:
    return "sh" if symbol.startswith(("5", "6", "9")) else "sz"


def _fetch_tencent(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    market_symbol = f"{_market_prefix(symbol)}{symbol}"
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    response = requests.get(
        url,
        params={"param": f"{market_symbol},day,{start_date[:4]}-{start_date[4:6]}-{start_date[6:]},{end_date[:4]}-{end_date[4:6]}-{end_date[6:]},5000,qfq"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()["data"][market_symbol]
    rows = payload.get("qfqday") or payload.get("day") or []
    return _finalize_quotes(pd.DataFrame(rows, columns=["trade_date", "open", "close", "high", "low", "volume"]))


def _fetch_sina(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    market_symbol = f"{_market_prefix(symbol)}{symbol}"
    response = requests.get(
        "https://quotes.sina.cn/cn/api/jsonp_v2.php/var_data=/CN_MarketData.getKLineData",
        params={"symbol": market_symbol, "scale": 240, "ma": "no", "datalen": 1023},
        timeout=15,
    )
    response.raise_for_status()
    match = re.search(r"var_data=\((\[.*\])\);?", response.text, re.S)
    if not match:
        raise ValueError("新浪财经返回格式无法识别。")
    rows = json.loads(match.group(1))
    data = pd.DataFrame(rows).rename(
        columns={"day": "trade_date", "open": "open", "high": "high",
                 "low": "low", "close": "close", "volume": "volume"}
    )
    return _finalize_quotes(data)
