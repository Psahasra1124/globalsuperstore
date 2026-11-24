import plotly.express as px
import streamlit as st


PALETTE = ["#60A5FA", "#22C5DC", "#34D399", "#FBBF24", "#A78BFA", "#F472B6"]


def _format_currency(value):
    amount = float(value)
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:,.2f}M"
    if abs(amount) >= 10_000:
        return f"${amount / 1_000:,.1f}K"
    if abs(amount) >= 1_000:
        return f"${amount / 1_000:,.2f}K"
    return f"${amount:,.2f}"


def chart(fig, height=390):
    fig.update_layout(
        template="plotly_dark",
        colorway=PALETTE,
        height=height,
        margin=dict(l=18, r=18, t=54, b=24),
        paper_bgcolor="#111C2C",
        plot_bgcolor="#111C2C",
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", size=12, color="#DCE6F2"),
        title_font=dict(size=17, color="#F1F6FC"),
        hoverlabel=dict(bgcolor="#0B1220", font_color="#F1F6FC", bordercolor="#344A63"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#B8C7D9"),
        ),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#26364B", zeroline=False, linecolor="#34465D")
    fig.update_yaxes(showgrid=True, gridcolor="#26364B", zeroline=False, linecolor="#34465D")
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "responsive": True})


def kpi_card(label, value, fmt="number", delta=None, icon=None, help_text=None):
    if fmt == "currency":
        exact_value = float(value)
        value = _format_currency(exact_value)
        if help_text:
            help_text = f"{help_text} Exact value: ${exact_value:,.2f}."
    elif fmt == "percent":
        value = f"{value:.1%}"
    elif fmt == "integer":
        value = f"{value:,.0f}"
    else:
        value = f"{value:,.0f}"
    metric_label = f"{icon}  {label}" if icon else label
    st.metric(metric_label, value, delta=delta, help=help_text)


def bar(df, x, y, title, horizontal=False, color=None):
    fig = px.bar(
        df,
        x=x,
        y=y,
        title=title,
        color=color,
        color_discrete_sequence=PALETTE,
        orientation="h" if horizontal else "v",
        labels={x: x.replace("_", " "), y: y.replace("_", " ")},
    )
    chart(fig)


def line(df, x, y, title, color=None):
    chart(
        px.line(
            df,
            x=x,
            y=y,
            title=title,
            color=color,
            markers=True,
            color_discrete_sequence=PALETTE,
        )
    )


def scatter(df, x, y, title, color=None):
    chart(
        px.scatter(
            df,
            x=x,
            y=y,
            title=title,
            color=color,
            color_discrete_sequence=PALETTE,
            opacity=0.75,
        )
    )
