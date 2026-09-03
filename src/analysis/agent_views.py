"""Deterministic analyst-role views built from the existing research signals."""

from __future__ import annotations

import pandas as pd


def _latest(indicators: pd.DataFrame) -> pd.Series:
    if indicators.empty:
        raise ValueError("没有可用于生成角色意见的行情数据。")
    return indicators.sort_values("trade_date").iloc[-1]


def build_agent_views(
    indicators: pd.DataFrame,
    score: dict,
    financials: pd.DataFrame | None = None,
) -> list[dict]:
    """Build explainable role opinions without requiring an LLM or API key."""
    last = _latest(indicators)
    sections = score["sections"]
    technical_score = sections["技术面"]["score"]
    financial_score = sections["财务面"]["score"]
    trend_score = sections["趋势强度"]["score"]
    risk_score = sections["风险指标"]["score"]

    close = last.get("close")
    ma20 = last.get("ma20")
    dif = last.get("dif")
    dea = last.get("dea")
    rsi = last.get("rsi14")
    technical_stance = "偏多" if technical_score >= 28 else "中性" if technical_score >= 16 else "偏空"
    trend_stance = "上行" if trend_score >= 14 else "震荡" if trend_score >= 8 else "偏弱"
    if pd.notna(close) and pd.notna(ma20):
        trend_detail = f"收盘价 {'位于' if close >= ma20 else '低于'} MA20（{float(ma20):.2f}）。"
    else:
        trend_detail = "均线数据不足，暂不对价格趋势做强判断。"
    momentum_detail = (
        f"MACD {'偏多' if pd.notna(dif) and pd.notna(dea) and dif >= dea else '偏弱'}"
        f"；RSI(14) 为 {float(rsi):.1f}。"
        if pd.notna(rsi)
        else "MACD 或 RSI 数据不足。"
    )

    finance_status = "数据充分且表现较好" if financial_score >= 20 else "数据有限或表现一般"
    if financials is None or financials.empty:
        finance_detail = "暂无可用财务数据，基本面结论需要后续补充。"
    else:
        finance_detail = "已使用最新财务报告期数据参与评分，请结合原始财报核验。"

    risk_stance = "风险相对可控" if risk_score >= 7 else "需要重点控制回撤与波动"
    risk_detail = "风险分项来自近 60 日回撤和近 20 日日波动率。"
    total = score["total"]
    decision = "进入重点跟踪" if total >= 70 else "保持观察" if total >= 50 else "暂不优先"

    return [
        {
            "role": "技术分析师",
            "tag": technical_stance,
            "color": "blue",
            "summary": f"技术面{technical_stance}，趋势{trend_stance}。",
            "details": f"{trend_detail}{momentum_detail}",
        },
        {
            "role": "基本面分析师",
            "tag": finance_status,
            "color": "green",
            "summary": f"财务面{finance_status}。",
            "details": finance_detail,
        },
        {
            "role": "风险经理",
            "tag": risk_stance,
            "color": "orange",
            "summary": risk_stance + "。",
            "details": risk_detail,
        },
        {
            "role": "研究主管",
            "tag": decision,
            "color": "purple",
            "summary": f"综合评分 {total:.1f}/100，建议{decision}。",
            "details": "这是基于历史数据的规则化协作结论，不代表未来收益，也不构成投资建议。",
        },
    ]
