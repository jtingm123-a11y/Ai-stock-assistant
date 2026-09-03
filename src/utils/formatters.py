import math


def format_number(value, digits: int = 2) -> str:
    if value is None:
        return "--"
    try:
        if math.isnan(float(value)):
            return "--"
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def format_percent(value, digits: int = 2) -> str:
    if value is None:
        return "--"
    try:
        if math.isnan(float(value)):
            return "--"
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "--"
