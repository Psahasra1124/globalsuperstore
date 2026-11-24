from datetime import timedelta

def filter_data(df,start,end,filters):
    out=df[(df["Order Date"].dt.date>=start)&(df["Order Date"].dt.date<=end)].copy()
    for col,vals in filters.items():
        if col in out.columns and vals:
            out=out[out[col].astype(str).isin(vals)]
    return out

def summary(df):
    sales=df["Sales"].sum()
    profit=df["Profit"].sum()
    customer_column = next(
        (column for column in ("Customer ID", "Customer Name") if column in df.columns),
        None,
    )
    return {"sales":sales,"profit":profit,"orders":df["Order ID"].nunique(),
            "customers":df[customer_column].nunique() if customer_column else 0,
            "aov":df.groupby("Order ID")["Sales"].sum().mean() if len(df) else 0,
            "margin":profit/sales if sales else 0}

def previous_period_data(df,start,end,filters):
    period_length=(end-start).days+1
    previous_end=start-timedelta(days=1)
    previous_start=previous_end-timedelta(days=period_length-1)
    return filter_data(df,previous_start,previous_end,filters)
