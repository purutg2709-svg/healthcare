"""Hospital Operations Dashboard — unified entry point.

Run: streamlit run app/main.py

Pages: Overview (here) + Predict + Recover (reused as functions).
Scoring lives in app/scoring.py; cached loading in app/shared.py.
Styling lives in app/theme.py. No ML logic in this file.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.predict import render_predict  # noqa: E402
from app.recover import init_state, metrics, render_recover  # noqa: E402
from app.scoring import DEFAULT_THRESHOLD  # noqa: E402
from app.shared import get_model, get_scored  # noqa: E402
from app.theme import inject_brutalist_css, kpi, section_label  # noqa: E402


def render_overview():
    inject_brutalist_css()
    st.title("NO-SHOW OPS")
    st.caption("PREDICT RISK. RECOVER CAPACITY. DEMO / SIMULATION.")

    scored = get_scored(get_model())
    proba = scored["predicted_no_show_probability"]
    flagged = int((proba >= DEFAULT_THRESHOLD).sum())
    rec = st.session_state.get("rec")
    recovered = metrics(rec)["recovered"] if rec else 0

    section_label(1, "risk overview")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi(f"{len(scored):,}", "scored")
    with c2:
        kpi(f"{flagged:,}", "high-risk", alert=True)
    with c3:
        kpi(f"{flagged / len(scored):.1%}", "high-risk %")
    with c4:
        kpi(f"{recovered}", "recovered")

    section_label(2, "operations flow")
    st.write("PREDICT — FLAG HIGH-RISK APPOINTMENTS.")
    st.write("RECOVER — REASSIGN OPEN CAPACITY.")
    st.caption("RISK ESTIMATE ONLY. NOT A CONFIRMED NO-SHOW.")

    b1, b2 = st.columns(2)
    # Internal navigation: stash the target and rerun; it is applied to
    # nav_page BEFORE the radio widget instantiates (assigning nav_page
    # after instantiation raises StreamlitWidgetAlreadyInstantiatedError).
    if b1.button("PREDICT NO-SHOW"):
        st.session_state._goto = "PREDICT"
        st.rerun()
    if b2.button("RECOVERY ACTIONS"):
        st.session_state._goto = "RECOVER"
        st.rerun()


st.set_page_config(layout="wide", page_title="No-Show Ops", page_icon=None)
inject_brutalist_css()
st.sidebar.title("NO-SHOW OPS")
st.sidebar.caption("DEMO / SIMULATION")
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "OVERVIEW"
if "_goto" in st.session_state:
    st.session_state.nav_page = st.session_state.pop("_goto")
page = st.sidebar.radio(
    "Navigation", ["OVERVIEW", "PREDICT", "RECOVER"],
    label_visibility="collapsed", key="nav_page",
)
if page == "OVERVIEW":
    render_overview()
elif page == "PREDICT":
    render_predict()
else:
    render_recover()
