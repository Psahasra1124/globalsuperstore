from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_ALIASES = {
    "Order ID": ["Order ID", "Order_ID", "OrderID"],
    "Order Date": ["Order Date", "Order_Date", "OrderDate"],
    "Ship Date": ["Ship Date", "Ship_Date", "ShipDate"],
    "Ship Mode": ["Ship Mode", "Ship_Mode", "ShipMode"],
    "Customer ID": ["Customer ID", "Customer_ID", "CustomerID"],
    "Customer Name": ["Customer Name", "Customer_Name", "CustomerName"],
    "Segment": ["Segment"],
    "Country": ["Country"],
    "City": ["City"],
    "State": ["State"],
    "Region": ["Region"],
    "Product ID": ["Product ID", "Product_ID", "ProductID"],
    "Category": ["Category"],
    "Sub-Category": ["Sub-Category", "Sub Category", "Sub_Category"],
    "Product Name": ["Product Name", "Product_Name"],
    "Sales": ["Sales"],
    "Quantity": ["Quantity"],
    "Discount": ["Discount"],
    "Profit": ["Profit"],
}
REQUIRED_COLUMNS = ("Order ID", "Order Date", "Sales", "Profit")
NUMERIC_COLUMNS = (
    "Row ID",
    "Postal Code",
    "Sales",
    "Quantity",
    "Discount",
    "Profit",
    "Shipping Cost",
)
TEXT_COLUMNS = tuple(
    column
    for column in REQUIRED_ALIASES
    if column not in {"Order Date", "Ship Date", "Sales", "Quantity", "Discount", "Profit"}
)
DESCRIPTIVE_COLUMNS = (
    "Ship Mode",
    "Customer Name",
    "Segment",
    "Country",
    "City",
    "State",
    "Region",
    "Category",
    "Sub-Category",
    "Product Name",
)
DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data"


def normalize_columns(df):
    df = df.copy()
    df.columns = [str(column).strip() for column in df.columns]
    rename = {}
    existing = set(df.columns)
    for target, aliases in REQUIRED_ALIASES.items():
        if target in existing:
            continue
        for alias in aliases:
            if alias in existing:
                rename[alias] = target
                existing.add(target)
                break
    return df.rename(columns=rename)


def _read_csv(source):
    last_error = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        if hasattr(source, "seek"):
            source.seek(0)
        try:
            return pd.read_csv(source, encoding=encoding, low_memory=False)
        except UnicodeDecodeError as error:
            last_error = error
    raise last_error


def _read_source(source):
    name = getattr(source, "name", str(source))
    if Path(name).suffix.lower() in {".xlsx", ".xls"}:
        if hasattr(source, "seek"):
            source.seek(0)
        return pd.read_excel(source)
    return _read_csv(source)


def load_dataset(source=None):
    if source is not None:
        return normalize_columns(_read_source(source))

    candidates = (
        DATA_DIRECTORY / "Global_Superstore2.xlsx",
        DATA_DIRECTORY / "Global_Superstore2.csv",
    )
    errors = []
    for candidate in candidates:
        try:
            if not candidate.is_file():
                raise FileNotFoundError(f"{candidate.name} was not found in the data folder")
            return normalize_columns(_read_source(candidate))
        except Exception as error:
            errors.append(f"{candidate.name}: {error}")
    raise RuntimeError(
        "Could not load either project dataset. "
        + " | ".join(errors)
        + " Place Global_Superstore2.xlsx or Global_Superstore2.csv in the data folder."
    )


def _parse_date(series):
    return pd.to_datetime(series, errors="coerce", dayfirst=True, format="mixed")


def clean_data(raw):
    df = normalize_columns(raw).drop_duplicates().copy()
    rows_before = len(raw)
    duplicates_removed = rows_before - len(df)

    missing_required = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_required:
        raise ValueError(
            "Missing essential columns: "
            + ", ".join(missing_required)
            + ". Required columns are Order ID, Order Date, Sales, and Profit."
        )

    missing_before = int(df.isna().sum().sum())
    for column in TEXT_COLUMNS:
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip()
            df[column] = df[column].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    invalid_date_mask = pd.Series(False, index=df.index)
    for column in ("Order Date", "Ship Date"):
        if column in df.columns:
            source_values = df[column]
            parsed = _parse_date(source_values)
            invalid_date_mask |= source_values.notna() & parsed.isna()
            df[column] = parsed
    invalid_date_rows = int(invalid_date_mask.sum())

    invalid_numeric_mask = pd.Series(False, index=df.index)
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            source_values = df[column]
            numeric_values = pd.to_numeric(source_values, errors="coerce")
            invalid_numeric_mask |= source_values.notna() & numeric_values.isna()
            df[column] = numeric_values

    for column in ("Sales", "Profit"):
        invalid_numeric_mask |= df[column].isna()

    invalid_rows = pd.Series(False, index=df.index)
    if "Quantity" in df.columns:
        invalid_rows |= df["Quantity"].notna() & df["Quantity"].le(0)
    if "Discount" in df.columns:
        invalid_rows |= df["Discount"].notna() & (
            df["Discount"].lt(0) | df["Discount"].gt(1)
        )
    invalid_numeric_mask |= invalid_rows
    invalid_numeric_rows = int(invalid_numeric_mask.sum())
    df = df.loc[~invalid_rows].copy()

    df = df.dropna(subset=list(REQUIRED_COLUMNS)).copy()

    for column in DESCRIPTIVE_COLUMNS:
        if column in df.columns:
            df[column] = df[column].fillna("Unknown")

    df["Year"] = df["Order Date"].dt.year.astype("Int64")
    df["Month"] = df["Order Date"].dt.month_name()
    df["Quarter"] = "Q" + df["Order Date"].dt.quarter.astype(str)
    df["Order Month"] = df["Order Date"].dt.to_period("M").astype(str)
    if "Ship Date" in df.columns:
        df["Shipping Duration"] = (df["Ship Date"] - df["Order Date"]).dt.days
        df.loc[df["Shipping Duration"] < 0, "Shipping Duration"] = np.nan
    df["Profit Margin"] = np.where(
        df["Sales"] != 0, df["Profit"] / df["Sales"], np.nan
    )

    outlier_counts = {}
    for column in ("Sales", "Profit", "Quantity", "Discount"):
        if column not in df.columns or df[column].notna().sum() == 0:
            continue
        q1, q3 = df[column].quantile([0.25, 0.75])
        iqr = q3 - q1
        outlier_counts[column] = int(
            ((df[column] < q1 - 1.5 * iqr) | (df[column] > q3 + 1.5 * iqr)).sum()
        )

    report = {
        "rows_before": rows_before,
        "duplicates_removed": duplicates_removed,
        "missing_before": missing_before,
        "invalid_date_rows": invalid_date_rows,
        "invalid_numeric_rows": invalid_numeric_rows,
        "outlier_counts": outlier_counts,
        "rows_after": len(df),
        "missing_after": int(df.isna().sum().sum()),
        "columns": len(df.columns),
    }
    return df, report
