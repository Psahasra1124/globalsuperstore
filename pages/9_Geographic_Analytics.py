import plotly.express as px
import streamlit as st

from utils.ui import page_header, section_header
from utils.visualizations import chart


df = st.session_state["df"]
page_header(
    "Geographic Analytics",
    "Compare country, market, and regional sales and profitability across the active filters.",
    "Geographic performance",
)

dimensions = [column for column in ("Country", "Market", "Region") if column in df]
if not dimensions:
    st.info("Geographic views require Country, Market, or Region in the dataset.")
else:
    left, right, third = st.columns(3)
    for column, dimension in zip((left, right, third), dimensions):
        sales = df.groupby(dimension)["Sales"].sum()
        profit = df.groupby(dimension)["Profit"].sum()
        top_sales = sales.idxmax() if len(sales) else "—"
        top_profit = profit.idxmax() if len(profit) else "—"
        column.metric(f"Top {dimension.lower()} by sales", str(top_sales))
        column.caption(f"Top profit: {top_profit}")

    section_header("Country performance", "Select a country on the map or hover for sales and profit.")
    if "Country" in df.columns:
        countries = (
            df.groupby("Country", as_index=False, dropna=False)
            .agg(
                Sales=("Sales", "sum"),
                Profit=("Profit", "sum"),
                Orders=("Order ID", "nunique"),
            )
            .sort_values("Sales", ascending=False)
        )
        left, right = st.columns([1.5, 1])
        with left:
            figure = px.choropleth(
                countries,
                locations="Country",
                locationmode="country names",
                color="Sales",
                hover_name="Country",
                hover_data={"Sales": ":$,.0f", "Profit": ":$,.0f", "Orders": True},
                color_continuous_scale=["#1e3a8a", "#60a5fa"],
                title="Sales by country",
                projection="natural earth",
            )
            chart(figure, height=470)
        with right:
            chart(
                px.bar(
                    countries.head(15).sort_values("Sales"),
                    x="Sales",
                    y="Country",
                    orientation="h",
                    title="Top 15 countries by sales",
                    color="Profit",
                    color_continuous_scale=["#f87171", "#334155", "#4f8ef7"],
                    hover_data={"Sales": ":$,.0f", "Profit": ":$,.0f"},
                )
            )
    else:
        st.info("Country mapping is unavailable because Country is missing.")

    available = [column for column in ("Market", "Region") if column in df]
    columns = st.columns(max(1, len(available)))
    for index, dimension in enumerate(available):
        with columns[index]:
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
                    title=f"Sales and profit by {dimension.lower()}",
                    hover_data={"Sales": ":$,.0f", "Profit": ":$,.0f"},
                )
            )

    if "Country" in df.columns:
        section_header("Country detail", "Searchable, filter-aware geography table.")
        search = st.text_input("Search countries", placeholder="Type a country name")
        if search:
            countries = countries.loc[
                countries["Country"].astype("string").str.contains(
                    search, case=False, na=False, regex=False
                )
            ]
        st.dataframe(
            countries.head(500),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sales": st.column_config.NumberColumn(format="$%.2f"),
                "Profit": st.column_config.NumberColumn(format="$%.2f"),
            },
        )
