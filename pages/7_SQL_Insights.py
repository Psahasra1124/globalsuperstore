import sqlite3
from time import perf_counter

import streamlit as st

from database.database import load_to_readonly_sqlite, query_df
from database.query_catalog import get_queries
from utils.exports import csv_bytes, excel_bytes
from utils.ui import page_header, section_header


df = st.session_state["df"]
page_header(
    "SQL Insights",
    "Run business questions against the current filtered view in SQLite.",
    "Self-service analytics",
)
st.caption("The query runner refreshes the local `orders` table with the active filters before execution.")
st.info(
    "Custom SQL is read-only and limited to `orders`, five seconds, and 10,000 result rows. "
    "Only SELECT statements are accepted."
)

left, right = st.columns([1, 3])
with left:
    if st.button("Load filtered data", type="primary", use_container_width=True):
        connection = None
        try:
            connection = load_to_readonly_sqlite(df)
            st.session_state["sql_loaded"] = True
            st.success(f"{len(df):,} rows loaded.")
        except (sqlite3.Error, ValueError, TypeError) as error:
            st.error(f"Could not load the SQLite table: {error}")
        finally:
            if connection is not None:
                connection.close()
with right:
    st.info("Sample queries are shown only when the required columns are available.")

queries = get_queries(df.columns)
if not queries:
    st.warning("No sample queries match the fields in this dataset.")
else:
    section_header("Business question")
    labels = [label for label, _ in queries]
    selected = st.selectbox("Select a query", labels, label_visibility="collapsed")
    sql = dict(queries)[selected]
    st.code(sql, language="sql")
    if st.button("Run query", type="primary"):
        connection = None
        st.session_state.pop("sql_result", None)
        st.session_state.pop("sql_elapsed", None)
        try:
            connection = load_to_readonly_sqlite(df)
            started = perf_counter()
            result = query_df(connection, sql)
            st.session_state["sql_result"] = result
            st.session_state["sql_elapsed"] = perf_counter() - started
            st.success(f"Query returned {len(result):,} rows.")
        except (sqlite3.Error, ValueError, TypeError) as error:
            st.error(f"Query failed: {error}")
        finally:
            if connection is not None:
                connection.close()

section_header("Read-only SQL explorer")
st.caption("Available columns: " + ", ".join(f"`{column}`" for column in df.columns))
custom_sql = st.text_area(
    "SQL statement",
    value="SELECT Category, SUM(Sales) AS sales FROM orders GROUP BY Category ORDER BY sales DESC;",
    height=120,
    help="Use one SELECT statement against the filtered orders table.",
)
if st.button("Run custom SELECT", type="primary", key="run_custom_sql"):
    connection = None
    st.session_state.pop("sql_result", None)
    st.session_state.pop("sql_elapsed", None)
    try:
        connection = load_to_readonly_sqlite(df)
        started = perf_counter()
        result = query_df(connection, custom_sql)
        st.session_state["sql_result"] = result
        st.session_state["sql_context"] = st.session_state.get("_filter_context")
        st.session_state["sql_elapsed"] = perf_counter() - started
        st.success(f"Query returned {len(result):,} rows.")
    except (sqlite3.Error, ValueError, TypeError) as error:
        st.error(f"Query failed or was blocked: {error}")
    finally:
        if connection is not None:
            connection.close()

if "sql_result" in st.session_state:
    result = st.session_state["sql_result"]
    section_header("Query result")
    if "sql_elapsed" in st.session_state:
        st.caption(f"Execution time: {st.session_state['sql_elapsed']:.3f} seconds")
    st.dataframe(result, use_container_width=True, hide_index=True)
    csv_column, excel_column = st.columns(2)
    with csv_column:
        st.download_button(
            "Download result CSV",
            csv_bytes(result),
            file_name="sql_result.csv",
            mime="text/csv",
        )
    with excel_column:
        st.download_button(
            "Download result Excel",
            excel_bytes(result, "SQL Result"),
            file_name="sql_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
