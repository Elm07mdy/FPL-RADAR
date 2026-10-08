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

    color: #e9f1f5 !important;
}

div[role="radiogroup"] label:hover {
    border-color: var(--green);
}

/* DATAFRAME */

div[data-testid="stDataFrame"] {
    border:
        1px solid var(--border);

    border-radius: 13px;

    overflow: hidden;
}

/* ALERTS */

div[data-testid="stAlert"] {
    border-radius: 13px;
}

/* FILE UPLOADER */

section[data-testid="stFileUploaderDropzone"] {
    background:
        #0d1b25 !important;

    border:
        1px dashed #3b596b !important;

    border-radius: 15px !important;
}

section[data-testid="stFileUploaderDropzone"] * {
    color: #eaf3f7 !important;
}

/* PITCH LEGEND */

.pitch-legend {
    display: flex;

    gap: 10px;

    flex-wrap: wrap;

    margin:
        8px
        0
        14px;
}

.pitch-legend-item {
    display: flex;

    align-items: center;

    gap: 6px;

    color: #dce7ed;

    font-size: 11px;

    font-weight: 800;
}

.pitch-dot {
    width: 11px;
    height: 11px;

    border-radius: 50%;

    display: inline-block;
}

.dot-red {
    background: #ff3d4d;
}

.dot-orange {
    background: #ff9d2e;
}

.dot-yellow {
    background: #ffd83d;
}

/* DATA CENTER */

.admin-header {
    background:
        linear-gradient(
            135deg,
            rgba(90,169,255,.12),
            rgba(46,230,166,.08)
        );

    border:
        1px solid rgba(90,169,255,.30);

    border-radius: 18px;

    padding: 18px;

    margin-bottom: 15px;
}

.admin-title {
    font-size: 23px;

    font-weight: 950;

    color: white;
}

.admin-subtitle {
    color: #a9bdca;

    font-size: 12px;

    margin-top: 5px;
}

/* MOBILE */

@media (max-width: 768px) {

    .block-container {
        padding-left: .55rem;
        padding-right: .55rem;
    }

    .brand {
        font-size: 20px;
    }

    .metric-card {
        min-height: 84px;
    }

    .metric-value {
        font-size: 21px;
    }

    .verdict-main {
        font-size: 20px;
    }

    h1 {
        font-size: 27px !important;
    }

    h2 {
        font-size: 22px !important;
    }

    h3 {
        font-size: 18px !important;
    }

    div[role="radiogroup"] {
        overflow-x: auto;
        flex-wrap: nowrap;
        padding-bottom: 5px;
    }

    div[role="radiogroup"] label {
        white-space: nowrap;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def money(value):
    return f"£{safe_float(value):.1f}m"


def pct(value):
    return f"{safe_float(value):.1f}%"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_secret(name, default=""):
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


def risk_badge(risk):
    risk = str(risk)

    if risk.lower() == "low":
        cls = "green"
    elif risk.lower() == "medium":
        cls = "yellow"
    else:
        cls = "red"

    return f'<span class="badge {cls}">{risk}</span>'


def difficulty_badge(difficulty):
    d = safe_int(difficulty, 3)

    if d <= 2:
        return '<span class="badge green">EASY</span>'

    if d == 3:
        return '<span class="badge yellow">MIXED</span>'

    return '<span class="badge red">HARD</span>'


def selected_gameweek(events):
    """
    Returns the Gameweek selected in the global top navigation.
    Falls back to next/current GW.
    """

    selected = st.session_state.get("selected_gw")

    if selected is not None:
        try:
            selected = int(selected)

            if any(e["id"] == selected for e in events):
                return selected
        except Exception:
            pass

    return get_next_gw(events)


# ============================================================
# FPL API ENGINE
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False,
)
def fetch_json(url: str):

    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={
            "User-Agent": "FPL-HOME/5.0"
        },
    )

    response.raise_for_status()

    return response.json()


@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False,
)
def load_fpl_data():

    bootstrap = fetch_json(
        BOOTSTRAP_URL
    )

    fixtures = fetch_json(
        FIXTURES_URL
    )

    return {
        "bootstrap": bootstrap,
        "fixtures": fixtures,
        "updated": utc_now(),
    }


@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False,
)
def load_player_summary(player_id: int):

    return fetch_json(
        f"{FPL_BASE}/element-summary/{player_id}/"
    )


@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False,
)
def load_fpl_team(team_id: int):

    entry = fetch_json(
        f"{FPL_BASE}/entry/{int(team_id)}/"
    )

    history = None

    try:
        history = fetch_json(
            f"{FPL_BASE}/entry/{int(team_id)}/history/"
        )
    except Exception:
        pass

    return {
        "entry": entry,
        "history": history,
    }


@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False,
)
def load_fpl_team_picks(team_id: int, gw: int):

    return fetch_json(
        f"{FPL_BASE}/entry/{int(team_id)}/event/{int(gw)}/picks/"
    )


def load_data_with_status():

    try:

        return (
            load_fpl_data(),
            True,
            None,
        )

    except Exception as exc:

        return (
            None,
            False,
            str(exc),
        )


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_data(raw):

    bootstrap = raw["bootstrap"]

    teams = {}

    for t in bootstrap.get("teams", []):

        teams[t["id"]] = {

            "id": t["id"],

            "name": t.get(
                "name",
                "",
            ),

            "short_name": t.get(
                "short_name",
                "",
            ),

            "code": t.get(
                "code",
                0,
            ),

            "strength": safe_float(
                t.get("strength")
            ),

            "strength_attack_home": safe_float(
                t.get("strength_attack_home")
            ),

            "strength_attack_away": safe_float(
                t.get("strength_attack_away")
            ),

            "strength_defence_home": safe_float(
                t.get("strength_defence_home")
            ),

            "strength_defence_away": safe_float(
                t.get("strength_defence_away")
            ),
        }

    positions = {
        p["id"]: p.get(
            "singular_name_short",
            "",
        )
        for p in bootstrap.get(
            "element_types",
            [],
        )
    }

    players = []

    for p in bootstrap.get(
        "elements",
        [],
    ):

        team_id = p.get(
            "team"
        )

        team = teams.get(
            team_id,
            {
                "name": "Unknown",
                "short_name": "UNK",
            },
        )

        players.append({

            "id": p.get("id"),

            "name":
                f"{p.get('first_name','')} "
                f"{p.get('second_name','')}"
                .strip(),

            "web_name":
                p.get(
                    "web_name",
                    "",
                ),

            "team_id":
                team_id,

            "team":
                team.get(
                    "name",
                    "",
                ),

            "team_short":
                team.get(
                    "short_name",
                    "",
                ),

            "position":
                positions.get(
                    p.get("element_type"),
                    "?",
                ),

            "price":
                safe_float(
                    p.get("now_cost")
                ) / 10,

            "total_points":
                safe_float(
                    p.get("total_points")
                ),

            "event_points":
                safe_float(
                    p.get("event_points")
                ),

            "form":
                safe_float(
                    p.get("form")
                ),

            "points_per_game":
                safe_float(
                    p.get("points_per_game")
                ),

            "selected_by":
                safe_float(
                    p.get("selected_by_percent")
                ),

            "minutes":
                safe_float(
                    p.get("minutes")
                ),

            "goals":
                safe_float(
                    p.get("goals_scored")
                ),

            "assists":
                safe_float(
                    p.get("assists")
                ),

            "clean_sheets":
                safe_float(
                    p.get("clean_sheets")
                ),

            "goals_conceded":
                safe_float(
                    p.get("goals_conceded")
                ),

            "saves":
                safe_float(
                    p.get("saves")
                ),

            "bonus":
                safe_float(
                    p.get("bonus")
                ),

            "bps":
                safe_float(
                    p.get("bps")
                ),

            "influence":
                safe_float(
                    p.get("influence")
                ),

            "creativity":
                safe_float(
                    p.get("creativity")
                ),

            "threat":
                safe_float(
                    p.get("threat")
                ),

            "ict_index":
                safe_float(
                    p.get("ict_index")
                ),

            "expected_goals":
                safe_float(
                    p.get("expected_goals")
                ),

            "expected_assists":
                safe_float(
                    p.get("expected_assists")
                ),

            "expected_goal_involvements":
                safe_float(
                    p.get(
                        "expected_goal_involvements"
                    )
                ),

            "expected_goals_per_90":
                safe_float(
                    p.get(
                        "expected_goals_per_90"
                    )
                ),

            "expected_assists_per_90":
                safe_float(
                    p.get(
                        "expected_assists_per_90"
                    )
                ),

            "expected_goal_involvements_per_90":
                safe_float(
                    p.get(
                        "expected_goal_involvements_per_90"
                    )
                ),

            "chance_next_round":
                safe_float(
                    p.get(
                        "chance_of_playing_next_round"
                    ),
                    100,
                ),

            "chance_this_round":
                safe_float(
                    p.get(
                        "chance_of_playing_this_round"
                    ),
                    100,
                ),

            "status":
                p.get(
                    "status",
                    "a",
                ),

            "news":
                p.get(
                    "news",
                    "",
                ),

            "starts":
                safe_float(
                    p.get("starts")
                ),

            "clean_sheets_per_90":
                safe_float(
                    p.get(
                        "clean_sheets_per_90"
                    )
                ),

            "form_rank":
                safe_float(
                    p.get("form_rank")
                ),

            "points_per_game_rank":
                safe_float(
                    p.get(
                        "points_per_game_rank"
                    )
                ),

            "cost_change_event":
                safe_float(
                    p.get(
                        "cost_change_event"
                    )
                ),

            "cost_change_start":
                safe_float(
                    p.get(
                        "cost_change_start"
                    )
                ),

            "cost_change_event_fall":
                safe_float(
                    p.get(
                        "cost_change_event_fall"
                    )
                ),

            "cost_change_start_fall":
                safe_float(
                    p.get(
                        "cost_change_start_fall"
                    )
                ),

            "transfers_in_event":
                safe_float(
                    p.get(
                        "transfers_in_event"
                    )
                ),

            "transfers_out_event":
                safe_float(
                    p.get(
                        "transfers_out_event"
                    )
                ),

            "transfers_in":
                safe_float(
                    p.get(
                        "transfers_in"
                    )
                ),

            "transfers_out":
                safe_float(
                    p.get(
                        "transfers_out"
                    )
                ),
        })

    events = []

    for e in bootstrap.get(
        "events",
        [],
    ):

        events.append({

            "id":
                e.get("id"),

            "name":
                e.get("name"),

            "deadline":
                e.get(
                    "deadline_time"
                ),

            "finished":
                e.get("finished"),

            "is_current":
                e.get("is_current"),

            "is_next":
                e.get("is_next"),

            "is_previous":
                e.get(
                    "is_previous"
                ),

            "average_score":
                e.get(
                    "average_entry_score"
                ),

            "highest_score":
                e.get(
                    "highest_score"
                ),

            "most_captained":
                e.get(
                    "most_captained"
                ),

            "top_element":
                e.get(
                    "top_element"
                ),
        })

    fixtures = []

    for f in raw.get(
        "fixtures",
        [],
    ):

        fixtures.append({

            "id":
                f.get("id"),

            "event":
                f.get("event"),

            "team_h":
                f.get("team_h"),

            "team_a":
                f.get("team_a"),

            "team_h_score":
                f.get("team_h_score"),

            "team_a_score":
                f.get("team_a_score"),

            "finished":
                f.get("finished"),

            "difficulty_h":
                safe_int(
                    f.get(
                        "team_h_difficulty"
                    )
                ),

            "difficulty_a":
                safe_int(
                    f.get(
                        "team_a_difficulty"
                    )
                ),

            "kickoff":
                f.get(
                    "kickoff_time"
                ),

            "provisional_start_time":
                f.get(
                    "provisional_start_time"
                ),
        })

    return {

        "teams":
            teams,

        "players":
            players,

        "events":
            events,

        "fixtures":
            fixtures,

        "updated":
            raw.get(
                "updated",
                utc_now(),
            ),
    }


