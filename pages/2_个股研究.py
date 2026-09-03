import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots

from src.analysis.scoring import build_research_summary
from src.analysis.agent_views import build_agent_views
from src.data_sources.market_data import normalize_symbol
from src.services.scoring_service import get_stock_score
from src.services.stock_service import get_analysis
from src.utils.formatters import format_number

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
    </style>""",
    unsafe_allow_html=True,
)
with st.form("individual_research_form", border=True):
    input_col, option_col, action_col = st.columns([4, 2, 1], vertical_alignment="bottom")
    with input_col:
        symbol = st.text_input("股票代码", value=st.session_state.get("symbol", "600519"), max_chars=6, placeholder="例如 600519")
    with option_col:
        refresh = st.checkbox("立即刷新行情与财务数据", value=True)
    with action_col:
        submitted = st.form_submit_button("开始研究", type="primary", icon=":material/manage_search:")

if submitted:
    try:
        with st.spinner("正在计算技术指标..."):
            symbol = normalize_symbol(symbol)
            profile, data = get_analysis(symbol, refresh=refresh)
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

payload = st.session_state.get("research_payload")
if payload and payload["symbol"] == st.session_state.get("symbol"):
    profile, data, score = payload["profile"], payload["data"], payload["score"]
    finance, finance_error = payload["finance"], payload["finance_error"]
    last = data.iloc[-1]
    st.subheader(f"{profile['name']}（{payload['symbol']}）")
    st.caption(f"{profile['industry']} · 上市日期 {profile['listing_date']} · 行情截至 {str(last['trade_date'])[:10]} · 前复权日线")

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
        period = st.radio(
            "查看范围",
            ["最近 60 个交易日", "最近 120 个交易日", "全部历史数据"],
            horizontal=True,
        )
        chart_data = data if period == "全部历史数据" else data.tail(60 if period.startswith("最近 60") else 120)
        selected_ma = st.multiselect(
            "均线显示",
            ["MA5", "MA10", "MA20", "MA60"],
            default=["MA5", "MA10", "MA20", "MA60"],
            key="research_selected_ma",
        )
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        chart_dates = pd.to_datetime(chart_data["trade_date"])
        chart_labels = [
            f"{date.strftime('%m/%d')} {weekday_names[date.weekday()]}"
            for date in chart_dates
        ]
        chart_x = chart_dates
        x_padding = pd.Timedelta(days=2)
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.72, 0.28],
            subplot_titles=("K 线与均线", "成交量"),
        )
        fig.add_trace(
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
        for col, name, color in [
            ("ma5", "MA5", "#FBBF24"),
            ("ma10", "MA10", "#60A5FA"), ("ma20", "MA20", "#A78BFA"),
            ("ma60", "MA60", "#22D3EE"),
        ]:
            if name not in selected_ma:
                continue
            fig.add_trace(
                go.Scatter(
                    x=chart_x, y=chart_data[col], name=name,
                    line=dict(color=color),
                ),
                row=1,
                col=1,
            )
        volume_colors = [
            "#F87171" if close >= open_price else "#34D399"
            for open_price, close in zip(chart_data["open"], chart_data["close"])
        ]
        fig.add_trace(
            go.Bar(
                x=chart_x,
                y=chart_data["volume"],
                name="成交量",
                marker_color=volume_colors,
            ),
            row=2,
            col=1,
        )
        fig.update_layout(
            title="K 线与成交量（红涨绿跌）", height=620,
            margin=dict(l=10, r=10, t=55, b=10), template="plotly_dark", dragmode="pan",
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            bargap=0.18,
            uirevision=f"research-{symbol}-{period}",
        )
        fig.update_xaxes(
            title_text="交易日期",
            type="date",
            tickangle=0,
            tickformat="%m/%d",
            rangebreaks=[dict(bounds=["sat", "mon"])],
            range=[chart_x.iloc[0] - x_padding, chart_x.iloc[-1] + x_padding],
            constrain="domain",
            row=2,
            col=1,
        )
        fig.update_xaxes(
            fixedrange=False,
            rangeslider_visible=False,
            constrain="domain",
            row=1,
            col=1,
        )
        fig.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.07, row=2, col=1)
        fig.update_yaxes(
            title_text="价格", autorange=True, fixedrange=False,
            rangemode="normal", constrain="domain", row=1, col=1,
        )
        fig.update_yaxes(
            title_text="成交量", autorange=True, fixedrange=False,
            rangemode="normal", constrain="domain", row=2, col=1,
        )
        with st.container(border=True):
            st.caption("提示：滚轮缩放，拖动查看；底部滑块可快速选择时间范围，双击图表可复位。")
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "scrollZoom": True,
                    "displaylogo": False,
                    "doubleClick": "reset",
                    "dragmode": "pan",
                    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                    "modeBarButtonsToAdd": ["autoScale2d", "resetScale2d"],
                },
            )
        macd = go.Figure()
        macd_colors = ["#F87171" if value >= 0 else "#34D399" for value in data["macd"].fillna(0)]
        macd.add_trace(go.Bar(x=data["trade_date"], y=data["macd"], name="MACD 柱", marker_color=macd_colors))
        macd.add_trace(go.Scatter(x=data["trade_date"], y=data["dif"], name="DIF", line=dict(color="#FBBF24")))
        macd.add_trace(go.Scatter(x=data["trade_date"], y=data["dea"], name="DEA", line=dict(color="#60A5FA")))
        macd.update_layout(
            title="MACD（红色为正、绿色为负）", height=300,
            margin=dict(l=10, r=10, t=30, b=10), template="plotly_dark",
            xaxis=dict(title="交易日期", tickformat="%Y年%m月%d日", hoverformat="%Y年%m月%d日"),
        )
        with st.container(border=True):
            st.plotly_chart(macd)
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
