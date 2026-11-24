import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from utils.analytics import product_performance, search_rows
from utils.exports import csv_bytes, excel_bytes
from utils.ui import page_header, section_header
from utils.visualizations import chart


df = st.session_state["df"]
page_header(
    "Product Performance",
    "Prioritize products by sales, profit, margin, and contribution to the portfolio.",
    "Assortment & mix",
)

products = product_performance(df)
if products.empty:
    st.info("Product analysis requires Product ID or Product Name.")
else:
    product_label = "Product Name" if "Product Name" in products else "Product ID"
    metric_columns = st.columns(4)
    metric_columns[0].metric("Distinct products", f"{len(products):,}")
    metric_columns[1].metric(
        "Top product sales", f"${products.iloc[0]['Sales']:,.0f}"
    )
    metric_columns[2].metric(
        "Products with losses", f"{int(products['Profit'].lt(0).sum()):,}"
    )
    metric_columns[3].metric(
        "Revenue in top 20%", f"{products.head(max(1, int(np.ceil(len(products) * 0.2))))['Sales'].sum() / products['Sales'].sum():.1%}"
        if products["Sales"].sum()
        else "—"
    )

    section_header("Leaders by sales and profit")
    left, right = st.columns(2)
    with left:
        chart(
            px.bar(
                products.head(15).sort_values("Sales"),
                x="Sales",
                y=product_label,
                orientation="h",
                title="Top products by sales",
                color_discrete_sequence=["#60a5fa"],
                hover_data={"Profit": ":$,.0f", "Profit Margin": ":.1%"},
            )
        )
    with right:
        chart(
            px.bar(
                products.nlargest(15, "Profit").sort_values("Profit"),
                x="Profit",
                y=product_label,
                orientation="h",
                title="Top products by profit",
                color_discrete_sequence=["#34d399"],
                hover_data={"Sales": ":$,.0f", "Profit Margin": ":.1%"},
            )
        )

    if "Category" in products.columns:
        section_header("Category contribution")
        categories = products.groupby("Category", as_index=False).agg(
            Sales=("Sales", "sum"), Profit=("Profit", "sum")
        )
        chart(
            px.pie(
                categories,
                names="Category",
                values="Sales",
                hole=0.55,
                title="Share of sales by category",
                hover_data={"Profit": ":$,.0f"},
            )
        )

    section_header("Product performance matrix", "Portfolio quadrants use median sales and margin as reference points.")
    sales_midpoint = products["Sales"].median()
    margin_midpoint = products["Profit Margin"].median()
    products["Performance"] = np.select(
        [
            products["Sales"].ge(sales_midpoint)
            & products["Profit Margin"].ge(margin_midpoint),
            products["Sales"].ge(sales_midpoint)
            & products["Profit Margin"].lt(margin_midpoint),
            products["Sales"].lt(sales_midpoint)
            & products["Profit Margin"].ge(margin_midpoint),
        ],
        ["Scale & protect", "High sales · low margin", "Profitable niche"],
        default="Review",
    )
    scatter_options = {"size": "Quantity"} if "Quantity" in products else {}
    if "Category" in products:
        scatter_options["hover_data"] = ["Category", "Orders"] if "Orders" in products else ["Category"]
    else:
        scatter_options["hover_data"] = ["Orders"] if "Orders" in products else None
    chart(
        px.scatter(
            products,
            x="Sales",
            y="Profit Margin",
            color="Performance",
            hover_name=product_label,
            color_discrete_map={
                "Scale & protect": "#60a5fa",
                "High sales · low margin": "#fbbf24",
                "Profitable niche": "#34d399",
                "Review": "#94a3b8",
            },
            title="Sales vs. profit margin by product",
            labels={"Sales": "Sales ($)", "Profit Margin": "Profit margin"},
            **scatter_options,
        )
    )

    section_header("Pareto contribution", "Cumulative sales share shows how concentrated revenue is across products.")
    pareto = products.head(30)
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Bar(
            x=pareto[product_label],
            y=pareto["Sales"],
            name="Sales",
            marker_color="#60a5fa",
            hovertemplate="%{x}<br>Sales: $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=pareto[product_label],
            y=pareto["Sales Share"] * 100,
            name="Cumulative sales share",
            mode="lines+markers",
            line=dict(color="#fbbf24", width=2.5),
        ),
        secondary_y=True,
    )
    figure.add_trace(
        go.Scatter(
            x=pareto[product_label],
            y=[80] * len(pareto),
            name="80% reference",
            mode="lines",
            line=dict(color="#94a3b8", dash="dash"),
        ),
        secondary_y=True,
    )
    figure.update_yaxes(title_text="Sales ($)", secondary_y=False)
    figure.update_yaxes(title_text="Cumulative share (%)", range=[0, 105], secondary_y=True)
    chart(figure, height=440)

    section_header("Searchable product catalogue")
    search = st.text_input("Search products", placeholder="Type a product name, ID, or category")
    catalogue = search_rows(
        products, search, ["Product Name", "Product ID", "Category", "Sub-Category"]
    )
    st.dataframe(
        catalogue.head(500),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Sales": st.column_config.NumberColumn(format="$%.2f"),
            "Profit": st.column_config.NumberColumn(format="$%.2f"),
            "Profit Margin": st.column_config.NumberColumn(format="%.1f%%"),
            "Sales Share": st.column_config.NumberColumn(format="%.1%"),
        },
    )
    export_csv, export_excel = st.columns(2)
    with export_csv:
        st.download_button(
            "Download product results · CSV",
            csv_bytes(catalogue),
            file_name="product_results.csv",
            mime="text/csv",
        )
    with export_excel:
        st.download_button(
            "Download product results · Excel",
            excel_bytes(catalogue, "Product Results"),
            file_name="product_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
