def answer_question(df, question):
    query = str(question or "").strip().lower()
    if not query:
        return "Enter a business question to analyze the current filtered data.", None
    if df.empty:
        return "There are no filtered records to analyze.", None

    if any(term in query for term in ("discount", "discounting")) and "Discount" in df:
        grouped = (
            df.groupby("Discount", as_index=False)
            .agg(Average_Profit=("Profit", "mean"), Sales=("Sales", "sum"))
            .sort_values("Discount")
        )
        return (
            "Observed discount levels and average line profit in the filtered data. "
            "This is an association, not evidence that discounts caused the outcome.",
            grouped,
        )

    if any(term in query for term in ("loss-making", "loss making", "losing", "losses")):
        name_column = next(
            (column for column in ("Product Name", "Product ID") if column in df),
            None,
        )
        if not name_column or "Profit" not in df:
            return "Product loss analysis requires Product Name or Product ID and Profit.", None
        losses = (
            df.groupby(name_column, as_index=False)
            .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
            .query("Profit < 0")
            .sort_values("Profit")
            .head(10)
        )
        if losses.empty:
            return "No products have negative aggregate profit in the filtered data.", losses
        return "Ten products with the largest aggregate losses in the filtered data.", losses

    if any(term in query for term in ("month", "monthly", "trend", "growth")):
        if "Order Date" not in df or "Sales" not in df:
            return "Monthly sales analysis requires Order Date and Sales.", None
        metric = "Profit" if "profit" in query else "Sales"
        if metric not in df:
            return f"Monthly {metric.lower()} analysis is not available.", None
        monthly = (
            df.assign(Month=df["Order Date"].dt.to_period("M").astype(str))
            .groupby("Month", as_index=False)[metric]
            .sum()
            .sort_values("Month")
        )
        monthly["Growth"] = monthly[metric].pct_change()
        if len(monthly) < 2:
            return "At least two observed months are needed to calculate monthly growth.", monthly
        latest = monthly.iloc[-1]
        previous = monthly.iloc[-2]
        growth = latest["Growth"]
        return (
            f"{metric} in {latest['Month']} was {latest[metric]:,.2f}, "
            f"{growth:+.1%} versus {previous['Month']} ({previous[metric]:,.2f}).",
            monthly,
        )

    customer_column = next(
        (column for column in ("Customer ID", "Customer Name") if column in df),
        None,
    )
    if customer_column and "customer" in query and any(
        term in query
        for term in ("how many", "unique", "count", "total customer")
    ):
        return (
            f"Distinct filtered customers: {df[customer_column].nunique():,}.",
            None,
        )
    if customer_column and "customer" in query and any(
        term in query for term in ("average spend", "average spending", "spends on average")
    ):
        spend = df.groupby(customer_column)["Sales"].sum()
        return (
            f"Average filtered sales per customer: {spend.mean():,.2f} "
            f"across {len(spend):,} customers.",
            spend.rename("Sales").reset_index(),
        )
    if customer_column and "customer" in query and any(
        term in query for term in ("frequency", "purchase frequency", "repeat", "frequent")
    ) and "Order ID" in df:
        frequency = (
            df.groupby(customer_column)["Order ID"]
            .nunique()
            .rename("Orders")
            .reset_index()
        )
        return (
            f"Customers placed {frequency['Orders'].mean():.2f} distinct orders on average.",
            frequency,
        )

    dimension = None
    for candidate, terms in (
        ("Region", ("region",)),
        ("Country", ("country",)),
        ("Market", ("market",)),
        ("Category", ("category",)),
        ("Sub-Category", ("sub-category", "subcategory", "sub category")),
        ("Segment", ("segment",)),
        ("Ship Mode", ("shipping mode", "ship mode")),
        ("Product Name", ("product",)),
    ):
        if any(term in query for term in terms):
            if candidate not in df:
                return f"{candidate} is not available in the active dataset.", None
            dimension = candidate
            break
    if dimension:
        metric = "Profit" if any(term in query for term in ("profit", "profitable")) else "Sales"
        if metric not in df:
            return f"{metric} is not available in the active dataset.", None
        summary = (
            df.groupby(dimension, dropna=False, as_index=False)
            .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
            .sort_values(metric, ascending=False)
        )
        if any(term in query for term in ("bottom", "lowest", "least")):
            result = summary.tail(10).sort_values(metric)
            return f"Lowest {metric.lower()} groups by {dimension}.", result
        result = summary.head(10)
        if result.empty:
            return f"No {dimension} results are available in the filtered data.", result
        leader = result.iloc[0]
        return (
            f"Highest {metric.lower()} {dimension.lower()}: {leader[dimension]} "
            f"({leader[metric]:,.2f}).",
            result,
        )

    if any(term in query for term in ("order value", "average order", "aov")):
        if not {"Order ID", "Sales"}.issubset(df.columns):
            return "Average order value requires Order ID and Sales.", None
        order_sales = df.groupby("Order ID")["Sales"].sum()
        return f"Average order value: {order_sales.mean():,.2f} across {len(order_sales):,} orders.", None

    if any(term in query for term in ("how many orders", "total orders", "order count")):
        if "Order ID" not in df:
            return "Order count requires Order ID.", None
        return f"Distinct filtered orders: {df['Order ID'].nunique():,}.", None

    if any(term in query for term in ("customer", "customers")):
        customer_column = next(
            (column for column in ("Customer ID", "Customer Name") if column in df),
            None,
        )
        if not customer_column:
            return "Customer analysis requires a customer identifier or name.", None
        metric = "Profit" if "profit" in query else "Sales"
        customers = (
            df.groupby(customer_column, as_index=False)
            .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
            .sort_values(metric, ascending=False)
            .head(10)
        )
        return f"Top customers by {metric.lower()} in the filtered data.", customers

    if "profit" in query:
        profit = float(df["Profit"].sum()) if "Profit" in df else None
        if profit is None:
            return "Profit is not available in the active dataset.", None
        return f"Total filtered profit: {profit:,.2f}.", None
    if any(term in query for term in ("sales", "revenue", "total")):
        if "Sales" not in df:
            return "Sales are not available in the active dataset.", None
        return f"Total filtered sales: {df['Sales'].sum():,.2f}.", None

    return (
        "I can answer questions about total sales, profit, orders, average order value, "
        "monthly growth, loss-making products, discounts, or performance by region, "
        "country, market, category, segment, product, customer, and shipping mode.",
        None,
    )
