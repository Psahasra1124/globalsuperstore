import pandas as pd
def monthly(df):
    return df.groupby("Order Month",as_index=False).agg(Sales=("Sales","sum"),Profit=("Profit","sum")).sort_values("Order Month")
def grouped(df,by):
    if by not in df.columns:
        return pd.DataFrame(columns=[by,"Sales","Profit","Orders","Quantity"])
    aggregations = {"Sales":("Sales","sum"),"Profit":("Profit","sum")}
    if "Order ID" in df.columns:
        aggregations["Orders"]=("Order ID","nunique")
    if "Quantity" in df.columns:
        aggregations["Quantity"]=("Quantity","sum")
    return df.groupby(by,dropna=False).agg(**aggregations).reset_index()
def customer_table(df):
    keys=[column for column in ("Customer ID","Customer Name","Segment") if column in df.columns]
    if not any(column in keys for column in ("Customer ID","Customer Name")):
        return pd.DataFrame(columns=keys+["Sales","Orders","Profit"])
    aggregations={"Sales":("Sales","sum"),"Profit":("Profit","sum")}
    if "Order ID" in df.columns:
        aggregations["Orders"]=("Order ID","nunique")
    return df.groupby(keys,as_index=False,dropna=False).agg(**aggregations).sort_values("Sales",ascending=False)
