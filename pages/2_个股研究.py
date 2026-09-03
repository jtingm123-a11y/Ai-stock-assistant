import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots

from src.analysis.scoring import build_research_summary
from src.analysis.agent_views import build_agent_views
from src.data_sources.market_data import normalize_symbol
from src.services.scoring_service import get_stock_score
from src.services.stock_service import get_analysis, get_quote_source
from src.utils.formatters import format_number


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


def _wan_number(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "--"
    return f"{float(number) / 10000:,.2f}万"


def _color_change(value: object) -> str:
    number = pd.to_numeric(str(value).replace("%", ""), errors="coerce")
    if pd.isna(number) or number == 0:
        return ""
    return "color: #F87171; font-weight: 700" if number > 0 else "color: #34D399; font-weight: 700"


st.title("个股研究")
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
    .role-card {min-height: 118px; padding: 1rem; margin: .35rem 0;
        border: 1px solid #26364D; border-radius: 12px; background: #131E2F;}
    .role-title {font-weight: 700; color: #E5EDF8;}
    .role-title span {float: right; font-size: .75rem; color: #60A5FA;}
    .role-summary {margin-top: .55rem; color: #D8E3F1;}
    .role-detail {margin-top: .35rem; font-size: .82rem; color: #94A3B8; line-height: 1.5;}
    .role-green .role-title span {color: #34D399;}
    .role-orange .role-title span {color: #FB923C;}
    .role-purple .role-title span {color: #A78BFA;}
    .source-badge {display:inline-block; padding:.25rem .6rem; border-radius:999px;
        background:#193452; color:#93C5FD; font-size:.78rem; font-weight:650;}
    .metric-card {height:102px; box-sizing:border-box; border:1px solid #26364D;
        border-radius:8px; padding:.75rem 1rem; background:#131E2F;}
    .metric-label {font-size:.85rem; line-height:1.35; color:#AFC0D4;}
    .metric-value {font-size:2rem; font-weight:700; line-height:1.2; margin-top:.35rem;}
    </style>""",
    unsafe_allow_html=True,
)
with st.form("individual_research_form", border=True):
    input_col, option_col, action_col = st.columns([4, 2, 1], vertical_alignment="bottom")
    with input_col:
        symbol = st.text_input("股票代码", value=st.session_state.get("symbol", ""), max_chars=6, placeholder="请输入 6 位 A 股代码")
    with option_col:
        refresh = st.checkbox("立即刷新行情与财务数据", value=True)
    with action_col:
        submitted = st.form_submit_button("开始研究", type="primary", icon=":material/manage_search:")

retry_requested = st.session_state.pop("research_retry", False)
auto_research = st.session_state.pop("auto_research", False)
if submitted or retry_requested or auto_research:
    try:
        with st.spinner("正在计算技术指标..."):
            symbol = normalize_symbol(
                st.session_state.get("symbol", "")
                if retry_requested or auto_research
                else symbol
            )
            profile, data = get_analysis(
                symbol, refresh=True if auto_research else refresh
            )
            score, finance, finance_error = get_stock_score(symbol, data)
        st.session_state["symbol"] = symbol
        st.session_state["research_payload"] = {
            "symbol": symbol, "profile": profile, "data": data, "score": score,
            "finance": finance, "finance_error": finance_error,
        }
    except Exception as exc:
        message = str(exc)
        if "ProxyError" in message or "Unable to connect to proxy" in message:
            st.error("行情接口暂时无法连接。请检查网络或代理设置后重试。", icon=":material/error:")
            st.info("查询新股票必须联网；网络恢复后重新点击“开始研究”即可。")
        else:
            st.error(message, icon=":material/error:")
        if st.session_state.get("symbol"):
            if st.button("重试获取研究数据", key="research_retry_button"):
                st.session_state["research_retry"] = True
                st.rerun()

payload = st.session_state.get("research_payload")
if payload and payload["symbol"] == st.session_state.get("symbol"):
    profile, data, score = payload["profile"], payload["data"], payload["score"]
    finance, finance_error = payload["finance"], payload["finance_error"]
    last = data.iloc[-1]
    st.subheader(f"{profile['name']}（{payload['symbol']}）")
    st.caption(f"{profile['industry']} · 上市日期 {profile['listing_date']} · 行情截至 {str(last['trade_date'])[:10]} · 前复权日线")
    change_pct = pd.to_numeric(last.get("change_pct"), errors="coerce")
    change_color = "#F87171" if pd.notna(change_pct) and change_pct >= 0 else "#34D399"
    st.markdown(
        f'<span class="source-badge">数据来源：{get_quote_source()}</span>',
        unsafe_allow_html=True,
    )
    market_columns = st.columns(4, gap="small")
    market_metrics = [
        ("收盘价", f"{last['close']:.2f}", "#F1F5F9"),
        ("涨跌幅", "--" if pd.isna(change_pct) else f"{change_pct:+.2f}%", change_color),
        ("成交量", _wan_number(last.get("volume")), "#F1F5F9"),
        ("成交额", format_number(last.get("amount")), "#F1F5F9"),
    ]
    for column, (label, value, color) in zip(market_columns, market_metrics):
        with column:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value" style="color:{color}">{value}</div></div>',
                unsafe_allow_html=True,
            )

    with st.container(border=True):
        st.subheader("行情 K 线")
        period = st.radio(
            "查看范围",
            ["最近 60 个交易日", "最近 120 个交易日", "全部历史数据"],
            horizontal=True,
            key="top_chart_period",
        )
        selected_ma = st.multiselect(
            "均线显示",
            ["MA5", "MA10", "MA20", "MA60"],
            default=["MA5", "MA10", "MA20", "MA60"],
            key="top_chart_selected_ma",
        )
        chart_data = data if period == "全部历史数据" else data.tail(
            60 if period.startswith("最近 60") else 120
        )
        chart_x = pd.to_datetime(chart_data["trade_date"])
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        tick_step = max(1, len(chart_x) // 10)
        tick_values = chart_x.iloc[::tick_step]
        tick_text = [
            f"{date.strftime('%m/%d')} {weekday_names[date.weekday()]}"
            for date in tick_values
        ]
        chart_fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.58, 0.22, 0.20],
            subplot_titles=("K 线与均线", "成交量", "MACD"),
        )
        chart_fig.add_trace(
            go.Candlestick(
                x=chart_x,
                open=chart_data["open"],
                high=chart_data["high"],
                low=chart_data["low"],
                close=chart_data["close"],
                name="K 线",
                increasing_line_color="#F87171",
                increasing_fillcolor="#F87171",
                decreasing_line_color="#34D399",
                decreasing_fillcolor="#34D399",
            ),
            row=1,
            col=1,
        )
        for column, name, color in [
            ("ma5", "MA5", "#FBBF24"),
            ("ma10", "MA10", "#60A5FA"),
            ("ma20", "MA20", "#A78BFA"),
            ("ma60", "MA60", "#22D3EE"),
        ]:
            if name not in selected_ma:
                continue
            chart_fig.add_trace(
                go.Scatter(
                    x=chart_x,
                    y=chart_data[column],
                    name=name,
                    line=dict(color=color),
                ),
                row=1,
                col=1,
            )
        chart_fig.add_trace(
            go.Bar(
                x=chart_x,
                y=chart_data["volume"],
                name="成交量",
                marker_color=[
                    "#F87171" if close >= open_price else "#34D399"
                    for open_price, close in zip(chart_data["open"], chart_data["close"])
                ],
            ),
            row=2,
            col=1,
        )
        macd_colors = [
            "#F87171" if value >= 0 else "#34D399"
            for value in chart_data["macd"].fillna(0)
        ]
        chart_fig.add_trace(
            go.Bar(
                x=chart_x,
                y=chart_data["macd"],
                name="MACD 柱",
                marker_color=macd_colors,
            ),
            row=3,
            col=1,
        )
        chart_fig.add_trace(
            go.Scatter(
                x=chart_x,
                y=chart_data["dif"],
                name="DIF",
                line=dict(color="#FBBF24"),
            ),
            row=3,
            col=1,
        )
        chart_fig.add_trace(
            go.Scatter(
                x=chart_x,
                y=chart_data["dea"],
                name="DEA",
                line=dict(color="#60A5FA"),
            ),
            row=3,
            col=1,
        )
        chart_fig.update_layout(
            height=680,
            template="plotly_dark",
            dragmode="pan",
            hovermode="x unified",
            margin=dict(l=10, r=10, t=45, b=10),
            xaxis_rangeslider_visible=False,
        )
        chart_fig.update_xaxes(
            type="date",
            rangebreaks=[dict(bounds=["sat", "mon"])],
            tickmode="array",
            tickvals=tick_values,
            ticktext=tick_text,
            tickangle=0,
            rangeslider_visible=False,
            row=3,
            col=1,
        )
        chart_fig.update_yaxes(title_text="价格", fixedrange=False, row=1, col=1)
        chart_fig.update_yaxes(title_text="成交量", fixedrange=False, row=2, col=1)
        chart_fig.update_yaxes(title_text="MACD", fixedrange=False, row=3, col=1)
        st.plotly_chart(
            chart_fig,
            use_container_width=True,
            config={
                "scrollZoom": True,
                "displaylogo": False,
                "doubleClick": "reset",
                "modeBarButtonsToAdd": ["autoScale2d", "resetScale2d"],
            },
        )
    with st.container(border=True):
        st.subheader("研究结论")
        st.write(build_research_summary(score))

    with st.container(border=True):
        st.subheader("多角色研究视角")
        st.caption("模拟研究团队基于现有数据协作，不调用大模型，不构成投资建议。")
        role_columns = st.columns(2)
        for index, view in enumerate(build_agent_views(data, score, finance)):
            with role_columns[index % 2]:
                st.markdown(
                    f"""<div class="role-card role-{view['color']}">
                    <div class="role-title">{view['role']} <span>{view['tag']}</span></div>
                    <div class="role-summary">{view['summary']}</div>
                    <div class="role-detail">{view['details']}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    with st.container(horizontal=True):
        st.metric("综合评分", f"{score['total']:.1f}/100", border=True)
        st.metric("技术评分", f"{score['sections']['技术面']['score']:.1f}/40", border=True)
        st.metric("财务评分", f"{score['sections']['财务面']['score']:.1f}/30", border=True)
        st.metric("风险评分", f"{score['sections']['风险指标']['score']:.1f}/10", border=True)
        st.metric("最新收盘", format_number(last.get("close")), border=True)

    overview_tab, technical_tab, financial_tab, risk_tab = st.tabs(["研究概览", "技术分析", "财务分析", "评分依据"])
    with overview_tab:
        metric_columns = st.columns(5, border=True)
        for box, label, key in zip(metric_columns, ["MA5", "MA20", "RSI14", "MACD", "涨跌幅"], ["ma5", "ma20", "rsi14", "macd", "change_pct"]):
            suffix = "%" if key == "change_pct" else ""
            box.metric(label, f"{format_number(last.get(key))}{suffix}")
        st.caption("评分由技术面、财务面、趋势强度和风险指标组成；仅供研究参考。")
    with technical_tab:
        st.subheader("近期交易数据")
        recent = data.tail(100).sort_values("trade_date", ascending=False).rename(
            columns={
                "trade_date": "交易日期", "open": "开盘价", "high": "最高价",
                "low": "最低价", "close": "收盘价", "volume": "成交量",
                "amount": "成交额", "turnover": "换手率(%)", "amplitude": "振幅(%)",
                "change_pct": "涨跌幅(%)", "change_amount": "涨跌额",
            }
        )
        for column in ("成交量", "成交额"):
            if column in recent:
                recent[column] = recent[column].map(_compact_number)
        if "涨跌幅(%)" in recent:
            recent["涨跌幅(%)"] = recent["涨跌幅(%)"].map(
                lambda value: "--" if pd.isna(value) else f"{value:+.2f}%"
            )
        st.dataframe(
            recent.style.map(_color_change, subset=["涨跌幅(%)"]),
            hide_index=True,
            use_container_width=True,
        )
    with financial_tab:
        if finance is not None:
            with st.container(border=True):
                st.dataframe(finance, hide_index=True, use_container_width=True)
        else:
            st.info(f"财务数据暂不可用：{finance_error}", icon=":material/info:")
    with risk_tab:
        for name, section in score["sections"].items():
            with st.container(border=True):
                st.markdown(f"**{name}　{section['score']:.1f}/{section['maximum']} 分**")
                for reason in section["reasons"]:
                    st.write(f"- {reason}")
elif not submitted:
    st.caption("输入股票代码并点击“开始研究”，查看综合评分、技术面、财务面与风险分析。")
