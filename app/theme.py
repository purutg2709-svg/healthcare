"""Brutalist theme for the No-Show Ops dashboard.

Single source of all custom CSS. Called once per page render.
Palette: paper #F2F0E9, black #000000, signal red #FF3B00, gray #8A8A8A.
"""

import streamlit as st

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Mono:wght@400;700&display=swap');

* { border-radius: 0 !important; }

html, body, [data-testid="stAppViewContainer"] { background: #F2F0E9; }

h1, h2, h3 { font-family: 'Archivo Black', sans-serif !important; text-align: left !important; }
p, span, div, label { font-family: 'Space Mono', monospace; }

#MainMenu, footer, [data-testid="stDeployButton"] { display: none; }

[data-testid="stSidebar"] { background: #E8E6DD; border-right: 3px solid #000; }

[data-testid="stMetric"] { background: #F2F0E9; border: 3px solid #000;
  box-shadow: 6px 6px 0 #000; padding: 12px; }

.stButton > button { background: #000; color: #fff; border: 3px solid #000;
  border-radius: 0; font-family: 'Space Mono', monospace; font-weight: 700;
  text-transform: uppercase; transition: none; }
.stButton > button:hover { background: #fff; color: #000; border: 3px solid #000; }
.stButton > button:focus { outline: 3px solid #FF3B00 !important; box-shadow: none !important; }

input, select, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div {
  border-radius: 0 !important; font-family: 'Space Mono', monospace !important; }
*:focus { box-shadow: none !important; }
input:focus, select:focus, textarea:focus { outline: 3px solid #FF3B00 !important; }

.stDownloadButton > button { background: #000; color: #fff; border: 3px solid #000;
  border-radius: 0; font-family: 'Space Mono', monospace; font-weight: 700;
  text-transform: uppercase; }
.stDownloadButton > button:hover { background: #fff; color: #000; }

[data-testid="stDataFrame"] { border: 3px solid #000; }
"""


def inject_brutalist_css():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def section_label(index, text):
    st.markdown(
        f"<div style=\"font-family:'Space Mono',monospace;font-weight:700;"
        f"letter-spacing:2px;margin:24px 0 8px;\">{index:02d} / {text.upper()}</div>",
        unsafe_allow_html=True,
    )


def kpi(value, caption, alert=False):
    color = "#FF3B00" if alert else "#000000"
    st.markdown(
        f"<div style=\"border:3px solid #000;box-shadow:6px 6px 0 #000;"
        f"padding:12px;background:#F2F0E9;\">"
        f"<div style=\"font-family:'Archivo Black',sans-serif;font-size:72px;"
        f"line-height:1;color:{color};\">{value}</div>"
        f"<div style=\"font-family:'Space Mono',monospace;font-size:12px;"
        f"letter-spacing:2px;color:#8A8A8A;\">{caption.upper()}</div></div>",
        unsafe_allow_html=True,
    )
