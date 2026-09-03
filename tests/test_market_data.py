import pytest

from src.data_sources.market_data import normalize_symbol


def test_normalize_symbol_accepts_six_digits():
    assert normalize_symbol(" 600519 ") == "600519"


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("", "请输入股票代码后再继续。"),
        ("abc123", "股票代码只能包含数字，请输入 6 位 A 股代码。"),
        ("60051", "股票代码必须是 6 位数字，例如 600519 或 000001。"),
    ],
)
def test_normalize_symbol_reports_clear_input_errors(value, message):
    with pytest.raises(ValueError) as error:
        normalize_symbol(value)
    assert str(error.value) == message
