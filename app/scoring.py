"""Scoring layer for the hospital no-show V3 model (Act 1 — Predict).

Model: models/best_calibrated_v3_candidate.joblib
  (HistGradientBoosting + isotonic calibration, PR-AUC 0.4104)

The function below reproduces EXACTLY the feature preparation used in
training (A1.3.1) and returns calibrated probabilities plus a risk flag.
No-show is never an input. PatientId is display-only, never a feature.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "best_calibrated_v3_candidate.joblib"
DEFAULT_THRESHOLD = 0.25

# Exact model feature set from A1.3.1 (order fixed for reproducibility).
MODEL_FEATURES = [
    "gender", "age", "neighbourhood", "scholarship", "hypertension",
    "diabetes", "alcoholism", "handicap", "sms_received",
    "prior_appointments", "prior_no_shows", "is_defaulter",
    "has_any_condition", "n_conditions",
    "lead_time_days", "scheduled_hour", "appointment_dow", "age_group",
]

HISTORY_FEATURES = ["prior_appointments", "prior_no_shows", "is_defaulter"]

# Fixed training-time mapping: neighbourhoods with <50 rows -> OTHER.
# Must be a constant (never recomputed on the scoring batch).
OTHER_NEIGHBOURHOODS = frozenset({
    "ILHA DO BOI", "ILHA DO FRADE", "AEROPORTO",
    "ILHAS OCEÂNICAS DE TRINDADE", "PARQUE INDUSTRIAL", "OTHER",
})

AGE_BINS = [-np.inf, 18, 35, 50, 64, np.inf]
AGE_LABELS = ["0-18", "19-35", "36-50", "51-64", "65+"]

_model_cache = {}


def load_model(model_path=MODEL_PATH):
    """Load (and cache) the saved V3 calibrated pipeline."""
    key = str(model_path)
    if key not in _model_cache:
        _model_cache[key] = joblib.load(model_path)
    return _model_cache[key]


def _pick(df, *names):
    """Return the first of `names` present in df, else None."""
    for n in names:
        if n in df.columns:
            return df[n]
    return None


def prepare_features(df):
    """Build the exact 18-column model matrix from appointment records.

    Accepts raw-style (ScheduledDay/...) or champion-style (lowercase)
    column names. Derives lead_time_days, scheduled_hour,
    appointment_dow, age_group, and condition flags when absent.
    prior_* history columns must be supplied (computed upstream from
    patient history); they are never fabricated here.
    """
    missing_hist = [c for c in HISTORY_FEATURES if c not in df.columns]
    if missing_hist:
        raise ValueError(
            f"Missing history features {missing_hist}. Compute them from patient "
            "history before scoring (see A1.2); scoring never invents them."
        )
    work = pd.DataFrame(index=df.index)
    work["gender"] = _pick(df, "gender", "Gender")
    work["age"] = _pick(df, "age", "Age")
    work["neighbourhood"] = _pick(df, "neighbourhood", "Neighbourhood")
    work["scholarship"] = _pick(df, "scholarship", "Scholarship")
    work["hypertension"] = _pick(df, "hypertension", "Hipertension")
    work["diabetes"] = _pick(df, "diabetes", "Diabetes")
    work["alcoholism"] = _pick(df, "alcoholism", "Alcoholism")
    work["handicap"] = _pick(df, "handicap", "Handcap")
    work["sms_received"] = _pick(df, "sms_received", "SMS_received")
    for c in HISTORY_FEATURES:
        work[c] = df[c]

    sched = pd.to_datetime(_pick(df, "scheduledday", "ScheduledDay"))
    appt = pd.to_datetime(_pick(df, "appointmentday", "AppointmentDay"))
    if _pick(df, "lead_time_days") is not None:
        work["lead_time_days"] = _pick(df, "lead_time_days")
    else:
        work["lead_time_days"] = (
            appt.dt.normalize() - sched.dt.normalize()
        ).dt.days
    work["scheduled_hour"] = (
        _pick(df, "scheduled_hour") if "scheduled_hour" in df.columns
        else sched.dt.hour
    ).astype(int)
    work["appointment_dow"] = (
        _pick(df, "appointment_dow") if "appointment_dow" in df.columns
        else appt.dt.dayofweek
    ).astype(int)
    if "age_group" in df.columns:
        work["age_group"] = df["age_group"].astype(str)
    else:
        work["age_group"] = pd.cut(
            work["age"], bins=AGE_BINS, labels=AGE_LABELS, right=True
        ).astype(str)
    if "has_any_condition" in df.columns:
        work["has_any_condition"] = df["has_any_condition"]
    else:
        work["has_any_condition"] = (
            (work["hypertension"] == 1) | (work["diabetes"] == 1)
            | (work["alcoholism"] == 1) | (work["handicap"] > 0)
        ).astype(int)
    if "n_conditions" in df.columns:
        work["n_conditions"] = df["n_conditions"]
    else:
        work["n_conditions"] = (
            work["hypertension"] + work["diabetes"] + work["alcoholism"]
            + (work["handicap"] > 0).astype(int)
        )

    work["neighbourhood"] = work["neighbourhood"].where(
        ~work["neighbourhood"].isin(OTHER_NEIGHBOURHOODS),
        "OTHER",
    )
    if work[MODEL_FEATURES].isna().any().any():
        bad = work[MODEL_FEATURES].isna().sum()
        raise ValueError(f"Missing values after preparation:\n{bad[bad > 0]}")
    return work[MODEL_FEATURES]


def score_appointments(df, threshold=DEFAULT_THRESHOLD, model=None, model_path=MODEL_PATH):
    """Score appointments; return display columns + probability + flag.

    threshold is an argument (default 0.25) so the UI can change it
    without touching model code.
    """
    if model is None:
        model = load_model(model_path)
    X = prepare_features(df)
    proba = model.predict_proba(X)[:, 1]
    out = pd.DataFrame(index=df.index)
    for src, dst in [("AppointmentID", "AppointmentID"), ("appointmentid", "AppointmentID"),
                     ("PatientId", "PatientId"), ("patientid", "PatientId"),
                     ("Neighbourhood", "Neighbourhood"), ("neighbourhood", "Neighbourhood"),
                     ("Age", "Age"), ("age", "Age"),
                     ("SMS_received", "SMS_received"), ("sms_received", "SMS_received")]:
        if src in df.columns and dst not in out.columns:
            out[dst] = df[src]
    out["lead_time_days"] = X["lead_time_days"].values
    out["predicted_no_show_probability"] = proba
    out["risk_flag"] = (proba >= threshold).astype(int)
    return out.sort_values("predicted_no_show_probability", ascending=False).reset_index(drop=True)
