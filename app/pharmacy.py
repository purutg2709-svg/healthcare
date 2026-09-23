"""B1 — Mock Pharmacy (demo / simulation).

Deterministic in-memory workflow: mock prescription -> inventory check ->
dispense -> audit event. NOT connected to any real pharmacy, hospital,
prescription, government, or medication system. No ML in this file.
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------- mock data
# Fixed demo inventory. Quantities are arbitrary demo values.
BASE_INVENTORY = {
    "MED-001": {"name": "Paracetamol 500mg", "category": "Analgesic", "stock": 500, "unit": "tablets", "reorder_level": 100},
    "MED-002": {"name": "Amoxicillin 250mg", "category": "Antibiotic", "stock": 120, "unit": "capsules", "reorder_level": 50},
    "MED-003": {"name": "Ibuprofen 200mg", "category": "Analgesic", "stock": 80, "unit": "tablets", "reorder_level": 50},
    "MED-004": {"name": "Cetirizine 10mg", "category": "Antihistamine", "stock": 200, "unit": "tablets", "reorder_level": 60},
    "MED-005": {"name": "Omeprazole 20mg", "category": "Antacid", "stock": 45, "unit": "capsules", "reorder_level": 50},
    "MED-006": {"name": "Salbutamol Inhaler", "category": "Respiratory", "stock": 30, "unit": "units", "reorder_level": 10},
    "MED-007": {"name": "ORS Sachet", "category": "Rehydration", "stock": 1000, "unit": "sachets", "reorder_level": 200},
    "MED-008": {"name": "Vitamin C 500mg", "category": "Supplement", "stock": 12, "unit": "tablets", "reorder_level": 20},
}

# Fixed demo prescriptions. AppointmentIDs are real IDs from the demo
# dataset (used only as display references); medications are NOT derived
# from any patient record.
BASE_PRESCRIPTIONS = [
    {"rx_id": "RX-1001", "appointment_id": 5642903, "patient_ref": "PT-DEMO-01", "med_id": "MED-001", "qty": 20, "dosage": "1 tablet twice daily", "date": "2016-04-29"},
    {"rx_id": "RX-1002", "appointment_id": 5642503, "patient_ref": "PT-DEMO-02", "med_id": "MED-002", "qty": 30, "dosage": "1 capsule three times daily", "date": "2016-04-29"},
    {"rx_id": "RX-1003", "appointment_id": 5642549, "patient_ref": "PT-DEMO-03", "med_id": "MED-003", "qty": 15, "dosage": "1 tablet as needed", "date": "2016-04-29"},
    {"rx_id": "RX-1004", "appointment_id": 5642828, "patient_ref": "PT-DEMO-04", "med_id": "MED-004", "qty": 10, "dosage": "1 tablet daily", "date": "2016-04-29"},
    {"rx_id": "RX-1005", "appointment_id": 5642494, "patient_ref": "PT-DEMO-05", "med_id": "MED-005", "qty": 30, "dosage": "1 capsule daily", "date": "2016-04-29"},
    {"rx_id": "RX-1006", "appointment_id": 5458502, "patient_ref": "PT-DEMO-06", "med_id": "MED-006", "qty": 2, "dosage": "2 puffs as needed", "date": "2016-03-11"},
    {"rx_id": "RX-1007", "appointment_id": 5476594, "patient_ref": "PT-DEMO-07", "med_id": "MED-007", "qty": 50, "dosage": "1 sachet after fluid loss", "date": "2016-03-16"},
    # Deliberately exceeds stock (12 on hand) to demonstrate the blocked path.
    {"rx_id": "RX-1008", "appointment_id": 5595358, "patient_ref": "PT-DEMO-08", "med_id": "MED-008", "qty": 60, "dosage": "1 tablet daily", "date": "2016-04-18"},
]


# ---------------------------------------------------------------- pure logic
def init_pharmacy():
    """Fresh session state. Plain data only."""
    return {
        "stock": {m: d["stock"] for m, d in BASE_INVENTORY.items()},
        "rx_status": {r["rx_id"]: "PENDING" for r in BASE_PRESCRIPTIONS},
        "audit": [],
    }


def _log(state, event, rx, status, outcome=""):
    med = next(r for r in BASE_PRESCRIPTIONS if r["rx_id"] == rx["rx_id"])
    state["audit"].append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event, "prescription_id": rx["rx_id"],
        "appointment_id": rx["appointment_id"],
        "medication": BASE_INVENTORY[med["med_id"]]["name"],
        "quantity": rx["qty"], "status": status, "outcome": outcome,
    })


def dispense(state, rx_id):
    """Dispense a prescription. Returns (ok, message). Never oversells."""
    rx = next((r for r in BASE_PRESCRIPTIONS if r["rx_id"] == rx_id), None)
    if rx is None:
        return False, "Unknown prescription."
    if state["rx_status"][rx_id] == "DISPENSED":
        return False, f"{rx_id} already DISPENSED — duplicate dispensing blocked."
    if state["stock"][rx["med_id"]] < rx["qty"]:
        _log(state, "Dispense blocked", rx, "PENDING", "INSUFFICIENT MOCK STOCK.")
        return False, (
            f"INSUFFICIENT MOCK STOCK: {BASE_INVENTORY[rx['med_id']]['name']} "
            f"has {state['stock'][rx['med_id']]} available, {rx['qty']} requested."
        )
    state["stock"][rx["med_id"]] -= rx["qty"]
    state["rx_status"][rx_id] = "DISPENSED"
    _log(state, "Dispensed", rx, "DISPENSED", "Stock updated.")
    return True, f"{rx_id} DISPENSED."


def inventory_frame(state):
    rows = []
    for med_id, d in BASE_INVENTORY.items():
        qty = state["stock"][med_id]
        rows.append({"med_id": med_id, "medication": d["name"], "category": d["category"],
                     "stock": qty, "unit": d["unit"],
                     "level": "LOW" if qty <= d["reorder_level"] else "OK"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- UI
def render_pharmacy():
    st.title("Mock Pharmacy")
    st.caption("DEMO / SIMULATION")
    st.warning("This pharmacy workflow uses synthetic prescriptions and inventory. "
               "It is not connected to a real pharmacy or healthcare system.")

    if "pharm" not in st.session_state:
        st.session_state.pharm = init_pharmacy()
    state = st.session_state.pharm

    st.subheader("1. Demo appointment / prescription")
    rx_id = st.selectbox("Select a MOCK prescription", [r["rx_id"] for r in BASE_PRESCRIPTIONS])
    rx = next(r for r in BASE_PRESCRIPTIONS if r["rx_id"] == rx_id)
    med = BASE_INVENTORY[rx["med_id"]]
    st.caption("MOCK / DEMO PRESCRIPTION — not an actual prescription.")

    st.subheader("2. Mock prescription")
    st.write(f"Prescription: {rx['rx_id']} · Appointment: {rx['appointment_id']} · "
             f"Patient ref: {rx['patient_ref']} (demo identifier)")
    st.write(f"Medication: {med['name']} · Quantity: {rx['qty']} {med['unit']} · "
             f"Dosage: {rx['dosage']} · Date: {rx['date']}")
    st.write(f"Status: **{state['rx_status'][rx_id]}**")

    st.subheader("3. Mock inventory")
    st.dataframe(inventory_frame(state), use_container_width=True)

    st.subheader("4. Dispensing action")
    if st.button("Dispense medication"):
        ok, msg = dispense(state, rx_id)
        st.success(msg) if ok else st.error(msg)
        st.rerun()

    st.subheader("5. Dispensing result")
    st.write(f"{rx_id}: **{state['rx_status'][rx_id]}** · "
             f"{med['name']} stock: {state['stock'][rx['med_id']]} {med['unit']}")

    st.subheader("6. Simulation audit log")
    st.caption("Simulation audit log — not a real pharmacy record.")
    audit = pd.DataFrame(state["audit"],
                         columns=["timestamp", "event", "prescription_id",
                                  "appointment_id", "medication", "quantity", "status", "outcome"])
    st.dataframe(audit, use_container_width=True)


if __name__ == "__main__":
    st.set_page_config(page_title="Mock Pharmacy", layout="wide")
    render_pharmacy()
