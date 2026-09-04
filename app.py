import streamlit as st

from src.database.schema import initialize_database


initialize_database()


st.set_page_config(
    page_title="A股研究工作台",
    page_icon=":material/home:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    /* Keep navigation in the same Streamlit tab and give every item one type scale. */
    [data-testid="stSidebar"] {
        display: none !important;
    }
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stBaseButton-headerNoPadding"],
    [data-testid="stExpandSidebarButton"] {
        display: none !important;
    }
    .st-key-fixed_nav {
        position: fixed;
        z-index: 999999;
        top: 0;
        left: 0;
        width: 260px;
        height: 100vh;
        padding: 2.4rem .7rem;
        box-sizing: border-box;
        background: #0F1928;
        border-right: 1px solid #26364D;
    }
    .st-key-fixed_nav [data-testid="stPageLink"] a {
        display: flex;
        align-items: center;
        min-height: 2.9rem;
        margin: .3rem 0;
        padding: .8rem 1rem;
        border: 1px solid transparent;
        border-radius: 12px;
        color: #D8E3F1 !important;
        font-family: sans-serif !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        line-height: 1.4 !important;
        text-decoration: none !important;
    }
    .st-key-fixed_nav [data-testid="stPageLink"] p,
    .st-key-fixed_nav [data-testid="stPageLink"] span {
        font-family: sans-serif !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        line-height: 1.4 !important;
    }
    .st-key-fixed_nav [data-testid="stPageLink"] [data-testid="stIconMaterial"] {
        display: none !important;
    }
    .st-key-fixed_nav [data-testid="stPageLink"] a:hover {
        background: linear-gradient(135deg, #1C3554, #162A43);
        border-color: #315176;
    }
    .st-key-fixed_nav [data-testid="stPageLink"] a[aria-current="page"] {
        background: linear-gradient(135deg, #34577F, #274568);
        border-color: #5279A5;
        box-shadow: 0 5px 14px rgba(4, 12, 24, .28);
        color: #FFFFFF !important;
    }
    .st-key-fixed_nav .nav-title {
        margin: 0 1rem 1.3rem;
        color: #60A5FA;
        font-size: .8rem;
        letter-spacing: .12em;
        font-weight: 700;
    }
    html, body, [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
    }
    [data-testid="stMain"] {
        margin-left: 0 !important;
        padding-left: 260px !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
    }
    [data-testid="stMain"] .block-container {
        width: 100% !important;
        max-width: none !important;
        box-sizing: border-box !important;
        padding-left: clamp(1rem, 2.2vw, 2.5rem) !important;
        padding-right: clamp(1rem, 2.2vw, 2.5rem) !important;
    }
    @media (max-width: 900px) {
        .st-key-fixed_nav {
            width: 210px;
        }
        [data-testid="stMain"] {
            padding-left: 210px !important;
        }
        .st-key-fixed_nav [data-testid="stPageLink"] a {
            font-size: 15px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

pages = [
    st.Page("pages/0_首页.py", title="首页", icon=":material/home:"),
    st.Page("pages/1_市场观察.py", title="市场观察", icon=":material/candlestick_chart:"),
    st.Page("pages/2_个股研究.py", title="个股研究", icon=":material/manage_search:"),
    st.Page("pages/3_我的股票池.py", title="我的股票池", icon=":material/bookmark:"),
    st.Page("pages/4_研究报告.py", title="研究报告", icon=":material/description:"),
]

with st.container(key="fixed_nav"):
    st.markdown('<div class="nav-title">A 股研究工作台</div>', unsafe_allow_html=True)
    for page, label in zip(
        pages,
        ("首页", "市场观察", "个股研究", "我的股票池", "研究报告"),
    ):
        st.page_link(page, label=label, use_container_width=True)

navigation = st.navigation(pages, position="hidden")
navigation.run()
