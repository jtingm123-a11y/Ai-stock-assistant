"""Derived trend, risk, and price-volume signals for individual research."""

from __future__ import annotations

import pandas as pd


def _series(data: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(data.get(column, pd.Series(dtype=float)), errors="coerce")


def build_trend_signal(data: pd.DataFrame) -> dict:
    if data.empty:
        return {"status": "数据不足", "detail": "暂无行情数据可判断趋势。", "score": None}
    frame = data.sort_values("trade_date").reset_index(drop=True)
    close = _series(frame, "close")
    ma20 = _series(frame, "ma20")
    ma60 = _series(frame, "ma60")
    latest_close = close.iloc[-1]
    latest_ma20 = ma20.iloc[-1] if not ma20.empty else None
    latest_ma60 = ma60.iloc[-1] if not ma60.empty else None
    ma20_slope = ma20.iloc[-1] - ma20.iloc[-21] if len(ma20.dropna()) >= 21 else None
    if pd.isna(latest_close) or pd.isna(latest_ma20):
        return {"status": "数据不足", "detail": "历史数据不足 20 个交易日，暂不判断趋势。", "score": None}
    if latest_close >= latest_ma20 and (latest_ma60 is None or pd.isna(latest_ma60) or latest_ma20 >= latest_ma60):
        status = "上升趋势"
    elif latest_close < latest_ma20 and (latest_ma60 is None or pd.isna(latest_ma60) or latest_ma20 < latest_ma60):
        status = "下降趋势"
    else:
        status = "震荡趋势"
    distance = (latest_close / latest_ma20 - 1) * 100
    slope_text = "MA20 向上" if ma20_slope is not None and ma20_slope > 0 else "MA20 走平或向下"
    return {
        "status": status,
        "detail": f"收盘价较 MA20 {'高' if distance >= 0 else '低'} {abs(distance):.2f}%，{slope_text}。",
        "score": float(distance),
    }


def build_risk_metrics(data: pd.DataFrame) -> dict:
    frame = data.sort_values("trade_date")
    close = _series(frame, "close").dropna()
    if len(close) < 2:
        return {"return_20d": None, "return_60d": None, "volatility_20d": None, "drawdown_60d": None}
    return {
        "return_20d": (close.iloc[-1] / close.iloc[max(0, len(close) - 21)] - 1) * 100,
        "return_60d": (close.iloc[-1] / close.iloc[max(0, len(close) - 61)] - 1) * 100,
        "volatility_20d": close.pct_change().tail(20).std() * 100,
        "drawdown_60d": (close.tail(60) / close.tail(60).cummax() - 1).min() * 100,
    }


def build_volume_signal(data: pd.DataFrame) -> dict:
    frame = data.sort_values("trade_date")
    close = _series(frame, "close")
    volume = _series(frame, "volume")
    if len(frame) < 6 or volume.iloc[-1] <= 0:
        return {"status": "数据不足", "detail": "成交量数据不足，暂无法判断量价关系。"}
    average_volume = volume.iloc[-6:-1].mean()
    ratio = volume.iloc[-1] / average_volume if average_volume > 0 else None
    change = close.iloc[-1] - close.iloc[-2]
    if ratio is None:
        status = "数据不足"
    elif ratio >= 1.5 and change > 0:
        status = "上涨放量"
    elif ratio >= 1.5 and change < 0:
        status = "下跌放量"
    elif ratio <= 0.7:
        status = "缩量整理"
    else:
        status = "量价平稳"
    detail = "--" if ratio is None else f"今日成交量为近 5 日均量的 {ratio:.2f} 倍。"
    return {"status": status, "detail": detail}
