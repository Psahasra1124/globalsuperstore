import json
import zipfile
from io import BytesIO

import pandas as pd
import streamlit as st
from openpyxl.utils.exceptions import InvalidFileException

from database.datasets import (
    MAX_UPLOAD_BYTES,
    activate_dataset,
    get_active_dataset_path,
    get_dataset_path,
    initialize_dataset_db,
    list_datasets,
    save_uploaded_dataset,
)
from utils.data_cleaning import clean_data, load_dataset
from utils.ui import page_header, section_header


class NamedBuffer(BytesIO):
    def __init__(self, name, content):
        super().__init__(content)
        self.name = name


initialize_dataset_db()
page_header(
    "Data Management",
    "Validate, track, and activate datasets without replacing the supplied source files.",
    "Dataset management",
)

section_header("Upload and validate")
st.caption("Supported: CSV and XLSX, up to 100 MB. Uploads are stored with generated filenames.")
uploaded = st.file_uploader(
    "Choose a dataset",
    type=["csv", "xlsx"],
    key="managed_dataset_upload",
)
if uploaded is not None and st.button("Validate and save upload", type="primary"):
    content = uploaded.getvalue()
    if len(content) > MAX_UPLOAD_BYTES:
        st.error("The dataset exceeds the 100 MB upload limit.")
    else:
        try:
            raw = load_dataset(NamedBuffer(uploaded.name, content))
            cleaned, report = clean_data(raw)
            if cleaned.empty:
                raise ValueError("No valid records remain after cleaning.")
            dataset_id = save_uploaded_dataset(
                uploaded.name,
                content,
                len(cleaned),
                list(cleaned.columns),
            )
            st.success(
                f"Upload #{dataset_id} validated: {len(cleaned):,} cleaned rows; "
                f"{len(cleaned.columns)} columns. The active dataset was not changed."
            )
            st.json(report)
        except (ValueError, RuntimeError, OSError) as error:
            st.error(f"Dataset validation failed: {error}")
        except (ImportError, UnicodeError, zipfile.BadZipFile, InvalidFileException, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
            st.error(f"Dataset could not be read: {error}")

section_header("Dataset history")
active_path = get_active_dataset_path()
if active_path:
    st.success(f"Managed active dataset: {active_path.name}")
else:
    st.info("The supplied project dataset is active. Original Excel/CSV files are not changed.")

datasets = list_datasets()
if datasets:
    display_rows = []
    for item in datasets:
        display_rows.append(
            {
                "ID": item["id"],
                "Source name": item["original_name"],
                "Rows": item["row_count"],
                "Uploaded at (UTC)": item["uploaded_at"],
                "Active": bool(item["is_active"]),
                "SHA-256": item["sha256"],
            }
        )
    st.dataframe(display_rows, use_container_width=True, hide_index=True)
    options = {
        f"#{item['id']} · {item['original_name']} · {item['uploaded_at']}": item
        for item in datasets
    }
    selected_label = st.selectbox("Dataset to activate", list(options))
    selected = options[selected_label]
    with st.expander("Selected dataset schema"):
        st.write(json.loads(selected["columns_json"]))
    if not selected["is_active"] and st.button("Activate selected dataset"):
        try:
            path = get_dataset_path(selected["id"])
            reloaded = load_dataset(NamedBuffer(path.name, path.read_bytes()))
            cleaned, _ = clean_data(reloaded)
            if cleaned.empty:
                raise ValueError("No valid rows remain in this dataset.")
            activate_dataset(selected["id"])
            st.success("Dataset activated. The dashboard will reload with the new source.")
            st.rerun()
        except (ValueError, RuntimeError, OSError) as error:
            st.error(f"Could not activate this dataset: {error}")
        except (ImportError, UnicodeError, zipfile.BadZipFile, InvalidFileException, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
            st.error(f"Could not read the selected dataset: {error}")
else:
    st.caption("No managed uploads yet.")
