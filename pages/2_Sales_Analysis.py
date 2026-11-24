import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.analytics import product_performance, sales_time_series
from utils.forecasting import forecast_monthly_sales
from utils.ui import page_header, section_header
from utils.visualizations import chart


df = st.session_state["df"]
page_header(
    "Sales Performance",
    "Track sales momentum across time, channels, regions, and products.",
    "Revenue & demand",
)

frequency = st.selectbox("Trend interval", ["Monthly", "Quarterly", "Yearly"], index=0)
trends = sales_time_series(df, frequency)
section_header(f"{frequency} sales trend", "Growth rates compare equivalent consecutive periods.")
left, right = st.columns(2)
with left:
    chart(
        px.line(
            trends,
            x="Period",
            y="Sales",
            markers=True,
            title=f"{frequency} sales",
            labels={"Period": frequency[:-2] if frequency != "Yearly" else "Year", "Sales": "Sales ($)"},
            hover_data={"Sales": ":$,.0f"},
        )
    )
with right:
    chart(
        px.line(
            trends,
            x="Period",
            y="Profit",
            markers=True,
            title=f"{frequency} profit",
            labels={"Profit": "Profit ($)"},
            hover_data={"Profit": ":$,.0f"},
            color_discrete_sequence=["#34d399"],
        )
    )

growth_columns = ["Period", "Sales"]
if "Orders" in trends.columns:
    growth_columns.insert(2, "Orders")
growth_columns.extend(
    column
    for column in ("MoM Growth %", "QoQ Growth %", "YoY Growth %")
    if column in trends.columns
)
growth_config = {
    column: st.column_config.NumberColumn(format="%.1f%%")
    for column in ("MoM Growth %", "QoQ Growth %", "YoY Growth %")
    if column in growth_columns
}
st.dataframe(
    trends[growth_columns].sort_values("Period", ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={"Sales": st.column_config.NumberColumn(format="$%.2f"), **growth_config},
)

section_header("Sales mix", "Compare performance across the dimensions available in this dataset.")
dimensions = [column for column in ("Category", "Sub-Category", "Market", "Region") if column in df]
columns = st.columns(2)
for index, dimension in enumerate(dimensions):
    with columns[index % 2]:
        summary = (
            df.groupby(dimension, as_index=False, dropna=False)
            .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
            .sort_values("Sales", ascending=False)
        )
        chart(
            px.bar(
                summary,
                x=dimension,
                y="Sales",
                color="Profit",
                color_continuous_scale=["#f87171", "#334155", "#4f8ef7"],
                title=f"Sales by {dimension}",
                hover_data={"Sales": ":$,.0f", "Profit": ":$,.0f"},
                labels={"Sales": "Sales ($)", "Profit": "Profit ($)"},
            )
        )
if not dimensions:
    st.info("Category, market, and regional sales breakdowns are unavailable.")

products = product_performance(df)
if not products.empty:
    product_label = "Product Name" if "Product Name" in products else "Product ID"
    section_header("Product leaders and laggards")
    top, bottom = st.columns(2)
    with top:
        chart(
            px.bar(
                products.head(10).sort_values("Sales"),
                x="Sales",
                y=product_label,
                orientation="h",
                title="Top 10 products by sales",
                hover_data={"Profit": ":$,.0f"},
            )
        )
    with bottom:
        chart(
            px.bar(
                products.nsmallest(10, "Sales").sort_values("Sales", ascending=False),
                x="Sales",
                y=product_label,
                orientation="h",
                title="Bottom 10 products by sales",
                color_discrete_sequence=["#71849d"],
                hover_data={"Profit": ":$,.0f"},
            )
        )

section_header(
    "Monthly sales forecast",
    "Forecast values are model estimates, not actual results. Accuracy is evaluated on a held-out period.",
)
horizon = st.radio("Forecast horizon", [3, 6], horizontal=True, format_func=lambda value: f"{value} months")
forecast = forecast_monthly_sales(df, horizon=horizon)
if "error" in forecast:
    st.info(forecast["error"])
else:
    history = forecast["history"]
    future = forecast["future"]
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=history["Period"],
            y=history["Actual Sales"],
            name="Actual sales",
            mode="lines",
            line=dict(color="#60a5fa", width=2.5),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=history["Period"],
            y=history["Backtest Forecast"],
            name="Held-out model estimate",
            mode="lines+markers",
            line=dict(color="#fbbf24", dash="dot"),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=future["Period"],
            y=future["Forecast Sales"],
            name=f"Forecast · next {horizon} months",
            mode="lines+markers",
            line=dict(color="#22c5dc", dash="dash", width=2.5),
        )
    )
    chart(figure, height=440)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Model", forecast["model"])
    metric_columns[1].metric("Holdout MAE", f"${forecast['metrics']['MAE']:,.0f}")
    metric_columns[2].metric("Holdout RMSE", f"${forecast['metrics']['RMSE']:,.0f}")
    metric_columns[3].metric("Holdout sMAPE", f"{forecast['metrics']['sMAPE']:.1f}%")
    st.caption(
        f"Backtest: last {forecast['holdout_months']} months held out; "
        f"{forecast['training_months']} earlier months used for fitting."
    )