# ============================================================
# GAMEWEEK
# ============================================================

def get_current_gw(events):

    current = [
        e for e in events
        if e.get("is_current")
    ]

    if current:
        return current[0]["id"]

    nxt = [
        e for e in events
        if e.get("is_next")
    ]

    if nxt:
        return nxt[0]["id"]

    return 1


def get_next_gw(events):

    nxt = [
        e for e in events
        if e.get("is_next")
    ]

    return (
        nxt[0]["id"]
        if nxt
        else get_current_gw(events)
    )


# ============================================================
# FIXTURES
# ============================================================

def team_fixture_rows(
    data,
    team_id,
    gw=None,
    horizon=5,
):

    if gw is None:
        gw = selected_gameweek(
            data["events"]
        )

    rows = []

    for f in data["fixtures"]:

        if f["event"] is None:
            continue

        if (
            f["event"] < gw
            or
            f["event"] > gw + horizon - 1
        ):
            continue

        if f["team_h"] == team_id:

            opponent = data["teams"].get(
                f["team_a"],
                {},
            )

            rows.append({

                "gw":
                    f["event"],

                "opponent":
                    opponent.get(
                        "short_name",
                        "?",
                    ),

                "opponent_id":
                    f["team_a"],

                "home":
                    True,

                "difficulty":
                    f["difficulty_h"],

                "kickoff":
                    f["kickoff"],
            })

        elif f["team_a"] == team_id:

            opponent = data["teams"].get(
                f["team_h"],
                {},
            )

            rows.append({

                "gw":
                    f["event"],

                "opponent":
                    opponent.get(
                        "short_name",
                        "?",
                    ),

                "opponent_id":
                    f["team_h"],

                "home":
                    False,

                "difficulty":
                    f["difficulty_a"],

                "kickoff":
                    f["kickoff"],
            })

    rows.sort(
        key=lambda x: (
            x["gw"],
            x["kickoff"] or "",
        )
    )

    return rows


def fixture_score(fixtures):

    if not fixtures:
        return 50.0

    avg = (
        sum(
            safe_float(
                x["difficulty"],
                3,
            )
            for x in fixtures
        )
        /
        len(fixtures)
    )

    return clamp(
        100 -
        ((avg - 1) / 4) * 100,
        0,
        100,
    )


def fixture_label(score):

    if score >= 75:
        return "Excellent"

    if score >= 60:
        return "Good"

    if score >= 45:
        return "Mixed"

    return "Difficult"


def fixture_text(
    fixtures,
    limit=5,
):

    return " · ".join(
        f"GW{x['gw']} "
        f"{x['opponent']} "
        f"{'H' if x['home'] else 'A'}"
        for x in fixtures[:limit]
    )


def fixture_swing(
    data,
    team_id,
):

    base_gw = selected_gameweek(
        data["events"]
    )

    upcoming = team_fixture_rows(
        data,
        team_id,
        gw=base_gw,
        horizon=5,
    )

    later = team_fixture_rows(
        data,
        team_id,
        gw=base_gw + 5,
        horizon=5,
    )

    a = fixture_score(
        upcoming
    )

    b = fixture_score(
        later
    )

    return {

        "current_score":
            a,

        "next_score":
            b,

        "swing":
            b - a,

        "current_label":
            fixture_label(a),

        "next_label":
            fixture_label(b),
    }


# ============================================================
# PLAYER ANALYTICS
# ============================================================

def minutes_score(player):

    chance = safe_float(
        player.get(
            "chance_next_round"
        ),
        100,
    )

    minutes = safe_float(
        player.get("minutes")
    )

    starts = safe_float(
        player.get("starts")
    )

    if minutes <= 0:
        base = 15

    else:
        base = min(
            100,
            45 +
            min(
                55,
                minutes / 1200 * 55
            )
        )

    if (
        starts > 0
        and
        minutes > 0
    ):

        start_rate = clamp(
            starts /
            max(
                1,
                minutes / 90
            ),
            0,
            1,
        )

        base = (
            base * .65
            +
            start_rate * 100 * .35
        )

    return clamp(
        base * chance / 100,
        0,
        100,
    )


def risk_score(player):

    injury_risk = (
        100 -
        safe_float(
            player.get(
                "chance_next_round"
            ),
            100,
        )
    )

    low_minutes = (
        100 -
        minutes_score(player)
    )

    news_penalty = (
        15
        if player.get("news")
        else 0
    )

    return clamp(

        injury_risk * .45
        +
        low_minutes * .45
        +
        news_penalty * .10,

        0,
        100,
    )


def player_radar_score(
    player,
    data,
):

    fixtures = team_fixture_rows(
        data,
        player["team_id"],
        horizon=5,
    )

    f_score = fixture_score(
        fixtures
    )

    form = clamp(
        safe_float(
            player["form"]
        ) * 10,
        0,
        100,
    )

    xgi = clamp(
        safe_float(
            player[
                "expected_goal_involvements_per_90"
            ]
        ) * 100,
        0,
        100,
    )

    ict = clamp(
        safe_float(
            player["ict_index"]
        ),
        0,
        100,
    )

    mins = minutes_score(
        player
    )

    risk = risk_score(
        player
    )

    score = (

        form * .20

        +

        xgi * .25

        +

        ict * .15

        +

        mins * .20

        +

        f_score * .20
    )

    return clamp(
        score - risk * .15,
        0,
        100,
    )


def captain_score(
    player,
    data,
):

    fixtures = team_fixture_rows(
        data,
        player["team_id"],
        horizon=3,
    )

    f_score = fixture_score(
        fixtures
    )

    form = clamp(
        safe_float(
            player["form"]
        ) * 10,
        0,
        100,
    )

    xgi = clamp(
        safe_float(
            player[
                "expected_goal_involvements_per_90"
            ]
        ) * 100,
        0,
        100,
    )

    mins = minutes_score(
        player
    )

    bonus = clamp(
        safe_float(
            player["bonus"]
        ) / 10,
        0,
        100,
    )

    home_bonus = (
        7
        if fixtures
        and fixtures[0]["home"]
        else 0
    )

    risk = risk_score(
        player
    )

    score = (

        xgi * .32

        +

        form * .20

        +

        f_score * .25

        +

        mins * .15

        +

        bonus * .08

        +

        home_bonus
    )

    return clamp(
        score - risk * .15,
        0,
        100,
    )


def differential_score(
    player,
    data,
):

    radar = player_radar_score(
        player,
        data,
    )

    ownership_score = clamp(
        100 -
        safe_float(
            player["selected_by"]
        ) * 4,
        0,
        100,
    )

    xgi = clamp(
        safe_float(
            player[
                "expected_goal_involvements_per_90"
            ]
        ) * 100,
        0,
        100,
    )

    minutes = minutes_score(
        player
    )

    return clamp(

        radar * .40

        +

        ownership_score * .25

        +

        xgi * .20

        +

        minutes * .15,

        0,
        100,
    )


def add_scores(
    players,
    data,
):

    out = []

    for p in players:

        row = dict(p)

        row["radar_score"] = (
            player_radar_score(
                p,
                data,
            )
        )

        row["captain_score"] = (
            captain_score(
                p,
                data,
            )
        )

        row["differential_score"] = (
            differential_score(
                p,
                data,
            )
        )

        row["minutes_score"] = (
            minutes_score(p)
        )

        row["risk_score"] = (
            risk_score(p)
        )

        out.append(row)

    return out


