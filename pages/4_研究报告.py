from pathlib import Path

import streamlit as st

from config.settings import REPORT_EXPORT_DIR
from src.data_sources.market_data import normalize_symbol
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
            score, _, _ = get_stock_score(symbol, indicators)
            report = generate_report(symbol, profile, indicators, score)
        st.session_state["report"] = report
        st.session_state["report_symbol"] = symbol
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
