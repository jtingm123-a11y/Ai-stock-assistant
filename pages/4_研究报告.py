from pathlib import Path

import pandas as pd

import streamlit as st

from config.settings import REPORT_EXPORT_DIR
from src.data_sources.market_data import normalize_symbol
from src.database.repositories import (
    get_research_report, list_research_reports, save_research_report,
)
from src.reports.report_generator import generate_report
from src.services.scoring_service import get_stock_score
from src.services.stock_service import get_analysis

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
    .report-intro {padding: 1rem 1.2rem; border-radius: 12px; background: #131E2F;
        border: 1px solid #26364D; color: #AFC0D4; margin-bottom: 1rem;}
    .report-area h1 {font-size: 2rem; margin-top: 1rem;}
    .report-area h2 {border-left: 4px solid #60A5FA; padding-left: .7rem; margin-top: 1.5rem;}
    .report-area li {margin: .35rem 0; line-height: 1.6;}
    </style>""",
    unsafe_allow_html=True,
)
st.title("自动分析报告")
st.markdown(
    '<div class="report-intro">输入股票代码生成结构化研究报告。报告会把基本信息、关键指标、评分依据和风险提示分开整理，便于阅读。</div>',
    unsafe_allow_html=True,
)
symbol = st.text_input("A 股代码", value=st.session_state.get("symbol", ""), max_chars=6, placeholder="请输入 6 位 A 股代码")
refresh = st.checkbox("生成前刷新行情", value=True)

retry_requested = st.session_state.pop("report_retry", False)
if st.button("生成报告", type="primary") or retry_requested:
    try:
        with st.spinner("正在整理数据并生成报告..."):
            symbol = normalize_symbol(
                st.session_state.get("symbol", "") if retry_requested else symbol
            )
            profile, indicators = get_analysis(symbol, refresh=refresh)
            score, _, _ = get_stock_score(symbol, indicators, refresh=refresh)
            report = generate_report(symbol, profile, indicators, score)
        st.session_state["report"] = report
        st.session_state["report_symbol"] = symbol
        st.session_state["report_id"] = save_research_report(
            symbol, profile.get("name", "--"), indicators.iloc[-1]["trade_date"], score, report
        )
    except Exception as exc:
        message = str(exc)
        if "ProxyError" in message or "Unable to connect to proxy" in message:
            st.error("行情接口暂时无法连接。请检查网络或代理设置后重试。")
            st.info("查询新股票必须联网；网络恢复后重新点击“生成报告”即可。")
        else:
            st.error(message)
        if st.session_state.get("symbol"):
            if st.button("重试生成报告", key="report_retry_button"):
                st.session_state["report_retry"] = True
                st.rerun()

if "report" in st.session_state:
    report = st.session_state["report"]
    with st.container(border=True):
        st.markdown(report, unsafe_allow_html=True)
    REPORT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{st.session_state['report_symbol']}_report.md"
    st.download_button("下载 Markdown 报告", data=report, file_name=filename, mime="text/markdown")
    if st.button("保存报告到 data/exports"):
        path = Path(REPORT_EXPORT_DIR) / filename
        path.write_text(report, encoding="utf-8")
        st.success(f"已保存：{path}")

st.divider()
st.subheader("历史报告")
history_symbol = st.text_input("按股票代码筛选（可选）", max_chars=6, key="report_history_symbol")
try:
    normalized_history_symbol = normalize_symbol(history_symbol) if history_symbol.strip() else None
except ValueError as exc:
    st.warning(str(exc))
    normalized_history_symbol = None
history = list_research_reports(normalized_history_symbol)
if history.empty:
    st.info("暂无历史报告。生成报告后会自动归档。")
else:
    history_display = history.rename(columns={
        "id": "编号", "symbol": "代码", "name": "名称", "trade_date": "行情日期",
        "total_score": "综合评分", "confidence": "可信度", "created_at": "生成时间",
    })
    st.dataframe(history_display, hide_index=True, use_container_width=True)
    selected_id = st.selectbox("选择历史报告", history["id"].tolist(), format_func=lambda value: f"报告 #{value}")
    selected_report = get_research_report(int(selected_id))
    if selected_report:
        st.download_button(
            "下载历史报告",
            data=selected_report["report"],
            file_name=f"{selected_report['symbol']}_report_{selected_report['id']}.md",
            mime="text/markdown",
        )
        with st.expander("查看历史报告内容"):
            st.markdown(selected_report["report"], unsafe_allow_html=True)
    if len(history) >= 2:
        compare_ids = st.multiselect(
            "选择两份报告进行对比", history["id"].tolist(), max_selections=2,
            format_func=lambda value: f"报告 #{value}",
        )
        if len(compare_ids) == 2:
            compare = history[history["id"].isin(compare_ids)].sort_values("created_at")
            first, second = compare.iloc[0], compare.iloc[1]
            st.subheader("报告评分对比")
            st.dataframe(pd.DataFrame({
                "项目": ["综合评分", "行情日期", "可信度"],
                "较早报告": [first["total_score"], first["trade_date"], first["confidence"]],
                "较新报告": [second["total_score"], second["trade_date"], second["confidence"]],
                "变化": [
                    f"{second['total_score'] - first['total_score']:+.1f}",
                    "--",
                    "--",
                ],
            }), hide_index=True, use_container_width=True)
