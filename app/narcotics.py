"""B2 — Mock Narcotics / Controlled-Substance Reporting (demo / simulation).

Reads the committed synthetic dataset (data/...csv). No ML, no external
systems, no real regulatory content. All flags are deterministic demo rules.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_controlled_substance_transactions.csv"
TABLE_COLS = ["transaction_id", "prescription_id", "patient_ref", "medication_name",
              "quantity", "transaction_date", "pharmacy_id", "prescriber_id",
              "transaction_status", "reporting_status", "anomaly_flag", "anomaly_reason"]


@st.cache_data
def load_transactions():
    df = pd.read_csv(DATA_PATH, parse_dates=["transaction_date", "report_date"])
    return df


def render_narcotics():
    st.title("Mock Narcotics / Controlled-Substance Reporting")
    st.caption("DEMO / SIMULATION")
    st.warning("This dashboard uses entirely synthetic controlled-substance transactions. "
               "It is not a regulatory submission system.")
    st.caption("B1 demonstrates individual dispensing. B2 demonstrates historical reporting and analytics.")

    df = load_transactions()

    # --- Filters (never mutate the source file) ---
    f1, f2, f3 = st.columns(3)
    dmin, dmax = df["transaction_date"].min().date(), df["transaction_date"].max().date()
    start, end = f1.slider("Date range", dmin, dmax, (dmin, dmax))
    pharm = f2.selectbox("Pharmacy", ["All"] + sorted(df["pharmacy_id"].unique()))
    med = f3.selectbox("Medication", ["All"] + sorted(df["medication_name"].unique()))
    f4, f5, f6, f7 = st.columns(4)
    cat = f4.selectbox("Category", ["All"] + sorted(df["controlled_category"].unique()))
    tstat = f5.selectbox("Txn status", ["All"] + sorted(df["transaction_status"].unique()))
    rstat = f6.selectbox("Reporting status", ["All"] + sorted(df["reporting_status"].unique()))
    aflag = f7.selectbox("Anomaly flag", ["All", "Flagged only", "Unflagged only"])

    view = df[(df["transaction_date"].dt.date >= start) & (df["transaction_date"].dt.date <= end)]
    if pharm != "All":
        view = view[view["pharmacy_id"] == pharm]
    if med != "All":
        view = view[view["medication_name"] == med]
    if cat != "All":
        view = view[view["controlled_category"] == cat]
    if tstat != "All":
        view = view[view["transaction_status"] == tstat]
    if rstat != "All":
        view = view[view["reporting_status"] == rstat]
    if aflag == "Flagged only":
        view = view[view["anomaly_flag"] == 1]
    elif aflag == "Unflagged only":
        view = view[view["anomaly_flag"] == 0]

    disp = view[view["transaction_status"] == "DISPENSED"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total transactions", f"{len(view):,}")
    c2.metric("Total dispensed quantity", f"{int(disp['quantity'].sum()):,}")
    c3.metric("Pending reports", f"{int((view['reporting_status'] == 'PENDING').sum()):,}")
    c4.metric("Flagged transactions", f"{int(view['anomaly_flag'].sum()):,}")

    st.subheader("Trends")
    monthly = view.set_index("transaction_date").resample("ME").size()
    monthly.index = monthly.index.strftime("%Y-%m")
    st.write("Transactions over time")
    st.line_chart(monthly)
    mqty = disp.set_index("transaction_date").resample("ME")["quantity"].sum()
    mqty.index = mqty.index.strftime("%Y-%m")
    st.write("Dispensed quantity over time (DISPENSED only)")
    st.line_chart(mqty)

    st.subheader("Breakdowns")
    b1, b2 = st.columns(2)
    with b1:
        st.write("Transactions by medication")
        st.bar_chart(view["medication_name"].value_counts())
        st.write("Reporting status")
        st.bar_chart(view["reporting_status"].value_counts())
    with b2:
        st.write("Transactions by pharmacy")
        st.bar_chart(view["pharmacy_id"].value_counts())
        st.write("Flagged by reason")
        st.bar_chart(view[view["anomaly_flag"] == 1]["anomaly_reason"].value_counts())

    st.subheader("Transactions (synthetic/demo data)")
    st.dataframe(view[TABLE_COLS], use_container_width=True)

    st.subheader("Transactions Requiring Review")
    st.caption("These flags are deterministic demonstration rules and are not evidence of "
               "illegal activity, diversion, misuse, or regulatory violations.")
    st.dataframe(view[view["anomaly_flag"] == 1][TABLE_COLS], use_container_width=True)

    st.subheader("Mock report")
    st.text(
        "MOCK CONTROLLED-SUBSTANCE REPORT — DEMO / SIMULATION\n"
        f"Reporting period: {start} to {end}\n"
        f"Total transactions: {len(view)}\n"
        f"Total dispensed quantity: {int(disp['quantity'].sum())}\n"
        f"Pending reports: {int((view['reporting_status'] == 'PENDING').sum())}\n"
        f"Flagged transactions: {int(view['anomaly_flag'].sum())}\n\n"
        "Medication summary:\n" + disp.groupby("medication_name")["quantity"].sum().to_string() + "\n\n"
        "Pharmacy summary:\n" + view["pharmacy_id"].value_counts().to_string()
    )
    st.download_button(
        "Download mock report (CSV)",
        data=view.to_csv(index=False),
        file_name="mock_controlled_substance_report.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    st.set_page_config(page_title="Mock Narcotics Reporting", layout="wide")
    render_narcotics()
