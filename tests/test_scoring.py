import pandas as pd

from src.analysis.scoring import calculate_stock_score
from src.analysis.agent_views import build_agent_views
from src.analysis.technical_indicators import add_technical_indicators


def test_stock_score_has_all_weighted_sections():
    dates = pd.date_range("2024-01-01", periods=100)
    data = pd.DataFrame({
        "trade_date": dates,
        "close": range(10, 110),
        "high": range(11, 111),
        "low": range(9, 109),
    })
    financials = pd.DataFrame([{
        "日期": "2024-12-31", "净资产收益率(%)": 18, "主营业务收入增长率(%)": 12,
        "净利润增长率(%)": 15, "资产负债率(%)": 45,
    }])
    result = calculate_stock_score(add_technical_indicators(data), financials)
    assert set(result["sections"]) == {"技术面", "财务面", "趋势强度", "风险指标"}
    assert 0 <= result["total"] <= 100
    assert result["sections"]["财务面"]["score"] == 30


def test_agent_views_cover_research_roles():
    dates = pd.date_range("2024-01-01", periods=30)
    data = pd.DataFrame({
        "trade_date": dates,
        "close": range(10, 40),
        "high": range(11, 41),
        "low": range(9, 39),
    })
    indicators = add_technical_indicators(data)
    score = {"total": 60, "sections": {
        "技术面": {"score": 20}, "财务面": {"score": 15},
        "趋势强度": {"score": 15}, "风险指标": {"score": 10},
    }}
    views = build_agent_views(indicators, score)
    assert [view["role"] for view in views] == [
        "技术分析师", "基本面分析师", "风险经理", "研究主管",
    ]
