import pandas as pd

from src.database.repositories import (
    load_score_history, load_signal_history, save_score_history, save_signal_history,
)


def test_score_and_signal_history_round_trip(tmp_path, monkeypatch):
    import src.database.connection as connection

    database = tmp_path / "history.db"
    monkeypatch.setattr(connection, "DATABASE_PATH", database)
    from src.database.schema import initialize_database

    initialize_database()
    score = {"total": 60, "confidence": "中", "sections": {
        "技术面": {"score": 20}, "财务面": {"score": 15},
        "趋势强度": {"score": 15}, "风险指标": {"score": 10},
    }}
    save_score_history("600519", pd.Timestamp("2024-01-02"), score)
    save_signal_history("600519", pd.Timestamp("2024-01-02"), [
        {"category": "MACD", "result": "金叉", "detail": "测试"},
    ])
    assert len(load_score_history("600519")) == 1
    assert load_signal_history("600519").iloc[0]["result"] == "金叉"