# ============================================================
# DEFENSIVE DATA
# ============================================================

def default_defensive_profile(
    team,
    data,
):

    strength_home = safe_float(
        team.get(
            "strength_defence_home"
        )
    )

    strength_away = safe_float(
        team.get(
            "strength_defence_away"
        )
    )

    strength = (
        strength_home
        +
        strength_away
    ) / 2

    strengths = [

        safe_float(
            t.get(
                "strength_defence_home"
            )
        )

        +

        safe_float(
            t.get(
                "strength_defence_away"
            )
        )

        for t in data["teams"].values()
    ]

    min_s = (
        min(strengths)
        if strengths
        else 1
    )

    max_s = (
        max(strengths)
        if strengths
        else 100
    )

    normalized = (
        strength * 2 -
        min_s
    ) / max(
        1,
        max_s - min_s,
    )

    vulnerability = clamp(
        100 -
        normalized * 100,
        0,
        100,
    )

    return {

        "team_id":
            team["id"],

        "team":
            team["name"],

        "source":
            "FPL API proxy",

        "defensive_strength":
            clamp(
                100 -
                vulnerability,
                0,
                100,
            ),

        "vulnerability":
            vulnerability,

        "left":
            clamp(
                vulnerability * .95
                +
                (
                    100 -
                    strength_home
                ) * .05,
                0,
                100,
            ),

        "center":
            clamp(
                vulnerability * 1.08,
                0,
                100,
            ),

        "right":
            clamp(
                vulnerability * .92
                +
                (
                    100 -
                    strength_away
                ) * .08,
                0,
                100,
            ),

        "confidence":
            "Proxy",
    }


def get_enrichment():

    return st.session_state.get(
        "defensive_enrichment",
        {},
    )


def set_enrichment(
    enrichment,
):

    st.session_state[
        "defensive_enrichment"
    ] = enrichment


def merged_defensive_profile(
    team,
    data,
):

    base = default_defensive_profile(
        team,
        data,
    )

    enriched = get_enrichment().get(
        str(team["id"])
    )

    if not enriched:
        return base

    result = dict(base)

    for key in [
        "left",
        "center",
        "right",
        "vulnerability",
        "defensive_strength",
    ]:

        if (
            key in enriched
            and
            enriched[key] is not None
        ):

            result[key] = safe_float(
                enriched[key],
                result[key],
            )

    result["source"] = enriched.get(
        "source",
        "Owner enrichment",
    )

    result["confidence"] = enriched.get(
        "confidence",
        "Owner data",
    )

    result["gw"] = enriched.get(
        "gw"
    )

    result["notes"] = enriched.get(
        "notes",
        "",
    )

    return result


def defensive_zone_rank(
    profile,
):

    zones = {

        "LEFT":
            safe_float(
                profile.get("left")
            ),

        "CENTER":
            safe_float(
                profile.get("center")
            ),

        "RIGHT":
            safe_float(
                profile.get("right")
            ),
    }

    return sorted(
        zones.items(),
        key=lambda x: x[1],
        reverse=True,
    )


# ============================================================
# PREMIUM FOOTBALL PITCH
# ============================================================

