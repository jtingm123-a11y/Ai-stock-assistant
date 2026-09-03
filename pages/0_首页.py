from textwrap import dedent

import pandas as pd
import streamlit as st

from src.data_sources.market_data import normalize_symbol
from src.data_sources.stock_info import fetch_stock_profile
from src.database.repositories import get_local_market_overview, list_recent_research
from src.database.schema import initialize_database
from src.services.watchlist_service import list_watchlist


initialize_database()

st.markdown(
    dedent(
        """\
        <style>
        .block-container {width: 100%; max-width: none; padding-top: 2rem; padding-bottom: 3rem;}
        #MainMenu, header[data-testid="stHeader"], [data-testid="stToolbar"] {visibility: hidden; height: 0;}
        footer {visibility: hidden;}
        .hero {padding: 1.4rem 1.6rem; border: 1px solid #26364D; border-radius: 16px;
            background: linear-gradient(120deg, #14243c 0%, #0f1928 65%, #18283b 100%);
            margin-bottom: 1.2rem;}
        .hero-title {font-size: 2rem; font-weight: 750; margin: .3rem 0;}
        .hero-copy {color: #AFC0D4; margin: 0;}
        .change-up {color: #F87171;}
        .change-down {color: #34D399;}
        .change-flat {color: #F1F5F9;}
        .recent-change-flat {color: #F1F5F9;}
        .recent-table {overflow-x: auto; border: 1px solid #26364D; border-radius: 10px;}
        .recent-table table {width: 100%; border-collapse: collapse; font-size: .9rem;}
        .recent-table th {background: #1B1F29; color: #AFC0D4; text-align: left;
            font-weight: 600; padding: .65rem .75rem; white-space: nowrap;}
        .recent-table td {color: #D8E3F1; border-top: 1px solid #1E3048;
            padding: .65rem .75rem; white-space: nowrap;}
        [data-testid="stSidebarNav"] {padding-top: 2rem;}
        [data-testid="stSidebarNav"] a {margin: .25rem .6rem; padding: .65rem .8rem;
            border-radius: 10px; font-size: 1.05rem; font-weight: 650;}
        [data-testid="stSidebarNav"] a:hover {background: #1B304B; color: #F1F5F9;}
        [data-testid="stSidebarNav"] a[aria-current="page"] {background: #2B4260; color: #FFFFFF;}
        .overview-metric {height: 132px; box-sizing: border-box; background: #131E2F;
            border: 1px solid #26364D; border-radius: 10px; padding: .95rem 1.1rem;
            display: flex; flex-direction: column; justify-content: flex-start;}
        .overview-metric-label {color: #D8E3F1; font-size: .9rem; line-height: 1.35;}
        .overview-metric-value {font-size: 2rem; line-height: 1.2; margin-top: .55rem;
            font-weight: 700; color: #F1F5F9;}
        .overview-metric-value.change-up {color: #F87171 !important;}
        .overview-metric-value.change-down {color: #34D399 !important;}
        </style>
        <div class="hero">
          <div class="hero-title">让数据先说话，再做研究判断</div>
          <p class="hero-copy">行情缓存、技术指标、财务评分与多角色视角，一站式整理你的 A 股研究流程。</p>
        </div>
        """
    ),
    unsafe_allow_html=True,
)

st.session_state.setdefault("symbol", "600519")
st.title("A 股研究工作台")
st.caption("本地研究数据 · 前复权日线 · 规则化评分 · 非投资建议")

with st.form("global_stock_search", border=True):
    search_col, action_col = st.columns([5, 1], vertical_alignment="bottom")
    with search_col:
        query = st.text_input(
            "股票代码",
            value=st.session_state["symbol"],
            max_chars=6,
            placeholder="输入 6 位 A 股代码，例如 600519",
        )
    with action_col:
        submitted = st.form_submit_button(
            "研究个股", type="primary", icon=":material/search:"
        )
if submitted:
    try:
        st.session_state["symbol"] = normalize_symbol(query)
        st.switch_page("pages/2_个股研究.py")
    except ValueError as exc:
        st.error(str(exc), icon=":material/error:")

overview = get_local_market_overview()
watchlist = list_watchlist()
latest_date = overview.get("latest_date") or "尚未缓存"
average_change = overview.get("average_change")
average_change_text = "--" if average_change is None else f"{average_change:+.2f}%"

st.subheader("本地市场概览")
overview_columns = st.columns(4, gap="small")
overview_cards = [
    ("缓存股票", f"{overview['cached_symbols']} 只", ""),
    ("我的股票池", f"{len(watchlist)} 只", ""),
    ("最新数据日期", str(latest_date), ""),
]
average_class = (
    "change-up"
    if average_change is not None and average_change > 0
    else "change-down"
    if average_change is not None and average_change < 0
    else ""
)
overview_cards.append(("股票池平均涨跌", average_change_text, average_class))
for column, (label, value, value_class) in zip(overview_columns, overview_cards):
    with column:
        st.markdown(
           f'<div class="overview-metric"><div class="overview-metric-label">{label}</div>'
           f'<div class="overview-metric-value {value_class}">{value}</div></div>',
           unsafe_allow_html=True,
        )

with st.container(border=True):
    st.subheader("最近研究股票")
    recent = list_recent_research()
    if recent.empty:
        st.caption("首次查询或刷新行情后，最近研究股票会显示在这里。")
    else:
        names = st.session_state.setdefault("stock_names", {})
        for code in recent["symbol"].tolist():
            if code not in names or names[code] == "--":
                try:
                    names[code] = fetch_stock_profile(code).get("name", "--")
                except Exception:
                    names[code] = "--"
        recent["name"] = recent["symbol"].map(names).fillna("--")
        recent["最新行情"] = recent.apply(
            lambda row: "--"
            if pd.isna(row["close"])
            else f"{row['close']:.2f}（{row['change_pct']:+.2f}%）",
            axis=1,
        )
        recent = recent.rename(
            columns={
                "symbol": "代码",
                "name": "名称",
                "trade_date": "行情日期",
                "updated_at": "更新于",
            }
        )
        def _recent_quote_html(row: pd.Series) -> str:
            if pd.isna(row["close"]):
                return "--"
            change = pd.to_numeric(row["change_pct"], errors="coerce")
            if pd.isna(change) or change == 0:
                change_html = f'<span class="recent-change-flat">（{change:+.2f}%）</span>' if not pd.isna(change) else ""
            else:
                change_class = "change-up" if change > 0 else "change-down"
                change_html = f'<span class="{change_class}">（{change:+.2f}%）</span>'
            return f'{row["close"]:.2f} {change_html}'

        recent["最新行情"] = recent.apply(_recent_quote_html, axis=1)
        display = recent[["代码", "名称", "最新行情", "行情日期", "更新于"]]
        headers = "".join(f"<th>{column}</th>" for column in display.columns)
        rows = "".join(
            "<tr>"
            + "".join(f"<td>{value}</td>" for value in row)
            + "</tr>"
            for row in display.itertuples(index=False, name=None)
        )
        st.markdown(
            f'<div class="recent-table"><table><thead><tr>{headers}</tr></thead>'
            f'<tbody>{rows}</tbody></table></div>',
            unsafe_allow_html=True,
        )

st.caption("市场概览基于本地缓存统计；首次使用请先查询或刷新一只股票。")
