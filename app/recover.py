"""Act 2 — Slot Recovery (demo / simulation).

Consumes probabilities from app/scoring.py. Contains NO model training,
NO preprocessing of its own, and NO real scheduling integration.
Run: streamlit run app/recover.py

Story: elevated predicted no-show risk -> potential capacity loss ->
simulate slot release -> offer recovered slot -> accept / decline.
The model predicts risk; it does NOT know a patient will no-show.
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scoring import DEFAULT_THRESHOLD  # noqa: E402
from app.shared import get_dates, get_model, get_scored  # noqa: E402

# Deterministic synthetic waiting list (NOT real patients). Fixed order,
# never regenerated randomly.
SYNTHETIC_QUEUE = [
    {"wait_id": "WAIT-001", "age": 34, "neighbourhood": "ITARARÉ", "service": "General practice", "wait_days": 9},
    {"wait_id": "WAIT-002", "age": 58, "neighbourhood": "CENTRO", "service": "Cardiology follow-up", "wait_days": 7},
    {"wait_id": "WAIT-003", "age": 42, "neighbourhood": "CARATOÍRA", "service": "General practice", "wait_days": 6},
    {"wait_id": "WAIT-004", "age": 23, "neighbourhood": "ANDORINHAS", "service": "Dermatology", "wait_days": 6},
    {"wait_id": "WAIT-005", "age": 61, "neighbourhood": "SANTA MARTHA", "service": "General practice", "wait_days": 5},
    {"wait_id": "WAIT-006", "age": 29, "neighbourhood": "JARDIM CAMBURI", "service": "Dental", "wait_days": 4},
    {"wait_id": "WAIT-007", "age": 47, "neighbourhood": "MARIA ORTIZ", "service": "General practice", "wait_days": 4},
    {"wait_id": "WAIT-008", "age": 52, "neighbourhood": "TABUAZEIRO", "service": "Ophthalmology", "wait_days": 3},
    {"wait_id": "WAIT-009", "age": 19, "neighbourhood": "RESISTÊNCIA", "service": "General practice", "wait_days": 2},
    {"wait_id": "WAIT-010", "age": 70, "neighbourhood": "BONFIM", "service": "General practice", "wait_days": 1},
]

STATUSES = ("AVAILABLE", "OFFERED", "OPEN", "RECOVERED")


# ---------------------------------------------------------------- pure logic
def init_state():
    """Fresh session state. Plain data only — no Streamlit dependency."""
    return {
        "slots": {},  # appt_id -> {info, risk, status, offered_to, offers: [(wait_id, outcome)]}
        "removed_waits": set(),
        "offer": None,  # {"appt_id":..., "wait_id":...}
        "audit": [],
    }


def _log(state, appt_id, risk, action, patient="", outcome=""):
    state["audit"].append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "appointment": appt_id, "risk": risk, "action": action,
        "patient": patient, "outcome": outcome,
    })


def release_slot(state, appt_row, threshold=DEFAULT_THRESHOLD):
    """Release a flagged appointment's slot for simulation. Idempotent guard."""
    appt_id = appt_row["AppointmentID"]
    risk = float(appt_row["predicted_no_show_probability"])
    if risk < threshold:
        return False, "Only appointments flagged at the current threshold are eligible."
    if appt_id in state["slots"]:
        return False, "Slot already released in this session."
    state["slots"][appt_id] = {
        "info": dict(appt_row), "risk": risk, "status": "AVAILABLE",
        "offered_to": None, "offers": [],
    }
    _log(state, appt_id, risk, "Slot released", "", "Slot released for simulation.")
    return True, "Slot released for simulation."


def next_waiting_patient(state, slot=None):
    """First synthetic patient still in the queue (deterministic order).

    When a slot is given, patients who already declined that slot are
    skipped, so a decline advances to the *next* synthetic patient.
    """
    declined = set()
    if slot is not None:
        declined = {w for w, o in slot["offers"] if o == "declined"}
    for w in SYNTHETIC_QUEUE:
        if w["wait_id"] not in state["removed_waits"] and w["wait_id"] not in declined:
            return w
    return None


def offer_slot(state, appt_id):
    """Offer an AVAILABLE/OPEN slot to the next waiting patient."""
    slot = state["slots"].get(appt_id)
    if slot is None or slot["status"] not in ("AVAILABLE", "OPEN"):
        return False, "Slot is not available for offer."
    if state["offer"] is not None:
        return False, "Another offer is already pending."
    w = next_waiting_patient(state, slot)
    if w is None:
        return False, "Waiting list is empty."
    if any(o[0] == w["wait_id"] and o[1] == "accepted" for o in slot["offers"]):
        return False, "This patient already accepted this slot."
    slot["status"] = "OFFERED"
    slot["offered_to"] = w["wait_id"]
    state["offer"] = {"appt_id": appt_id, "wait_id": w["wait_id"]}
    _log(state, appt_id, slot["risk"], "Slot offered", w["wait_id"], "Offer pending.")
    return True, f"Slot offered to {w['wait_id']} (demo — no message was sent)."


