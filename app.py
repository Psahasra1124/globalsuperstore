from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import streamlit as st

from database.datasets import get_active_dataset_path, initialize_dataset_db
from utils.data_cleaning import clean_data, load_dataset
from utils.exports import csv_bytes, excel_bytes, pdf_report_bytes
from utils.metrics import filter_data, previous_period_data


ROOT = Path(__file__).resolve().parent
DATA_DIRECTORY = ROOT / "data"

st.set_page_config(
    page_title="Global Superstore | Business Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --canvas: #0b1220;
        --sidebar: #0c1524;
        --surface: #111c2c;
        --surface-raised: #142238;
        --navy: #e9f0f8;
        --navy-2: #c7d5e5;
        --blue: #4f8ef7;
        --cyan: #22c5dc;
        --ink: #e5edf6;
        --muted: #91a2b8;
        --line: #26364b;
        --line-soft: #1b2a3d;
    }
    html, body, [class*="css"] { font-family: Inter, "Segoe UI", sans-serif; }
    .stApp, [data-testid="stAppViewContainer"] { background: var(--canvas); color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(11, 18, 32, .82); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0e1929 0%, var(--sidebar) 55%, #0a1321 100%);
        border-right: 1px solid var(--line-soft);
    }
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stSidebar"] * { color: #dbe5f1; }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        border: 1px solid var(--line);
        border-radius: 12px;
        background: rgba(17, 28, 44, .68);
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary p {
        color: #c9d6e5;
        font-size: .73rem;
        font-weight: 750;
        letter-spacing: .1em;
    }
    .block-container { max-width: 1600px; padding: 1.35rem 2rem 3.2rem; }
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: .75rem;
        padding: .55rem .2rem 1.1rem;
        border-bottom: 1px solid var(--line-soft);
        margin-bottom: 1rem;
    }
    .brand-mark {
        display: grid;
        place-items: center;
        width: 2.45rem;
        height: 2.45rem;
        border-radius: .8rem;
        background: linear-gradient(145deg, #4f8ef7, #22c5dc);
        color: #071322 !important;
        font-size: .85rem;
        font-weight: 850;
        letter-spacing: -.04em;
        box-shadow: 0 7px 20px rgba(34, 197, 220, .16);
    }
    .sidebar-brand p { margin: 0; color: #f1f5fb; font-size: .82rem; font-weight: 760; letter-spacing: .06em; }
    .sidebar-brand span { display: block; margin-top: .18rem; color: var(--muted); font-size: .62rem; font-weight: 700; letter-spacing: .14em; }
    .sidebar-section-label {
        margin: .5rem 0 .45rem;
        color: #8296ae;
        font-size: .65rem;
        font-weight: 750;
        letter-spacing: .13em;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] { gap: .18rem; }
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label {
        min-height: 2.5rem;
        padding: .62rem .78rem;
        border: 1px solid transparent;
        border-radius: .7rem;
        transition: background .16s ease, border-color .16s ease, transform .16s ease;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
        background: #15253a;
        border-color: #263a54;
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(90deg, rgba(79, 142, 247, .2), rgba(34, 197, 220, .08));
        border-color: rgba(79, 142, 247, .35);
        box-shadow: inset 3px 0 #4f8ef7;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-testid="stDateInput"] input {
        background: #101b2c !important;
        border-color: #2a3b52 !important;
        border-radius: .65rem !important;
    }
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        color: #e7f1ff !important;
        background: #1d3d60 !important;
        border-radius: .45rem;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background: #101b2c;
        border-color: #30425a;
        border-radius: .8rem;
    }
    .page-header {
        position: relative;
        padding: .25rem 0 1.2rem;
        margin-bottom: 1.35rem;
        border-bottom: 1px solid var(--line);
    }
    .page-header h1 {
        color: var(--navy);
        font-size: clamp(1.8rem, 3vw, 2.35rem);
        font-weight: 740;
        letter-spacing: -.045em;
        margin: .25rem 0 .4rem;
    }
    .page-header p { color: #a4b3c6; font-size: .96rem; margin: 0; }
    .page-eyebrow {
        color: var(--cyan);
        font-size: .66rem;
        font-weight: 760;
        letter-spacing: .15em;
    }
    .section-title {
        color: #e5edf6;
        font-size: 1.08rem;
        font-weight: 700;
        letter-spacing: -.015em;
        margin: 1.55rem 0 .28rem;
    }
    div[data-testid="stMetric"] {
        position: relative;
        overflow: hidden;
        background: linear-gradient(145deg, #15243a 0%, #111c2c 80%);
        border: 1px solid #263a52;
        border-top: 2px solid rgba(79, 142, 247, .72);
        border-radius: 15px;
        padding: 1rem 1.05rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, .14);
        min-height: 118px;
        transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #3b5879;
        box-shadow: 0 12px 28px rgba(0, 0, 0, .22);
    }
    label[data-testid="stMetricLabel"] { color: #9fb0c4; font-weight: 650; }
    label[data-testid="stMetricLabel"] > div,
    label[data-testid="stMetricLabel"] > div p {
        font-size: .72rem;
        overflow: visible;
        white-space: nowrap;
        text-overflow: clip;
    }
    div[data-testid="stMetricValue"] { color: #f1f6fc; font-size: clamp(1.2rem, 1.6vw, 1.55rem); font-weight: 730; letter-spacing: -.035em; }
    div[data-testid="stMetricDelta"] { font-size: .76rem; font-weight: 650; }
    div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
    div[data-testid="stPlotlyChart"] {
        overflow: hidden;
        border: 1px solid var(--line-soft);
        border-radius: 14px;
        background: var(--surface);
        box-shadow: 0 7px 22px rgba(0, 0, 0, .11);
    }
    div[data-testid="stTabs"] { margin-top: .35rem; }
    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        color: #9eafc3 !important;
        border-bottom: 2px solid transparent !important;
        border-radius: .6rem .6rem 0 0;
        font-weight: 650;
        transition: color .16s ease, background .16s ease, border-color .16s ease;
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"] * { color: inherit !important; }
    div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        color: #79b4ff !important;
        border-bottom-color: var(--blue) !important;
        background: rgba(79, 142, 247, .08) !important;
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
        color: #dcecff !important;
        background: #15243a !important;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background-color: var(--blue) !important; }
    div[data-testid="stTextInput"] label,
    div[data-testid="stTextInput"] label p,
    div[data-testid="stTextArea"] label,
    div[data-testid="stTextArea"] label p {
        color: var(--ink) !important;
        font-weight: 600;
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea {
        color: var(--ink) !important;
        background: #101b2c !important;
        border-color: #2a3b52 !important;
        border-radius: 9px;
    }
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stTextArea"] textarea:focus {
        border-color: var(--blue) !important;
        box-shadow: 0 0 0 1px var(--blue) !important;
    }
    div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        background: #101b2c !important;
        border-color: #2a3b52 !important;
        border-radius: 9px !important;
    }
    div[data-testid="stAlert"] { border-radius: 10px; font-weight: 500; }
    div[data-testid="stExpander"] { border-color: var(--line); border-radius: 12px; }
    div[data-testid="stDownloadButton"] button,
    div.stButton > button[kind="primary"] {
        border-radius: 9px;
        font-weight: 650;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(100deg, #3978e3, #287fbd);
        border-color: #4d94ed;
        color: #fff;
    }
    div.stButton > button:hover,
    div[data-testid="stDownloadButton"] button:hover {
        transform: translateY(-1px);
        box-shadow: 0 7px 18px rgba(34, 103, 189, .22);
    }
    [data-testid="stSidebar"] div.stButton > button,
    [data-testid="stSidebar"] div[data-testid="stDownloadButton"] button {
        width: 100%;
        border-radius: .65rem;
        border-color: #2a3b52;
        background: #15243a;
        color: #e2eaf4;
    }
    @media (max-width: 800px) {
        .block-container { padding: 1rem .85rem 2rem; }
        div[data-testid="stMetric"] { min-height: 96px; padding: .78rem; }
        .sidebar-brand { padding-bottom: .85rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


class UploadedBuffer(BytesIO):
    def __init__(self, name, content):
        super().__init__(content)
        self.name = name


def _dataset_signature():
    signature = []
    for name in ("Global_Superstore2.xlsx", "Global_Superstore2.csv"):
        path = DATA_DIRECTORY / name
        if path.is_file():
            stat = path.stat()
            signature.append((name, stat.st_size, stat.st_mtime_ns))
        else:
            signature.append((name, None, None))
    return tuple(signature)


@st.cache_data(show_spinner="Loading and validating the Superstore dataset…", max_entries=3)
def _load_default_dataset(signature, active_source=None):
    _ = signature
    raw = load_dataset(active_source)
    cleaned, report = clean_data(raw)
    return raw, cleaned, report


@st.cache_data(show_spinner="Loading uploaded data…", max_entries=3)
def _load_uploaded_dataset(file_name, content):
    raw = load_dataset(UploadedBuffer(file_name, content))
    cleaned, report = clean_data(raw)
    return raw, cleaned, report


initialize_dataset_db()

st.sidebar.markdown(
    """
    <div class="sidebar-brand">
        <div class="brand-mark">GS</div>
        <div><p>GLOBAL SUPERSTORE</p><span>BUSINESS INTELLIGENCE</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)
pages = {
    "📊  Executive Overview": "pages/1_Executive_Overview.py",
    "📈  Sales & Forecasting": "pages/2_Sales_Analysis.py",
    "◒  Profitability": "pages/3_Profitability_Analysis.py",
    "👥  Customer Intelligence": "pages/4_Customer_Analytics.py",
    "▦  Product Performance": "pages/5_Product_Analytics.py",
    "🌍  Geographic Analytics": "pages/9_Geographic_Analytics.py",
    "🚚  Shipping & Operations": "pages/6_Shipping_Analytics.py",
    "⌘  SQL Insights": "pages/7_SQL_Insights.py",
    "▤  Data Explorer": "pages/8_Data_Explorer.py",
    "💡  BI Assistant": "pages/10_BI_Assistant.py",
    "🗂️  Data Management": "pages/11_Data_Management.py",
}
st.sidebar.markdown('<div class="sidebar-section-label">ANALYTICS</div>', unsafe_allow_html=True)
choice = st.sidebar.radio("Dashboard", list(pages), label_visibility="collapsed")
st.sidebar.divider()
with st.sidebar.expander("DATA SOURCE", expanded=False):
    uploaded = st.file_uploader(
        "Use another CSV dataset",
        type=["csv"],
        key="session_dataset_upload",
    )

try:
    if uploaded is None:
        active_source = get_active_dataset_path()
        active_signature = None
        if active_source is not None:
            stat = active_source.stat()
            active_signature = (
                str(active_source),
                stat.st_size,
                stat.st_mtime_ns,
            )
        signature = (_dataset_signature(), active_signature)
        dataset_token = ("local", signature)
        raw, clean, cleaning_report = _load_default_dataset(
            signature, str(active_source) if active_source else None
        )
    else:
        uploaded_content = uploaded.getvalue()
        dataset_token = (
            "uploaded",
            uploaded.name,
            sha256(uploaded_content).hexdigest(),
        )
        raw, clean, cleaning_report = _load_uploaded_dataset(
            uploaded.name, uploaded_content
        )
except Exception as error:
    st.title("Global Superstore")
    st.error(f"The dataset could not be loaded: {error}")
    st.info(
        "The app tries data/Global_Superstore2.xlsx first, then "
        "data/Global_Superstore2.csv. You can also upload a compatible CSV."
    )
    st.stop()

if clean.empty:
    st.error("No valid records remain after cleaning. Check the essential fields and values.")
    st.stop()

filter_keys = {
    "global_date_range": "Order Date",
    "global_country": "Country",
    "global_region": "Region",
    "global_market": "Market",
    "global_category": "Category",
    "global_subcategory": "Sub-Category",
    "global_segment": "Segment",
    "global_ship_mode": "Ship Mode",
}

if st.session_state.get("_active_dataset_token") != dataset_token:
    for key in ("global_date_range", *filter_keys.keys()):
        st.session_state.pop(key, None)
    st.session_state.pop("sql_result", None)
    st.session_state.pop("sql_loaded", None)
    st.session_state["_active_dataset_token"] = dataset_token


def reset_filters():
    for key in ("global_date_range", *filter_keys.keys()):
        st.session_state.pop(key, None)


with st.sidebar.expander("GLOBAL FILTERS", expanded=True):
    st.button(
        "↺  Reset filters",
        key="reset_global_filters",
        use_container_width=True,
        on_click=reset_filters,
    )
    date_min = clean["Order Date"].min().date()
    date_max = clean["Order Date"].max().date()
    date_range = st.date_input(
        "Order date range",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
        key="global_date_range",
    )

    filter_labels = {
        "Country": ("Country", "global_country"),
        "Region": ("Region", "global_region"),
        "Market": ("Market", "global_market"),
        "Category": ("Category", "global_category"),
        "Sub-Category": ("Sub-category", "global_subcategory"),
        "Segment": ("Segment", "global_segment"),
        "Ship Mode": ("Shipping mode", "global_ship_mode"),
    }
    filters = {}
    for column, (label, key) in filter_labels.items():
        if column in clean.columns:
            values = sorted(clean[column].dropna().astype(str).unique().tolist())
            filters[column] = st.multiselect(
                label,
                values,
                default=[],
                key=key,
                placeholder="All values",
            )

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
elif isinstance(date_range, date):
    start = end = date_range
else:
    start, end = date_min, date_max

df = filter_data(clean, start, end, filters)
if df.empty:
    st.warning("No records match these filters. Adjust a filter or use Reset filters.")
    st.stop()

filter_context = (
    dataset_token,
    start,
    end,
    tuple((column, tuple(values or ())) for column, values in sorted(filters.items())),
)
if st.session_state.get("_filter_context") != filter_context:
    for key in (
        "sql_result",
        "sql_context",
        "sql_elapsed",
        "assistant_response",
        "assistant_result",
    ):
        st.session_state.pop(key, None)
    st.session_state["_filter_context"] = filter_context

previous_df = previous_period_data(clean, start, end, filters)
st.session_state["df"] = df
st.session_state["clean"] = clean
st.session_state["raw"] = raw
st.session_state["cleaning_report"] = cleaning_report
st.session_state["previous_df"] = previous_df
st.session_state["date_range"] = (start, end)
st.session_state["filters"] = filters

st.sidebar.markdown(
    f'<div class="sidebar-section-label">{len(df):,} FILTERED ORDER LINES</div>',
    unsafe_allow_html=True,
)

with st.sidebar.expander("EXPORT FILTERED DATA", expanded=False):
    st.download_button(
        "Download CSV",
        csv_bytes(df),
        file_name="superstore_filtered.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.download_button(
        "Download Excel",
        excel_bytes(df),
        file_name="superstore_filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.download_button(
        "Download PDF brief",
        pdf_report_bytes(df, (start, end)),
        file_name="superstore_filtered_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
st.sidebar.caption("Python  ·  Streamlit  ·  Pandas  ·  SQLite")

page_path = ROOT / pages[choice]
exec(compile(page_path.read_text(encoding="utf-8"), str(page_path), "exec"), {"__name__": "__main__"})
