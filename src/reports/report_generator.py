from datetime import datetime

import pandas as pd

from src.analysis.rule_engine import build_technical_signals
from src.analysis.agent_views import build_agent_views
from src.utils.formatters import format_number


def _change_html(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "--"
    color = "#F87171" if number > 0 else "#34D399" if number < 0 else "#F1F5F9"
    return f'<span style="color:{color};font-weight:700">{number:+.2f}%</span>'


def generate_report(symbol: str, profile: dict, indicators: pd.DataFrame, score: dict | None = None) -> str:
    if indicators.empty:
        raise ValueError("没有可用于生成报告的行情数据。")
    last = indicators.iloc[-1]
    trade_date = pd.to_datetime(last["trade_date"]).strftime("%Y-%m-%d")
    signals = build_technical_signals(indicators)
    agent_views = build_agent_views(indicators, score or {"total": 0, "sections": {
        "技术面": {"score": 0}, "财务面": {"score": 0},
        "趋势强度": {"score": 0}, "风险指标": {"score": 0},
    }})
    signal_lines = "\n".join(f"- {item['category']}：{item['result']}；{item['detail']}" for item in signals) or "- 暂无足够数据"
    agent_lines = "\n".join(
        f"- **{item['role']}｜{item['tag']}**：{item['summary']}{item['details']}"
        for item in agent_views
    )
    score_text = ""
    if score:
        sections = score.get("sections", {})
        score_rows = ["| 维度 | 得分 | 说明 |", "|---|---:|---|"]
        for name, section in sections.items():
            reasons = "；".join(section.get("reasons", []))
            score_rows.append(f"| {name} | {section['score']:.1f}/{section['maximum']} | {reasons or '暂无说明'} |")
        score_text = f"""## 三、综合评分

**总分：{score.get('total', 0):.1f}/100 分**

{chr(10).join(score_rows)}

"""
    return f"""# {profile.get('name', '--')}（{symbol}）研究报告

> 报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}  
> 行情数据截止日：{trade_date}  
> 数据源：公开行情接口；指标基于前复权日线计算。

## 一、基本信息

- 股票代码：{symbol}
- 股票名称：{profile.get('name', '--')}
- 行业：{profile.get('industry', '--')}
- 上市日期：{profile.get('listing_date', '--')}

## 二、最新行情与关键指标

> 指标说明：MA 是移动平均线，用于观察趋势；MACD 用于观察动量；RSI 用于观察短期强弱。指标只反映历史数据。

| 指标 | 当前值 | 怎么理解 |
|---|---:|---|
| 收盘价 | {format_number(last.get('close'))} | 最近一个交易日收盘价格 |
| 涨跌幅 | {_change_html(last.get('change_pct'))} | 相比前一交易日的价格变化 |
| MA5 / MA20 / MA60 | {format_number(last.get('ma5'))} / {format_number(last.get('ma20'))} / {format_number(last.get('ma60'))} | 不同周期平均价格，辅助判断趋势 |
| MACD（DIF / DEA / 柱） | {format_number(last.get('dif'))} / {format_number(last.get('dea'))} / {format_number(last.get('macd'))} | 判断趋势动能，柱值为正通常表示动能偏强 |
| RSI(14) | {format_number(last.get('rsi14'))} | 观察短期强弱，数值越高代表近期越强 |

{score_text}## 四、多角色研究视角

{agent_lines}

## 五、规则化研判

{signal_lines}

## 六、风险提示

本报告为程序依据公开历史数据和固定规则自动生成，仅用于个人研究与学习，不构成任何投资建议。技术指标具有滞后性；请结合公司公告、财务数据、估值、市场环境及自身风险承受能力独立判断。
"""
