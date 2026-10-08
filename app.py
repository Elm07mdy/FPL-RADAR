# ============================================================
# FPL HOME — Streamlit Single-File Application
# ============================================================
#
# FPL HOME
# Premium Fantasy Premier League Decision Support
#
# DATA CONTRACT
# ------------------------------------------------------------
# FPL API       = source of core FPL numbers
# Owner Data    = optional enrichment layer
# Gemini        = image interpretation + explanation only
#
# NORMAL USERS
# ------------------------------------------------------------
# - Can use FPL HOME normally
# - Cannot upload data
# - Cannot enter API keys
#
# OWNER / ADMIN
# ------------------------------------------------------------
# - Access protected by OWNER_PASSWORD
# - Can upload screenshots
# - Gemini extracts visible structured data
# - Owner reviews and edits values
# - Owner publishes enrichment
#
# Suggested Streamlit Secrets:
#
# GEMINI_API_KEY = "..."
# OWNER_PASSWORD = "..."
#
# Install:
# pip install streamlit requests pandas plotly openpyxl google-genai
#
# Run:
# streamlit run fpl_home.py
# ============================================================

import os
import json
import math
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# ============================================================
# OPTIONAL GEMINI
# ============================================================

try:
    from google import genai
    from google.genai import types

    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "FPL HOME"
APP_VERSION = "5.0"

FPL_BASE = "https://fantasy.premierleague.com/api"

BOOTSTRAP_URL = f"{FPL_BASE}/bootstrap-static/"
FIXTURES_URL = f"{FPL_BASE}/fixtures/"

REQUEST_TIMEOUT = 20
CACHE_TTL = 300

GEMINI_MODEL = "gemini-2.5-flash"

POSITIONS = ["GKP", "DEF", "MID", "FWD"]


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# PREMIUM DARK UI
# ============================================================

