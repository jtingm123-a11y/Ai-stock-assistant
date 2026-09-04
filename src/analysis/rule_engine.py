import pandas as pd


def build_technical_signals(indicators: pd.DataFrame) -> list[dict]:
    if indicators.empty:
        return []
    data = indicators.sort_values("trade_date").reset_index(drop=True)
    last = data.iloc[-1]
    signals = []
    close = last.get("close")
    ma20 = last.get("ma20")
    if pd.notna(close) and pd.notna(ma20):
        signals.append({"category": "趋势", "result": "偏强" if close >= ma20 else "偏弱", "detail": "收盘价位于 MA20 上方" if close >= ma20 else "收盘价位于 MA20 下方"})
    if pd.notna(last.get("dif")) and pd.notna(last.get("dea")):
        signals.append({"category": "MACD", "result": "偏多" if last["dif"] >= last["dea"] else "偏空", "detail": "DIF 位于 DEA 上方" if last["dif"] >= last["dea"] else "DIF 位于 DEA 下方"})
    if pd.notna(last.get("rsi14")):
        rsi = float(last["rsi14"])
        condition = "超买警示" if rsi >= 70 else "超卖关注" if rsi <= 30 else "中性"
        signals.append({"category": "RSI(14)", "result": condition, "detail": f"当前 RSI 为 {rsi:.2f}"})
    if pd.notna(last.get("k")) and pd.notna(last.get("d")):
        j_value = last.get("j")
        j_text = "--" if pd.isna(j_value) else f"{j_value:.2f}"
        signals.append({"category": "KDJ", "result": "K线上方" if last["k"] >= last["d"] else "K线下方", "detail": f"K={last['k']:.2f}，D={last['d']:.2f}，J={j_text}"})
    for label, fast, slow in (("MACD", "dif", "dea"), ("均线", "ma5", "ma20"), ("KDJ", "k", "d")):
        if len(data) < 2 or pd.isna(data.iloc[-1].get(fast)) or pd.isna(data.iloc[-2].get(fast)):
            continue
        previous_fast, previous_slow = data.iloc[-2].get(fast), data.iloc[-2].get(slow)
        current_fast, current_slow = data.iloc[-1].get(fast), data.iloc[-1].get(slow)
        if pd.isna(previous_slow) or pd.isna(current_slow):
            continue
        if previous_fast <= previous_slow and current_fast > current_slow:
            signals.append({"category": label, "result": "金叉", "detail": f"{fast.upper()} 上穿 {slow.upper()}，发生于 {pd.to_datetime(data.iloc[-1]['trade_date']).strftime('%Y-%m-%d')}"})
        elif previous_fast >= previous_slow and current_fast < current_slow:
            signals.append({"category": label, "result": "死叉", "detail": f"{fast.upper()} 下穿 {slow.upper()}，发生于 {pd.to_datetime(data.iloc[-1]['trade_date']).strftime('%Y-%m-%d')}"})
    return signals
