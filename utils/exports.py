from html import escape
from io import BytesIO

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@st.cache_data(show_spinner=False, max_entries=8)
def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


@st.cache_data(show_spinner=False, max_entries=8)
def excel_bytes(df, sheet_name="Filtered Data"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return output.getvalue()


@st.cache_data(show_spinner=False, max_entries=8)
def quality_report_excel_bytes(df, report):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Filtered Data", index=False)
        pd.DataFrame(
            [{"Check": key, "Result": str(value)} for key, value in report.items()]
        ).to_excel(writer, sheet_name="Data Quality", index=False)
    return output.getvalue()


@st.cache_data(show_spinner=False, max_entries=8)
def pdf_report_bytes(df, date_range):
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="Global Superstore filtered report",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            textColor=colors.HexColor("#64758a"),
            alignment=TA_LEFT,
            spaceAfter=12,
        )
    )
    start, end = date_range
    story = [
        Paragraph("Global Superstore", styles["Title"]),
        Paragraph(
            f"Filtered business report · {escape(str(start))} to {escape(str(end))}",
            styles["ReportSubtitle"],
        ),
    ]

    sales = float(df["Sales"].sum()) if "Sales" in df else 0.0
    profit = float(df["Profit"].sum()) if "Profit" in df else 0.0
    orders = int(df["Order ID"].nunique()) if "Order ID" in df else len(df)
    customer_column = next(
        (column for column in ("Customer ID", "Customer Name") if column in df),
        None,
    )
    customers = int(df[customer_column].nunique()) if customer_column else 0
    metrics = [
        ["Metric", "Value"],
        ["Filtered order lines", f"{len(df):,}"],
        ["Orders", f"{orders:,}"],
        ["Customers", f"{customers:,}"],
        ["Sales", f"{sales:,.2f}"],
        ["Profit", f"{profit:,.2f}"],
        ["Profit margin", f"{profit / sales:.1%}" if sales else "N/A"],
    ]
    story.append(Table(metrics, colWidths=[3.1 * inch, 3.1 * inch]))
    story.append(Spacer(1, 16))

    for column, title, metric in (
        ("Category", "Category performance", ("Sales", "Profit")),
        ("Region", "Regional performance", ("Sales", "Profit")),
        ("Product Name", "Top products by sales", ("Sales",)),
    ):
        if column not in df.columns or not set(metric).issubset(df.columns):
            continue
        summary = (
            df.groupby(column, dropna=False)[list(metric)]
            .sum()
            .sort_values(metric[0], ascending=False)
            .head(10)
            .reset_index()
        )
        table_rows = [[column, *metric]]
        for _, row in summary.iterrows():
            table_rows.append(
                [
                    escape(str(row[column]))[:120],
                    *[f"{float(row[name]):,.2f}" for name in metric],
                ]
            )
        story.extend(
            [
                Paragraph(escape(title), styles["Heading2"]),
                Table(table_rows, repeatRows=1, colWidths=[3.1 * inch] + [1.55 * inch] * len(metric)),
                Spacer(1, 12),
            ]
        )

    for table in (item for item in story if isinstance(item, Table)):
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dce4ed")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
    document.build(story)
    return output.getvalue()
