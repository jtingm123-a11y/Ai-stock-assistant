import pandas as pd
import streamlit as st

from src.data_sources.global_markets import fetch_global_market_quotes


st.title("市场观察")
st.caption("查看中国、香港、美国、欧洲、日本和韩国主要金融市场行情。")

st.markdown(
    """<style>
    .market-table {overflow-x:auto;border:1px solid #26364D;border-radius:10px;}
    .market-table table {width:100%;border-collapse:collapse;font-size:.95rem;}
    .market-table th {background:#1B1F29;color:#AFC0D4;text-align:left;padding:.7rem .8rem;}
    .market-table td {border-top:1px solid #1E3048;color:#D8E3F1;padding:.7rem .8rem;}
    .change-up {color:#F87171 !important;font-weight:700;}
    .change-down {color:#34D399 !important;font-weight:700;}
    </style>""",
    unsafe_allow_html=True,
)

if st.button("刷新全球行情", type="primary", key="refresh_market_page"):
    st.session_state["market_global_refresh"] = True

if st.session_state.pop("market_global_refresh", False):
    with st.spinner("正在获取全球主要市场行情..."):
        quotes, errors = fetch_global_market_quotes()
    st.session_state["market_global_quotes"] = quotes
    st.session_state["market_global_errors"] = errors

quotes = st.session_state.get("market_global_quotes")
errors = st.session_state.get("market_global_errors", [])
if quotes is None:
    st.info("点击“刷新全球行情”后显示最新市场数据。")
elif quotes.empty:
    st.warning("暂时无法获取全球行情，请检查网络后点击“刷新全球行情”。")
else:
    display = quotes.copy()
    display["最新"] = display["最新"].map(lambda value: f"{value:,.2f}")
    display["涨跌"] = display["涨跌"].map(lambda value: f"{value:+,.2f}")
    display["涨跌幅"] = display["涨跌幅"].map(lambda value: f"{value:+.2f}%")
    rows = []
    for _, row in display.iterrows():
        change_class = (
            "change-up"
            if row["涨跌幅"].startswith("+")
            else "change-down"
            if row["涨跌幅"].startswith("-")
            else ""
        )
        rows.append(
            f'<tr><td>{row["市场"]}</td><td>{row["代码"]}</td>'
            f'<td>{row["最新"]}</td><td class="{change_class}">{row["涨跌"]}</td>'
            f'<td class="{change_class}">{row["涨跌幅"]}</td></tr>'
        )
    st.markdown(
        '<div class="market-table"><table><thead><tr>'
        "<th>市场</th><th>代码</th><th>最新</th><th>涨跌</th><th>涨跌幅</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )
if errors:
    st.caption("部分市场暂时不可用：" + "；".join(errors))
st.caption("数据来自 Yahoo Finance 公开接口，可能存在延迟，仅供研究参考。")
