# ============================================================
# FPL RADAR PRO
# Ultimate Fantasy Premier League Analytics
# Single-file Streamlit Application
# ============================================================

import os
import json
import math
from datetime import datetime
from typing import Dict, List, Any, Optional

import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Gemini
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "FPL Radar"
APP_VERSION = "3.0"

FPL_BASE = "https://fantasy.premierleague.com/api"

BOOTSTRAP_URL = f"{FPL_BASE}/bootstrap-static/"
FIXTURES_URL = f"{FPL_BASE}/fixtures/"

REQUEST_TIMEOUT = 20

GEMINI_MODEL = "gemini-3.8-flash"

CACHE_TTL = 300


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="FPL Radar",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

html, body, [class*="css"] {
    font-family: Inter, Arial, sans-serif;
}

.main {
    background:
        radial-gradient(circle at top left, rgba(48, 96, 160, .12), transparent 30%),
        #070b12;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* Sidebar */

section[data-testid="stSidebar"] {
    background: #090e17;
    border-right: 1px solid #182231;
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 1.2rem;
}

/* Cards */

.radar-card {
    background: linear-gradient(145deg, #101722, #0b1018);
    border: 1px solid #1d2a3a;
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 14px;
    box-shadow: 0 8px 30px rgba(0,0,0,.20);
}

.radar-card h3 {
    margin-top: 0;
}

.metric-card {
    background: #0e151f;
    border: 1px solid #1d2a3a;
    border-radius: 16px;
    padding: 16px;
    min-height: 110px;
}

.metric-label {
    color: #8e9aab;
    font-size: 13px;
}

.metric-value {
    font-size: 28px;
    font-weight: 800;
    margin-top: 5px;
}

.metric-sub {
    color: #6f7d90;
    font-size: 12px;
}

/* Verdict */

.verdict {
    border-radius: 18px;
    padding: 20px;
    background:
        linear-gradient(135deg, rgba(20, 135, 100, .18), rgba(10, 20, 30, .95));
    border: 1px solid #205744;
}

.verdict-title {
    font-size: 14px;
    letter-spacing: 1px;
    font-weight: 800;
    color: #74e0bd;
}

.verdict-main {
    font-size: 25px;
    font-weight: 900;
    margin-top: 6px;
}

.verdict-text {
    color: #aab5c4;
    margin-top: 7px;
}

/* Badges */

.badge {
    display: inline-block;
    padding: 4px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
    margin-right: 5px;
}

.badge-green {
    background: rgba(45, 180, 130, .16);
    color: #6ee7bd;
}

.badge-yellow {
    background: rgba(220, 170, 50, .16);
    color: #f2ca67;
}

.badge-red {
    background: rgba(220, 75, 80, .16);
    color: #ff9296;
}

/* Player rows */

.player-row {
    background: #0d141e;
    border: 1px solid #1b2736;
    border-radius: 14px;
    padding: 13px;
    margin-bottom: 8px;
}

/* Mobile */

@media (max-width: 768px) {

    .block-container {
        padding-left: .75rem;
        padding-right: .75rem;
    }

    .metric-card {
        min-height: 90px;
    }

    .metric-value {
        font-size: 22px;
    }

    .verdict-main {
        font-size: 21px;
    }

    h1 {
        font-size: 28px !important;
    }

    h2 {
        font-size: 23px !important;
    }

    h3 {
        font-size: 18px !important;
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
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def pct(value):
    return f"{safe_float(value):.1f}%"


def money(value):
    return f"£{safe_float(value):.1f}m"


def badge_html(risk):
    risk = str(risk)

    if risk.lower() == "low":
        cls = "badge-green"
    elif risk.lower() == "medium":
        cls = "badge-yellow"
    else:
        cls = "badge-red"

    return f'<span class="badge {cls}">{risk}</span>'


# ============================================================
# FPL DATA ENGINE
# ============================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_json(url: str):
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={
            "User-Agent": "FPL-Radar/3.0"
        },
    )

    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_fpl_data():

    bootstrap = fetch_json(BOOTSTRAP_URL)
    fixtures = fetch_json(FIXTURES_URL)

    return {
        "bootstrap": bootstrap,
        "fixtures": fixtures,
        "updated": datetime.now().isoformat(),
    }


def load_data_with_status():

    try:
        data = load_fpl_data()

        return data, True, None

    except Exception as e:

        return None, False, str(e)


# ============================================================
# DATA NORMALIZATION
# ============================================================

def normalize_data(data):

    bootstrap = data["bootstrap"]

    teams_raw = bootstrap.get("teams", [])
    players_raw = bootstrap.get("elements", [])
    events_raw = bootstrap.get("events", [])
    positions_raw = bootstrap.get("element_types", [])

    teams = {}

    for t in teams_raw:

        teams[t["id"]] = {
            "id": t["id"],
            "name": t.get("name", ""),
            "short_name": t.get("short_name", ""),
            "code": t.get("code", 0),

            "strength": safe_float(t.get("strength")),
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
        p["id"]: p.get("singular_name_short", "")
        for p in positions_raw
    }

    players = []

    for p in players_raw:

        team_id = p.get("team")

        team = teams.get(
            team_id,
            {
                "name": "Unknown",
                "short_name": "UNK",
            },
        )

        player = {

            "id": p.get("id"),

            "name": (
                f"{p.get('first_name', '')} "
                f"{p.get('second_name', '')}"
            ).strip(),

            "web_name": p.get("web_name", ""),

            "team_id": team_id,
            "team": team.get("name", ""),
            "team_short": team.get("short_name", ""),

            "position": positions.get(
                p.get("element_type"),
                "?"
            ),

            "price": safe_float(
                p.get("now_cost", 0)
            ) / 10,

            "total_points": safe_float(
                p.get("total_points")
            ),

            "event_points": safe_float(
                p.get("event_points")
            ),

            "form": safe_float(
                p.get("form")
            ),

            "points_per_game": safe_float(
                p.get("points_per_game")
            ),

            "selected_by": safe_float(
                p.get("selected_by_percent")
            ),

            "minutes": safe_float(
                p.get("minutes")
            ),

            "goals": safe_float(
                p.get("goals_scored")
            ),

            "assists": safe_float(
                p.get("assists")
            ),

            "clean_sheets": safe_float(
                p.get("clean_sheets")
            ),

            "goals_conceded": safe_float(
                p.get("goals_conceded")
            ),

            "saves": safe_float(
                p.get("saves")
            ),

            "bonus": safe_float(
                p.get("bonus")
            ),

            "bps": safe_float(
                p.get("bps")
            ),

            "influence": safe_float(
                p.get("influence")
            ),

            "creativity": safe_float(
                p.get("creativity")
            ),

            "threat": safe_float(
                p.get("threat")
            ),

            "ict_index": safe_float(
                p.get("ict_index")
            ),

            "expected_goals": safe_float(
                p.get("expected_goals")
            ),

            "expected_assists": safe_float(
                p.get("expected_assists")
            ),

            "expected_goal_involvements": safe_float(
                p.get("expected_goal_involvements")
            ),

            "expected_goals_per_90": safe_float(
                p.get("expected_goals_per_90")
            ),

            "expected_assists_per_90": safe_float(
                p.get("expected_assists_per_90")
            ),

            "expected_goal_involvements_per_90": safe_float(
                p.get("expected_goal_involvements_per_90")
            ),

            "chance_next_round": safe_float(
                p.get("chance_of_playing_next_round"),
                100
            ),

            "chance_this_round": safe_float(
                p.get("chance_of_playing_this_round"),
                100
            ),

            "status": p.get("status", "a"),

            "news": p.get("news", ""),

            "starts": safe_float(
                p.get("starts")
            ),

            "clean_sheets_per_90": safe_float(
                p.get("clean_sheets_per_90")
            ),

            "form_rank": safe_float(
                p.get("form_rank")
            ),

            "points_per_game_rank": safe_float(
                p.get("points_per_game_rank")
            ),
        }

        players.append(player)

    events = []

    for e in events_raw:

        events.append(
            {
                "id": e.get("id"),
                "name": e.get("name"),
                "deadline": e.get("deadline_time"),
                "finished": e.get("finished"),
                "is_current": e.get("is_current"),
                "is_next": e.get("is_next"),
                "is_previous": e.get("is_previous"),
                "average_score": e.get("average_entry_score"),
                "highest_score": e.get("highest_score"),
                "most_captained": e.get("most_captained"),
                "top_element": e.get("top_element"),
            }
        )

    fixtures = []

    for f in data.get("fixtures", []):

        fixtures.append(
            {
                "id": f.get("id"),
                "event": f.get("event"),
                "team_h": f.get("team_h"),
                "team_a": f.get("team_a"),
                "team_h_score": f.get("team_h_score"),
                "team_a_score": f.get("team_a_score"),
                "finished": f.get("finished"),
                "difficulty_h": safe_int(
                    f.get("team_h_difficulty")
                ),
                "difficulty_a": safe_int(
                    f.get("team_a_difficulty")
                ),
                "kickoff": f.get("kickoff_time"),
            }
        )

    return {
        "teams": teams,
        "players": players,
        "events": events,
        "fixtures": fixtures,
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

    next_gw = [
        e for e in events
        if e.get("is_next")
    ]

    if next_gw:
        return next_gw[0]["id"]

    return 1


# ============================================================
# FIXTURE ENGINE
# ============================================================

def team_fixture_rows(data, team_id, gw=None, horizon=5):

    fixtures = data["fixtures"]

    if gw is None:
        gw = get_current_gw(data["events"])

    rows = []

    for f in fixtures:

        if f["event"] is None:
            continue

        if f["event"] < gw:
            continue

        if f["event"] > gw + horizon - 1:
            continue

        if f["team_h"] == team_id:

            opponent = data["teams"].get(
                f["team_a"],
                {}
            )

            rows.append(
                {
                    "gw": f["event"],
                    "opponent": opponent.get(
                        "short_name",
                        "?"
                    ),
                    "opponent_id": f["team_a"],
                    "home": True,
                    "difficulty": f["difficulty_h"],
                    "kickoff": f["kickoff"],
                }
            )

        elif f["team_a"] == team_id:

            opponent = data["teams"].get(
                f["team_h"],
                {}
            )

            rows.append(
                {
                    "gw": f["event"],
                    "opponent": opponent.get(
                        "short_name",
                        "?"
                    ),
                    "opponent_id": f["team_h"],
                    "home": False,
                    "difficulty": f["difficulty_a"],
                    "kickoff": f["kickoff"],
                }
            )

    rows.sort(key=lambda x: (
        x["gw"],
        x["kickoff"] or ""
    ))

    return rows


def fixture_score(fixtures):

    if not fixtures:
        return 50

    difficulties = [
        safe_float(x["difficulty"], 3)
        for x in fixtures
    ]

    avg = sum(difficulties) / len(difficulties)

    # FPL difficulty 1-5.
    # Lower = better.
    return clamp(
        100 - ((avg - 1) / 4) * 100,
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


# ============================================================
# PLAYER ANALYTICS ENGINE
# ============================================================

def minutes_score(player):

    chance = safe_float(
        player["chance_next_round"],
        100
    )

    minutes = safe_float(
        player["minutes"]
    )

    starts = safe_float(
        player["starts"]
    )

    if minutes <= 0:
        base = 15

    else:
        base = min(
            100,
            45 + min(
                55,
                minutes / 1200 * 55
            )
        )

    if starts > 0 and minutes > 0:
        start_rate = clamp(
            starts / max(1, minutes / 90),
            0,
            1,
        )

        base = (
            base * 0.65
            + start_rate * 100 * 0.35
        )

    return clamp(
        base * chance / 100,
        0,
        100,
    )


def risk_score(player):

    minutes = minutes_score(player)

    injury_risk = (
        100 - safe_float(
            player["chance_next_round"],
            100
        )
    )

    low_minutes = 100 - minutes

    news_penalty = (
        15
        if player.get("news")
        else 0
    )

    risk = (
        injury_risk * 0.45
        + low_minutes * 0.45
        + news_penalty * 0.10
    )

    return clamp(risk, 0, 100)


def player_radar_score(player, data):

    team_id = player["team_id"]

    fixtures = team_fixture_rows(
        data,
        team_id,
        horizon=5,
    )

    f_score = fixture_score(fixtures)

    form = clamp(
        safe_float(player["form"]) * 10,
        0,
        100,
    )

    xgi = clamp(
        safe_float(
            player["expected_goal_involvements_per_90"]
        ) * 100,
        0,
        100,
    )

    ict = clamp(
        safe_float(player["ict_index"]),
        0,
        100,
    )

    mins = minutes_score(player)

    risk = risk_score(player)

    # Universal score
    score = (
        form * 0.20
        + xgi * 0.25
        + ict * 0.15
        + mins * 0.20
        + f_score * 0.20
    )

    score -= risk * 0.15

    return clamp(score, 0, 100)


def captain_score(player, data):

    fixtures = team_fixture_rows(
        data,
        player["team_id"],
        horizon=3,
    )

    f_score = fixture_score(fixtures)

    form = clamp(
        safe_float(player["form"]) * 10,
        0,
        100,
    )

    xgi = clamp(
        safe_float(
            player["expected_goal_involvements_per_90"]
        ) * 100,
        0,
        100,
    )

    mins = minutes_score(player)

    home_bonus = 0

    if fixtures and fixtures[0]["home"]:
        home_bonus = 7

    bonus = clamp(
        safe_float(player["bonus"]) / 10,
        0,
        100,
    )

    risk = risk_score(player)

    score = (
        xgi * 0.32
        + form * 0.20
        + f_score * 0.25
        + mins * 0.15
        + bonus * 0.08
        + home_bonus
    )

    score -= risk * 0.15

    return clamp(score, 0, 100)


def differential_score(player, data):

    radar = player_radar_score(
        player,
        data
    )

    ownership = safe_float(
        player["selected_by"]
    )

    ownership_score = clamp(
        100 - ownership * 4,
        0,
        100,
    )

    # Strong differential but not blindly low ownership
    xgi = clamp(
        safe_float(
            player["expected_goal_involvements_per_90"]
        ) * 100,
        0,
        100,
    )

    minutes = minutes_score(player)

    score = (
        radar * 0.40
        + ownership_score * 0.25
        + xgi * 0.20
        + minutes * 0.15
    )

    return clamp(score, 0, 100)


# ============================================================
# RANKING FUNCTIONS
# ============================================================

def add_scores(players, data):

    output = []

    for p in players:

        row = dict(p)

        row["radar_score"] = player_radar_score(
            p,
            data
        )

        row["captain_score"] = captain_score(
            p,
            data
        )

        row["differential_score"] = differential_score(
            p,
            data
        )

        row["minutes_score"] = minutes_score(
            p
        )

        row["risk_score"] = risk_score(
            p
        )

        output.append(row)

    return output


# ============================================================
# DEFENSIVE ANALYTICS
# ============================================================

def team_defensive_profile(team, data):

    team_id = team["id"]

    # We derive a relative defensive profile from FPL
    # team strength values + player defensive output.
    strength_home = safe_float(
        team["strength_defence_home"]
    )

    strength_away = safe_float(
        team["strength_defence_away"]
    )

    strength = (
        strength_home
        + strength_away
    ) / 2

    all_teams = list(
        data["teams"].values()
    )

    strengths = [
        safe_float(
            t["strength_defence_home"]
        )
        + safe_float(
            t["strength_defence_away"]
        )
        for t in all_teams
    ]

    min_s = min(strengths) if strengths else 1
    max_s = max(strengths) if strengths else 100

    defensive_strength = (
        (strength * 2 - min_s)
        / max(
            1,
            max_s - min_s
        )
    )

    # Convert to 0-100:
    # stronger defence = lower vulnerability
    vulnerability = clamp(
        100 - defensive_strength * 100,
        0,
        100,
    )

    # Tactical zone proxy.
    # These are analytical proxies, not claimed Opta data.
    left = clamp(
        vulnerability
        * 0.95
        + (100 - strength_home) * 0.05,
        0,
        100,
    )

    center = clamp(
        vulnerability
        * 1.08,
        0,
        100,
    )

    right = clamp(
        vulnerability
        * 0.92
        + (100 - strength_away) * 0.08,
        0,
        100,
    )

    return {
        "defensive_strength": clamp(
            100 - vulnerability,
            0,
            100
        ),
        "vulnerability": vulnerability,
        "left": left,
        "center": center,
        "right": right,
        "strength_home": strength_home,
        "strength_away": strength_away,
    }


# ============================================================
# TACTICAL PITCH
# ============================================================

def draw_interactive_pitch(
    left_val,
    center_val,
    right_val,
    team_name,
):

    fig = go.Figure()

    # Pitch
    fig.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=100,
        y1=60,
        line=dict(
            color="rgba(255,255,255,.35)",
            width=2,
        ),
        fillcolor="rgba(0,0,0,0)",
    )

    # Vertical zones
    for x in [33.33, 66.66]:
        fig.add_shape(
            type="line",
            x0=x,
            y0=0,
            x1=x,
            y1=60,
            line=dict(
                color="rgba(255,255,255,.20)",
                width=1,
            ),
        )

    # Zones
    zones = [
        (
            0,
            33.33,
            left_val,
            "LEFT",
        ),
        (
            33.33,
            66.66,
            center_val,
            "CENTER",
        ),
        (
            66.66,
            100,
            right_val,
            "RIGHT",
        ),
    ]

    for x0, x1, value, label in zones:

        alpha = 0.15 + value / 100 * 0.55

        fig.add_shape(
            type="rect",
            x0=x0,
            y0=0,
            x1=x1,
            y1=60,
            fillcolor=(
                f"rgba(255,80,80,{alpha})"
            ),
            line=dict(width=0),
        )

        fig.add_annotation(
            x=(x0 + x1) / 2,
            y=30,
            text=(
                f"<b>{label}</b><br>"
                f"{value:.0f}/100"
            ),
            showarrow=False,
            font=dict(
                size=15,
                color="white",
            ),
        )

    fig.update_layout(
        title=f"{team_name} — Defensive Vulnerability",
        height=390,
        margin=dict(
            l=10,
            r=10,
            t=45,
            b=10,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            visible=False,
            range=[0, 100],
        ),
        yaxis=dict(
            visible=False,
            range=[0, 60],
        ),
        font=dict(
            color="white"
        ),
    )

    return fig


# ============================================================
# RADAR VERDICT
# ============================================================

def verdict_for_player(
    player,
    data,
    purpose="general",
):

    if purpose == "captain":
        score = captain_score(
            player,
            data
        )

    elif purpose == "differential":
        score = differential_score(
            player,
            data
        )

    else:
        score = player_radar_score(
            player,
            data
        )

    risk = risk_score(player)

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

    if safe_float(player["form"]) >= 5:
        reasons.append("strong recent form")

    if safe_float(
        player["expected_goal_involvements_per_90"]
    ) >= 0.40:
        reasons.append("strong xGI/90")

    if minutes_score(player) >= 75:
        reasons.append("good minutes security")

    fixtures = team_fixture_rows(
        data,
        player["team_id"],
        horizon=3,
    )

    f_score = fixture_score(fixtures)

    if f_score >= 65:
        reasons.append("favorable upcoming fixtures")

    if not reasons:
        reasons.append("balanced underlying profile")

    return {
        "score": score,
        "risk": risk_label,
        "confidence": confidence,
        "reason": ", ".join(reasons),
    }


def render_verdict(
    title,
    main,
    reason,
    confidence="High",
    risk="Low",
):

    st.markdown(
        f"""
<div class="verdict">

<div class="verdict-title">
🎯 RADAR VERDICT
</div>

<div class="verdict-main">
{main}
</div>

<div style="margin-top:8px">
{badge_html(risk)}
<span class="badge badge-green">
Confidence: {confidence}
</span>
</div>

<div class="verdict-text">
{reason}
</div>

</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# SIDEBAR
# ============================================================

def sidebar(data):

    st.sidebar.markdown(
        """
# 🎯 FPL RADAR
### Ultimate FPL Analytics
"""
    )

    st.sidebar.caption(
        f"Version {APP_VERSION}"
    )

    st.sidebar.divider()

    current_gw = get_current_gw(
        data["events"]
    )

    st.sidebar.markdown(
        "### 📅 Gameweek"
    )

    gw_options = [
        e["id"]
        for e in data["events"]
    ]

    if not gw_options:
        gw_options = [current_gw]

    selected_gw = st.sidebar.selectbox(
        "Select GW",
        gw_options,
        index=(
            gw_options.index(current_gw)
            if current_gw in gw_options
            else 0
        ),
        label_visibility="collapsed",
    )

    st.session_state["selected_gw"] = selected_gw

    st.sidebar.divider()

    st.sidebar.markdown(
        "### 📍 Navigation"
    )

    pages = {
        "🏠 Dashboard": "Dashboard",
        "🛡️ Defensive Radar": "Defensive Radar",
        "⚔️ Head-to-Head": "Head-to-Head",
        "💎 Differential Scout": "Differential Scout",
        "👑 Captaincy Planner": "Captaincy Planner",
        "🔄 Transfer Planner": "Transfer Planner",
        "🧠 Team Optimizer": "Team Optimizer",
        "🤖 Ask FPL Radar": "Ask FPL Radar",
    }

    page = st.sidebar.selectbox(
        "Navigation",
        list(pages.keys()),
        label_visibility="collapsed",
    )

    st.session_state["page"] = pages[page]

    st.sidebar.divider()

    st.sidebar.markdown(
        "### ⚙️ Settings"
    )

    st.sidebar.caption(
        f"Data updated: "
        f"{data.get('updated', '')[:19]}"
    )

    if st.sidebar.button(
        "🔄 Refresh FPL Data",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()

    return st.session_state["page"]


# ============================================================
# DASHBOARD
# ============================================================

def dashboard(data):

    st.title("🎯 FPL Radar Dashboard")

    current_gw = get_current_gw(
        data["events"]
    )

    players = add_scores(
        data["players"],
        data
    )

    active_players = [
        p for p in players
        if p["status"] == "a"
    ]

    captain_rank = sorted(
        active_players,
        key=lambda x: x["captain_score"],
        reverse=True,
    )[:10]

    diff_rank = sorted(
        active_players,
        key=lambda x: x["differential_score"],
        reverse=True,
    )[:10]

    # Metrics
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
<div class="metric-card">
<div class="metric-label">CURRENT GAMEWEEK</div>
<div class="metric-value">GW {current_gw}</div>
<div class="metric-sub">FPL data engine</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
<div class="metric-card">
<div class="metric-label">PLAYERS</div>
<div class="metric-value">{len(active_players)}</div>
<div class="metric-sub">active players</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
<div class="metric-card">
<div class="metric-label">TEAMS</div>
<div class="metric-value">{len(data["teams"])}</div>
<div class="metric-sub">Premier League clubs</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with c4:
        next_event = next(
            (
                e for e in data["events"]
                if e["is_next"]
            ),
            None,
        )

        label = (
            next_event["name"]
            if next_event
            else f"GW {current_gw}"
        )

        st.markdown(
            f"""
<div class="metric-card">
<div class="metric-label">NEXT GW</div>
<div class="metric-value">
{label}
</div>
<div class="metric-sub">planning window</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.write("")

    left, right = st.columns(
        [1.15, 1]
    )

    # Captain
    with left:

        st.subheader(
            "👑 Captain Radar"
        )

        for i, p in enumerate(
            captain_rank[:5],
            1,
        ):

            v = verdict_for_player(
                p,
                data,
                "captain",
            )

            st.markdown(
                f"""
<div class="player-row">
<b>#{i} {p["name"]}</b>
<br>
{p["team_short"]} · {p["position"]} · {money(p["price"])}
<br>
Radar: <b>{p["captain_score"]:.1f}</b>
&nbsp; Form: {p["form"]}
&nbsp; xGI/90: {p["expected_goal_involvements_per_90"]:.2f}
<br>
{badge_html(v["risk"])}
<span class="badge badge-green">
{v["confidence"]}
</span>
</div>
""",
                unsafe_allow_html=True,
            )

    # Differentials
    with right:

        st.subheader(
            "💎 Differential Radar"
        )

        for i, p in enumerate(
            diff_rank[:5],
            1,
        ):

            st.markdown(
                f"""
<div class="player-row">
<b>#{i} {p["name"]}</b>
<br>
{p["team_short"]} · {p["position"]}
<br>
Ownership: <b>{pct(p["selected_by"])}</b>
&nbsp; Radar: <b>{p["differential_score"]:.1f}</b>
<br>
Price: {money(p["price"])}
</div>
""",
                unsafe_allow_html=True,
            )

    st.divider()

    # Best fixtures
    st.subheader(
        "📅 Best Fixture Runs"
    )

    fixture_rows = []

    for team in data["teams"].values():

        fixtures = team_fixture_rows(
            data,
            team["id"],
            horizon=5,
        )

        score = fixture_score(
            fixtures
        )

        fixture_rows.append(
            {
                "Team": team["name"],
                "Fixtures": " · ".join(
                    [
                        f"GW{x['gw']} {x['opponent']}"
                        for x in fixtures
                    ]
                ),
                "Fixture Score": round(
                    score,
                    1,
                ),
                "Verdict": fixture_label(
                    score
                ),
            }
        )

    fixture_df = pd.DataFrame(
        fixture_rows
    ).sort_values(
        "Fixture Score",
        ascending=False,
    )

    st.dataframe(
        fixture_df.head(10),
        use_container_width=True,
        hide_index=True,
    )

    st.write("")

    if captain_rank:

        best = captain_rank[0]

        v = verdict_for_player(
            best,
            data,
            "captain",
        )

        render_verdict(
            "Captain",
            f"{best['name']} — {v['score']:.1f}/100",
            v["reason"],
            v["confidence"],
            v["risk"],
        )


# ============================================================
# DEFENSIVE RADAR
# ============================================================

def defensive_radar(data):

    st.title(
        "🛡️ Defensive Radar"
    )

    teams = data["teams"]

    team_names = {
        t["name"]: t["id"]
        for t in teams.values()
    }

    selected_name = st.selectbox(
        "Select team",
        sorted(team_names.keys()),
    )

    team_id = team_names[
        selected_name
    ]

    team = teams[team_id]

    profile = team_defensive_profile(
        team,
        data
    )

    col1, col2 = st.columns(
        [1.1, 1]
    )

    with col1:

        fig = draw_interactive_pitch(
            profile["left"],
            profile["center"],
            profile["right"],
            selected_name,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    with col2:

        st.subheader(
            "📊 Defensive Profile"
        )

        metrics = [
            (
                "Defensive Strength",
                profile["defensive_strength"]
            ),
            (
                "Overall Vulnerability",
                profile["vulnerability"]
            ),
            (
                "Left Zone",
                profile["left"]
            ),
            (
                "Central Zone",
                profile["center"]
            ),
            (
                "Right Zone",
                profile["right"]
            ),
        ]

        for label, value in metrics:

            st.progress(
                int(clamp(value, 0, 100))
            )

            st.caption(
                f"{label}: {value:.0f}/100"
            )

    st.divider()

    st.subheader(
        "🎯 Where to Attack"
    )

    zones = {
        "Left": profile["left"],
        "Center": profile["center"],
        "Right": profile["right"],
    }

    weakest = max(
        zones,
        key=zones.get
    )

    st.success(
        f"Primary target zone: **{weakest}**"
    )

    st.subheader(
        "⚡ Best attacking targets"
    )

    players = add_scores(
        data["players"],
        data
    )

    attacking = [
        p for p in players
        if p["team_id"] != team_id
        and p["position"] in ["FWD", "MID"]
        and p["status"] == "a"
    ]

    attacking = sorted(
        attacking,
        key=lambda x: x["radar_score"],
        reverse=True,
    )[:10]

    rows = []

    for p in attacking:

        rows.append(
            {
                "Player": p["name"],
                "Team": p["team_short"],
                "Pos": p["position"],
                "Price": money(p["price"]),
                "Ownership": pct(
                    p["selected_by"]
                ),
                "Form": p["form"],
                "xGI/90": round(
                    p["expected_goal_involvements_per_90"],
                    2,
                ),
                "Radar": round(
                    p["radar_score"],
                    1,
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    render_verdict(
        "Attack",
        f"Attack the {weakest} zone",
        (
            f"{selected_name} shows the highest relative "
            f"vulnerability on the {weakest.lower()} side. "
            f"Use high-Radar attackers with secure minutes "
            f"and favorable fixtures."
        ),
        "Medium",
        "Medium",
    )


# ============================================================
# H2H
# ============================================================

def h2h(data):

    st.title(
        "⚔️ Head-to-Head"
    )

    team_names = sorted(
        [
            t["name"]
            for t in data["teams"].values()
        ]
    )

    col1, col2 = st.columns(2)

    with col1:

        team_a_name = st.selectbox(
            "Team A",
            team_names,
            index=0,
        )

    with col2:

        default_b = (
            1 if len(team_names) > 1
            else 0
        )

        team_b_name = st.selectbox(
            "Team B",
            team_names,
            index=default_b,
        )

    if team_a_name == team_b_name:

        st.warning(
            "Please select two different teams."
        )
        return

    team_a = next(
        t for t in data["teams"].values()
        if t["name"] == team_a_name
    )

    team_b = next(
        t for t in data["teams"].values()
        if t["name"] == team_b_name
    )

    profile_a = team_defensive_profile(
        team_a,
        data
    )

    profile_b = team_defensive_profile(
        team_b,
        data
    )

    fixtures_a = team_fixture_rows(
        data,
        team_a["id"],
        horizon=5,
    )

    fixtures_b = team_fixture_rows(
        data,
        team_b["id"],
        horizon=5,
    )

    fixture_a_score = fixture_score(
        fixtures_a
    )

    fixture_b_score = fixture_score(
        fixtures_b
    )

    players = add_scores(
        data["players"],
        data
    )

    a_players = [
        p for p in players
        if p["team_id"] == team_a["id"]
    ]

    b_players = [
        p for p in players
        if p["team_id"] == team_b["id"]
    ]

    def team_attack_score(
        team_players
    ):

        values = [
            p["radar_score"]
            for p in team_players
            if p["status"] == "a"
        ]

        if not values:
            return 0

        return sum(
            sorted(
                values,
                reverse=True
            )[:5]
        ) / min(
            5,
            len(values)
        )

    attack_a = team_attack_score(
        a_players
    )

    attack_b = team_attack_score(
        b_players
    )

    # Comparison
    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Defensive Strength",
            f"{profile_a['defensive_strength']:.0f}",
            f"{profile_a['defensive_strength'] - profile_b['defensive_strength']:+.0f} vs B",
        )

    with c2:

        st.metric(
            "Attack Radar",
            f"{attack_a:.0f}",
            f"{attack_a - attack_b:+.0f} vs B",
        )

    with c3:

        st.metric(
            "Fixture Score",
            f"{fixture_a_score:.0f}",
            f"{fixture_a_score - fixture_b_score:+.0f} vs B",
        )

    st.divider()

    comparison = pd.DataFrame(
        {
            "Metric": [
                "Defensive Strength",
                "Vulnerability",
                "Attack Radar",
                "Fixture Score",
                "Left Vulnerability",
                "Center Vulnerability",
                "Right Vulnerability",
            ],
            team_a_name: [
                profile_a["defensive_strength"],
                profile_a["vulnerability"],
                attack_a,
                fixture_a_score,
                profile_a["left"],
                profile_a["center"],
                profile_a["right"],
            ],
            team_b_name: [
                profile_b["defensive_strength"],
                profile_b["vulnerability"],
                attack_b,
                fixture_b_score,
                profile_b["left"],
                profile_b["center"],
                profile_b["right"],
            ],
        }
    )

    st.dataframe(
        comparison.round(1),
        use_container_width=True,
        hide_index=True,
    )

    # Best target
    target_team = team_b

    target_players = [
        p for p in players
        if p["team_id"] == target_team["id"]
        and p["status"] == "a"
    ]

    # Attacking target is from team A if attacking B.
    attacking_targets = sorted(
        [
            p for p in players
            if p["team_id"] == team_a["id"]
            and p["status"] == "a"
            and p["position"] in ["FWD", "MID"]
        ],
        key=lambda x: x["radar_score"],
        reverse=True,
    )

    best_target = (
        attacking_targets[0]
        if attacking_targets
        else None
    )

    if attack_a >= attack_b:

        winner = team_a_name

    else:

        winner = team_b_name

    if best_target:

        render_verdict(
            "H2H",
            f"{winner} has the stronger current profile",
            (
                f"Best attacking target from {team_a_name}: "
                f"{best_target['name']} "
                f"({best_target['radar_score']:.1f}/100). "
                f"Fixture and underlying player profile are "
                f"used together rather than relying on one metric."
            ),
            "Medium",
            "Medium",
        )


# ============================================================
# DIFFERENTIAL SCOUT
# ============================================================

def differential_scout(data):

    st.title(
        "💎 Differential Scout"
    )

    ownership_limit = st.slider(
        "Maximum ownership %",
        1.0,
        30.0,
        10.0,
        0.5,
    )

    min_price = st.slider(
        "Minimum price",
        3.5,
        15.0,
        5.0,
        0.1,
    )

    positions = st.multiselect(
        "Positions",
        ["GKP", "DEF", "MID", "FWD"],
        default=["MID", "FWD"],
    )

    players = add_scores(
        data["players"],
        data
    )

    pool = [
        p for p in players
        if p["status"] == "a"
        and p["selected_by"] <= ownership_limit
        and p["price"] >= min_price
        and p["position"] in positions
        and p["minutes"] > 100
    ]

    pool = sorted(
        pool,
        key=lambda x: x["differential_score"],
        reverse=True,
    )

    if not pool:

        st.info(
            "No players match the selected filters."
        )
        return

    rows = []

    for p in pool[:30]:

        rows.append(
            {
                "Player": p["name"],
                "Team": p["team_short"],
                "Pos": p["position"],
                "Price": money(p["price"]),
                "Own %": round(
                    p["selected_by"],
                    1,
                ),
                "Form": p["form"],
                "xGI/90": round(
                    p["expected_goal_involvements_per_90"],
                    2,
                ),
                "Minutes Score": round(
                    p["minutes_score"],
                    1,
                ),
                "Radar": round(
                    p["differential_score"],
                    1,
                ),
                "Risk": (
                    "Low"
                    if p["risk_score"] < 25
                    else
                    "Medium"
                    if p["risk_score"] < 55
                    else
                    "High"
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    best = pool[0]

    v = verdict_for_player(
        best,
        data,
        "differential",
    )

    render_verdict(
        "Differential",
        f"{best['name']} — {v['score']:.1f}/100",
        (
            f"Ownership {best['selected_by']:.1f}% · "
            f"{v['reason']}"
        ),
        v["confidence"],
        v["risk"],
    )


# ============================================================
# CAPTAINCY PLANNER
# ============================================================

def captaincy(data):

    st.title(
        "👑 Captaincy Planner"
    )

    players = add_scores(
        data["players"],
        data
    )

    eligible = [
        p for p in players
        if p["status"] == "a"
        and p["position"] in ["MID", "FWD"]
        and p["minutes"] > 250
    ]

    ranked = sorted(
        eligible,
        key=lambda x: x["captain_score"],
        reverse=True,
    )[:20]

    rows = []

    for i, p in enumerate(
        ranked,
        1,
    ):

        v = verdict_for_player(
            p,
            data,
            "captain",
        )

        fixtures = team_fixture_rows(
            data,
            p["team_id"],
            horizon=3,
        )

        fixture_text = " · ".join(
            [
                (
                    f"GW{x['gw']} "
                    f"{x['opponent']} "
                    f"{'H' if x['home'] else 'A'}"
                )
                for x in fixtures[:3]
            ]
        )

        rows.append(
            {
                "Rank": i,
                "Player": p["name"],
                "Team": p["team_short"],
                "Fixture": fixture_text,
                "Price": money(p["price"]),
                "Form": p["form"],
                "xGI/90": round(
                    p["expected_goal_involvements_per_90"],
                    2,
                ),
                "Minutes": round(
                    p["minutes_score"],
                    0,
                ),
                "Captain Score": round(
                    p["captain_score"],
                    1,
                ),
                "Confidence": v["confidence"],
                "Risk": v["risk"],
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    if ranked:

        top = ranked[0]

        v = verdict_for_player(
            top,
            data,
            "captain",
        )

        render_verdict(
            "Captain",
            f"{top['name']} — {top['captain_score']:.1f}/100",
            (
                f"{top['team_short']} · "
                f"Form {top['form']} · "
                f"xGI/90 "
                f"{top['expected_goal_involvements_per_90']:.2f}. "
                f"{v['reason']}."
            ),
            v["confidence"],
            v["risk"],
        )


# ============================================================
# TRANSFER PLANNER
# ============================================================

def transfer_planner(data):

    st.title(
        "🔄 Transfer Planner"
    )

    st.info(
        "أدخل لاعبي فريقك الحالي يدويًا. "
        "بعدها سيقارن Radar بين خيارات OUT و IN."
    )

    players = add_scores(
        data["players"],
        data
    )

    player_map = {
        f"{p['name']} — {p['team_short']} — £{p['price']:.1f}m":
        p["id"]
        for p in players
        if p["status"] == "a"
    }

    selected_labels = st.multiselect(
        "Your current squad",
        list(player_map.keys()),
        max_selections=15,
    )

    free_transfers = st.number_input(
        "Free Transfers",
        min_value=1,
        max_value=5,
        value=1,
    )

    bank = st.number_input(
        "Money in Bank (£m)",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
        step=0.1,
    )

    if not selected_labels:

        st.warning(
            "Select your current squad first."
        )
        return

    current_ids = {
        player_map[x]
        for x in selected_labels
    }

    current = [
        p for p in players
        if p["id"] in current_ids
    ]

    st.subheader(
        "🔻 Suggested OUT"
    )

    out_candidates = sorted(
        current,
        key=lambda x: x["radar_score"]
    )

    out_rows = []

    for p in out_candidates:

        out_rows.append(
            {
                "Player": p["name"],
                "Team": p["team_short"],
                "Price": money(p["price"]),
                "Radar": round(
                    p["radar_score"],
                    1,
                ),
                "Risk": (
                    "Low"
                    if p["risk_score"] < 25
                    else
                    "Medium"
                    if p["risk_score"] < 55
                    else
                    "High"
                ),
                "Reason": (
                    "Low current Radar score"
                    if p["radar_score"] < 55
                    else
                    "Consider only if upgrading structure"
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(out_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader(
        "🔺 Suggested IN"
    )

    # Candidates
    candidates = [
        p for p in players
        if p["status"] == "a"
        and p["id"] not in current_ids
    ]

    suggestions = []

    for out_player in out_candidates[:5]:

        max_price = (
            out_player["price"]
            + bank
        )

        candidates_same_pos = [
            p for p in candidates
            if p["position"]
            == out_player["position"]
            and p["price"] <= max_price
        ]

        candidates_same_pos.sort(
            key=lambda x: x["radar_score"],
            reverse=True,
        )

        for candidate in candidates_same_pos[:3]:

            improvement = (
                candidate["radar_score"]
                - out_player["radar_score"]
            )

            if improvement > 0:

                suggestions.append(
                    {
                        "OUT": out_player["name"],
                        "IN": candidate["name"],
                        "Position": candidate["position"],
                        "Price": money(candidate["price"]),
                        "Radar Gain": round(
                            improvement,
                            1,
                        ),
                        "IN Radar": round(
                            candidate["radar_score"],
                            1,
                        ),
                        "Risk": (
                            "Low"
                            if candidate["risk_score"] < 25
                            else
                            "Medium"
                            if candidate["risk_score"] < 55
                            else
                            "High"
                        ),
                    }
                )

    suggestions.sort(
        key=lambda x: x["Radar Gain"],
        reverse=True,
    )

    st.dataframe(
        pd.DataFrame(
            suggestions[:20]
        ),
        use_container_width=True,
        hide_index=True,
    )

    if suggestions:

        best = suggestions[0]

        render_verdict(
            "Transfer",
            f"{best['OUT']} → {best['IN']}",
            (
                f"Estimated Radar improvement: "
                f"+{best['Radar Gain']:.1f}. "
                f"This is a model-based recommendation, "
                f"not a guarantee of future points."
            ),
            "Medium",
            best["Risk"],
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
        min_value=50.0,
        max_value=120.0,
        value=100.0,
        step=0.1,
    )

    strategy = st.selectbox(
        "Strategy",
        [
            "Safe",
            "Balanced",
            "Differential",
        ],
    )

    if strategy == "Safe":
        ownership_weight = 0.20

    elif strategy == "Balanced":
        ownership_weight = 0.10

    else:
        ownership_weight = -0.05

    players = add_scores(
        data["players"],
        data
    )

    # Strategy score
    for p in players:

        ownership_component = clamp(
            p["selected_by"] * 4,
            0,
            100,
        )

        p["optimizer_score"] = (
            p["radar_score"] * 0.80
            + ownership_component
            * ownership_weight
        )

    positions = {
        "GKP": 2,
        "DEF": 5,
        "MID": 5,
        "FWD": 3,
    }

    selected = []

    # Simple but valid positional optimizer.
    # It respects budget and max 3 players per team.
    team_counts = {}

    remaining_budget = budget

    for position, max_count in positions.items():

        pool = sorted(
            [
                p for p in players
                if p["position"] == position
                and p["status"] == "a"
                and p["minutes"] > 100
            ],
            key=lambda x: x["optimizer_score"],
            reverse=True,
        )

        count = 0

        for p in pool:

            if count >= max_count:
                break

            if (
                remaining_budget
                - p["price"]
                < 0
            ):
                continue

            team_count = team_counts.get(
                p["team_id"],
                0,
            )

            if team_count >= 3:
                continue

            selected.append(p)

            remaining_budget -= p["price"]

            team_counts[
                p["team_id"]
            ] = team_count + 1

            count += 1

    # If budget constraints caused incomplete squad,
    # tell user instead of pretending.
    st.subheader(
        "Recommended Squad"
    )

    rows = []

    for p in selected:

        rows.append(
            {
                "Player": p["name"],
                "Team": p["team_short"],
                "Pos": p["position"],
                "Price": money(p["price"]),
                "Radar": round(
                    p["optimizer_score"],
                    1,
                ),
                "Ownership": pct(
                    p["selected_by"]
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    total_cost = sum(
        p["price"]
        for p in selected
    )

    st.metric(
        "Squad Cost",
        f"£{total_cost:.1f}m",
        f"£{budget - total_cost:.1f}m remaining",
    )

    st.warning(
        "Optimizer uses a transparent algorithmic "
        "selection. Before a real GW deadline, "
        "check injuries, predicted lineups and "
        "official FPL news."
    )


# ============================================================
# GEMINI
# ============================================================

def get_gemini_key():

    # Streamlit secrets first
    try:

        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets[
                "GEMINI_API_KEY"
            ]

    except Exception:
        pass

    # Environment variable
    key = os.getenv(
        "GEMINI_API_KEY"
    )

    if key:
        return key

    return st.session_state.get(
        "gemini_key",
        ""
    )


def ai_answer(question, data):

    if not GEMINI_AVAILABLE:

        return (
            "Gemini SDK is not installed. "
            "Run: pip install -U google-genai"
        )

    api_key = get_gemini_key()

    if not api_key:

        return (
            "Gemini API key is missing. "
            "Add GEMINI_API_KEY to Streamlit secrets "
            "or enter it in the sidebar."
        )

    client = genai.Client(
        api_key=api_key
    )

    players = add_scores(
        data["players"],
        data
    )

    top_players = sorted(
        players,
        key=lambda x: x["radar_score"],
        reverse=True,
    )[:40]

    player_context = []

    for p in top_players:

        player_context.append(
            {
                "name": p["name"],
                "team": p["team_short"],
                "pos": p["position"],
                "price": round(
                    p["price"],
                    1,
                ),
                "ownership": round(
                    p["selected_by"],
                    1,
                ),
                "form": round(
                    p["form"],
                    2,
                ),
                "xgi90": round(
                    p[
                        "expected_goal_involvements_per_90"
                    ],
                    2,
                ),
                "minutes_score": round(
                    p["minutes_score"],
                    1,
                ),
                "radar": round(
                    p["radar_score"],
                    1,
                ),
                "captain": round(
                    p["captain_score"],
                    1,
                ),
                "risk": round(
                    p["risk_score"],
                    1,
                ),
            }
        )

    team_context = []

    for team in data["teams"].values():

        fixtures = team_fixture_rows(
            data,
            team["id"],
            horizon=5,
        )

        team_context.append(
            {
                "team": team["name"],
                "short": team["short_name"],
                "fixture_score": round(
                    fixture_score(
                        fixtures
                    ),
                    1,
                ),
                "fixtures": [
                    {
                        "gw": f["gw"],
                        "opp": f["opponent"],
                        "home": f["home"],
                        "difficulty": f["difficulty"],
                    }
                    for f in fixtures
                ],
            }
        )

    context = {
        "gameweek": get_current_gw(
            data["events"]
        ),
        "top_players": player_context,
        "teams": team_context,
    }

    prompt = f"""
You are FPL Radar AI.

You are an expert Fantasy Premier League analyst.

IMPORTANT RULES:
1. Use ONLY the supplied structured data for numerical claims.
2. Never invent prices, ownership, fixtures or statistics.
3. If the supplied data does not contain something, say so.
4. Distinguish between model score and actual FPL points.
5. Give practical FPL advice.
6. Be concise but explain WHY.
7. Mention risk.
8. Never claim that Radar Score guarantees points.

USER QUESTION:
{question}

CURRENT DATA:
{json.dumps(context, ensure_ascii=False)}

Answer in clear English with:
- Verdict
- Why
- Risk
- Best alternative if relevant
"""

    try:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.25,
                max_output_tokens=900,
            ),
        )

        return response.text

    except Exception as e:

        return (
            f"Gemini error: {str(e)}"
        )


# ============================================================
# ASK FPL RADAR
# ============================================================

def ask_radar(data):

    st.title(
        "🤖 Ask FPL Radar"
    )

    st.caption(
        "Ask questions using the current FPL data engine."
    )

    if "chat_history" not in st.session_state:

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
        "Example: Salah or Haaland captain?"
    )

    if question:

        st.session_state[
            "chat_history"
        ].append(
            {
                "role": "user",
                "content": question,
            }
        )

        with st.chat_message("user"):

            st.markdown(question)

        with st.chat_message("assistant"):

            with st.spinner(
                "FPL Radar is analyzing..."
            ):

                answer = ai_answer(
                    question,
                    data,
                )

            st.markdown(answer)

        st.session_state[
            "chat_history"
        ].append(
            {
                "role": "assistant",
                "content": answer,
            }
        )


# ============================================================
# SETTINGS / GEMINI KEY
# ============================================================

def render_gemini_settings():

    st.sidebar.divider()

    st.sidebar.markdown(
        "### 🤖 AI Settings"
    )

    key = st.sidebar.text_input(
        "Gemini API Key",
        type="password",
        value=st.session_state.get(
            "gemini_key",
            ""
        ),
        help=(
            "Optional if GEMINI_API_KEY "
            "exists in Streamlit secrets."
        ),
    )

    if key:

        st.session_state[
            "gemini_key"
        ] = key


# ============================================================
# DATA HEALTH
# ============================================================

def data_health(data):

    st.sidebar.divider()

    st.sidebar.markdown(
        "### 🩺 Data Health"
    )

    st.sidebar.success(
        "FPL API: Connected"
    )

    st.sidebar.caption(
        f"Teams: {len(data['teams'])}"
    )

    st.sidebar.caption(
        f"Players: {len(data['players'])}"
    )

    st.sidebar.caption(
        f"Fixtures: {len(data['fixtures'])}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    data_raw, ok, error = (
        load_data_with_status()
    )

    if not ok:

        st.error(
            "❌ Unable to load FPL data."
        )

        st.code(
            str(error)
        )

        st.info(
            "Check internet connection or FPL API availability."
        )

        # Still allow user to retry
        if st.button(
            "🔄 Retry"
        ):

            st.cache_data.clear()
            st.rerun()

        return

    data = normalize_data(
        data_raw
    )

    page = sidebar(
        data
    )

    render_gemini_settings()

    data_health(
        data
    )

    # --------------------------------------------------------
    # PAGE ROUTER
    # --------------------------------------------------------

    if page == "Dashboard":

        dashboard(data)

    elif page == "Defensive Radar":

        defensive_radar(data)

    elif page == "Head-to-Head":

        h2h(data)

    elif page == "Differential Scout":

        differential_scout(data)

    elif page == "Captaincy Planner":

        captaincy(data)

    elif page == "Transfer Planner":

        transfer_planner(data)

    elif page == "Team Optimizer":

        team_optimizer(data)

    elif page == "Ask FPL Radar":

        ask_radar(data)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
