import pandas as pd
import requests
import re

from src.data_sources.market_data import normalize_symbol, _market_prefix


def fetch_stock_profile(symbol: str) -> dict:
    """Get available basic profile fields. Fields vary slightly by data provider version."""
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("尚未安装 akshare，请先执行 pip install -r requirements.txt") from exc
    symbol = normalize_symbol(symbol)
    profile = {"symbol": symbol, "name": "--", "industry": "--", "market": "A股", "listing_date": "--"}
    try:
        info = ak.stock_individual_info_em(symbol=symbol)
        if isinstance(info, pd.DataFrame) and {"item", "value"}.issubset(info.columns):
            values = dict(zip(info["item"], info["value"]))
            profile["name"] = str(values.get("股票简称", profile["name"]))
            profile["industry"] = str(values.get("行业", profile["industry"]))
            profile["listing_date"] = str(values.get("上市时间", profile["listing_date"]))
    except Exception:
        pass
    if profile["name"] == "--":
        profile["name"] = _fetch_fallback_name(symbol)
    return profile


def _fetch_fallback_name(symbol: str) -> str:
    """Try lightweight quote endpoints when the AkShare profile endpoint is unavailable."""
    market_symbol = f"{_market_prefix(symbol)}{symbol}"
    try:
        response = requests.get(
            "https://qt.gtimg.cn/q=" + market_symbol,
            timeout=10,
        )
        response.encoding = "gbk"
        fields = response.text.split("~")
        if len(fields) > 1 and fields[1].strip():
            return fields[1].strip()
    except requests.RequestException:
        pass
    try:
        response = requests.get(
            "https://hq.sinajs.cn/list=" + market_symbol,
            headers={"Referer": "https://finance.sina.com.cn/"},
            timeout=10,
        )
        response.encoding = "gbk"
        match = re.search(r'="([^,]+)', response.text)
        if match and match.group(1).strip():
            return match.group(1).strip()
    except requests.RequestException:
        pass
    return "--"
