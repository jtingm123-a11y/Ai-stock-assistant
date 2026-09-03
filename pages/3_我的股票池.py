import pandas as pd
import streamlit as st

from src.services.watchlist_service import add_watchlist, get_watchlist_snapshot, list_watchlist, refresh_watchlist, remove_watchlist
from src.data_sources.stock_info import fetch_stock_profile

st.markdown(
    """<style>
    #MainMenu, header[data-testid="stHeader"], [data-testid="stToolbar"] {visibility: hidden; height: 0;}
    footer {visibility: hidden;}
    [data-testid="stSidebarNav"] {padding-top: 2rem;}
    [data-testid="stSidebarNav"] a {margin: .25rem .6rem; padding: .65rem .8rem;
        border-radius: 10px; font-size: 1.05rem; font-weight: 650;}
    [data-testid="stSidebarNav"] a:hover {background: #1B304B; color: #F1F5F9;}
    [data-testid="stSidebarNav"] a[aria-current="page"] {background: #2B4260; color: #FFFFFF;}
    [data-testid="stSidebarNav"] li:first-child a p {font-size: 0;}
    [data-testid="stSidebarNav"] li:first-child a p:after {content: "首页"; font-size: 1.05rem;}
    [data-testid="stMetricValue"], .watchlist-average-value {
        font-size: 2rem !important; line-height: 1.2 !important;
        margin-top: .35rem !important; font-weight: 700 !important;
    }
    .watchlist-average-card {height: 100%; box-sizing: border-box;}
    .watchlist-average-card {min-height: 102px; display: flex; flex-direction: column;
        justify-content: flex-start;}
    .watchlist-change-details {font-size:.78rem; line-height:1.35; margin-top:.25rem; white-space:nowrap;}
    .watchlist-change-details .up {color:#F1F5F9 !important;}
    .watchlist-change-details .down {color:#F1F5F9 !important;}
    .watchlist-change-details .flat {color:#F1F5F9 !important;}
    [data-testid="stMetric"] {height: 102px; box-sizing: border-box;
        display: flex; flex-direction: column; justify-content: flex-start;}
    [data-testid="stMetricLabel"] {min-height: 1.35rem;}
    [data-testid="stMetricValue"] {font-size: 2rem !important; line-height: 1.2 !important;
        margin-top: .35rem !important;}
    </style>""",
    unsafe_allow_html=True,
)
st.title("自选股票")
st.caption("集中管理你正在跟踪的股票，行情数据来自本地缓存和公开数据源。")
if st.button("查看我的自选股", type="secondary", key="show_watchlist_button"):
    st.session_state["watchlist_visible"] = True
    st.rerun()

with st.form("add_watchlist_form", border=True):
    col1, col2, col3 = st.columns([2, 3, 1], vertical_alignment="bottom")
    with col1:
        symbol = st.text_input("股票代码", max_chars=6, placeholder="例如 600519")
    with col2:
        note = st.text_input("备注（可选）", placeholder="例如：长期关注、待观察")
    with col3:
        submitted = st.form_submit_button("加入自选", type="primary")
if submitted:
    try:
        add_watchlist(symbol, note.strip())
        st.success(f"{symbol.strip()} 已加入自选股。")
        st.rerun()
    except Exception as exc:
        st.error(str(exc))


def _load_stock_names(symbols: list[str]) -> dict[str, str]:
    names = st.session_state.setdefault("stock_names", {})
    for code in symbols:
        if code in names and names[code] != "--":
            continue
        try:
            names[code] = fetch_stock_profile(code).get("name", "--")
        except Exception:
            names[code] = "--"
    return names


