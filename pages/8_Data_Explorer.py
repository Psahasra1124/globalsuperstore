import pandas as pd
import streamlit as st

from utils.exports import csv_bytes, excel_bytes, quality_report_excel_bytes
from utils.ui import page_header, section_header


df = st.session_state["df"]
clean = st.session_state["clean"]
raw = st.session_state["raw"]
report = st.session_state["cleaning_report"]
page_header(
    "Data Explorer",
    "Inspect source data, cleaning decisions, schema quality, and downloadable extracts.",
    "Data governance",
)

metrics = st.columns(4)
metrics[0].metric("Filtered rows", f"{len(df):,}")
metrics[1].metric("Source rows", f"{len(raw):,}")
metrics[2].metric("Fields", f"{len(df.columns):,}")
metrics[3].metric("Missing filtered values", f"{int(df.isna().sum().sum()):,}")

section_header("Data quality summary", "Cleaning is applied consistently before analysis.")
quality = st.columns(4)
quality[0].metric("Duplicates removed", f"{report['duplicates_removed']:,}")
quality[1].metric("Invalid date rows", f"{report['invalid_date_rows']:,}")
quality[2].metric("Invalid numeric rows", f"{report['invalid_numeric_rows']:,}")
quality[3].metric("Cleaned rows", f"{report['rows_after']:,}")
with st.expander("Full cleaning report"):
    st.json(report)

section_header("Schema and missing values")
schema = pd.DataFrame(
    {
        "Column": clean.columns,
        "Data type": [str(dtype) for dtype in clean.dtypes],
        "Missing": clean.isna().sum().values,
        "Missing %": (clean.isna().mean().values * 100).round(2),
        "Unique values": clean.nunique(dropna=True).values,
    }
)
search = st.text_input("Search fields", placeholder="Type a column name or data type")
if search:
    visible = schema.astype("string").apply(
        lambda column: column.str.contains(search, case=False, na=False, regex=False)
    ).any(axis=1)
    schema = schema.loc[visible]
st.dataframe(
    schema.sort_values("Missing", ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={"Missing %": st.column_config.NumberColumn(format="%.2f%%")},
)

section_header("Source and cleaned previews")
raw_tab, cleaned_tab, missing_tab = st.tabs(
    ["Source sample", "Filtered cleaned data", "Missing-value profile"]
)
with raw_tab:
    st.dataframe(raw.head(100), use_container_width=True, hide_index=True)
with cleaned_tab:
    st.dataframe(df.head(500), use_container_width=True, hide_index=True)
with missing_tab:
    missing = (
        df.isna()
        .sum()
        .rename("Missing values")
        .to_frame()
        .query("`Missing values` > 0")
        .sort_values("Missing values", ascending=False)
    )
    if missing.empty:
        st.success("No missing values in the current filtered view.")
    else:
        st.dataframe(missing, use_container_width=True)

section_header("Download data and quality report")
csv_column, excel_column, report_column = st.columns(3)
with csv_column:
    st.download_button(
        "Filtered data · CSV",
        csv_bytes(df),
        file_name="superstore_filtered.csv",
        mime="text/csv",
    )
with excel_column:
    st.download_button(
        "Filtered data · Excel",
        excel_bytes(df),
        file_name="superstore_filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
with report_column:
    st.download_button(
        "Quality report · Excel",
        quality_report_excel_bytes(df, report),
        file_name="superstore_quality_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
raw_csv, raw_excel = st.columns(2)
with raw_csv:
    st.download_button(
        "Raw source · CSV",
        csv_bytes(raw),
        file_name="superstore_raw.csv",
        mime="text/csv",
    )
with raw_excel:
    st.download_button(
        "Raw source · Excel",
        excel_bytes(raw, "Raw Source"),
        file_name="superstore_raw.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
