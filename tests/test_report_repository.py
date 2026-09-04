import pandas as pd

from src.database.repositories import get_research_report, list_research_reports, save_research_report
from src.database.schema import initialize_database


def test_research_report_round_trip(tmp_path, monkeypatch):
    import src.database.connection as connection

    monkeypatch.setattr(connection, "DATABASE_PATH", tmp_path / "reports.db")
    initialize_database()
    score = {"total": 72.5, "confidence": "高"}
    report_id = save_research_report("600519", "测试", pd.Timestamp("2024-01-02"), score, "# 报告")
    assert get_research_report(report_id)["report"] == "# 报告"
    assert list_research_reports("600519").iloc[0]["total_score"] == 72.5