st.markdown(
    """
<style>

:root {
    --bg: #050a0f;
    --bg2: #08121a;

    --surface: #0d1821;
    --surface2: #111f2b;
    --surface3: #162734;

    --border: #29404f;
    --border-soft: #1c303e;

    --text: #f7fafc;
    --text-soft: #d8e2e9;
    --muted: #9eb0bd;

    --green: #2ee6a6;
    --green-dark: #113f31;

    --blue: #5aa9ff;
    --blue-dark: #102e4d;

    --yellow: #ffd15c;
    --yellow-dark: #4c3d12;

    --orange: #ff9d3d;
    --orange-dark: #4d2d0f;

    --red: #ff5c68;
    --red-dark: #4b151b;

    --white: #ffffff;
}

/* GLOBAL */

html,
body,
[class*="css"] {
    font-family:
        Inter,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;
}

.stApp {
    background:
        radial-gradient(
            circle at 0% 0%,
            rgba(46, 230, 166, 0.10),
            transparent 28%
        ),
        radial-gradient(
            circle at 100% 0%,
            rgba(90, 169, 255, 0.10),
            transparent 28%
        ),
        linear-gradient(
            180deg,
            var(--bg2),
            var(--bg)
        );

    color: var(--text);
}

/* MAIN CONTAINER */

.block-container {
    max-width: 1450px;
    padding-top: 0.65rem;
    padding-bottom: 4rem;
    padding-left: 0.8rem;
    padding-right: 0.8rem;
}

/* HIDE SIDEBAR */

section[data-testid="stSidebar"] {
    display: none;
}

/* TEXT */

h1,
h2,
h3,
h4,
h5,
h6,
p,
label,
span,
div {
    color: inherit;
}

h1 {
    font-weight: 950 !important;
    letter-spacing: -0.7px;
}

h2,
h3 {
    font-weight: 900 !important;
}

/* TOP BAR */

.topbar {
    position: sticky;
    top: 0;
    z-index: 999;

    background:
        linear-gradient(
            135deg,
            rgba(9, 22, 31, 0.97),
            rgba(7, 15, 22, 0.97)
        );

    backdrop-filter: blur(18px);

    border-bottom:
        1px solid var(--border);

    padding:
        11px
        13px;

    margin-bottom: 16px;

    border-radius:
        0 0 16px 16px;
}

.brand {
    font-size: 24px;
    font-weight: 950;
    letter-spacing: -0.8px;
}

.brand span {
    color: var(--green);
}

.subtle {
    color: var(--muted) !important;
    font-size: 12px;
}

/* CARDS */

.card {
    background:
        linear-gradient(
            145deg,
            rgba(17, 31, 43, 0.98),
            rgba(10, 20, 29, 0.98)
        );

    border:
        1px solid var(--border);

    border-radius: 18px;

    padding: 17px;

    margin-bottom: 14px;

    box-shadow:
        0 8px 28px rgba(0, 0, 0, 0.20);
}

/* METRICS */

.metric-card {
    background:
        linear-gradient(
            145deg,
            var(--surface2),
            var(--surface)
        );

    border:
        1px solid var(--border);

    border-radius: 16px;

    padding: 15px;

    min-height: 102px;

    box-shadow:
        0 7px 22px rgba(0, 0, 0, 0.16);
}

.metric-label {
    color: var(--muted) !important;

    font-size: 10px;

    font-weight: 900;

    letter-spacing: 1px;
}

.metric-value {
    color: var(--white) !important;

    font-size: 26px;

    font-weight: 950;

    margin-top: 6px;
}

.metric-sub {
    color: var(--text-soft) !important;

    font-size: 11px;

    margin-top: 4px;
}

/* VERDICT */

.verdict {
    border:
        1px solid rgba(46, 230, 166, 0.35);

    border-radius: 18px;

    padding: 18px;

    background:
        linear-gradient(
            135deg,
            rgba(46, 230, 166, 0.13),
            rgba(10, 22, 31, 0.98)
        );

    box-shadow:
        0 8px 28px rgba(0, 0, 0, 0.18);
}

.verdict-kicker {
    color: var(--green) !important;

    font-size: 10px;

    font-weight: 950;

    letter-spacing: 1.3px;
}

.verdict-main {
    color: var(--white) !important;

    font-size: 24px;

    font-weight: 950;

    margin:
        6px
        0;
}

/* BADGES */

.badge {
    display: inline-block;

    border-radius: 999px;

    padding:
        5px
        9px;

    font-size: 10px;

    font-weight: 950;

    margin-right: 5px;

    border: 1px solid transparent;
}

.green {
    background: rgba(46, 230, 166, 0.15);
    color: #66efbf !important;
    border-color: rgba(46, 230, 166, 0.28);
}

.yellow {
    background: rgba(255, 209, 92, 0.15);
    color: #ffe18a !important;
    border-color: rgba(255, 209, 92, 0.28);
}

.orange {
    background: rgba(255, 157, 61, 0.15);
    color: #ffb66d !important;
    border-color: rgba(255, 157, 61, 0.28);
}

.red {
    background: rgba(255, 92, 104, 0.15);
    color: #ff929a !important;
    border-color: rgba(255, 92, 104, 0.28);
}

.blue {
    background: rgba(90, 169, 255, 0.15);
    color: #9bcaff !important;
    border-color: rgba(90, 169, 255, 0.28);
}

/* SECTION */

.section-title {
    color: var(--white) !important;

    font-size: 19px;

    font-weight: 950;

    margin:
        13px
        0
        11px;
}

/* PLAYER */

.player-card {
    background:
        linear-gradient(
            145deg,
            var(--surface2),
            var(--surface)
        );

    border:
        1px solid var(--border);

    border-radius: 15px;

    padding: 14px;

    margin-bottom: 9px;

    transition:
        transform .15s ease,
        border-color .15s ease;
}

.player-card:hover {
    transform: translateY(-1px);

    border-color:
        rgba(46, 230, 166, 0.5);
}

/* ZONE */

.zone-card {
    border:
        1px solid var(--border);

    border-radius: 15px;

    padding: 14px;

    background:
        linear-gradient(
            145deg,
            var(--surface2),
            var(--surface)
        );
}

/* DISCLAIMER */

.disclaimer {
    color: var(--muted) !important;

    font-size: 11px;

    line-height: 1.6;
}

/* STREAMLIT BUTTONS */

.stButton > button {
    width: 100%;

    background:
        linear-gradient(
            135deg,
            #173044,
            #102331
        );

    color: #ffffff !important;

    border:
        1px solid #315064;

    border-radius: 11px;

    min-height: 42px;

    font-weight: 850;

    transition:
        all .15s ease;
}

.stButton > button:hover {
    border-color: var(--green);

    background:
        linear-gradient(
            135deg,
            #19402f,
            #102c22
        );

    color: #ffffff !important;
}

/* INPUTS */

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea,
input {
    background-color: #101e29 !important;

    color: #ffffff !important;

    border-color: #304858 !important;
}

div[data-baseweb="select"] span {
    color: #ffffff !important;
}

.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    color: #ffffff !important;
}

/* RADIO */

div[role="radiogroup"] {
    gap: 5px;

    flex-wrap: wrap;
}

div[role="radiogroup"] label {
    background:
        #0e1b25;

    border:
        1px solid #29404f;

    border-radius: 10px;

    padding:
        5px
        9px;

    color: #e9f
