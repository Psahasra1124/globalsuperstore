import plotly.express as px
import streamlit as st

from utils.ui import page_header, section_header
from utils.visualizations import chart


df = st.session_state["df"]
page_header(
    "Shipping & Operations",
    "Evaluate delivery speed, shipping cost, service mix, and order urgency.",
    "Fulfilment performance",
)

has_duration = "Shipping Duration" in df.columns
has_cost = "Shipping Cost" in df.columns
metric_columns = st.columns(4)
metric_columns[0].metric(
    "Average delivery time",
    f"{df['Shipping Duration'].mean():.1f} days" if has_duration and df["Shipping Duration"].notna().any() else "—",
)
metric_columns[1].metric(
    "Average shipping cost",
    f"${df['Shipping Cost'].mean():,.2f}" if has_cost and df["Shipping Cost"].notna().any() else "—",
)
metric_columns[2].metric(
    "Shipping cost / sales",
    f"{df['Shipping Cost'].sum() / df['Sales'].sum():.1%}"
    if has_cost and df["Sales"].sum()
    else "—",
)
metric_columns[3].metric(
    "Shipping modes",
    f"{df['Ship Mode'].nunique():,}" if "Ship Mode" in df.columns else "—",
)

if "Ship Mode" in df.columns:
    section_header("Shipping mode performance")
    aggregations = {
        "Orders": ("Order ID", "nunique"),
        "Sales": ("Sales", "sum"),
        "Profit": ("Profit", "sum"),
    }
    if has_cost:
        aggregations["Shipping Cost"] = ("Shipping Cost", "sum")
    if has_duration:
        aggregations["Average Delivery Days"] = ("Shipping Duration", "mean")
    shipping = (
        df.groupby("Ship Mode", as_index=False, dropna=False)
        .agg(**aggregations)
        .sort_values("Sales", ascending=False)
    )
    left, right = st.columns(2)
    with left:
        chart(
            px.bar(
                shipping,
                x="Ship Mode",
                y="Sales",
                color="Profit",
                color_continuous_scale=["#f87171", "#334155", "#4f8ef7"],
                title="Sales by shipping mode",
                hover_data={"Sales": ":$,.0f", "Profit": ":$,.0f", "Orders": True},
            )
        )
    with right:
        chart(
            px.pie(
                shipping,
                names="Ship Mode",
                values="Orders",
                hole=0.55,
                title="Order mix by shipping mode",
                hover_data={"Sales": ":$,.0f"},
            )
        )
    if has_duration:
        chart(
            px.bar(
                shipping.sort_values("Average Delivery Days"),
                x="Ship Mode",
                y="Average Delivery Days",
                color="Average Delivery Days",
                color_continuous_scale=["#34d399", "#fbbf24"],
                title="Average delivery time by shipping mode",
                labels={"Average Delivery Days": "Days"},
            )
        )
else:
    st.info("Shipping mode comparisons are unavailable because Ship Mode is missing.")

if has_duration and "Region" in df.columns:
    section_header("Regional delivery speed")
    regional_duration = (
        df.groupby("Region", as_index=False)["Shipping Duration"]
        .mean()
        .dropna()
        .sort_values("Shipping Duration")
    )
    chart(
        px.bar(
            regional_duration,
            x="Region",
            y="Shipping Duration",
            title="Average shipping duration by region",
            color="Shipping Duration",
            color_continuous_scale=["#34d399", "#fbbf24"],
            labels={"Shipping Duration": "Days"},
        )
    )
elif not has_duration:
    st.info("Delivery-time metrics require valid Order Date and Ship Date values.")

if "Order Priority" in df.columns:
    section_header("Order priority")
    priority = df.groupby("Order Priority", as_index=False, dropna=False).agg(
        Orders=("Order ID", "nunique"), Sales=("Sales", "sum")
    )
    chart(
        px.bar(
            priority.sort_values("Orders", ascending=False),
            x="Order Priority",
            y="Orders",
            color="Order Priority",
            title="Order volume by priority",
            hover_data={"Sales": ":$,.0f"},
        )
    )
else:
    st.info("Order priority analysis is unavailable because Order Priority is missing.")
