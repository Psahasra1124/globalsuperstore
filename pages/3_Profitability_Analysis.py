import numpy as np
import plotly.express as px
import streamlit as st

from utils.analytics import product_performance, profitability_heatmap
from utils.ui import page_header, section_header
from utils.visualizations import chart


df = st.session_state["df"]
page_header(
    "Profitability Analysis",
    "Understand margin quality, loss drivers, and the relationship between discounting and profit.",
    "Margin & mix",
)

sales = df["Sales"].sum()
profit = df["Profit"].sum()
margin = profit / sales if sales else 0
loss_lines = int(df["Profit"].lt(0).sum())
metric_columns = st.columns(4)
metric_columns[0].metric("Net sales", f"${sales:,.0f}")
metric_columns[1].metric("Net profit", f"${profit:,.0f}")
metric_columns[2].metric("Weighted profit margin", f"{margin:.1%}")
metric_columns[3].metric("Loss-making order lines", f"{loss_lines:,}")

section_header("Profit contribution", "Profit and margin are aggregated from the filtered order lines.")
dimensions = [column for column in ("Category", "Region") if column in df]
columns = st.columns(max(1, len(dimensions)))
for index, dimension in enumerate(dimensions):
    with columns[index]:
        summary = (
            df.groupby(dimension, as_index=False, dropna=False)
            .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
        )
        summary["Profit Margin"] = np.where(
            summary["Sales"] != 0, summary["Profit"] / summary["Sales"], np.nan
        )
        chart(
            px.bar(
                summary.sort_values("Profit"),
                x="Profit",
                y=dimension,
                orientation="h",
                color="Profit Margin",
                color_continuous_scale=["#f87171", "#334155", "#4f8ef7"],
                title=f"Profit and margin by {dimension}",
                hover_data={"Sales": ":$,.0f", "Profit": ":$,.0f", "Profit Margin": ":.1%"},
                labels={"Profit": "Profit ($)", "Profit Margin": "Margin"},
            )
        )
if not dimensions:
    st.info("Category and region profitability are unavailable for this dataset.")

heatmap = profitability_heatmap(df)
if not heatmap.empty:
    section_header("Category × region margin", "Weighted margin is total profit divided by total sales.")
    figure = px.imshow(
        heatmap,
        color_continuous_scale=["#f87171", "#334155", "#4f8ef7"],
        aspect="auto",
        text_auto=".1%",
        labels={"x": "Region", "y": "Category", "color": "Margin"},
        title="Profit margin heatmap",
    )
    chart(figure, height=360)

products = product_performance(df)
if not products.empty:
    product_label = "Product Name" if "Product Name" in products else "Product ID"
    products["Profitability"] = np.select(
        [
            products["Sales"].ge(products["Sales"].quantile(0.75))
            & products["Profit Margin"].le(products["Profit Margin"].quantile(0.25)),
            products["Profit"].lt(0),
        ],
        ["High sales · low margin", "Loss-making"],
        default="Other products",
    )
    section_header("High sales, low margin", "Products in the top sales quartile and bottom margin quartile.")
    high_sales_low_margin = products.loc[
        products["Profitability"].eq("High sales · low margin")
        | products["Profitability"].eq("Loss-making")
    ]
    if not high_sales_low_margin.empty:
        st.dataframe(
            high_sales_low_margin.sort_values(["Sales", "Profit"], ascending=[False, True]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sales": st.column_config.NumberColumn(format="$%.2f"),
                "Profit": st.column_config.NumberColumn(format="$%.2f"),
                "Profit Margin": st.column_config.NumberColumn(format="%.1f%%"),
                "Sales Share": st.column_config.NumberColumn(format="%.1%"),
            },
        )
    else:
        st.info("No products meet these filtered-data thresholds.")

    left, right = st.columns(2)
    with left:
        chart(
            px.scatter(
                products,
                x="Sales",
                y="Profit",
                color="Profitability",
                hover_name=product_label,
                hover_data={"Profit Margin": ":.1%", "Sales": ":$,.0f", "Profit": ":$,.0f"},
                color_discrete_map={
                    "High sales · low margin": "#fbbf24",
                    "Loss-making": "#fb7185",
                    "Other products": "#60a5fa",
                },
                title="Product sales vs. profit",
            )
        )
    with right:
        worst = products.nsmallest(12, "Profit").sort_values("Profit")
        chart(
            px.bar(
                worst,
                x="Profit",
                y=product_label,
                orientation="h",
                title="Largest product losses",
                color_discrete_sequence=["#fb7185"],
                hover_data={"Sales": ":$,.0f", "Profit Margin": ":.1%"},
            )
        )

if "Discount" in df.columns:
    section_header("Discount and profit", "Observed association only; this view does not imply causation.")
    hover = {"Sales": ":$,.0f"}
    if "Category" in df.columns:
        hover["Category"] = True
    chart(
        px.scatter(
            df,
            x="Discount",
            y="Profit",
            color="Category" if "Category" in df.columns else None,
            hover_data=hover,
            opacity=0.55,
            title="Discount vs. order-line profit",
            labels={"Discount": "Discount rate", "Profit": "Profit ($)"},
        )
    )
