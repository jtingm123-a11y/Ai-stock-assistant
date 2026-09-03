from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests


MARKETS = (
    ("中国上证指数", "000001.SS"),
    ("中国深证成指", "399001.SZ"),
    ("香港恒生指数", "^HSI"),
    ("美国标普500", "^GSPC"),
    ("美国纳斯达克", "^IXIC"),
    ("日本日经225", "^N225"),
    ("欧洲斯托克50", "^STOXX50E"),
    ("英国富时100", "^FTSE"),
    ("德国DAX", "^GDAXI"),
    ("法国CAC40", "^FCHI"),
    ("韩国综合指数", "^KS11"),
)


def _fetch_market_quote(item: tuple[str, str]) -> dict:
    name, symbol = item
    response = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"range": "5d", "interval": "1d"},
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    result = response.json()["chart"]["result"][0]
    meta = result.get("meta", {})
    price = meta.get("regularMarketPrice")
    previous = meta.get("previousClose") or meta.get("chartPreviousClose")
    if price is None or previous in (None, 0):
        raise ValueError("行情数据不完整")
    price = float(price)
    previous = float(previous)
    return {
        "市场": name,
        "代码": symbol,
        "最新": price,
        "涨跌": price - previous,
        "涨跌幅": (price - previous) / previous * 100,
    }


def fetch_global_market_quotes() -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_fetch_market_quote, item): item for item in MARKETS}
        for future in as_completed(futures):
            name, _ = futures[future]
            try:
                rows.append(future.result())
            except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
                errors.append(f"{name}：{exc}")
    order = {name: index for index, (name, _) in enumerate(MARKETS)}
    quotes = pd.DataFrame(rows)
    if not quotes.empty:
        quotes["_order"] = quotes["市场"].map(order)
        quotes = quotes.sort_values("_order").drop(columns="_order")
    return quotes, errors
