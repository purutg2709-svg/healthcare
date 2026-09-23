"""Act 1 — Predict screen (demo).

Single source of truth for scoring: app/scoring.py (via app/shared.py).
This file contains NO model training and NO preprocessing of its own.
Run standalone: streamlit run app/predict.py
Or unified:     streamlit run app/main.py
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scoring import DEFAULT_THRESHOLD  # noqa: E402
from app.shared import get_model, get_scored  # noqa: E402


def render_predict():
    st.title("Hospital Appointment Risk Prediction")
    st.subheader("Identify appointments with elevated no-show risk before the appointment day.")
    st.caption("Demonstration / mock system — scored on historical demo data, not live hospital data.")

    model = get_model()
    scored = get_scored(model)

    # --- Threshold: operational rule only; probabilities already fixed ---
    threshold = st.slider(
        "High-risk threshold",
        min_value=0.05, max_value=0.75, step=0.01, value=DEFAULT_THRESHOLD,
    )
    st.caption("Appointments with predicted no-show probability at or above this threshold are flagged.")
    st.caption("MODEL OUTPUT → probability (fixed). OPERATIONAL RULE → threshold (adjustable).")

    proba = scored["predicted_no_show_probability"]
    flag = (proba >= threshold).astype(int)
    view = scored.assign(risk_flag=flag)

    # --- Summary metrics (from scoring output, never hard-coded) ---
    total = len(view)
    high = int(flag.sum())
    avg = float(proba.mean())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total appointments scored", f"{total:,}")
    c2.metric("High-risk appointments", f"{high:,}")
    c3.metric("High-risk %", f"{high / total:.1%}" if total else "—")
    c4.metric("Avg predicted probability", f"{avg:.1%}")

    # --- Risk distribution (buckets, no extra ML metrics) ---
    buckets = pd.cut(proba, bins=[0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.01],
                     labels=["0–10%", "10–20%", "20–30%", "30–50%", "50–75%", "75%+"])
    dist = buckets.value_counts().sort_index()
    st.subheader("Risk distribution")
    st.bar_chart(dist)

    # --- Filters (applied AFTER scoring) ---
    f1, f2, f3 = st.columns(3)
    high_only = f1.checkbox("Show high-risk only", value=False)
    nbh_options = ["All"] + sorted(view["Neighbourhood"].dropna().unique().tolist())
    nbh = f2.selectbox("Neighbourhood", nbh_options)
    age_min, age_max = int(view["Age"].min()), int(view["Age"].max())
    age_lo, age_hi = f3.slider("Age range", age_min, age_max, (age_min, age_max))

    table = view
    if high_only:
        table = table[table["risk_flag"] == 1]
    if nbh != "All":
        table = table[table["Neighbourhood"] == nbh]
    table = table[(table["Age"] >= age_lo) & (table["Age"] <= age_hi)]

    # --- Ranked table (already sorted descending by probability) ---
    st.subheader("Ranked appointments")
    show = table.assign(risk_pct=table["predicted_no_show_probability"].map(lambda p: f"{p:.1%}"))[
        ["AppointmentID", "PatientId", "Neighbourhood", "Age", "SMS_received",
         "lead_time_days", "risk_pct", "risk_flag"]
    ].rename(columns={"risk_pct": "Predicted risk", "risk_flag": "High-risk"})
    st.dataframe(
        show.style.apply(
            lambda r: ["background-color: #ffd9d9" if r["High-risk"] == 1 else "" for _ in r],
            axis=1,
        ),
        use_container_width=True,
    )

    # --- Export flagged rows at the current threshold ---
    st.download_button(
        "Export flagged appointments",
        data=view[view["risk_flag"] == 1][
            ["AppointmentID", "PatientId", "Neighbourhood", "Age", "SMS_received",
             "lead_time_days", "predicted_no_show_probability", "risk_flag"]
        ].to_csv(index=False),
        file_name=f"flagged_appointments_t{threshold:.2f}.csv",
        mime="text/csv",
    )

    with st.expander("How does this work?"):
        st.write(
            "1. The model estimates a probability of no-show between 0 and 1 — "
            "a likelihood, not a certainty.\n"
            "2. The threshold decides which appointments get flagged.\n"
            "3. Lowering the threshold catches more potential no-shows but also flags "
            "more appointments that would actually attend.\n"
            "4. Raising the threshold produces fewer flags but may miss some no-shows.\n"
            "This is a triage aid, not a clinical decision system, and flagging does "
            "not itself change attendance."
        )


if __name__ == "__main__":
    st.set_page_config(page_title="Hospital Appointment Risk Prediction", layout="wide")
    render_predict()
