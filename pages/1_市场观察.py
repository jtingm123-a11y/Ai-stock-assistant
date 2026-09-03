import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots

from src.data_sources.market_data import normalize_symbol
from src.analysis.technical_indicators import add_technical_indicators
from src.services.stock_service import get_quote_source, get_quotes

st.title("市场观察")
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
    .metric-card {height: 102px; box-sizing: border-box; border: 1px solid #26364D;
        border-radius: 8px; padding: .75rem 1rem; background: #131E2F;
        display: flex; flex-direction: column; justify-content: flex-start;}
    .metric-label {font-size: .85rem; line-height: 1.35; color: #AFC0D4;}
    .metric-value {font-size: 2rem; font-weight: 700; line-height: 1.2; margin-top: .35rem;}
    .source-badge {display:inline-block; padding:.25rem .6rem; border-radius:999px;
        background:#193452; color:#93C5FD; font-size:.78rem; font-weight:650;}
    </style>""",
    unsafe_allow_html=True,
)
st.caption("查看个股日线行情、价格区间与本地缓存数据。日线数据会在新交易日自动检查更新。")


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


def _color_change(value: object) -> str:
    number = pd.to_numeric(str(value).replace("%", ""), errors="coerce")
    if pd.isna(number) or number == 0:
        return ""
    return "color: #F87171; font-weight: 700" if number > 0 else "color: #34D399; font-weight: 700"

with st.form("market_observation_form", border=True):
    input_col, option_col, action_col = st.columns([4, 2, 1], vertical_alignment="bottom")
    with input_col:
        symbol = st.text_input("股票代码", value=st.session_state.get("symbol", "600519"), max_chars=6, placeholder="例如 600519")
    with option_col:
        refresh = st.checkbox("立即从公开数据源刷新", value=True)
    with action_col:
        submitted = st.form_submit_button("查看行情", type="primary", icon=":material/candlestick_chart:")

request_submitted = submitted
if submitted or st.session_state.get("market_quotes") is not None:
    try:
        if request_submitted:
            with st.spinner("正在获取行情..."):
                symbol = normalize_symbol(symbol)
                quotes = get_quotes(symbol, refresh=refresh)
            st.session_state["symbol"] = symbol
            st.session_state["market_quotes"] = quotes
        else:
            quotes = st.session_state["market_quotes"]
        latest = quotes.iloc[-1]
        change_pct = latest.get("change_pct")
        change_color = "#F87171" if change_pct >= 0 else "#34D399"
        st.caption(f"已载入 {len(quotes)} 条前复权日线数据 · 数据截至 {str(latest['trade_date'])[:10]}")
        st.markdown(f'<span class="source-badge">数据来源：{get_quote_source()}</span>', unsafe_allow_html=True)
        metric_values = [
            ("收盘价", f"{latest['close']:.2f}", "#F1F5F9"),
            ("涨跌幅", f"{change_pct:+.2f}%", change_color),
            ("成交量", _compact_number(latest["volume"]), "#F1F5F9"),
            ("成交额", _compact_number(latest["amount"]), "#F1F5F9"),
        ]
        metric_columns = st.columns(4, gap="small")
        for column, (label, value, color) in zip(metric_columns, metric_values):
            with column:
                st.markdown(
                    f'<div class="metric-card"><div class="metric-label">{label}</div>'
                    f'<div class="metric-value" style="color:{color}">{value}</div></div>',
                    unsafe_allow_html=True,
                )
        period = st.radio(
            "查看范围",
            ["最近 60 个交易日", "最近 120 个交易日", "全部历史数据"],
            horizontal=True,
            key="market_chart_period",
        )
        chart_data = add_technical_indicators(quotes)
        chart_data = chart_data if period == "全部历史数据" else chart_data.tail(
            60 if period.startswith("最近 60") else 120
        )
        selected_ma = st.multiselect(
            "均线显示",
            ["MA5", "MA10", "MA20", "MA60"],
            default=["MA5", "MA10", "MA20", "MA60"],
            key="market_selected_ma",
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
            rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04,
            row_heights=[0.72, 0.28], subplot_titles=("K线与均线", "成交量"),
        )
        fig.add_trace(
            go.Candlestick(
                x=chart_x,                 open=chart_data["open"], high=chart_data["high"],
                low=chart_data["low"], close=chart_data["close"], name="K线",
                increasing_line_color="#F87171", increasing_fillcolor="#F87171",
                decreasing_line_color="#34D399", decreasing_fillcolor="#34D399",
            ), row=1, col=1,
        )
        for col, name, color in [
            ("ma5", "MA5", "#FBBF24"), ("ma10", "MA10", "#60A5FA"),
            ("ma20", "MA20", "#A78BFA"), ("ma60", "MA60", "#22D3EE"),
        ]:
            if name in selected_ma and col in chart_data:
                fig.add_trace(go.Scatter(x=chart_x, y=chart_data[col], name=name, line=dict(color=color)), row=1, col=1)
        volume_colors = [
            "#F87171" if close >= open_price else "#34D399"
            for open_price, close in zip(chart_data["open"], chart_data["close"])
        ]
        fig.add_trace(
            go.Bar(            x=chart_x, y=chart_data["volume"], name="成交量",
                   marker_color=volume_colors),
            row=2, col=1,
        )
        fig.update_layout(
            title="K线与成交量（红涨绿跌）", height=620,
            xaxis_rangeslider_visible=False, hovermode="x unified",
            bargap=0.18, margin=dict(l=10, r=10, t=55, b=10),
            template="plotly_dark", dragmode="pan",
            uirevision=f"market-{symbol}-{period}",
        )
        fig.update_xaxes(
            title_text="交易日期", type="date", tickformat="%m/%d",
            rangebreaks=[dict(bounds=["sat", "mon"])],
            range=[chart_x.iloc[0] - x_padding, chart_x.iloc[-1] + x_padding],
            constrain="domain",
            row=2, col=1,
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
        with st.container(border=True):
            st.subheader("近期交易数据")
            recent = quotes.tail(100).sort_values("trade_date", ascending=False).rename(columns={
                "trade_date": "交易日期", "open": "开盘价", "high": "最高价", "low": "最低价",
                "close": "收盘价", "volume": "成交量", "amount": "成交额", "turnover": "换手率(%)",
                "amplitude": "振幅(%)", "change_pct": "涨跌幅(%)", "change_amount": "涨跌额",
            })
            for column in ("成交量", "成交额"):
                recent[column] = recent[column].map(_compact_number)
            recent["涨跌幅(%)"] = recent["涨跌幅(%)"].map(
                lambda value: "--" if pd.isna(value) else f"{value:+.2f}%"
            )
            st.dataframe(
                recent.style.map(_color_change, subset=["涨跌幅(%)"]),
                hide_index=True,
                use_container_width=True,
            )
    except Exception as exc:
        message = str(exc)
        if "ProxyError" in message or "Unable to connect to proxy" in message:
            st.error("行情接口暂时无法连接。请检查网络或代理设置后重试。", icon=":material/error:")
            st.info("如果这是第一次查询该股票，需要联网获取数据；当前没有可用的本地缓存。")
        else:
            st.error(message, icon=":material/error:")