def _compact_number(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "--"
    absolute = abs(float(number))
    if absolute >= 100000000:
        return f"{number / 100000000:.2f}亿"
    if absolute >= 10000:
        return f"{number / 10000:.2f}万"
    return f"{number:,.2f}".rstrip("0").rstrip(".")


watchlist = list_watchlist()
if not st.session_state.get("watchlist_visible", False):
    st.caption("添加股票后，点击“查看我的自选股”展示行情和管理内容。")
elif watchlist.empty:
    st.subheader("我的自选股")
    st.info("尚未添加自选股。")
else:
    st.subheader("我的自选股")
    with st.spinner("正在加载我的自选股，请稍等..."):
        snapshot = get_watchlist_snapshot()
        names = _load_stock_names(watchlist["symbol"].tolist())
    snapshot["name"] = snapshot["symbol"].map(names).fillna("--")
    cached_count = int(snapshot["trade_date"].notna().sum())
    avg_change = pd.to_numeric(snapshot["change_pct"], errors="coerce").mean()
    rising_count = int((snapshot["change_pct"] > 0).sum())
    falling_count = int((snapshot["change_pct"] < 0).sum())
    flat_count = int((snapshot["change_pct"] == 0).sum())
    summary_columns = st.columns(3, gap="small")
    with summary_columns[0]:
        st.metric("股票数量", f"{len(watchlist)} 只", border=True)
    with summary_columns[1]:
        st.metric("已有行情", f"{cached_count} 只", border=True)
    with summary_columns[2]:
        avg_text = "--" if pd.isna(avg_change) else f"{avg_change:+.2f}%"
        avg_color = "#F87171" if avg_change > 0 else "#34D399" if avg_change < 0 else "#F1F5F9"
        st.markdown(
            f'<div data-testid="stMetric" style="height:100%;box-sizing:border-box;border:1px solid #26364D;'
            f'border-radius:10px;padding:.7rem .9rem;background:#131E2F" class="watchlist-average-card">'
            f'<div style="color:#AFC0D4">股票池综合涨跌</div><div class="watchlist-average-value" '
            f'style="color:{avg_color}">{avg_text}</div>'
            f'<div class="watchlist-change-details">'
            f'<span class="up">上涨 {rising_count}</span> · '
            f'<span class="down">下跌 {falling_count}</span> · '
            f'<span class="flat">平盘 {flat_count}</span></div></div>',
            unsafe_allow_html=True,
        )
    st.caption("综合涨跌 = 有行情股票的日涨跌幅算术平均值；无行情股票不参与计算。")
    refresh = st.button("批量刷新行情", type="primary")
    st.caption("批量刷新会依次从公开接口获取每只自选股的日线行情，并写入本地缓存。")
    if refresh:
        progress = st.progress(0, text="正在刷新自选股行情...")
        with st.spinner("请稍候..."):
            succeeded, failed = refresh_watchlist()
        progress.progress(100, text="刷新完成")
        if succeeded:
            st.success(f"已刷新 {len(succeeded)} 只：{'、'.join(succeeded)}")
        if failed:
            st.warning("以下股票刷新失败：\n\n" + "\n".join(failed))

    snapshot = get_watchlist_snapshot()
    snapshot["name"] = snapshot["symbol"].map(names).fillna("--")
    sort_by = st.selectbox("排序方式", ["添加时间", "涨跌幅（高到低）", "涨跌幅（低到高）", "代码"])
    if sort_by == "涨跌幅（高到低）":
        snapshot = snapshot.assign(_sort=pd.to_numeric(snapshot["change_pct"], errors="coerce")).sort_values("_sort", ascending=False, na_position="last")
    elif sort_by == "涨跌幅（低到高）":
        snapshot = snapshot.assign(_sort=pd.to_numeric(snapshot["change_pct"], errors="coerce")).sort_values("_sort", na_position="last")
    elif sort_by == "代码":
        snapshot = snapshot.sort_values("symbol")
    display = snapshot.rename(columns={
        "symbol": "代码", "name": "名称", "note": "备注", "trade_date": "行情日期", "close": "收盘价",
        "change_pct": "涨跌幅(%)", "volume": "成交量", "amount": "成交额", "updated_at": "缓存更新于"
    })
    for column in ("收盘价", "涨跌幅(%)", "成交量", "成交额"):
        if column in display:
            display[column] = pd.to_numeric(display[column], errors="coerce")
    display["涨跌幅(%)"] = display["涨跌幅(%)"].map(
        lambda value: "--" if pd.isna(value) else f"{value:+.2f}%"
    )
    for column in ("成交量", "成交额"):
        if column in display:
            display[column] = display[column].map(_compact_number)
    display = display.drop(columns=["created_at", "_sort"], errors="ignore")

    def _color_change(value: object) -> str:
        number = pd.to_numeric(str(value).replace("%", ""), errors="coerce")
        if pd.isna(number) or number == 0:
            return ""
        return "color: #F87171; font-weight: 700" if number > 0 else "color: #34D399; font-weight: 700"

    styled = display.style.map(_color_change, subset=["涨跌幅(%)"])
    st.dataframe(styled, use_container_width=True, hide_index=True)
    remove_symbol = st.selectbox("选择要删除的代码", watchlist["symbol"].tolist())
    if st.button("删除所选股票"):
        remove_watchlist(remove_symbol)
        st.rerun()
