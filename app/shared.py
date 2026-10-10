"""Shared cached loaders for the unified dashboard.

Single scoring cache for the whole app: Overview, Predict, and Recover
all read from here, so the dataset is scored once per session.
No ML logic lives here — it delegates to app/scoring.py.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from app.scoring import DEFAULT_THRESHOLD, load_model, score_appointments

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "appointments_v3.csv"


@st.cache_resource
def get_model():
    return load_model()


@st.cache_data(show_spinner="Scoring appointments with the V3 model...")
def get_scored(_model):
    """Score once per session. Probabilities are never recomputed."""
    df = pd.read_csv(DATA_PATH, parse_dates=["ScheduledDay", "AppointmentDay"])
    df = df.drop(columns=["No-show"], errors="ignore")  # future data has no outcome
    return score_appointments(df, threshold=DEFAULT_THRESHOLD, model=_model)


@st.cache_data
def get_dates():
    return pd.read_csv(DATA_PATH, usecols=["AppointmentID", "AppointmentDay"],
                       parse_dates=["AppointmentDay"]).set_index("AppointmentID")["AppointmentDay"]