def draw_defensive_pitch(
    profile,
    team_name,
):

    zone_values = {
        "LEFT":
            safe_float(
                profile.get("left")
            ),

        "CENTER":
            safe_float(
                profile.get("center")
            ),

        "RIGHT":
            safe_float(
                profile.get("right")
            ),
    }

    ranked = sorted(
        zone_values.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    rank_color = {
        0: "#ff3d4d",
        1: "#ff9d2e",
        2: "#ffd83d",
    }

    fig = go.Figure()

    # --------------------------------------------------------
    # PITCH BASE
    # --------------------------------------------------------

    fig.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=100,
        y1=60,
        line=dict(
            color="rgba(255,255,255,.65)",
            width=2,
        ),
        fillcolor="#126b43",
        layer="below",
    )

    # Center line
    fig.add_shape(
        type="line",
        x0=50,
        y0=0,
        x1=50,
        y1=60,
        line=dict(
            color="rgba(255,255,255,.55)",
            width=2,
        ),
    )

    # Center circle
    fig.add_shape(
        type="circle",
        x0=42,
        y0=22,
        x1=58,
        y1=38,
        line=dict(
            color="rgba(255,255,255,.55)",
            width=2,
        ),
    )

    # Center spot
    fig.add_trace(
        go.Scatter(
            x=[50],
            y=[30],
            mode="markers",
            marker=dict(
                size=5,
                color="white",
            ),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # --------------------------------------------------------
    # PENALTY AREA
    # --------------------------------------------------------

    fig.add_shape(
        type="rect",
        x0=72,
        y0=11,
        x1=100,
        y1=49,
        line=dict(
            color="rgba(255,255,255,.60)",
            width=2,
        ),
        fillcolor="rgba(255,255,255,.035)",
    )

    # Six-yard box
    fig.add_shape(
        type="rect",
        x0=88,
        y0=21,
        x1=100,
        y1=39,
        line=dict(
            color="rgba(255,255,255,.60)",
            width=2,
        ),
        fillcolor="rgba(255,255,255,.025)",
    )

    # Goal
    fig.add_shape(
        type="rect",
        x0=98.5,
        y0=24,
        x1=100,
        y1=36,
        line=dict(
            color="#ffffff",
            width=3,
        ),
        fillcolor="rgba(255,255,255,.18)",
    )

    # Penalty spot
    fig.add_trace(
        go.Scatter(
            x=[88],
            y=[30],
            mode="markers",
            marker=dict(
                size=5,
                color="white",
            ),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # --------------------------------------------------------
    # ZONE DIVIDERS
    # --------------------------------------------------------

    for x in [33.33, 66.66]:

        fig.add_shape(
            type="line",
            x0=x,
            y0=0,
            x1=x,
            y1=60,
            line=dict(
                color="rgba(255,255,255,.22)",
                width=1,
                dash="dot",
            ),
        )

    # --------------------------------------------------------
    # ZONE LABELS
    # --------------------------------------------------------

    zone_x = {
        "LEFT": 16.66,
        "CENTER": 50,
        "RIGHT": 83.33,
    }

    for zone, value in zone_values.items():

        fig.add_annotation(

            x=zone_x[zone],
            y=56,

            text=(
                f"<b>{zone}</b>"
                f"<br>"
                f"{value:.0f}/100"
            ),

            showarrow=False,

            font=dict(
                color="white",
                size=13,
            ),

            bgcolor="rgba(0,0,0,.35)",

            bordercolor="rgba(255,255,255,.20)",

            borderwidth=1,

            borderpad=5,
        )

    # --------------------------------------------------------
    # TOP 3 ARROWS
    # --------------------------------------------------------
    #
    # Arrows move from the attacking area toward the team's
    # goal on the right side.
    #
    # #1 = RED
    # #2 = ORANGE
    # #3 = YELLOW
    #
    # --------------------------------------------------------

    for rank, (zone, value) in enumerate(
        ranked[:3]
    ):

        color = rank_color[rank]

        start_x = {
            "LEFT": 15,
            "CENTER": 50,
            "RIGHT": 82,
        }[zone]

        start_y = {
            0: 14,
            1: 30,
            2: 46,
        }[rank]

        # Arrow ends near goal
        end_x = 94

        # Keep the arrow visually aligned
        # with its starting lane.
        end_y = start_y

        fig.add_annotation(

            x=end_x,
            y=end_y,

            ax=start_x,
            ay=start_y,

            xref="x",
            yref="y",
            axref="x",
            ayref="y",

            text="",

            showarrow=True,

            arrowhead=3,

            arrowsize=1.5,

            arrowwidth=5,

            arrowcolor=color,
        )

        # Rank marker
        fig.add_annotation(

            x=start_x,
            y=start_y,

            text=(
                f"<b>#{rank + 1}</b>"
            ),

            showarrow=False,

            font=dict(
                color="#061018",
                size=11,
            ),

            bgcolor=color,

            bordercolor=color,

            borderwidth=1,

            borderpad=4,
        )

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    fig.add_annotation(

        x=50,
        y=-4,

        text=(
            f"<b>{team_name}</b> "
            "— Defensive Opportunity Map"
        ),

        showarrow=False,

        font=dict(
            color="white",
            size=14,
        ),
    )

    # --------------------------------------------------------
    # LAYOUT
    # --------------------------------------------------------

    fig.update_layout(

        height=410,

        margin=dict(
            l=8,
            r=8,
            t=12,
            b=35,
        ),

        paper_bgcolor="rgba(0,0,0,0)",

        plot_bgcolor="#126b43",

        xaxis=dict(
            visible=False,
            range=[0, 100],
            fixedrange=True,
        ),

        yaxis=dict(
            visible=False,
            range=[-7, 60],
            fixedrange=True,
            scaleanchor="x",
            scaleratio=1,
        ),

        showlegend=False,

        hovermode=False,
    )

    return fig


# ============================================================
# VERDICTS
# ============================================================

def verdict_for_player(
    player,
    data,
    purpose="general",
):

    if purpose == "captain":

        score = captain_score(
            player,
            data,
        )

    elif purpose == "differential":

        score = differential_score(
            player,
            data,
        )

    else:

        score = player_radar_score(
            player,
            data,
        )

    risk = risk_score(
        player
    )

    if risk < 25:
        risk_label = "Low"

    elif risk < 55:
        risk_label = "Medium"

    else:
        risk_label = "High"

    if score >= 80:
        confidence = "Very High"

    elif score >= 70:
        confidence = "High"

    elif score >= 60:
        confidence = "Medium"

    else:
        confidence = "Low"

    reasons = []

    if safe_float(
        player["form"]
    ) >= 5:

        reasons.append(
            "strong recent form"
        )

    if safe_float(
        player[
            "expected_goal_involvements_per_90"
        ]
    ) >= .40:

        reasons.append(
            "strong xGI/90"
        )

    if minutes_score(
        player
    ) >= 75:

        reasons.append(
            "good minutes security"
        )

    if fixture_score(
        team_fixture_rows(
            data,
            player["team_id"],
            horizon=3,
        )
    ) >= 65:

        reasons.append(
            "favorable upcoming fixtures"
        )

    if not reasons:
        reasons.append(
            "balanced underlying profile"
        )

    return {

        "score":
            score,

        "risk":
            risk_label,

        "confidence":
            confidence,

        "reason":
            ", ".join(reasons),
    }


def render_verdict(
    main,
    reason,
    confidence="Medium",
    risk="Medium",
    kicker="FPL HOME VERDICT",
):

    st.markdown(
        f"""
        <div class="verdict">

            <div class="verdict-kicker">
                {kicker}
            </div>

            <div class="verdict-main">
                {main}
            </div>

            <div>
                {risk_badge(risk)}

                <span class="badge blue">
                    Confidence: {confidence}
                </span>
            </div>

            <div
                class="subtle"
                style="margin-top:8px"
            >
                {reason}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SEARCH
# ============================================================

def global_search(data):

    st.title("🔎 Search")

    query = st.text_input(
        "Search players or clubs",
        placeholder=(
            "e.g. Salah, Haaland, Liverpool..."
        ),
    ).strip().lower()

    if not query:

        st.info(
            "Search any player or Premier League club."
        )

        return

    players = add_scores(
        data["players"],
        data,
    )

    player_hits = [

        p
        for p in players

        if
        query in p["name"].lower()

        or

        query in p["web_name"].lower()

        or

        query in p["team"].lower()

        or

        query in p["team_short"].lower()

    ][:20]

    if player_hits:

        st.subheader(
            "Players"
        )

        for p in player_hits:

            st.markdown(
                f"""
                <div class="player-card">

                    <b>
                        {p['name']}
                    </b>

                    · {p['team_short']}
                    · {p['position']}

                    <br>

                    <span class="subtle">
                        {money(p['price'])}
                        · Form {p['form']:.1f}
                        · Radar {p['radar_score']:.1f}
                    </span>

                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                f"Open {p['web_name']}",
                key=f"search_{p['id']}",
            ):

                st.session_state[
                    "selected_player_id"
                ] = p["id"]

                st.session_state[
                    "page"
                ] = "Player Profile"

                st.rerun()

    team_hits = [

        t
        for t in data["teams"].values()

        if
        query in t["name"].lower()

        or

        query in t["short_name"].lower()

    ]

    if team_hits:

        st.subheader(
            "Clubs"
        )

        for t in team_hits:

            fs = fixture_score(
                team_fixture_rows(
                    data,
                    t["id"],
                    horizon=5,
                )
            )

            st.markdown(
                f"""
                <div class="player-card">

                    <b>
                        {t['name']}
                    </b>

                    · Fixture Score
                    {fs:.0f}

                    <br>

                    <span class="subtle">
                        {fixture_text(
                            team_fixture_rows(
                                data,
                                t["id"],
                                horizon=5,
                            )
                        )}
                    </span>

                </div>
                """,
                unsafe_allow_html=True,
            )

    if (
        not player_hits
        and
        not team_hits
    ):

        st.warning(
            "No matching player or club found."
        )


# ============================================================
# PLAYER PROFILE
# ============================================================

def player_profile(data):

    st.title(
        "👤 Player Profile"
    )

    players = add_scores(
        data["players"],
        data,
    )

    labels = {

        f"{p['name']} — "
        f"{p['team_short']} — "
        f"{money(p['price'])}":
            p["id"]

        for p in players
    }

    default_id = st.session_state.get(
        "selected_player_id"
    )

    default_index = 0

    if default_id:

        for i, pid in enumerate(
            labels.values()
        ):

            if pid == default_id:

                default_index = i
                break

    selected = st.selectbox(
        "Player",
        list(labels.keys()),
        index=default_index,
    )

    player = next(
        p
        for p in players
        if p["id"] == labels[selected]
    )

    st.session_state[
        "selected_player_id"
    ] = player["id"]

    v = verdict_for_player(
        player,
        data,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Price",
            money(
                player["price"]
            ),
        )

    with c2:
        st.metric(
            "Form",
            f"{player['form']:.1f}",
        )

    with c3:
        st.metric(
            "xGI/90",
            f"{player['expected_goal_involvements_per_90']:.2f}",
        )

    with c4:
        st.metric(
            "Ownership",
            pct(
                player["selected_by"]
            ),
        )

    render_verdict(

        f"{player['name']} — "
        f"Radar {v['score']:.1f}/100",

        (
            f"{v['reason']}. "
            f"Minutes score "
            f"{player['minutes_score']:.0f}/100."
        ),

        v["confidence"],

        v["risk"],
    )

    st.subheader(
        "📊 Core FPL Data"
    )

    core = pd.DataFrame([{

        "Total Points":
            player["total_points"],

        "GW Points":
            player["event_points"],

        "PPG":
            player["points_per_game"],

        "Goals":
            player["goals"],

        "Assists":
            player["assists"],

        "Bonus":
            player["bonus"],

        "BPS":
            player["bps"],

        "Minutes":
            player["minutes"],

        "xG":
            player["expected_goals"],

        "xA":
            player["expected_assists"],

        "xGI":
            player[
                "expected_goal_involvements"
            ],

        "ICT":
            player["ict_index"],
    }])

    st.dataframe(
        core.round(2),
        use_container_width=True,
        hide_index=True,
    )

    fixtures = team_fixture_rows(
        data,
        player["team_id"],
        horizon=5,
    )

    st.subheader(
        "📅 Fixtures"
    )

    st.dataframe(

        pd.DataFrame([{

            "GW":
                f["gw"],

            "Opponent":
                f["opponent"],

            "H/A":
                "H"
                if f["home"]
                else "A",

            "Difficulty":
                f["difficulty"],

        } for f in fixtures]),

        use_container_width=True,

        hide_index=True,
    )

    st.subheader(
        "📰 FPL Status / News"
    )

    if player["news"]:

        st.warning(
            player["news"]
        )

    else:

        st.success(
            "No FPL news supplied by the API."
        )

    if st.button(
        "Load detailed player history",
        use_container_width=True,
    ):

        try:

            summary = load_player_summary(
                int(player["id"])
            )

            histories = summary.get(
                "history",
                [],
            )

            if histories:

                df = pd.DataFrame(
                    histories
                )

                cols = [
                    c
                    for c in [
                        "round",
                        "minutes",
                        "total_points",
                        "goals_scored",
                        "assists",
                        "clean_sheets",
                        "bonus",
                        "bps",
                        "expected_goals",
                        "expected_assists",
                    ]
                    if c in df.columns
                ]

                st.dataframe(
                    df[cols].tail(10),
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info(
                    "No detailed history returned."
                )

        except Exception as exc:

            st.error(
                f"Unable to load player history: {exc}"
            )


# ============================================================
# HOME
# ============================================================

def home(data):

    gw = selected_gameweek(
        data["events"]
    )

    players = add_scores(
        data["players"],
        data,
    )

    active = [
        p
        for p in players
        if p["status"] == "a"
    ]

    captain_rank = sorted(

        [
            p
            for p in active

            if
            p["position"]
            in ["MID", "FWD"]

            and
            p["minutes"] > 250
        ],

        key=lambda p:
            p["captain_score"],

        reverse=True,
    )

    top = captain_rank[:3]

    best_fixture_teams = sorted(

        data["teams"].values(),

        key=lambda t:
            fixture_score(
                team_fixture_rows(
                    data,
                    t["id"],
                    horizon=5,
                )
            ),

        reverse=True,
    )[:3]

    st.markdown(
        f"""
        <div class="topbar">

            <div class="brand">
                ⚽ FPL
                <span>HOME</span>
            </div>

            <div class="subtle">
                Decision Support · GW {gw}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.title(
        "🏠 Home"
    )

    st.caption(
        "Focus on the decisions that matter most this Gameweek."
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-label">
                    GAMEWEEK
                </div>

                <div class="metric-value">
                    GW {gw}
                </div>

                <div class="metric-sub">
                    selected planning point
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-label">
                    PLAYERS
                </div>

                <div class="metric-value">
                    {len(active)}
                </div>

                <div class="metric-sub">
                    active FPL players
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:

        st.markdown(
            """
            <div class="metric-card">

                <div class="metric-label">
                    FPL DATA
                </div>

                <div class="metric-value">
                    LIVE
                </div>

                <div class="metric-sub">
                    public FPL API
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:

        enrichment_count = len(
            get_enrichment()
        )

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-label">
                    ENRICHMENT
                </div>

                <div class="metric-value">
                    {enrichment_count}
                </div>

                <div class="metric-sub">
                    owner data profiles
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="section-title">👑 Captain Decision</div>',
        unsafe_allow_html=True,
    )

    if top:

        safe_pick = top[0]

        upside = sorted(

            top,

            key=lambda p:
                (
                    p[
                        "expected_goal_involvements_per_90"
                    ],

                    p[
                        "differential_score"
                    ],
                ),

            reverse=True,
        )[0]

        col1, col2 = st.columns(2)

        with col1:

            v = verdict_for_player(
                safe_pick,
                data,
                "captain",
            )

            render_verdict(

                f"SAFE PICK · "
                f"{safe_pick['name']}",

                (
                    f"{safe_pick['team_short']} · "
                    f"Captain Score "
                    f"{safe_pick['captain_score']:.1f}. "
                    f"{v['reason']}."
                ),

                v["confidence"],

                v["risk"],

                "SAFE CAPTAIN",
            )

        with col2:

            render_verdict(

                f"HIGH UPSIDE · "
                f"{upside['name']}",

                (
                    f"{upside['team_short']} · "
                    f"xGI/90 "
                    f"{upside['expected_goal_involvements_per_90']:.2f}. "
                    f"Higher upside can come with more variance."
                ),

                "Medium",

                "Medium",

                "HIGH UPSIDE",
            )

    else:

        st.info(
            "Not enough eligible players for a captain recommendation."
        )

    st.markdown(
        '<div class="section-title">🛡️ Defensive Opportunity</div>',
        unsafe_allow_html=True,
    )

    zone_rows = []

    for t in data["teams"].values():

        profile = merged_defensive_profile(
            t,
            data,
        )

        zones = defensive_zone_rank(
            profile
        )

        zone_rows.append({

            "Team":
                t["name"],

            "Top Weak Zone":
                zones[0][0],

            "Vulnerability":
                round(
                    zones[0][1],
                    0,
                ),

            "Data":
                profile["source"],
        })

    zone_df = (
        pd.DataFrame(zone_rows)
        .sort_values(
            "Vulnerability",
            ascending=False,
        )
    )

    st.dataframe(
        zone_df.head(5),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        '<div class="section-title">📅 Fixture Edge</div>',
        unsafe_allow_html=True,
    )

    st.dataframe(

        pd.DataFrame([{

            "Team":
                t["name"],

            "Fixture Score":
                round(
                    fixture_score(
                        team_fixture_rows(
                            data,
                            t["id"],
                            horizon=5,
                        )
                    ),
                    0,
                ),

            "Run":
                fixture_text(
                    team_fixture_rows(
                        data,
                        t["id"],
                        horizon=5,
                    )
                ),

        } for t in best_fixture_teams]),

        use_container_width=True,

        hide_index=True,
    )

    st.markdown(
        """
        <div class="disclaimer">

        Model scores are decision-support signals,
        not predicted FPL points or guarantees.

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# DEFENSIVE RADAR
# ============================================================

def defensive_radar(data):

    st.title(
        "🛡️ Defensive Radar"
    )

    st.caption(
        "Three-zone defensive opportunity map. "
        "Red = highest vulnerability, orange = second, yellow = third."
    )

    teams = data["teams"]

    names = sorted(
        t["name"]
        for t in teams.values()
    )

    selected_name = st.selectbox(
        "Select team",
        names,
    )

    team = next(
        t
        for t in teams.values()
        if t["name"] == selected_name
    )

    profile = merged_defensive_profile(
        team,
        data,
    )

    # --------------------------------------------------------
    # LEGEND
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="pitch-legend">

            <div class="pitch-legend-item">
                <span class="pitch-dot dot-red"></span>
                #1 Highest Opportunity
            </div>

            <div class="pitch-legend-item">
                <span class="pitch-dot dot-orange"></span>
                #2 Highest Opportunity
            </div>

            <div class="pitch-legend-item">
                <span class="pitch-dot dot-yellow"></span>
                #3 Highest Opportunity
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(
        [1.35, 1]
    )

    with c1:

        st.plotly_chart(

            draw_defensive_pitch(
                profile,
                selected_name,
            ),

            use_container_width=True,

            config={
                "displayModeBar": False,
                "responsive": True,
            },
        )

    with c2:

        st.markdown(
            f"""
            <div class="card">

                <div class="section-title">
                    Defensive Signal
                </div>

                <b>Data source:</b>
                {profile['source']}

                <br><br>

                <b>Confidence:</b>
                {profile.get('confidence','')}

                <br><br>

                <b>Overall vulnerability:</b>
                {profile['vulnerability']:.0f}/100

                <br><br>

                <b>Defensive strength:</b>
                {profile['defensive_strength']:.0f}/100

            </div>
            """,
            unsafe_allow_html=True,
        )

        if profile.get("notes"):

            st.info(
                profile["notes"]
            )

    st.subheader(
        "🎯 Top 3 Defensive Opportunity Zones"
    )

    top3 = defensive_zone_rank(
        profile
    )[:3]

    cols = st.columns(3)

    colors = [
        ("red", "🟥"),
        ("orange", "🟧"),
        ("yellow", "🟨"),
    ]

    for index, (
        col,
        item,
    ) in enumerate(
        zip(cols, top3)
    ):

        zone, value = item

        css_class, icon = colors[index]

        with col:

            st.markdown(
                f"""
                <div class="zone-card">

                    <div class="metric-label">
                        {icon} OPPORTUNITY #{index + 1}
                    </div>

                    <div class="metric-value">
                        {zone}
                    </div>

                    <div class="metric-sub">
                        Vulnerability
                        {value:.0f}/100
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    st.warning(
        "Important: if the source is 'FPL API proxy', "
        "LEFT/CENTER/RIGHT values are analytical proxies derived "
        "from FPL team-strength fields. They are not claimed "
        "Opta or StatsBomb event data. Owner-uploaded values "
        "are labeled separately."
    )


# ============================================================
# FIXTURES
# ============================================================

def fixtures_page(data):

    gw = selected_gameweek(
        data["events"]
    )

    st.title(
        "🟢🟡🔴 Fixture Difficulty"
    )

    st.caption(
        f"Fixture analysis starting from GW {gw}. "
        "Lower FPL fixture difficulty means a better fixture."
    )

    rows = []

    for team in data["teams"].values():

        fixtures = team_fixture_rows(
            data,
            team["id"],
            gw=gw,
            horizon=5,
        )

        score = fixture_score(
            fixtures
        )

        swing = fixture_swing(
            data,
            team["id"],
        )

        rows.append({

            "Team":
                team["name"],

            "Score":
                round(score, 1),

            "Verdict":
                fixture_label(score),

            "GW Run":
                fixture_text(fixtures),

            "Swing":
                round(
                    swing["swing"],
                    1,
                ),
        })

    df = (
        pd.DataFrame(rows)
        .sort_values(
            "Score",
            ascending=False,
        )
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader(
        "🔄 Fixture Swing"
    )

    st.caption(
        "Compares the next five fixtures with the following five. "
        "Positive = easier later run."
    )

    st.dataframe(

        df.sort_values(
            "Swing",
            ascending=False,
        )[

            [
                "Team",
                "Score",
                "Swing",
                "GW Run",
            ]
        ],

        use_container_width=True,

        hide_index=True,
    )


# ============================================================
# CAPTAINCY
# ============================================================

def captaincy(data):

    st.title(
        "👑 Captaincy"
    )

    st.caption(
        "Safe Pick + High Upside. "
        "Scores are model signals, not projected points."
    )

    players = add_scores(
        data["players"],
        data,
    )

    eligible = [

        p
        for p in players

        if
        p["status"] == "a"

        and
        p["position"]
        in ["MID", "FWD"]

        and
        p["minutes"] > 250
    ]

    ranked = sorted(
        eligible,
        key=lambda p:
            p["captain_score"],
        reverse=True,
    )

    if not ranked:

        st.warning(
            "No eligible captain candidates."
        )

        return

    safe_pick = ranked[0]

    upside = sorted(

        ranked,

        key=lambda p:

            (
                p[
                    "expected_goal_involvements_per_90"
                ] * .55

                +

                p[
                    "captain_score"
                ] * .25

                +

                (
                    100 -
                    p["selected_by"] * 2
                ) * .20
            ),

        reverse=True,
    )[0]

    c1, c2 = st.columns(2)

    with c1:

        v = verdict_for_player(
            safe_pick,
            data,
            "captain",
        )

        render_verdict(

            f"{safe_pick['name']} · "
            f"{safe_pick['captain_score']:.1f}",

            (
                f"{safe_pick['team_short']} · "
                f"{v['reason']}."
            ),

            v["confidence"],

            v["risk"],

            "SAFE PICK",
        )

    with c2:

        v = verdict_for_player(
            upside,
            data,
            "captain",
        )

        render_verdict(

            f"{upside['name']} · "
            f"{upside['captain_score']:.1f}",

            (
                f"{upside['team_short']} · "
                f"xGI/90 "
                f"{upside['expected_goal_involvements_per_90']:.2f}."
            ),

            v["confidence"],

            v["risk"],

            "HIGH UPSIDE",
        )

    st.subheader(
        "Top captain candidates"
    )

    rows = []

    for i, p in enumerate(
        ranked[:20],
        1,
    ):

        v = verdict_for_player(
            p,
            data,
            "captain",
        )

        rows.append({

            "Rank":
                i,

            "Player":
                p["name"],

            "Team":
                p["team_short"],

            "Fixture":
                fixture_text(
                    team_fixture_rows(
                        data,
                        p["team_id"],
                        horizon=3,
                    ),
                    3,
                ),

            "Price":
                money(p["price"]),

            "Form":
                p["form"],

            "xGI/90":
                round(
                    p[
                        "expected_goal_involvements_per_90"
                    ],
                    2,
                ),

            "Minutes":
                round(
                    p["minutes_score"]
                ),

            "Captain Score":
                round(
                    p["captain_score"],
                    1,
                ),

            "Risk":
                v["risk"],
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# TRANSFER PLANNER
# ============================================================

def transfer_planner(data):

    st.title(
        "🔄 Transfer Planner"
    )

    st.caption(
        "Analyze a squad manually or connect a public FPL Team ID. "
        "No API key is required."
    )

    players = add_scores(
        data["players"],
        data,
    )

    # --------------------------------------------------------
    # OPTIONAL TEAM ID
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="card">

        <b>Optional squad connection</b><br>

        <span class="subtle">
        You can enter your public FPL Team ID here.
        This replaces the old separate My Team tab.
        </span>

        </div>
        """,
        unsafe_allow_html=True,
    )

    team_id_input = st.number_input(
        "FPL Team ID (optional)",
        min_value=0,
        value=int(
            st.session_state.get(
                "fpl_team_id",
                0,
            )
        ),
        step=1,
    )

    if st.button(
        "🔗 Load FPL Squad",
        use_container_width=True,
    ):

        if team_id_input <= 0:

            st.warning(
                "Enter a valid FPL Team ID."
            )

        else:

            try:

                gw = selected_gameweek(
                    data["events"]
                )

                picks = load_fpl_team_picks(
                    int(team_id_input),
                    gw,
                )

                current_ids = {
                    x["element"]
                    for x in picks.get(
                        "picks",
                        [],
                    )
                }

                if current_ids:

                    st.session_state[
                        "fpl_team_id"
                    ] = int(
                        team_id_input
                    )

                    st.session_state[
                        "transfer_current_ids"
                    ] = current_ids

                    st.success(
                        f"Loaded {len(current_ids)} "
                        f"players from GW {gw}."
                    )

                else:

                    st.warning(
                        "No squad players were returned."
                    )

            except Exception as exc:

                st.error(
                    f"Could not load squad: {exc}"
                )

    current_ids = set(
        st.session_state.get(
            "transfer_current_ids",
            set(),
        )
    )

    labels = {

        f"{p['name']} — "
        f"{p['team_short']} — "
        f"{money(p['price'])}":
            p["id"]

        for p in players

        if p["status"] == "a"
    }

    if not current_ids:

        selected = st.multiselect(
            "Your current squad",
            list(labels.keys()),
            max_selections=15,
        )

        current_ids = {
            labels[x]
            for x in selected
        }

    free_transfers = st.number_input(
        "Free Transfers",
        1,
        5,
        1,
    )

    bank = st.number_input(
        "Money in Bank (£m)",
        0.0,
        20.0,
        0.0,
        .1,
    )

    if not current_ids:

        st.info(
            "Connect your FPL Team ID or select your squad manually."
        )

        return

    current = [

        p
        for p in players
        if p["id"] in current_ids
    ]

    out_candidates = sorted(
        current,
        key=lambda p:
            p["radar_score"],
    )

    st.subheader(
        "🔻 Suggested OUT"
    )

    st.dataframe(

        pd.DataFrame([{

            "Player":
                p["name"],

            "Team":
                p["team_short"],

            "Price":
                money(p["price"]),

            "Radar":
                round(
                    p["radar_score"],
                    1,
                ),

            "Risk":
                (
                    "Low"
                    if p["risk_score"] < 25
                    else
                    "Medium"
                    if p["risk_score"] < 55
                    else
                    "High"
                ),

        } for p in out_candidates]),

        use_container_width=True,

        hide_index=True,
    )

    candidates = [

        p
        for p in players

        if
        p["status"] == "a"

        and
        p["id"] not in current_ids
    ]

    suggestions = []

    for out_player in out_candidates[:5]:

        max_price = (
            out_player["price"]
            +
            bank
        )

        same_pos = [

            p
            for p in candidates

            if
            p["position"]
            ==
            out_player["position"]

            and
            p["price"]
            <=
            max_price
        ]

        for candidate in sorted(

            same_pos,

            key=lambda p:
                p["radar_score"],

            reverse=True,

        )[:5]:

            gain = (
                candidate["radar_score"]
                -
                out_player["radar_score"]
            )

            if gain > 0:

                suggestions.append({

                    "OUT":
                        out_player["name"],

                    "IN":
                        candidate["name"],

                    "Position":
                        candidate["position"],

                    "Price":
                        money(
                            candidate["price"]
                        ),

                    "Radar Gain":
                        round(
                            gain,
                            1,
                        ),

                    "IN Radar":
                        round(
                            candidate[
                                "radar_score"
                            ],
                            1,
                        ),

                    "Risk":
                        (
                            "Low"
                            if candidate["risk_score"] < 25
                            else
                            "Medium"
                            if candidate["risk_score"] < 55
                            else
                            "High"
                        ),
                })

    suggestions.sort(
        key=lambda x:
            x["Radar Gain"],
        reverse=True,
    )

    st.subheader(
        "🔺 Suggested IN"
    )

    if suggestions:

        st.dataframe(
            pd.DataFrame(
                suggestions[:20]
            ),
            use_container_width=True,
            hide_index=True,
        )

        best = suggestions[0]

        render_verdict(

            f"{best['OUT']} → "
            f"{best['IN']}",

            (
                f"Model Radar gain "
                f"+{best['Radar Gain']:.1f}. "
                f"This is decision support, "
                f"not a guarantee."
            ),

            "Medium",

            best["Risk"],

            "TRANSFER IDEA",
        )

    else:

        st.info(
            "No positive-Radar upgrade found "
            "under the current budget constraints."
        )

    st.caption(
        f"Free transfers selected: "
        f"{free_transfers}. "
        "The planner does not pretend to know future points."
    )


# ============================================================
# TEAM OPTIMIZER
# ============================================================

def team_optimizer(data):

    st.title(
        "🧠 Team Optimizer"
    )

    budget = st.number_input(
        "Total squad budget (£m)",
        50.0,
        120.0,
        100.0,
        .1,
    )

    strategy = st.selectbox(
        "Strategy",
        [
            "Safe",
            "Balanced",
            "Differential",
        ],
    )

    ownership_weight = {

        "Safe":
            .20,

        "Balanced":
            .10,

        "Differential":
            -.05,

    }[strategy]

    players = add_scores(
        data["players"],
        data,
    )

    for p in players:

        ownership_component = clamp(
            p["selected_by"] * 4,
            0,
            100,
        )

        p["optimizer_score"] = (

            p["radar_score"] * .80

            +

            ownership_component
            * ownership_weight
        )

    requirements = {

        "GKP":
            2,

        "DEF":
            5,

        "MID":
            5,

        "FWD":
            3,
    }

    selected = []

    team_counts = {}

    remaining = budget

    for pos, count_needed in requirements.items():

        pool = sorted(

            [

                p
                for p in players

                if
                p["position"] == pos

                and
                p["status"] == "a"

                and
                p["minutes"] > 100
            ],

            key=lambda x:
                x["optimizer_score"],

            reverse=True,
        )

        count = 0

        for p in pool:

            if count >= count_needed:
                break

            if remaining - p["price"] < 0:
                continue

            if team_counts.get(
                p["team_id"],
                0,
            ) >= 3:

                continue

            selected.append(
                p
            )

            remaining -= p["price"]

            team_counts[
                p["team_id"]
            ] = (
                team_counts.get(
                    p["team_id"],
                    0,
                )
                + 1
            )

            count += 1

    st.subheader(
        "Recommended Squad"
    )

    st.dataframe(

        pd.DataFrame([{

            "Player":
                p["name"],

            "Team":
                p["team_short"],

            "Pos":
                p["position"],

            "Price":
                money(p["price"]),

            "Score":
                round(
                    p["optimizer_score"],
                    1,
                ),

            "Ownership":
                pct(
                    p["selected_by"]
                ),

        } for p in selected]),

        use_container_width=True,

        hide_index=True,
    )

    total = sum(
        p["price"]
        for p in selected
    )

    st.metric(
        "Squad Cost",
        f"£{total:.1f}m",
        f"£{budget-total:.1f}m remaining",
    )

    if len(selected) < 15:

        st.warning(
            "The transparent greedy optimizer "
            "could not fill all 15 slots under "
            "the selected budget/team constraints. "
            "It will not pretend the squad is valid."
        )

    st.caption(
        "Transparent heuristic optimizer. "
        "It can later be replaced with an exact ILP/OR-Tools solver."
    )


# ============================================================
# GEMINI
# ============================================================

def get_gemini_client():

    if not GEMINI_AVAILABLE:

        return (
            None,
            "google-genai is not installed.",
        )

    key = get_secret(
        "GEMINI_API_KEY"
    )

    if not key:

        return (
            None,
            "GEMINI_API_KEY is not configured in Streamlit Secrets.",
        )

    try:

        return (
            genai.Client(
                api_key=key
            ),
            None,
        )

    except Exception as exc:

        return (
            None,
            str(exc),
        )


def build_ai_context(data):

    players = add_scores(
        data["players"],
        data,
    )

    top = sorted(

        players,

        key=lambda p:
            p["radar_score"],

        reverse=True,
    )[:40]

    player_context = []

    for p in top:

        player_context.append({

            "id":
                p["id"],

            "name":
                p["name"],

            "team":
                p["team_short"],

            "position":
                p["position"],

            "price":
                round(
                    p["price"],
                    1,
                ),

            "ownership":
                round(
                    p["selected_by"],
                    1,
                ),

            "form":
                round(
                    p["form"],
                    2,
                ),

            "xgi90":
                round(
                    p[
                        "expected_goal_involvements_per_90"
                    ],
                    2,
                ),

            "minutes_score":
                round(
                    p["minutes_score"],
                    1,
                ),

            "radar":
                round(
                    p["radar_score"],
                    1,
                ),

            "captain":
                round(
                    p["captain_score"],
                    1,
                ),

            "risk":
                round(
                    p["risk_score"],
                    1,
                ),
        })

    team_context = []

    for team in data["teams"].values():

        fixtures = team_fixture_rows(
            data,
            team["id"],
            horizon=5,
        )

        team_context.append({

            "team":
                team["name"],

            "short":
                team["short_name"],

            "fixture_score":
                round(
                    fixture_score(
                        fixtures
                    ),
                    1,
                ),

            "fixtures": [

                {

                    "gw":
                        f["gw"],

                    "opp":
                        f["opponent"],

                    "home":
                        f["home"],

                    "difficulty":
                        f["difficulty"],
                }

                for f in fixtures
            ],

            "defensive_enrichment":
                merged_defensive_profile(
                    team,
                    data,
                ),
        })

    return {

        "gameweek":
            selected_gameweek(
                data["events"]
            ),

        "top_players":
            player_context,

        "teams":
            team_context,

        "linked_team_id":
            st.session_state.get(
                "fpl_team_id"
            ),
    }


def ai_answer(
    question,
    data,
):

    client, error = get_gemini_client()

    if error:
        return error

    context = build_ai_context(
        data
    )

    prompt = f"""

You are Ask FPL HOME,
an expert Fantasy Premier League
decision-support assistant.

DATA RULES:

1. FPL API data is the authoritative
   source for core FPL numbers.

2. Owner enrichment is optional and
   must be described as owner-supplied
   enrichment.

3. Gemini is NOT a source of FPL numbers.

4. Never invent:
   prices,
   ownership,
   fixtures,
   points,
   historical values.

5. If a number is absent,
   say that it is unavailable.

6. Clearly distinguish model scores
   from actual FPL points.

7. Give a practical verdict.

8. Explain why.

9. Mention risk.

10. Provide an alternative when useful.

11. Never claim a recommendation
    guarantees points.

QUESTION:

{question}

STRUCTURED DATA:

{json.dumps(
    context,
    ensure_ascii=False,
)}

Return:

Verdict
Why
Risk
Alternative
"""

    try:

        response = client.models.generate_content(

            model=GEMINI_MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(

                temperature=0.2,

                max_output_tokens=1000,
            ),
        )

        return response.text

    except Exception as exc:

        return f"Gemini error: {exc}"


# ============================================================
# ASK FPL HOME
# ============================================================

def ask_fpl_home(data):

    st.title(
        "🤖 Ask FPL HOME"
    )

    st.caption(
        "AI interpretation of FPL HOME's structured data. "
        "Gemini does not create the underlying FPL numbers."
    )

    if (
        "chat_history"
        not in st.session_state
    ):

        st.session_state[
            "chat_history"
        ] = []

    for msg in st.session_state[
        "chat_history"
    ]:

        with st.chat_message(
            msg["role"]
        ):

            st.markdown(
                msg["content"]
            )

    question = st.chat_input(
        "e.g. Salah or Haaland captain this GW?"
    )

    if question:

        st.session_state[
            "chat_history"
        ].append({

            "role":
                "user",

            "content":
                question,
        })

        with st.chat_message(
            "user"
        ):

            st.markdown(
                question
            )

        with st.chat_message(
            "assistant"
        ):

            with st.spinner(
                "Ask FPL HOME is analyzing..."
            ):

                answer = ai_answer(
                    question,
                    data,
                )

            st.markdown(
                answer
            )

        st.session_state[
            "chat_history"
        ].append({

            "role":
                "assistant",

            "content":
                answer,
        })


# ============================================================
# OWNER AUTHENTICATION
# ============================================================

def owner_unlock():

    configured = bool(
        get_secret(
            "OWNER_PASSWORD"
        )
    )

    if not configured:

        st.error(
            "OWNER_PASSWORD is missing from Streamlit Secrets."
        )

        st.info(
            "Data Center remains locked until OWNER_PASSWORD is configured."
        )

        return False

    if st.session_state.get(
        "owner_unlocked"
    ):

        return True

    password = st.text_input(
        "Owner password",
        type="password",
    )

    if st.button(
        "🔐 Unlock Data Center",
        use_container_width=True,
    ):

        if (
            password
            ==
            get_secret(
                "OWNER_PASSWORD"
            )
        ):

            st.session_state[
                "owner_unlocked"
            ] = True

            st.success(
                "Owner access enabled for this session."
            )

            st.rerun()

        else:

            st.error(
                "Incorrect password."
            )

    return st.session_state.get(
        "owner_unlocked",
        False,
    )


# ============================================================
# GEMINI IMAGE EXTRACTION
# ============================================================

def gemini_image_to_structured(
    uploaded_file,
    team_hint=None,
    gw_hint=None,
):

    client, error = get_gemini_client()

    if error:

        return (
            None,
            error,
        )

    image_bytes = (
        uploaded_file.getvalue()
    )

    mime = (
        uploaded_file.type
        or
        "image/jpeg"
    )

    schema = {

        "team_name":
            "string or null",

        "team_id":
            "integer or null",

        "gameweek":
            "integer or null",

        "left_vulnerability":
            "number 0-100 or null",

        "center_vulnerability":
            "number 0-100 or null",

        "right_vulnerability":
            "number 0-100 or null",

        "overall_vulnerability":
            "number 0-100 or null",

        "defensive_strength":
            "number 0-100 or null",

        "source_label":
            "string",

        "confidence":
            "High/Medium/Low/Unknown",

        "notes":
            "string",
    }

    prompt = f"""

You are the data extraction layer
inside FPL HOME.

Analyze ONLY the uploaded image.

Convert visible defensive/tactical
information into structured JSON.

IMPORTANT:

This is OWNER-SUPPLIED DATA ENRICHMENT.

Do not invent values.

If a value is not visible,
return null.

Do not infer a number from general
football knowledge.

Preserve the source label
if visible.

Team hint:
{team_hint or "none"}

Gameweek hint:
{gw_hint or "none"}

Return JSON matching this schema:

{json.dumps(
    schema,
    indent=2,
)}

"""

    try:

        response = client.models.generate_content(

            model=GEMINI_MODEL,

            contents=[

                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime,
                ),

                prompt,
            ],

            config=types.GenerateContentConfig(

                temperature=0,

                response_mime_type=
                    "application/json",
            ),
        )

        return (
            json.loads(
                response.text
            ),
            None,
        )

    except Exception as exc:

        return (
            None,
            str(exc),
        )


# ============================================================
# DATA CENTER
# ============================================================

def data_center(data):

    st.markdown(
        """
        <div class="admin-header">

            <div class="admin-title">
                🗄️ FPL HOME Data Center
            </div>

            <div class="admin-subtitle">
                Owner-only data enrichment center.
                Upload screenshots, let Gemini extract
                visible tactical data, review it,
                then publish it into FPL HOME.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    if not owner_unlock():
        return

    st.success(
        "Owner mode is active for this browser session."
    )

    # --------------------------------------------------------
    # DATA CONTRACT
    # --------------------------------------------------------

    st.subheader(
        "📚 Data Architecture"
    )

    st.markdown(
        """
        <div class="card">

        <b>FPL API</b><br>
        Core FPL numbers, players, teams,
        fixtures and official API fields.

        <br><br>

        <b>Owner Enrichment</b><br>
        Additional defensive/tactical information
        supplied through owner screenshots.

        <br><br>

        <b>Gemini</b><br>
        Reads the uploaded image and extracts
        visible information. Gemini does not replace
        the FPL API and does not create core FPL numbers.

        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    st.subheader(
        "📸 1. Upload Image"
    )

    team_names = sorted(
        t["name"]
        for t in data["teams"].values()
    )

    team_name = st.selectbox(
        "Team represented in the image",
        team_names,
    )

    team = next(
        t
        for t in data["teams"].values()
        if t["name"] == team_name
    )

    gw_default = selected_gameweek(
        data["events"]
    )

    gw = st.number_input(
        "Gameweek represented",
        min_value=1,
        max_value=50,
        value=gw_default,
    )

    uploaded = st.file_uploader(

        "Upload defensive / tactical screenshot",

        type=[
            "png",
            "jpg",
            "jpeg",
            "webp",
        ],

        accept_multiple_files=False,
    )

    if uploaded:

        st.image(
            uploaded,
            caption="Uploaded source image",
            use_container_width=True,
        )

    if uploaded:

        if st.button(
            "🤖 2. Analyze Image with Gemini",
            use_container_width=True,
        ):

            with st.spinner(
                "Gemini is extracting visible structured data..."
            ):

                result, error = (
                    gemini_image_to_structured(
                        uploaded,
                        team_name,
                        gw,
                    )
                )

            if error:

                st.error(
                    error
                )

            else:

                st.session_state[
                    "last_extracted_enrichment"
                ] = result

                st.session_state[
                    "last_extracted_team_id"
                ] = team["id"]

                st.session_state[
                    "last_extracted_gw"
                ] = gw

                st.success(
                    "Image analyzed successfully."
                )

    # --------------------------------------------------------
    # REVIEW
    # --------------------------------------------------------

    extracted = st.session_state.get(
        "last_extracted_enrichment"
    )

    if extracted:

        st.divider()

        st.subheader(
            "✏️ 3. Review & Edit"
        )

        st.warning(
            "Review every value before publishing. "
            "The extracted information is owner enrichment "
            "and should not be treated as core FPL API truth."
        )

        st.json(
            extracted
        )

        editable = {

            "left":
                (
                    safe_float(
                        extracted.get(
                            "left_vulnerability"
                        )
                    )
                    if extracted.get(
                        "left_vulnerability"
                    )
                    is not None
                    else None
                ),

            "center":
                (
                    safe_float(
                        extracted.get(
                            "center_vulnerability"
                        )
                    )
                    if extracted.get(
                        "center_vulnerability"
                    )
                    is not None
                    else None
                ),

            "right":
                (
                    safe_float(
                        extracted.get(
                            "right_vulnerability"
                        )
                    )
                    if extracted.get(
                        "right_vulnerability"
                    )
                    is not None
                    else None
                ),

            "vulnerability":
                (
                    safe_float(
                        extracted.get(
                            "overall_vulnerability"
                        )
                    )
                    if extracted.get(
                        "overall_vulnerability"
                    )
                    is not None
                    else None
                ),

            "defensive_strength":
                (
                    safe_float(
                        extracted.get(
                            "defensive_strength"
                        )
                    )
                    if extracted.get(
                        "defensive_strength"
                    )
                    is not None
                    else None
                ),
        }

        cols = st.columns(5)

        keys = [

            "left",

            "center",

            "right",

            "vulnerability",

            "defensive_strength",
        ]

        for col, key in zip(
            cols,
            keys,
        ):

            with col:

                editable[key] = st.number_input(

                    key.replace(
                        "_",
                        " ",
                    ).title(),

                    min_value=0.0,

                    max_value=100.0,

                    value=float(
                        editable[key]
                        if editable[key]
                        is not None
                        else 0
                    ),

                    step=1.0,

                    key=f"edit_{key}",
                )

        notes = st.text_area(

            "Owner notes",

            extracted.get(
                "notes",
                "",
            ),

            key="edit_notes",
        )

        source_label = st.text_input(

            "Source label",

            extracted.get(
                "source_label",
                "Owner-uploaded image",
            ),

            key="edit_source_label",
        )

        confidence = st.selectbox(

            "Confidence",

            [
                "High",
                "Medium",
                "Low",
                "Unknown",
            ],

            index=(
                [
                    "High",
                    "Medium",
                    "Low",
                    "Unknown",
                ].index(
                    extracted.get(
                        "confidence",
                        "Unknown",
                    )
                )
                if extracted.get(
                    "confidence",
                    "Unknown",
                )
                in [
                    "High",
                    "Medium",
                    "Low",
                    "Unknown",
                ]
                else 3
            ),

            key="edit_confidence",
        )

        # ----------------------------------------------------
        # PUBLISH
        # ----------------------------------------------------

        if st.button(
            "✅ 4. Publish Enrichment",
            use_container_width=True,
        ):

            enrichment = get_enrichment()

            enrichment[
                str(team["id"])
            ] = {

                **editable,

                "source":
                    source_label
                    or
                    "Owner-uploaded image",

                "confidence":
                    confidence,

                "notes":
                    notes,

                "gw":
                    int(gw),

                "updated":
                    utc_now(),

                "owner_enrichment":
                    True,
            }

            set_enrichment(
                enrichment
            )

            st.success(
                f"Defensive enrichment published for {team_name}."
            )

            st.session_state[
                "last_extracted_enrichment"
            ] = None

            st.rerun()

    # --------------------------------------------------------
    # CURRENT PUBLISHED DATA
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "📋 Published Enrichment"
    )

    enrichment = get_enrichment()

    if enrichment:

        rows = []

        for tid, item in enrichment.items():

            team_item = data["teams"].get(
                int(tid),
                {},
            )

            rows.append({

                "Team":
                    team_item.get(
                        "name",
                        tid,
                    ),

                "GW":
                    item.get(
                        "gw"
                    ),

                "Left":
                    item.get(
                        "left"
                    ),

                "Center":
                    item.get(
                        "center"
                    ),

                "Right":
                    item.get(
                        "right"
                    ),

                "Overall":
                    item.get(
                        "vulnerability"
                    ),

                "Source":
                    item.get(
                        "source"
                    ),

                "Confidence":
                    item.get(
                        "confidence"
                    ),

                "Updated":
                    item.get(
                        "updated",
                        "",
                    ),
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No owner enrichment has been published in this session."
        )

    # --------------------------------------------------------
    # CLEAR
    # --------------------------------------------------------

    if st.button(
        "🗑️ Clear all session enrichment",
        use_container_width=True,
    ):

        st.session_state[
            "defensive_enrichment"
        ] = {}

        st.success(
            "All session enrichment cleared."
        )

        st.rerun()

    st.markdown(
        """
        <div class="disclaimer">

        Note: Published enrichment currently lives in the
        active Streamlit session. It is not automatically
        persisted to a permanent database.

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# DATA HEALTH
# ============================================================

def data_health_page(
    data,
    api_ok=True,
):

    st.title(
        "🩺 Data Health"
    )

    st.caption(
        "Transparent view of which layer supplies each data type."
    )

    rows = [

        {

            "Layer":
                "FPL API",

            "Role":
                "Core FPL numbers, players, teams, fixtures",

            "Status":
                (
                    "Connected"
                    if api_ok
                    else
                    "Error"
                ),

            "API Key":
                "Not required",
        },

        {

            "Layer":
                "Owner enrichment",

            "Role":
                "Optional defensive/tactical enrichment from images",

            "Status":
                (
                    f"{len(get_enrichment())} "
                    "team profiles"
                    if get_enrichment()
                    else
                    "None"
                ),

            "API Key":
                "Owner only",
        },

        {

            "Layer":
                "Gemini",

            "Role":
                "Image interpretation + AI explanation",

            "Status":
                (
                    "Configured"
                    if get_secret(
                        "GEMINI_API_KEY"
                    )
                    else
                    "Not configured"
                ),

            "API Key":
                "Streamlit Secrets only",
        },
    ]

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Teams",
        len(
            data["teams"]
        ),
    )

    c2.metric(
        "Players",
        len(
            data["players"]
        ),
    )

    c3.metric(
        "Fixtures",
        len(
            data["fixtures"]
        ),
    )

    st.subheader(
        "Rules"
    )

    st.markdown(
        """
        - **FPL API = source of core FPL numbers**
        - **Owner uploads = enrichment only**
        - **Gemini = image interpretation / extraction**
        - **Gemini does not replace FPL API**
        - **Normal users do not upload data**
        - **Normal users do not provide API keys**
        - **No invented historical prices**
        """
    )


# ============================================================
# NAVIGATION
# ============================================================

NAV_ITEMS = {

    "🏠 Home":
        "Home",

    "🔎 Search":
        "Search",

    "👤 Player":
        "Player Profile",

    "🛡️ Defensive Radar":
        "Defensive Radar",

    "📅 Fixtures":
        "Fixtures",

    "👑 Captaincy":
        "Captaincy",

    "🔄 Transfers":
        "Transfer Planner",

    "🧠 Optimizer":
        "Team Optimizer",

    "🤖 Ask FPL HOME":
        "Ask FPL HOME",

    "🗄️ Data Center":
        "Data Center",

    "🩺 Data Health":
        "Data Health",
}


def top_navigation(data):

    labels = list(
        NAV_ITEMS.keys()
    )

    current_page = (
        st.session_state.get(
            "page",
            "Home",
        )
    )

    default_idx = 0

    for i, value in enumerate(
        NAV_ITEMS.values()
    ):

        if value == current_page:

            default_idx = i
            break

    nav = st.radio(

        "Navigation",

        labels,

        index=default_idx,

        horizontal=True,

        label_visibility="collapsed",
    )

    st.session_state[
        "page"
    ] = NAV_ITEMS[nav]

    # --------------------------------------------------------
    # GLOBAL GAMEWEEK
    # --------------------------------------------------------

    gw_options = [

        e["id"]
        for e in data["events"]
        if e.get("id") is not None
    ]

    default_gw = selected_gameweek(
        data["events"]
    )

    if gw_options:

        default_index = (

            gw_options.index(
                default_gw
            )

            if default_gw
            in gw_options

            else 0
        )

        selected_gw = st.selectbox(

            "Gameweek",

            gw_options,

            index=default_index,

            key="global_gw_selector",
        )

        st.session_state[
            "selected_gw"
        ] = selected_gw


# ============================================================
# MAIN
# ============================================================

def main():

    raw, ok, error = (
        load_data_with_status()
    )

    if not ok:

        st.error(
            "❌ Unable to load FPL API data."
        )

        st.code(
            str(error)
        )

        if st.button(
            "🔄 Retry"
        ):

            st.cache_data.clear()

            st.rerun()

        return

    data = normalize_data(
        raw
    )

    top_navigation(
        data
    )

    # --------------------------------------------------------
    # GLOBAL REFRESH
    # --------------------------------------------------------

    col1, col2 = st.columns(
        [5, 1]
    )

    with col2:

        if st.button(
            "↻ Refresh"
        ):

            st.cache_data.clear()

            st.rerun()

    page = st.session_state.get(
        "page",
        "Home",
    )

    # --------------------------------------------------------
    # ROUTING
    # --------------------------------------------------------

    if page == "Home":

        home(data)

    elif page == "Search":

        global_search(data)

    elif page == "Player Profile":

        player_profile(data)

    elif page == "Defensive Radar":

        defensive_radar(data)

    elif page == "Fixtures":

        fixtures_page(data)

    elif page == "Captaincy":

        captaincy(data)

    elif page == "Transfer Planner":

        transfer_planner(data)

    elif page == "Team Optimizer":

        team_optimizer(data)

    elif page == "Ask FPL HOME":

        ask_fpl_home(data)

    elif page == "Data Center":

        data_center(data)

    elif page == "Data Health":

        data_health_page(
            data,
            api_ok=True,
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
ملاحظة مهمة: في النسخة دي Data Center يحفظ الـ enrichment داخل Session الحالية مثل الكود القديم، يعني لو التطبيق اتعمل له restart البيانات المنشورة في الجلسة تختفي. ده مقصود حاليًا حتى ما نضيفش Database أو ملفات دائمة من غير ما نتفق عليها.