def accept_offer(state):
    """Accept the pending offer. Counts exactly one recovery."""
    if state["offer"] is None:
        return False, "No pending offer."
    appt_id, wait_id = state["offer"]["appt_id"], state["offer"]["wait_id"]
    slot = state["slots"][appt_id]
    if slot["status"] != "OFFERED":
        return False, "Offer is no longer pending."
    slot["status"] = "RECOVERED"
    slot["offers"].append((wait_id, "accepted"))
    state["removed_waits"].add(wait_id)
    state["offer"] = None
    _log(state, appt_id, slot["risk"], "Offer accepted", wait_id, "Slot recovered.")
    return True, "Slot recovered."


def decline_offer(state):
    """Decline the pending offer. Slot stays OPEN; never counts as recovery."""
    if state["offer"] is None:
        return False, "No pending offer."
    appt_id, wait_id = state["offer"]["appt_id"], state["offer"]["wait_id"]
    slot = state["slots"][appt_id]
    slot["status"] = "OPEN"
    slot["offered_to"] = None
    slot["offers"].append((wait_id, "declined"))
    state["offer"] = None
    _log(state, appt_id, slot["risk"], "Offer declined", wait_id, "Slot still open.")
    return True, "Declined. Slot remains open for the next patient."


def metrics(state):
    released = len(state["slots"])
    recovered = sum(1 for s in state["slots"].values() if s["status"] == "RECOVERED")
    open_slots = released - recovered
    return {
        "released": released, "recovered": recovered, "open": open_slots,
        "rate": (recovered / released) if released else 0.0,
    }


# ---------------------------------------------------------------- UI
def render_recover():
    st.title("Slot Recovery")
    st.subheader("Simulate how an available appointment slot could be reassigned.")
    st.caption("DEMO / SIMULATION — synthetic recovery workflow. No real scheduling integration.")
    st.caption("Use the sidebar to switch between dashboard modules.")
    st.caption(
        "The model identifies appointments with elevated predicted no-show risk. "
        "This simulation demonstrates one possible workflow for managing capacity "
        "if a slot becomes available."
    )

    if "rec" not in st.session_state:
        st.session_state.rec = init_state()
    state = st.session_state.rec

    model = get_model()
    scored = get_scored(model)
    threshold = st.slider("High-risk threshold", 0.05, 0.75, DEFAULT_THRESHOLD, 0.01)
    flagged = scored[scored["predicted_no_show_probability"] >= threshold]
    eligible_ids = set(flagged["AppointmentID"]) - set(state["slots"])

    m = metrics(state)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Slots released", m["released"])
    c2.metric("Slots recovered", m["recovered"])
    c3.metric("Slots still open", m["open"])
    c4.metric("Recovery rate", f"{m['rate']:.1%}")

    st.subheader("Flagged appointment")
    if eligible_ids:
        pick = st.selectbox("Select a flagged appointment", sorted(eligible_ids))
        row = flagged[flagged["AppointmentID"] == pick].iloc[0]
        st.write(f"Appointment: {row['AppointmentID']} · Patient: {row['PatientId']} · "
                 f"{row['Neighbourhood']} · Age {row['Age']}")
        appt_date = get_dates().loc[pick]
        st.write(f"Date: {appt_date.date()} · Lead time: {row['lead_time_days']} days")
        st.write(f"Predicted no-show risk: {row['predicted_no_show_probability']:.1%}")
        st.caption("This is a model prediction, not a confirmed cancellation.")
        if st.button("Release slot"):
            ok, msg = release_slot(state, row, threshold)
            st.success(msg) if ok else st.warning(msg)
            st.rerun()
    else:
        st.info("No unreleased flagged appointments at this threshold.")

    st.subheader("Available slot")
    actionable = {k: s for k, s in state["slots"].items() if s["status"] in ("AVAILABLE", "OPEN")}
    if actionable:
        sel = st.selectbox("Released slot", sorted(actionable))
        slot = state["slots"][sel]
        st.write(f"Slot: {sel} · Status: {slot['status']} · Risk: {slot['risk']:.1%}")
        st.subheader("Synthetic waiting list")
        st.caption("Synthetic waiting list — demonstration data.")
        w = next_waiting_patient(state, slot)
        if w:
            st.write(f"{w['wait_id']} · Age {w['age']} · {w['neighbourhood']} · "
                     f"{w['service']} · Waited {w['wait_days']} days")
            if st.button("Offer slot"):
                ok, msg = offer_slot(state, sel)
                st.success(msg) if ok else st.warning(msg)
                st.rerun()
        else:
            st.info("Waiting list is empty.")
    else:
        st.info("Release a flagged appointment to create an available slot.")

    if state["offer"]:
        o = state["offer"]
        st.subheader("Offer")
        st.write(f"{o['wait_id']} · Status: OFFERED (demo — no message was sent)")
        b1, b2 = st.columns(2)
        if b1.button("Accept"):
            ok, msg = accept_offer(state)
            st.success(msg) if ok else st.warning(msg)
            st.rerun()
        if b2.button("Decline"):
            ok, msg = decline_offer(state)
            st.success(msg) if ok else st.warning(msg)
            st.rerun()

    st.subheader("Recovery audit trail")
    st.caption("Demo audit trail only — not a compliance record.")
    audit = pd.DataFrame(state["audit"],
                         columns=["timestamp", "appointment", "risk", "action", "patient", "outcome"])
    st.dataframe(audit, use_container_width=True)


if __name__ == "__main__":
    st.set_page_config(page_title="Slot Recovery", layout="wide")
    render_recover()
