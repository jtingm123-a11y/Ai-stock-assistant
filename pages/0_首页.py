from textwrap import dedent

import pandas as pd
import streamlit as st

from src.data_sources.market_data import normalize_symbol
from src.database.repositories import get_local_market_overview
from src.database.schema import initialize_database
from src.services.watchlist_service import list_watchlist
from src.analysis.alerts import build_research_alerts
from src.services.stock_service import get_quotes
from src.analysis.technical_indicators import add_technical_indicators


initialize_database()

st.markdown(
    dedent(
        """\
        <style>
        .block-container {width: 100%; max-width: none; padding-top: 2rem; padding-bottom: 3rem;}
        #MainMenu, header[data-testid="stHeader"], [data-testid="stToolbar"] {visibility: hidden; height: 0;}
        footer {visibility: hidden;}
        .hero {padding: 1.4rem 1.6rem; border: 1px solid #26364D; border-radius: 16px;
            background: linear-gradient(120deg, #14243c 0%, #0f1928 65%, #18283b 100%); margin-bottom: 1.2rem;}
        .hero-title {font-size: 2rem; font-weight: 750; margin: .3rem 0;}
        .hero-copy {color: #AFC0D4; margin: 0;}
        .change-up {color: #F87171 !important;}
        .change-down {color: #34D399 !important;}
        .overview-metric {height: 132px; box-sizing: border-box; background: #131E2F;
            border: 1px solid #26364D; border-radius: 10px; padding: .95rem 1.1rem;}
        .overview-metric-label {color: #D8E3F1; font-size: .9rem;}
        .overview-metric-value {font-size: 2rem; line-height: 1.2; margin-top: .55rem;
            font-weight: 700; color: #F1F5F9;}
        .overview-change-details {font-size: .78rem; line-height: 1.35; margin-top: .25rem;
            font-weight: 500; white-space: nowrap;}
        .overview-change-details .up {color: #F1F5F9 !important;}
        .overview-change-details .down {color: #F1F5F9 !important;}
        .overview-change-details .flat {color: #F1F5F9 !important;}
        </style>
        <div class="hero">
          <div class="hero-title">让数据先说话，再做研究判断</div>
          <p class="hero-copy">行情缓存、技术指标、财务评分与多角色视角，一站式整理你的 A 股研究流程。</p>
        </div>
        """
    ),
    unsafe_allow_html=True,
)

st.title("A 股研究工作台")
st.caption("本地研究数据 · 前复权日线 · 规则化评分 · 非投资建议")

with st.form("homepage_stock_search", border=True):
    search_col, action_col = st.columns([5, 1], vertical_alignment="bottom")
    with search_col:
        query = st.text_input(
            "股票代码",
            max_chars=6,
            placeholder="请输入 6 位 A 股代码",
        )
    with action_col:
        submitted = st.form_submit_button(
            "开始研究", type="primary", icon=":material/manage_search:"
        )
if submitted:
    try:
        st.session_state["symbol"] = normalize_symbol(query)
        st.session_state["auto_research"] = True
        st.switch_page("pages/2_个股研究.py")
    except ValueError as exc:
        st.error(str(exc), icon=":material/error:")

overview = get_local_market_overview()
watchlist = list_watchlist()
alert_rows = []
for cached_symbol in watchlist["symbol"].tolist():
    try:
        cached_quotes = get_quotes(cached_symbol, refresh=False)
        alert_rows.extend(build_research_alerts(cached_symbol, add_technical_indicators(cached_quotes)))
    except (ValueError, RuntimeError, KeyError):
        continue
latest_date = overview.get("latest_date") or "尚未缓存"
average_change = overview.get("average_change")
average_change_text = "--" if average_change is None else f"{average_change:+.2f}%"

st.subheader("股票自选概览")
overview_cards = [
    ("我的股票池", f"{len(watchlist)} 只", ""),
    ("最新数据日期", str(latest_date), ""),
]
average_class = "change-up" if average_change and average_change > 0 else "change-down" if average_change and average_change < 0 else ""
overview_cards.append(("股票池综合涨跌", average_change_text, average_class))
for column, (label, value, value_class) in zip(st.columns(3, gap="small"), overview_cards):
    with column:
        details = ""
        if label == "股票池综合涨跌":
            details = (
                '<div class="overview-change-details">'
                f'<span class="up">上涨 {overview["rising_count"]}</span> · '
                f'<span class="down">下跌 {overview["falling_count"]}</span> · '
                f'<span class="flat">平盘 {overview["flat_count"]}</span></div>'
            )
        st.markdown(
            f'<div class="overview-metric"><div class="overview-metric-label">{label}</div>'
            f'<div class="overview-metric-value {value_class}">{value}</div>{details}</div>',
            unsafe_allow_html=True,
        )
st.caption("综合涨跌 = 股票池中有行情股票的日涨跌幅算术平均值；无行情股票不参与计算。")
st.subheader("本地研究提醒")
if alert_rows:
    alert_frame = pd.DataFrame(alert_rows)
    st.metric("提醒数量", f"{len(alert_frame)} 条", border=True)
    st.dataframe(
        alert_frame.rename(columns={"symbol": "代码", "trade_date": "日期", "category": "类型",
                                    "level": "级别", "message": "提醒内容"}),
        hide_index=True, use_container_width=True,
    )
else:
    st.success("当前股票池没有新的本地研究提醒。")
