"""Hospital Operations Dashboard — unified entry point.

Run: streamlit run app/main.py

Pages: Overview (here) + Predict + Recover + Pharmacy + Narcotics (reused as functions).
Scoring lives in app/scoring.py; cached loading in app/shared.py.
No ML logic in this file.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.narcotics import render_narcotics  # noqa: E402
from app.pharmacy import render_pharmacy  # noqa: E402
from app.predict import render_predict  # noqa: E402
from app.recover import init_state, metrics, render_recover  # noqa: E402
from app.scoring import DEFAULT_THRESHOLD  # noqa: E402
from app.shared import get_model, get_scored  # noqa: E402


def render_overview():
    st.title("Hospital Operations Dashboard")
    st.subheader("Predict appointment no-show risk and simulate capacity recovery.")
    st.caption("DEMO / SIMULATION — hackathon demonstration, not a live hospital system.")

    scored = get_scored(get_model())
    proba = scored["predicted_no_show_probability"]
    flagged = (proba >= DEFAULT_THRESHOLD).sum()
    rec = st.session_state.get("rec")
    recovered = metrics(rec)["recovered"] if rec else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total appointments scored", f"{len(scored):,}")
    c2.metric("High-risk appointments", f"{int(flagged):,}")
    c3.metric("High-risk %", f"{flagged / len(scored):.1%}")
    c4.metric("Slots recovered", f"{recovered}")

    st.subheader("Today's workflow")
    st.write("**PREDICT** — Identify appointments with elevated predicted no-show risk.")
    st.write("↓")
    st.write("**RECOVER** — Simulate reassignment of capacity if a slot becomes available.")
    st.caption("Prediction estimates risk; it does not confirm a cancellation.")

    b1, b2 = st.columns(2)
    # Internal navigation: stay inside main.py so Recover session state survives.
    if b1.button("Go to Predict 🎯"):
        st.session_state.nav_page = "🎯 Predict"
        st.rerun()
    if b2.button("Go to Recover 🔄"):
        st.session_state.nav_page = "🔄 Recover"
        st.rerun()


st.set_page_config(page_title="Hospital Operations Dashboard", layout="wide")
st.sidebar.title("🏥 Hospital Operations")
st.sidebar.caption("DEMO / SIMULATION")
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "🏠 Overview"
page = st.sidebar.radio(
    "Navigation", ["🏠 Overview", "🎯 Predict", "🔄 Recover", "💊 Pharmacy", "📋 Narcotics Report"],
    label_visibility="collapsed", key="nav_page",
)
if page == "🏠 Overview":
    render_overview()
elif page == "🎯 Predict":
    render_predict()
elif page == "🔄 Recover":
    render_recover()
elif page == "💊 Pharmacy":
    render_pharmacy()
else:
    render_narcotics()
