import plotly.express as px
import streamlit as st

from utils.analytics import customer_performance, customer_rfm, search_rows
from utils.exports import csv_bytes, excel_bytes
from utils.ui import page_header, section_header
from utils.visualizations import chart


df = st.session_state["df"]
page_header(
    "Customer Intelligence",
    "Explore customer value, repeat purchasing, and RFM segments within the selected period.",
    "Retention & value",
)

customers = customer_performance(df)
rfm = customer_rfm(df)
if customers.empty or rfm.empty:
    st.info("Customer analytics require Customer ID or Customer Name.")
else:
    repeat_customers = int(customers["Orders"].gt(1).sum())
    metrics = st.columns(4)
    metrics[0].metric("Unique customers", f"{len(customers):,}")
    metrics[1].metric("Repeat customers", f"{repeat_customers:,}")
    metrics[2].metric("Average customer spend", f"${rfm['Monetary'].mean():,.0f}")
    metrics[3].metric("Average orders / customer", f"{rfm['Frequency'].mean():.1f}")

    section_header("RFM segmentation", "Recency, frequency, and monetary scores are calculated from the filtered records.")
    left, right = st.columns(2)
    with left:
        segment_summary = (
            rfm.groupby("RFM Segment", as_index=False)
            .agg(Customers=(rfm.columns[0], "size"), Revenue=("Monetary", "sum"))
            .sort_values("Revenue", ascending=False)
        )
        chart(
            px.bar(
                segment_summary,
                x="RFM Segment",
                y="Customers",
                color="Revenue",
                color_continuous_scale=["#1d4ed8", "#60a5fa"],
                title="Customers by RFM segment",
                hover_data={"Revenue": ":$,.0f"},
            )
        )
    with right:
        chart(
            px.scatter(
                rfm,
                x="Frequency",
                y="Monetary",
                color="RFM Segment",
                size="Recency",
                hover_name="Customer Name" if "Customer Name" in rfm.columns else None,
                hover_data={"Recency": True, "Profit": ":$,.0f"} if "Profit" in rfm.columns else {"Recency": True},
                color_discrete_sequence=["#60a5fa", "#22c5dc", "#34d399", "#fbbf24", "#a78bfa", "#fb7185"],
                title="Customer frequency vs. spend",
                labels={"Frequency": "Distinct orders", "Monetary": "Net sales ($)", "Recency": "Days since last order"},
            )
        )

    if "Segment" in df.columns:
        section_header("Revenue by customer type")
        segment_revenue = df.groupby("Segment", as_index=False).agg(
            Sales=("Sales", "sum"), Profit=("Profit", "sum")
        )
        chart(
            px.pie(
                segment_revenue,
                names="Segment",
                values="Sales",
                hole=0.55,
                title="Revenue contribution by customer segment",
                hover_data={"Profit": ":$,.0f"},
            )
        )

    section_header("Customer directory", "Search by customer name or ID; results follow all global filters.")
    search = st.text_input("Search customers", placeholder="Type a customer name or ID")
    visible = search_rows(customers, search, ["Customer Name", "Customer ID"])

    sales_tab, profit_tab, rfm_tab = st.tabs(
        ["Top by sales", "Top by profit", "RFM detail"]
    )
    with sales_tab:
        st.dataframe(
            visible.sort_values("Sales", ascending=False).head(100),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sales": st.column_config.NumberColumn(format="$%.2f"),
                "Profit": st.column_config.NumberColumn(format="$%.2f"),
            },
        )
    with profit_tab:
        st.dataframe(
            visible.sort_values("Profit", ascending=False).head(100),
            use_container_width=True,
            hide_index=True,
        )
    with rfm_tab:
        rfm_search = search_rows(rfm, search, ["Customer Name", "Customer ID"])
        st.dataframe(
            rfm_search.head(100),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Monetary": st.column_config.NumberColumn(format="$%.2f"),
                "Profit": st.column_config.NumberColumn(format="$%.2f"),
            },
        )
    export_csv, export_excel = st.columns(2)
    with export_csv:
        st.download_button(
            "Download customer results · CSV",
            csv_bytes(visible),
            file_name="customer_results.csv",
            mime="text/csv",
        )
    with export_excel:
        st.download_button(
            "Download customer results · Excel",
            excel_bytes(visible, "Customer Results"),
            file_name="customer_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
