import plotly.express as px
import streamlit as st

from utils.analytics import product_performance
from utils.eda import grouped
from utils.insights import generate_insights
from utils.ui import page_header, render_kpis, section_header
from utils.visualizations import chart


df = st.session_state["df"]
page_header(
    "Executive Overview",
    "A concise view of performance, momentum, and the factors shaping results.",
    "Leadership brief",
)
render_kpis(df, st.session_state["previous_df"])

section_header("Performance trends", "Actual results for the current filter and comparison period.")
monthly = df.groupby("Order Month", as_index=False).agg(
    Sales=("Sales", "sum"), Profit=("Profit", "sum")
)
monthly["Period"] = monthly["Order Month"].astype(str)
left, right = st.columns(2)
with left:
    chart(
        px.line(
            monthly,
            x="Period",
            y="Sales",
            markers=True,
            title="Monthly sales",
            labels={"Sales": "Sales ($)", "Period": "Month"},
            hover_data={"Sales": ":$,.0f"},
        )
    )
with right:
    chart(
        px.line(
            monthly,
            x="Period",
            y="Profit",
            markers=True,
            title="Monthly profit",
            labels={"Profit": "Profit ($)", "Period": "Month"},
            hover_data={"Profit": ":$,.0f"},
        )
    )

section_header("Where results are coming from")
left, right = st.columns(2)
with left:
    if "Region" in df.columns:
        regions = grouped(df, "Region").sort_values("Sales", ascending=False)
        chart(
            px.bar(
                regions,
                x="Region",
                y="Sales",
                color="Sales",
                color_continuous_scale=["#1d4ed8", "#60a5fa"],
                title="Regional sales and profit",
                hover_data={"Profit": ":$,.0f", "Orders": True},
                labels={"Sales": "Sales ($)", "Profit": "Profit ($)"},
            )
        )
    else:
        st.info("Regional performance is unavailable because Region is missing.")
with right:
    products = product_performance(df)
    if not products.empty:
        product_label = "Product Name" if "Product Name" in products else "Product ID"
        chart(
            px.bar(
                products.head(10).sort_values("Sales"),
                x="Sales",
                y=product_label,
                orientation="h",
                title="Top 10 products by sales",
                color_discrete_sequence=["#60a5fa"],
                hover_data={"Profit": ":$,.0f", "Profit Margin": ":.1%"},
                labels={"Sales": "Sales ($)"},
            )
        )
    else:
        st.info("Product rankings are unavailable because product identifiers are missing.")

section_header("Business signals", "Observations are calculated from the filtered records.")
insights = generate_insights(df)
if insights:
    for item in insights[:6]:
        with st.container():
            st.markdown(f"**{item['Finding']}**  \n{item['Evidence']}")
            st.caption(item["Recommendation"])
else:
    st.info("There is not enough filtered data to generate business signals.")
