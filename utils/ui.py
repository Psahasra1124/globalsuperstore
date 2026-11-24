from html import escape

import streamlit as st

from utils.metrics import summary
from utils.visualizations import kpi_card


def page_header(title, subtitle, eyebrow="GLOBAL SUPERSTORE INTELLIGENCE"):
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-eyebrow">{escape(eyebrow.upper())}</div>
            <h1>{escape(title)}</h1>
            <p>{escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title, subtitle=None):
    st.markdown(f'<div class="section-title">{escape(title)}</div>', unsafe_allow_html=True)
    if subtitle:
        st.caption(subtitle)


def render_kpis(current_df, previous_df):
    current = summary(current_df)
    previous = summary(previous_df)
    no_previous_data = previous_df.empty
    definitions = [
        ("Sales", "sales", "currency", "💰"),
        ("Profit", "profit", "currency", "↗️"),
        ("Orders", "orders", "integer", "🧾"),
        ("Customers", "customers", "integer", "👥"),
        ("Avg. order", "aov", "currency", "🛍️"),
        ("Margin", "margin", "percent", "◒"),
    ]
    columns = st.columns(6)
    for column, (label, key, fmt, icon) in zip(columns, definitions):
        delta = None
        if not no_previous_data:
            current_value = current[key]
            previous_value = previous[key]
            if key == "margin":
                delta = f"{(current_value - previous_value) * 100:+.1f} pp"
            elif previous_value:
                delta = f"{(current_value - previous_value) / abs(previous_value) * 100:+.1f}%"
            else:
                delta = "New"
        with column:
            kpi_card(
                label,
                current[key],
                fmt,
                delta=delta,
                icon=icon,
                help_text=(
                    "Compared with the immediately preceding date range using the same filters."
                    if not no_previous_data
                    else "No records were available in the preceding date range."
                ),
            )
