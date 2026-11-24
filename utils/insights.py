from utils.analytics import customer_performance, product_performance
from utils.eda import grouped


def generate_insights(df):
    insights = []

    def add(finding, evidence, recommendation):
        insights.append(
            {
                "Finding": finding,
                "Evidence": evidence,
                "Recommendation": recommendation,
            }
        )

    for column, label in (
        ("Region", "region"),
        ("Market", "market"),
        ("Category", "category"),
        ("Sub-Category", "sub-category"),
        ("Ship Mode", "shipping mode"),
    ):
        if column not in df.columns:
            continue
        summary = grouped(df, column)
        if not summary.empty:
            top = summary.sort_values("Sales", ascending=False).iloc[0]
            add(
                f"Highest sales {label}: {top[column]}",
                f"Sales ${top.Sales:,.2f}; profit ${top.Profit:,.2f}.",
                "Review this group's drivers before applying the same approach elsewhere.",
            )

    if "Category" in df.columns:
        categories = grouped(df, "Category")
        if not categories.empty:
            top = categories.sort_values("Profit", ascending=False).iloc[0]
            add(
                f"Most profitable category: {top['Category']}",
                f"Profit ${top.Profit:,.2f} on sales of ${top.Sales:,.2f}.",
                "Protect availability and monitor margin in this category.",
            )

    products = product_performance(df)
    if not products.empty:
        product_column = "Product Name" if "Product Name" in products else "Product ID"
        losses = products.loc[products["Profit"] < 0].nsmallest(1, "Profit")
        if not losses.empty:
            loss = losses.iloc[0]
            add(
                "Largest loss-making product",
                f"{loss[product_column]} generated ${loss.Profit:,.2f} profit.",
                "Review product costs, discounting, and pricing before increasing promotion.",
            )

        if len(products) >= 4:
            high_sales = products["Sales"] >= products["Sales"].quantile(0.75)
            low_margin = products["Profit Margin"] <= products["Profit Margin"].quantile(0.25)
            watchlist = products.loc[high_sales & low_margin].sort_values("Sales", ascending=False)
            if not watchlist.empty:
                item = watchlist.iloc[0]
                add(
                    "High sales, low margin product",
                    f"{item[product_column]} has ${item.Sales:,.2f} sales at {item['Profit Margin']:.1%} margin.",
                    "Check unit economics and discount exposure for this high-volume product.",
                )

    if {"Region", "Order Date"}.issubset(df.columns):
        regional_months = df.assign(
            _month=df["Order Date"].dt.to_period("M").dt.start_time
        ).groupby(["Region", "_month"], as_index=False)["Sales"].sum()
        declines = []
        for region, history in regional_months.groupby("Region"):
            history = history.sort_values("_month")
            if len(history) >= 2:
                previous = history.iloc[-2]["Sales"]
                latest = history.iloc[-1]["Sales"]
                if previous > 0:
                    declines.append((float((latest - previous) / previous), region, previous, latest))
        negative = [item for item in declines if item[0] < 0]
        if negative:
            growth, region, previous, latest = min(negative, key=lambda item: item[0])
            add(
                f"Recent regional decline: {region}",
                f"Sales changed {growth:.1%} between its latest two observed months "
                f"(${previous:,.2f} to ${latest:,.2f}).",
                "Check whether the change is seasonal, mix-driven, or a temporary demand shift.",
            )

    if "Discount" in df.columns:
        discount_summary = df.groupby("Discount", as_index=False).agg(
            Average_Profit=("Profit", "mean"), Sales=("Sales", "sum")
        )
        discount_summary = discount_summary.loc[discount_summary["Sales"] > 0]
        if len(discount_summary) >= 2:
            best = discount_summary.loc[discount_summary["Average_Profit"].idxmax()]
            worst = discount_summary.loc[discount_summary["Average_Profit"].idxmin()]
            add(
                "Discount-profit association",
                f"Average line profit ranged from ${worst.Average_Profit:,.2f} "
                f"at {worst.Discount:.0%} discount to ${best.Average_Profit:,.2f} "
                f"at {best.Discount:.0%}.",
                "Treat this as an observed association, not proof that discounting caused the outcome.",
            )

    customers = customer_performance(df)
    if not customers.empty:
        top = customers.iloc[0]
        customer_label = top.get("Customer Name", top.iloc[0])
        add(
            "Top customer by sales",
            f"{customer_label} contributed ${top.Sales:,.2f} sales and ${top.Profit:,.2f} profit.",
            "Consider retention outreach while checking customer-level profitability.",
        )
        if "Segment" in df.columns:
            segments = df.groupby("Segment")["Sales"].sum().sort_values(ascending=False)
            if not segments.empty:
                add(
                    f"Leading customer segment: {segments.index[0]}",
                    f"Sales ${segments.iloc[0]:,.2f} ({segments.iloc[0] / df['Sales'].sum():.1%} of filtered sales).",
                    "Compare this segment's margin and repeat behavior before shifting acquisition spend.",
                )

    monthly = df.groupby("Order Month", as_index=False)["Sales"].sum().sort_values("Order Month")
    if len(monthly) >= 2 and monthly.iloc[-2]["Sales"] > 0:
        previous = monthly.iloc[-2]
        latest = monthly.iloc[-1]
        growth = latest["Sales"] / previous["Sales"] - 1
        direction = "grew" if growth >= 0 else "declined"
        add(
            f"Latest monthly sales {direction}",
            f"{latest['Order Month']} changed {growth:+.1%} from {previous['Order Month']}.",
            "Compare the change with the same period last year to separate momentum from seasonality.",
        )

    if {"Ship Mode", "Shipping Duration"}.issubset(df.columns):
        duration = df.groupby("Ship Mode")["Shipping Duration"].mean().dropna()
        if not duration.empty:
            mode = duration.idxmin()
            add(
                "Fastest observed shipping mode",
                f"{mode} averaged {duration.min():.1f} days in the filtered data.",
                "Compare delivery speed with shipping cost and profitability before changing the service mix.",
            )

    return insights[:12]
