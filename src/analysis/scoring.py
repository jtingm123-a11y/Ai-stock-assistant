"""Explainable, rule-based stock scoring for the V1 research assistant."""

from __future__ import annotations

import re

import pandas as pd


WEIGHTS = {"technical": 40, "financial": 30, "trend": 20, "risk": 10}


def _number(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        value = re.sub(r"[% ,]", "", value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _latest_financial_row(financials: pd.DataFrame | None) -> pd.Series | None:
    if financials is None or financials.empty:
        return None
    data = financials.copy()
    for column in ("日期", "报告期", "报告日期"):
        if column in data.columns:
            data["_report_date"] = pd.to_datetime(data[column], errors="coerce")
            return data.sort_values("_report_date", ascending=False).iloc[0]
    return data.iloc[0]


def _financial_value(row: pd.Series | None, candidates: tuple[str, ...]) -> float | None:
    if row is None:
        return None
    for name in candidates:
        if name in row.index:
            value = _number(row[name])
            if value is not None:
                return value
    return None


def _section(score: float, maximum: int, reasons: list[str]) -> dict:
    return {"score": round(max(0, min(score, maximum)), 1), "maximum": maximum, "reasons": reasons}


def score_technical(indicators: pd.DataFrame) -> dict:
    reasons: list[str] = []
    if indicators.empty:
        return _section(0, WEIGHTS["technical"], ["没有可用于技术评分的行情数据。"]) 
    last = indicators.iloc[-1]
    score = 0.0
    close, ma20, ma60 = (_number(last.get(key)) for key in ("close", "ma20", "ma60"))
    if close is not None and ma20 is not None and ma60 is not None:
        if close >= ma20 >= ma60:
            score += 12
            reasons.append("收盘价位于 MA20、MA60 上方，长短趋势一致向上（+12）。")
        elif close >= ma20:
            score += 7
            reasons.append("收盘价位于 MA20 上方，但长期趋势尚未完全确认（+7）。")
        else:
            reasons.append("收盘价位于 MA20 下方，均线趋势偏弱（+0）。")
    else:
        reasons.append("均线历史数据不足，趋势均线项未评分。")

    dif, dea, macd = (_number(last.get(key)) for key in ("dif", "dea", "macd"))
    if None not in (dif, dea, macd):
        if dif >= dea and macd >= 0:
            score += 10
            reasons.append("DIF 在 DEA 上方且 MACD 柱为正，动量偏多（+10）。")
        elif dif >= dea:
            score += 6
            reasons.append("DIF 在 DEA 上方，但 MACD 柱尚未转正（+6）。")
        else:
            reasons.append("DIF 位于 DEA 下方，MACD 动量偏弱（+0）。")

    rsi = _number(last.get("rsi14"))
    if rsi is not None:
        if 45 <= rsi <= 65:
            score += 8
            reasons.append(f"RSI(14) 为 {rsi:.1f}，处于健康强势区间（+8）。")
        elif 30 <= rsi < 70:
            score += 4
            reasons.append(f"RSI(14) 为 {rsi:.1f}，未出现明显极端（+4）。")
        else:
            reasons.append(f"RSI(14) 为 {rsi:.1f}，处于超买或超卖区间（+0）。")

    k, d = (_number(last.get(key)) for key in ("k", "d"))
    if k is not None and d is not None:
        if k >= d and k < 85:
            score += 10
            reasons.append("KDJ 中 K 线在 D 线上方，且未进入高位钝化（+10）。")
        elif k >= d:
            score += 5
            reasons.append("KDJ 偏多，但处于高位，追涨风险较高（+5）。")
        else:
            reasons.append("KDJ 中 K 线位于 D 线下方（+0）。")
    return _section(score, WEIGHTS["technical"], reasons)


def score_financial(financials: pd.DataFrame | None) -> dict:
    reasons: list[str] = []
    row = _latest_financial_row(financials)
    if row is None:
        return _section(0, WEIGHTS["financial"], ["财务数据暂不可用，财务面按 0 分处理。"])
    score = 0.0
    metrics = [
        ("ROE", ("净资产收益率(%)", "净资产收益率", "净资产收益率-摊薄"), 10, 15, 8),
        ("营收增长", ("主营业务收入增长率(%)", "营业收入增长率(%)", "营业收入增长率"), 8, 10, 3),
        ("净利润增长", ("净利润增长率(%)", "净利润增长率"), 8, 10, 3),
    ]
    for label, names, points, strong, positive in metrics:
        value = _financial_value(row, names)
        if value is None:
            reasons.append(f"未识别到{label}字段，该项未评分。")
        elif value >= strong:
            score += points
            reasons.append(f"{label}为 {value:.2f}%，表现较强（+{points}）。")
        elif value >= positive:
            score += points / 2
            reasons.append(f"{label}为 {value:.2f}%，保持正向（+{points / 2:g}）。")
        else:
            reasons.append(f"{label}为 {value:.2f}%，未达到评分标准（+0）。")
    debt = _financial_value(row, ("资产负债率(%)", "资产负债率"))
    if debt is None:
        reasons.append("未识别到资产负债率字段，该项未评分。")
    elif debt <= 50:
        score += 4
        reasons.append(f"资产负债率为 {debt:.2f}%，负债压力相对可控（+4）。")
    elif debt <= 70:
        score += 2
        reasons.append(f"资产负债率为 {debt:.2f}%，负债压力中等（+2）。")
    else:
        reasons.append(f"资产负债率为 {debt:.2f}%，负债压力偏高（+0）。")
    return _section(score, WEIGHTS["financial"], reasons)


def score_trend(indicators: pd.DataFrame) -> dict:
    reasons: list[str] = []
    if len(indicators) < 21:
        return _section(0, WEIGHTS["trend"], ["不足 21 个交易日，趋势强度未评分。"])
    data = indicators.sort_values("trade_date").reset_index(drop=True)
    last, prior = data.iloc[-1], data.iloc[-21]
    score = 0.0
    close, old_close = _number(last.get("close")), _number(prior.get("close"))
    if close and old_close:
        change = (close / old_close - 1) * 100
        if change >= 15:
            score += 10
        elif change >= 5:
            score += 8
        elif change >= 0:
            score += 6
        elif change >= -5:
            score += 3
        reasons.append(f"近 20 日价格涨跌幅为 {change:.2f}%（+{score:g}）。")
    ma20_now, ma20_old = _number(last.get("ma20")), _number(prior.get("ma20"))
    if ma20_now is not None and ma20_old is not None:
        if ma20_now > ma20_old:
            score += 10
            reasons.append("MA20 较 20 日前上行，趋势斜率为正（+10）。")
        else:
            reasons.append("MA20 未较 20 日前上行，趋势斜率偏弱（+0）。")
    else:
        reasons.append("MA20 数据不足，趋势斜率项未评分。")
    return _section(score, WEIGHTS["trend"], reasons)


def score_risk(indicators: pd.DataFrame) -> dict:
    reasons: list[str] = []
    if len(indicators) < 21:
        return _section(0, WEIGHTS["risk"], ["不足 21 个交易日，风险指标未评分。"])
    data = indicators.sort_values("trade_date").copy()
    close = pd.to_numeric(data["close"], errors="coerce")
    score = 0.0
    window = close.tail(60)
    drawdown = (window / window.cummax() - 1).min() * 100
    if drawdown >= -10:
        score += 5
        reasons.append(f"近 60 日最大回撤为 {drawdown:.2f}%，回撤可控（+5）。")
    elif drawdown >= -20:
        score += 3
        reasons.append(f"近 60 日最大回撤为 {drawdown:.2f}%，存在一定回撤压力（+3）。")
    else:
        reasons.append(f"近 60 日最大回撤为 {drawdown:.2f}%，回撤风险偏高（+0）。")
    volatility = close.pct_change().tail(20).std() * 100
    if pd.notna(volatility):
        if volatility <= 2:
            score += 5
            reasons.append(f"近 20 日日波动率为 {volatility:.2f}%，波动较低（+5）。")
        elif volatility <= 3.5:
            score += 3
            reasons.append(f"近 20 日日波动率为 {volatility:.2f}%，波动中等（+3）。")
        else:
            reasons.append(f"近 20 日日波动率为 {volatility:.2f}%，波动较高（+0）。")
    return _section(score, WEIGHTS["risk"], reasons)


def calculate_stock_score(indicators: pd.DataFrame, financials: pd.DataFrame | None = None) -> dict:
    """Return a 100-point score with four weighted, explainable sections."""
    sections = {
        "技术面": score_technical(indicators),
        "财务面": score_financial(financials),
        "趋势强度": score_trend(indicators),
        "风险指标": score_risk(indicators),
    }
    total = round(sum(section["score"] for section in sections.values()), 1)
    return {"total": total, "sections": sections}


def build_research_summary(score: dict) -> str:
    """Create one concise, data-derived research summary without using an LLM."""
    sections = score["sections"]
    technical = sections["技术面"]["score"]
    financial = sections["财务面"]["score"]
    trend = sections["趋势强度"]["score"]
    risk = sections["风险指标"]["score"]
    technical_text = "技术面偏强" if technical >= 28 else "技术面中性" if technical >= 16 else "技术面偏弱"
    trend_text = "趋势上行" if trend >= 14 else "趋势平稳" if trend >= 8 else "趋势偏弱"
    risk_text = "风险相对可控" if risk >= 7 else "需关注回撤与波动风险"
    finance_text = "财务数据待补充" if financial == 0 else "财务表现较好" if financial >= 20 else "财务表现一般"
    return f"综合评分 {score['total']:.1f}/100：{technical_text}，{trend_text}；{finance_text}，{risk_text}。"
