"""Act 1 — Predict screen (demo).

Single source of truth for scoring: app/scoring.py (via app/shared.py).
This file contains NO model training and NO preprocessing of its own.
Run standalone: streamlit run app/predict.py
Or unified:     streamlit run app/main.py
"""

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scoring import DEFAULT_THRESHOLD  # noqa: E402
from app.shared import get_model, get_scored  # noqa: E402
from app.theme import inject_brutalist_css, kpi, section_label  # noqa: E402


def render_predict():
    inject_brutalist_css()
    st.title("PREDICT NO-SHOW")
    st.caption("RISK ESTIMATES. NOT CONFIRMED NO-SHOWS. DEMO DATA.")

    model = get_model()
    scored = get_scored(model)

    # --- Threshold: operational rule only; probabilities already fixed ---
    threshold = st.slider(
        "HIGH-RISK THRESHOLD",
        min_value=0.05, max_value=0.75, step=0.01, value=DEFAULT_THRESHOLD,
    )
    st.caption("AT OR ABOVE THRESHOLD = FLAGGED. PROBABILITY FIXED. THRESHOLD ADJUSTABLE.")

    proba = scored["predicted_no_show_probability"]
    flag = (proba >= threshold).astype(int)
    view = scored.assign(risk_flag=flag)

    # --- Summary metrics (from scoring output, never hard-coded) ---
    section_label(1, "risk overview")
    total = len(view)
    high = int(flag.sum())
    avg = float(proba.mean())
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    with c1:
        kpi(f"{total:,}", "scored")
    with c2:
        kpi(f"{high:,}", "high-risk", alert=high > 0)
    with c3:
        kpi(f"{high / total:.1%}", "high-risk %")
    with c4:
        kpi(f"{avg:.1%}", "avg risk")

    # --- Risk distribution (buckets, no extra ML metrics) ---
    section_label(2, "risk distribution")
    buckets = pd.cut(proba, bins=[0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.01],
                     labels=["0-10%", "10-20%", "20-30%", "30-50%", "50-75%", "75%+"])
    dist = buckets.value_counts().sort_index().reset_index()
    dist.columns = ["bucket", "count"]
    chart = alt.Chart(dist).mark_bar(color="#000000").encode(
        x=alt.X("bucket", axis=alt.Axis(labelFont="Space Mono", titleFont="Space Mono")),
        y=alt.Y("count", axis=alt.Axis(labelFont="Space Mono", titleFont="Space Mono")),
    ).configure_view(stroke="#000000", strokeWidth=3).configure_axis(
        grid=False, domainColor="#000000", tickColor="#000000",
    ).properties(background="transparent")
    st.altair_chart(chart, use_container_width=True)

    # --- Filters (applied AFTER scoring) ---
    section_label(3, "filters")
    f1, f2, f3 = st.columns([2, 2, 1])
    high_only = f1.checkbox("HIGH-RISK ONLY", value=False)
    nbh_options = ["All"] + sorted(view["Neighbourhood"].dropna().unique().tolist())
    nbh = f2.selectbox("NEIGHBOURHOOD", nbh_options)
    age_min, age_max = int(view["Age"].min()), int(view["Age"].max())
    age_lo, age_hi = f3.slider("AGE RANGE", age_min, age_max, (age_min, age_max))

    table = view
    if high_only:
        table = table[table["risk_flag"] == 1]
    if nbh != "All":
        table = table[table["Neighbourhood"] == nbh]
    table = table[(table["Age"] >= age_lo) & (table["Age"] <= age_hi)]

    # --- Ranked table (already sorted descending by probability) ---
    section_label(4, "ranked appointments")
    # Styler has a cell limit, so show the top slice; full data via export/filters.
    MAX_TABLE_ROWS = 1000
    table = table.head(MAX_TABLE_ROWS)
    if len(table) == 0:
        st.write("NO RECORDS MATCH.")
    else:
        st.caption(f"SHOWING TOP {len(table):,} ROWS BY RISK.")
    show = table.assign(risk_pct=table["predicted_no_show_probability"].map(lambda p: f"{p:.1%}"))[
        ["AppointmentID", "PatientId", "Neighbourhood", "Age", "SMS_received",
         "lead_time_days", "risk_pct", "risk_flag"]
    ].rename(columns={"risk_pct": "RISK", "risk_flag": "FLAG",
                      "AppointmentID": "APPT", "PatientId": "PATIENT",
                      "Neighbourhood": "AREA", "Age": "AGE",
                      "SMS_received": "SMS", "lead_time_days": "LEAD"})
    def _row_style(r):
        rows = []
        for i, (_, cell) in enumerate(r.items()):
            if r["FLAG"] == 1:
                rows.append("background-color: #FF3B00; color: #fff; font-weight: bold")
            elif i % 2:
                rows.append("background-color: #E8E6DD")
            else:
                rows.append("")
        return rows
    styler = (
        show.style
        .set_table_styles([
            {"selector": "th", "props": [("background", "#000"), ("color", "#fff"),
                                        ("font-family", "'Space Mono',monospace"),
                                        ("text-transform", "uppercase"), ("border", "2px solid #000")]},
            {"selector": "td", "props": [("border", "1px solid #000"),
                                        ("font-family", "'Space Mono',monospace")]},
        ])
        .apply(_row_style, axis=1)
    )
    st.dataframe(styler, use_container_width=True)

    # --- Export flagged rows at the current threshold ---
    st.download_button(
        "EXPORT FLAGGED",
        data=view[view["risk_flag"] == 1][
            ["AppointmentID", "PatientId", "Neighbourhood", "Age", "SMS_received",
             "lead_time_days", "predicted_no_show_probability", "risk_flag"]
        ].to_csv(index=False),
        file_name=f"flagged_appointments_t{threshold:.2f}.csv",
        mime="text/csv",
    )

    with st.expander("HOW DOES THIS WORK?"):
        st.write(
            "1. MODEL OUTPUTS A NO-SHOW PROBABILITY BETWEEN 0 AND 1.\n"
            "2. THRESHOLD DECIDES WHAT GETS FLAGGED.\n"
            "3. LOWER THRESHOLD CATCHES MORE, FLAGS MORE ATTENDERS.\n"
            "4. HIGHER THRESHOLD FLAGS LESS, MISSES MORE.\n"
            "TRIAGE AID ONLY. NOT A CLINICAL SYSTEM."
        )


if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="No-Show Ops", page_icon=None)
    render_predict()
