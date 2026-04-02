"""
Interactive Expenses Dashboard
--------------------------------
Run with:  streamlit run dashboard/app.py

Features:
  - Month selector sidebar
  - KPI cards: total spend, # transactions, top category, daily average
  - Monthly trend bar chart (all months)
  - Category breakdown pie chart
  - Category comparison bar chart
  - Top merchants table
  - Full transaction table with search & filters
"""

import sys
import os

# Make sure project root is on the path so imports work when running from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agents import data_manager as dm

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Monthly Expenses Analyzer",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Load category colours
# ---------------------------------------------------------------------------
CATEGORIES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "categories.json"
)

@st.cache_data
def load_category_config():
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {cat["name"]: cat["color"] for cat in data.get("categories", [])}

CATEGORY_COLORS = load_category_config()


# ---------------------------------------------------------------------------
# Data loading helpers (cached so the DB isn't hit on every interaction)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30)  # refresh every 30 seconds
def load_all_transactions():
    rows = dm.get_all_transactions()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=30)
def load_monthly_summary():
    rows = dm.get_monthly_summary()
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=30)
def load_available_months():
    return dm.get_available_months()


# ---------------------------------------------------------------------------
# Sidebar — month selector & filters
# ---------------------------------------------------------------------------

def render_sidebar(df: pd.DataFrame):
    st.sidebar.image("https://img.icons8.com/color/96/000000/bank-card-front-side.png", width=60)
    st.sidebar.title("💳 Expense Analyzer")
    st.sidebar.markdown("---")

    available = load_available_months()
    if not available:
        st.sidebar.info("No data yet. Run `python main.py --pdf <file>` to get started.")
        return None, None, []

    month_options = [f"{m['month']} {m['year']}" for m in available]
    selected_label = st.sidebar.selectbox("📅 Select Month", ["All Time"] + month_options)

    st.sidebar.markdown("---")

    # Category filter
    all_categories = sorted(df["category"].dropna().unique().tolist()) if not df.empty else []
    selected_categories = st.sidebar.multiselect(
        "🏷️ Filter Categories",
        options=all_categories,
        default=all_categories,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ Quick Help")
    st.sidebar.markdown(
        "**Add a statement:**\n```\npython main.py --pdf data/statement.pdf\n```"
    )

    return selected_label, all_categories, selected_categories


# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------

def render_kpi_cards(df: pd.DataFrame):
    debits = df[df["transaction_type"] == "debit"] if not df.empty else df

    total_spend = debits["amount"].sum() if not debits.empty else 0
    num_tx = len(debits)
    top_category = (
        debits.groupby("category")["amount"].sum().idxmax()
        if not debits.empty else "—"
    )
    # Daily average (based on distinct dates)
    num_days = debits["date"].dt.date.nunique() if not debits.empty else 1
    daily_avg = total_spend / num_days if num_days > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Total Spend", f"AED {total_spend:,.0f}")
    with col2:
        st.metric("🧾 Transactions", f"{num_tx:,}")
    with col3:
        st.metric("🏆 Top Category", top_category)
    with col4:
        st.metric("📆 Daily Average", f"AED {daily_avg:,.0f}")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def render_monthly_trend(monthly_df: pd.DataFrame):
    if monthly_df.empty:
        st.info("No monthly data available.")
        return

    # Build a display label like "March 2024"
    monthly_df = monthly_df.copy()
    monthly_df["label"] = monthly_df["month"] + " " + monthly_df["year"].astype(str)

    fig = px.bar(
        monthly_df,
        x="label",
        y="total_spend",
        text="total_spend",
        color_discrete_sequence=["#4ECDC4"],
        title="Monthly Spend (AED)",
        labels={"label": "Month", "total_spend": "Total Spend (AED)"},
    )
    fig.update_traces(
        texttemplate="AED %{text:,.0f}",
        textposition="outside",
    )
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis={"tickangle": -30},
        margin={"t": 50, "b": 80},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_category_pie(df: pd.DataFrame):
    debits = df[df["transaction_type"] == "debit"] if not df.empty else df
    if debits.empty:
        st.info("No data to display.")
        return

    cat_totals = (
        debits.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )
    colors = [CATEGORY_COLORS.get(c, "#D5DBDB") for c in cat_totals["category"]]

    fig = px.pie(
        cat_totals,
        names="category",
        values="amount",
        title="Spend by Category",
        color="category",
        color_discrete_map=CATEGORY_COLORS,
        hole=0.4,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(
        showlegend=True,
        legend={"orientation": "v", "x": 1.05},
        margin={"t": 50, "b": 20},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_category_bar(df: pd.DataFrame):
    debits = df[df["transaction_type"] == "debit"] if not df.empty else df
    if debits.empty:
        return

    cat_totals = (
        debits.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=True)
    )
    colors = [CATEGORY_COLORS.get(c, "#D5DBDB") for c in cat_totals["category"]]

    fig = go.Figure(
        go.Bar(
            x=cat_totals["amount"],
            y=cat_totals["category"],
            orientation="h",
            marker_color=colors,
            text=cat_totals["amount"].apply(lambda x: f"AED {x:,.0f}"),
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Category Breakdown",
        xaxis_title="Amount (AED)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin={"t": 50, "b": 20, "l": 150},
        height=max(300, len(cat_totals) * 40),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_top_merchants(df: pd.DataFrame):
    debits = df[df["transaction_type"] == "debit"] if not df.empty else df
    if debits.empty:
        return

    top = (
        debits.groupby(["description", "category"])
        .agg(total=("amount", "sum"), visits=("amount", "count"))
        .reset_index()
        .sort_values("total", ascending=False)
        .head(10)
    )
    top["total"] = top["total"].apply(lambda x: f"AED {x:,.2f}")

    st.dataframe(
        top.rename(
            columns={
                "description": "Merchant",
                "category": "Category",
                "total": "Total Spent",
                "visits": "Transactions",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def render_transaction_table(df: pd.DataFrame):
    if df.empty:
        st.info("No transactions found.")
        return

    search = st.text_input("🔍 Search transactions", placeholder="e.g. Carrefour, Uber...")

    display_df = df.copy()
    if search:
        display_df = display_df[
            display_df["description"].str.contains(search, case=False, na=False)
        ]

    display_df = display_df.sort_values("date", ascending=False)
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    display_df["amount"] = display_df["amount"].apply(lambda x: f"AED {x:,.2f}")

    cols = ["date", "description", "category", "subcategory", "amount", "transaction_type"]
    cols = [c for c in cols if c in display_df.columns]

    st.dataframe(
        display_df[cols].rename(
            columns={
                "date": "Date",
                "description": "Description",
                "category": "Category",
                "subcategory": "Subcategory",
                "amount": "Amount",
                "transaction_type": "Type",
            }
        ),
        use_container_width=True,
        hide_index=True,
        height=400,
    )
    st.caption(f"Showing {len(display_df):,} transactions")


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    df = load_all_transactions()
    monthly_df = load_monthly_summary()

    selected_label, all_categories, selected_categories = render_sidebar(df)

    # Title
    st.title("💳 Monthly Expenses Dashboard")
    st.markdown("---")

    if df.empty:
        st.warning(
            "No data yet! Process your first statement:\n"
            "```\npython main.py --pdf data/your_statement.pdf\n```"
        )
        return

    # Apply month filter
    if selected_label and selected_label != "All Time":
        parts = selected_label.split()
        sel_month, sel_year = parts[0], int(parts[1])
        filtered_df = df[(df["month"] == sel_month) & (df["year"] == sel_year)]
        period_label = selected_label
    else:
        filtered_df = df
        period_label = "All Time"

    # Apply category filter
    if selected_categories and len(selected_categories) < len(all_categories):
        filtered_df = filtered_df[filtered_df["category"].isin(selected_categories)]

    st.subheader(f"📊 Overview — {period_label}")

    # KPI cards
    render_kpi_cards(filtered_df)

    st.markdown("---")

    # Charts row 1
    col1, col2 = st.columns([3, 2])
    with col1:
        render_monthly_trend(monthly_df)
    with col2:
        render_category_pie(filtered_df)

    st.markdown("---")

    # Charts row 2
    col3, col4 = st.columns([2, 3])
    with col3:
        st.subheader("🏆 Top 10 Merchants")
        render_top_merchants(filtered_df)
    with col4:
        render_category_bar(filtered_df)

    st.markdown("---")

    # Transaction table
    st.subheader("📋 All Transactions")
    render_transaction_table(filtered_df)


if __name__ == "__main__":
    main()
