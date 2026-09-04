"""Local, deterministic research alerts derived from cached market data."""

from __future__ import annotations

import pandas as pd

from src.analysis.research_signals import build_risk_metrics, build_support_resistance
from src.analysis.rule_engine import build_technical_signals


def build_research_alerts(symbol: str, data: pd.DataFrame) -> list[dict]:
    if data.empty:
        return []
    alerts: list[dict] = []
    latest = data.sort_values("trade_date").iloc[-1]
    trade_date = str(latest["trade_date"])[:10]
    for signal in build_technical_signals(data):
        if signal["result"] in {"金叉", "死叉"}:
            alerts.append({
                "symbol": symbol, "trade_date": trade_date, "category": signal["category"],
                "level": "关注" if signal["result"] == "金叉" else "风险",
                "message": f"{signal['category']}{signal['result']}：{signal['detail']}",
            })
    levels = build_support_resistance(data)
    close = levels["close"]
    if close and levels["support_20"] and close < levels["support_20"]:
        alerts.append({"symbol": symbol, "trade_date": trade_date, "category": "支撑位",
                       "level": "风险", "message": "收盘价跌破 20 日支撑位。"})
    elif close and levels["resistance_20"] and (levels["resistance_20"] / close - 1) <= 0.03:
        alerts.append({"symbol": symbol, "trade_date": trade_date, "category": "压力位",
                       "level": "关注", "message": "当前价格接近 20 日压力位。"})
    risk = build_risk_metrics(data)
    if risk["drawdown_60d"] is not None and risk["drawdown_60d"] <= -20:
        alerts.append({"symbol": symbol, "trade_date": trade_date, "category": "回撤",
                       "level": "风险", "message": f"近 60 日最大回撤达到 {risk['drawdown_60d']:.2f}%。"})
    return alerts
