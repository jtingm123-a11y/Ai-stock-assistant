import numpy as np
import pandas as pd


def add_technical_indicators(data: pd.DataFrame) -> pd.DataFrame:
    required = {"close", "high", "low"}
    if data.empty or not required.issubset(data.columns):
        raise ValueError("指标计算需要包含 close、high、low 字段的行情数据。")

    df = data.copy().sort_values("trade_date")
    close, high, low = df["close"].astype(float), df["high"].astype(float), df["low"].astype(float)
    for period in (5, 10, 20, 60):
        df[f"ma{period}"] = close.rolling(period, min_periods=period).mean()

    ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
    df["dif"] = ema12 - ema26
    df["dea"] = df["dif"].ewm(span=9, adjust=False).mean()
    df["macd"] = 2 * (df["dif"] - df["dea"])

    low9, high9 = low.rolling(9, min_periods=9).min(), high.rolling(9, min_periods=9).max()
    rsv = ((close - low9) / (high9 - low9).replace(0, np.nan) * 100).fillna(50)
    df["k"] = rsv.ewm(com=2, adjust=False).mean()
    df["d"] = df["k"].ewm(com=2, adjust=False).mean()
    df["j"] = 3 * df["k"] - 2 * df["d"]

    delta = close.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi14"] = 100 - (100 / (1 + rs))
    return df
