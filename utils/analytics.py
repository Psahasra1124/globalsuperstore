import numpy as np
import pandas as pd


def product_performance(df):
    dimensions = [
        column
        for column in ("Product ID", "Product Name", "Category", "Sub-Category")
        if column in df.columns
    ]
    if not any(column in dimensions for column in ("Product ID", "Product Name")):
        return pd.DataFrame()

    aggregations = {
        "Sales": ("Sales", "sum"),
        "Profit": ("Profit", "sum"),
    }
    if "Quantity" in df.columns:
        aggregations["Quantity"] = ("Quantity", "sum")
    if "Order ID" in df.columns:
        aggregations["Orders"] = ("Order ID", "nunique")
    products = (
        df.groupby(dimensions, as_index=False, dropna=False)
        .agg(**aggregations)
        .sort_values("Sales", ascending=False)
    )
    products["Profit Margin"] = np.where(
        products["Sales"] != 0, products["Profit"] / products["Sales"], np.nan
    )
    products["Sales Share"] = (
        products["Sales"].clip(lower=0).cumsum()
        / products["Sales"].clip(lower=0).sum()
        if products["Sales"].clip(lower=0).sum()
        else 0
    )
    return products


def sales_time_series(df, frequency="Monthly"):
    periods = {"Monthly": "M", "Quarterly": "Q", "Yearly": "Y"}
    if frequency not in periods:
        raise ValueError(f"Unsupported sales frequency: {frequency}")
    if df.empty:
        return pd.DataFrame(
            columns=["Period", "Sales", "Profit", "Orders", "MoM Growth %", "QoQ Growth %", "YoY Growth %"]
        )

    data = df.copy()
    data["Period"] = data["Order Date"].dt.to_period(periods[frequency]).dt.start_time
    aggregations = {"Sales": ("Sales", "sum"), "Profit": ("Profit", "sum")}
    if "Order ID" in data.columns:
        aggregations["Orders"] = ("Order ID", "nunique")
    result = data.groupby("Period", as_index=False).agg(**aggregations).sort_values("Period")
    growth_label = {"Monthly": "MoM Growth %", "Quarterly": "QoQ Growth %", "Yearly": "YoY Growth %"}[frequency]
    result[growth_label] = result["Sales"].pct_change() * 100
    if frequency == "Monthly":
        result["YoY Growth %"] = result["Sales"].pct_change(12) * 100
    elif frequency == "Quarterly":
        result["YoY Growth %"] = result["Sales"].pct_change(4) * 100
    return result.replace([np.inf, -np.inf], np.nan)


def customer_rfm(df):
    customer_key = next(
        (column for column in ("Customer ID", "Customer Name") if column in df.columns),
        None,
    )
    if customer_key is None or df.empty:
        return pd.DataFrame()

    as_of = df["Order Date"].max()
    aggregations = {
        "Recency": ("Order Date", lambda dates: (as_of - dates.max()).days),
        "Monetary": ("Sales", "sum"),
    }
    if "Profit" in df.columns:
        aggregations["Profit"] = ("Profit", "sum")
    if "Order ID" in df.columns:
        aggregations["Frequency"] = ("Order ID", "nunique")
    if "Customer Name" in df.columns and customer_key != "Customer Name":
        aggregations["Customer Name"] = ("Customer Name", "first")
    if "Segment" in df.columns:
        aggregations["Segment"] = ("Segment", "first")

    result = df.groupby(customer_key, as_index=False, dropna=False).agg(**aggregations)
    if "Frequency" not in result.columns:
        result["Frequency"] = 0

    recency_rank = result["Recency"].rank(method="average", pct=True)
    result["R_Score"] = (6 - np.ceil(recency_rank * 5)).clip(1, 5).astype(int)
    for column, score in (("Frequency", "F_Score"), ("Monetary", "M_Score")):
        rank = result[column].rank(method="average", pct=True)
        result[score] = np.ceil(rank * 5).clip(1, 5).astype(int)

    def segment(row):
        if row.R_Score >= 4 and row.F_Score >= 4 and row.M_Score >= 4:
            return "Champions"
        if row.F_Score >= 4 and row.R_Score >= 3:
            return "Loyal"
        if row.R_Score <= 2 and row.F_Score >= 3:
            return "At risk"
        if row.R_Score >= 3 and row.F_Score >= 3:
            return "Potential loyalists"
        if row.M_Score >= 4:
            return "Big spenders"
        return "Needs attention"

    result["RFM Segment"] = result.apply(segment, axis=1)
    return result.sort_values(["RFM Segment", "Monetary"], ascending=[True, False])


def customer_performance(df):
    customer_key = next(
        (column for column in ("Customer ID", "Customer Name") if column in df.columns),
        None,
    )
    if customer_key is None:
        return pd.DataFrame()
    dimensions = [customer_key]
    for column in ("Customer Name", "Segment"):
        if column in df.columns and column not in dimensions:
            dimensions.append(column)
    aggregations = {
        "Sales": ("Sales", "sum"),
        "Profit": ("Profit", "sum"),
        "Orders": ("Order ID", "nunique"),
    }
    return (
        df.groupby(dimensions, as_index=False, dropna=False)
        .agg(**aggregations)
        .sort_values("Sales", ascending=False)
    )


def profitability_heatmap(df):
    if not {"Category", "Region"}.issubset(df.columns):
        return pd.DataFrame()
    grouped = df.groupby(["Category", "Region"], dropna=False).agg(
        Sales=("Sales", "sum"), Profit=("Profit", "sum")
    )
    grouped["Profit Margin"] = grouped["Profit"].div(
        grouped["Sales"].replace(0, np.nan)
    )
    return grouped["Profit Margin"].unstack("Region")


def search_rows(df, query, columns):
    if not query:
        return df
    searchable = [column for column in columns if column in df.columns]
    if not searchable:
        return df.iloc[0:0]
    mask = pd.Series(False, index=df.index)
    query = query.casefold()
    for column in searchable:
        mask |= df[column].astype("string").fillna("").str.casefold().str.contains(
            query, regex=False
        )
    return df.loc[mask]
