"""Generate the persistent synthetic controlled-substance transaction dataset.

Deterministic (seed 42). Run ONCE; the CSV is committed as a project data
file. All identifiers, medications, and patterns are fictional demo data.
Usage: python3 scripts/generate_mock_controlled_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_ROWS = 2000
OUT = Path(__file__).resolve().parent.parent / "data" / "mock_controlled_substance_transactions.csv"

MEDS = [
    {"medication_id": "CMED-01", "medication_name": "CONTROL-DEMO-A", "controlled_category": "CONTROLLED-DEMO-1", "dosage_form": "Tablet", "unit": "tablets", "qty_max": 30, "high_qty": 40},
    {"medication_id": "CMED-02", "medication_name": "CONTROL-DEMO-B", "controlled_category": "CONTROLLED-DEMO-1", "dosage_form": "Capsule", "unit": "capsules", "qty_max": 30, "high_qty": 40},
    {"medication_id": "CMED-03", "medication_name": "CONTROL-DEMO-C", "controlled_category": "CONTROLLED-DEMO-2", "dosage_form": "Syrup", "unit": "ml", "qty_max": 200, "high_qty": 300},
    {"medication_id": "CMED-04", "medication_name": "CONTROL-DEMO-D", "controlled_category": "CONTROLLED-DEMO-2", "dosage_form": "Tablet", "unit": "tablets", "qty_max": 20, "high_qty": 30},
    {"medication_id": "CMED-05", "medication_name": "CONTROL-DEMO-E", "controlled_category": "CONTROLLED-DEMO-3", "dosage_form": "Injection", "unit": "vials", "qty_max": 10, "high_qty": 15},
    {"medication_id": "CMED-06", "medication_name": "CONTROL-DEMO-F", "controlled_category": "CONTROLLED-DEMO-3", "dosage_form": "Capsule", "unit": "capsules", "qty_max": 60, "high_qty": 90},
]
PHARMS = [f"PHARM-DEMO-{i:02d}" for i in range(1, 9)]
PRESCRIBERS = [f"PRESC-DEMO-{i:02d}" for i in range(1, 26)]
PATIENTS = [f"PT-DEMO-{i:04d}" for i in range(1, 401)]
MONTH_W = np.array([0.06, 0.07, 0.08, 0.08, 0.09, 0.09, 0.10, 0.09, 0.08, 0.08, 0.09, 0.09])
MONTH_W = MONTH_W / MONTH_W.sum()


def main():
    rng = np.random.default_rng(SEED)
    months = rng.choice(np.arange(1, 13), size=N_ROWS, p=MONTH_W)
    days = rng.integers(1, 29, size=N_ROWS)  # safe day range for every month
    dates = pd.to_datetime({"year": 2026, "month": months, "day": days})
    order = np.argsort(dates.values)
    rows = []
    for i, idx in enumerate(order):
        med = MEDS[rng.integers(len(MEDS))]
        # 5% of rows get an inflated quantity to seed HIGH_QUANTITY flags
        qty = int(rng.integers(1, med["qty_max"] + 1))
        if rng.random() < 0.05:
            qty = med["high_qty"] + int(rng.integers(1, 11))
        status = "CANCELLED" if rng.random() < 0.08 else "DISPENSED"
        reported = rng.random() < 0.78
        rows.append({
            "transaction_id": f"TX-{i+1:06d}",
            "prescription_id": f"RX-{200001 + int(rng.integers(0, 3000))}",
            "patient_ref": PATIENTS[rng.integers(len(PATIENTS))],
            "medication_id": med["medication_id"],
            "pharmacy_id": PHARMS[rng.integers(len(PHARMS))],
            "prescriber_id": PRESCRIBERS[rng.integers(len(PRESCRIBERS))],
            "medication_name": med["medication_name"],
            "controlled_category": med["controlled_category"],
            "dosage_form": med["dosage_form"],
            "unit": med["unit"],
            "quantity": qty,
            "transaction_date": dates[idx].strftime("%Y-%m-%d"),
            "transaction_status": status,
            "reporting_status": "REPORTED" if reported else "PENDING",
        })
    df = pd.DataFrame(rows)
    # report linkage for REPORTED rows (init first: loc-assign onto a
    # nonexistent column misaligns values)
    rep_mask = df["reporting_status"] == "REPORTED"
    df["report_id"] = ""
    df.loc[rep_mask, "report_id"] = [f"RPT-{(i % 400) + 1:04d}" for i in df[rep_mask].index]
    df["report_date"] = ""
    tdates = pd.to_datetime(df["transaction_date"])
    df.loc[rep_mask, "report_date"] = (
        tdates[rep_mask] + pd.to_timedelta(rng.integers(1, 6, size=rep_mask.sum()), unit="D")
    ).dt.strftime("%Y-%m-%d")

    # Deterministic rule-based anomaly flags (demo analytics only).
    df["anomaly_flag"] = 0
    df["anomaly_reason"] = ""
    high = df.apply(lambda r: r["quantity"] > next(
        m["high_qty"] for m in MEDS if m["medication_id"] == r["medication_id"]), axis=1)
    df.loc[high, ["anomaly_flag", "anomaly_reason"]] = [1, "HIGH_QUANTITY"]
    df = df.sort_values(["patient_ref", "medication_id", "transaction_date"]).reset_index(drop=True)
    prev = df.groupby(["patient_ref", "medication_id"])["transaction_date"].shift(1)
    gap = (pd.to_datetime(df["transaction_date"]) - pd.to_datetime(prev)).dt.days
    rep_txn = (gap <= 7) & df["anomaly_flag"].eq(0)
    df.loc[rep_txn, ["anomaly_flag", "anomaly_reason"]] = [1, "REPEATED_TRANSACTION"]
    max_date = pd.to_datetime(df["transaction_date"]).max()
    stale = (df["reporting_status"] == "PENDING") & \
            ((max_date - pd.to_datetime(df["transaction_date"])).dt.days > 60) & df["anomaly_flag"].eq(0)
    df.loc[stale, ["anomaly_flag", "anomaly_reason"]] = [1, "PENDING_REPORT"]
    big_round = (df["quantity"] % 50 == 0) & (df["quantity"] >= 50) & df["anomaly_flag"].eq(0)
    df.loc[big_round, ["anomaly_flag", "anomaly_reason"]] = [1, "UNUSUAL_PATTERN"]
    df = df.sort_values("transaction_id").reset_index(drop=True)

    OUT.parent.mkdir(exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"wrote {OUT} shape={df.shape}")
    print("status:", df["transaction_status"].value_counts().to_dict())
    print("reporting:", df["reporting_status"].value_counts().to_dict())
    print("flagged:", int(df["anomaly_flag"].sum()), df["anomaly_reason"].value_counts().to_dict())


if __name__ == "__main__":
    main()
