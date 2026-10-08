# FPL HOME - Streamlit single-file application
# Premium FPL decision-support dashboard
#
# Core data contract:
# FPL API = source of core FPL numbers
# Owner enrichment = optional defensive/tactical data
# Gemini = image interpretation and explanation only
#
# Required/optional secrets:
# GEMINI_API_KEY = "..."
# OWNER_PASSWORD = "..."
#
# Install:
# pip install streamlit requests pandas plotly google-genai
#
# Run:
# streamlit run app.py

import os
import json
from datetime import datetime, timezone

import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

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
APP_VERSION = "5.1"

FPL_BASE = "https://fantasy.premierleague.com/api"
BOOTSTRAP_URL = f"{FPL_BASE}/bootstrap-static/"
FIXTURES_URL = f"{FPL_BASE}/fixtures/"

REQUEST_TIMEOUT = 20
CACHE_TTL = 300
GEMINI_MODEL = "gemini-2.5-flash"


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
# UI CSS
# ============================================================

st.markdown(
    """ <style> :root { --bg: #050a0f; --surface: #0d1821; --surface2: #12222e; --surface3: #172b39; --border: #2a4352; --text: #f8fbfd; --soft: #d9e4ea; --muted: #9eb1bd; --green: #31e6a5; --blue: #62adff; --yellow: #ffd45c; --orange: #ff9c3a; --red: #ff5d69; } html, body, [class*="css"] { font-family: Inter, Arial, sans-serif; } .stApp { background: radial-gradient(circle at 0% 0%, rgba(49,230,165,.10), transparent 28%), radial-gradient(circle at 100% 0%, rgba(98,173,255,.10), transparent 30%), linear-gradient(180deg, #08131b 0%, var(--bg) 70%); color: var(--text); } .block-container { max-width: 1450px; padding: .65rem .75rem 4rem .75rem; } section[data-testid="stSidebar"] { display: none; } h1, h2, h3, h4, p, label { color: var(--text); } h1, h2, h3 { font-weight: 900 !important; } .topbar { background: rgba(7,18,26,.96); border: 1px solid var(--border); border-radius: 18px; padding: 14px 16px; margin: 0 0 16px 0; } .brand { color: #ffffff; font-size: 25px; font-weight: 950; letter-spacing: -.8px; } .brand span { color: var(--green); } .subtle { color: var(--muted) !important; font-size: 12px; } .card { background: linear-gradient(145deg, rgba(18,34,46,.98), rgba(9,19,27,.98)); border: 1px solid var(--border); border-radius: 18px; padding: 17px; margin-bottom: 14px; } .metric-card { background: linear-gradient(145deg, var(--surface2), var(--surface)); border: 1px solid var(--border); border-radius: 16px; padding: 15px; min-height: 100px; } .metric-label { color: var(--muted) !important; font-size: 10px; font-weight: 900; letter-spacing: 1px; } .metric-value { color: #ffffff !important; font-size: 26px; font-weight: 950; margin-top: 5px; } .metric-sub { color: var(--soft) !important; font-size: 11px; margin-top: 3px; } .section-title { color: #ffffff !important; font-size: 19px; font-weight: 950; margin: 14px 0 10px; } .verdict { border: 1px solid rgba(49,230,165,.36); border-radius: 18px; padding: 17px; background: linear-gradient(135deg, rgba(49,230,165,.13), rgba(8,20,28,.98)); } .verdict-kicker { color: var(--green) !important; font-size: 10px; font-weight: 950; letter-spacing: 1.2px; } .verdict-main { color: #ffffff !important; font-size: 23px; font-weight: 950; margin: 6px 0; } .badge { display: inline-block; border-radius: 999px; padding: 5px 9px; font-size: 10px; font-weight: 900; margin-right: 5px; } .green { background: rgba(49,230,165,.14); color: #69efc0 !important; border: 1px solid rgba(49,230,165,.28); } .yellow { background: rgba(255,212,92,.14); color: #ffe28c !important; border: 1px solid rgba(255,212,92,.28); } .orange { background: rgba(255,156,58,.14); color: #ffb46e !important; border: 1px solid rgba(255,156,58,.28); } .red { background: rgba(255,93,105,.14); color: #ff969e !important; border: 1px solid rgba(255,93,105,.28); } .blue { background: rgba(98,173,255,.14); color: #a0ceff !important; border: 1px solid rgba(98,173,255,.28); } .player-card, .zone-card { background: linear-gradient(145deg, var(--surface2), var(--surface)); border: 1px solid var(--border); border-radius: 15px; padding: 14px; margin-bottom: 9px; } .disclaimer { color: var(--muted) !important; font-size: 11px; line-height: 1.6; } .stButton > button { width: 100%; min-height: 42px; border-radius: 11px; border: 1px solid #345465; background: linear-gradient(135deg, #173245, #102430); color: #ffffff !important; font-weight: 850; } .stButton > button:hover { border-color: var(--green); background: linear-gradient(135deg, #194635, #102d24); color: #ffffff !important; } div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, textarea, input { background-color: #101f2a !important; color: #ffffff !important; border-color: #34505f !important; } div[data-baseweb="select"] span { color: #ffffff !important; } div[role="radiogroup"] { gap: 5px; flex-wrap: wrap; } div[role="radiogroup"] label { background: #0d1b25; border: 1px solid #2a4352; border-radius: 10px; padding: 5px 9px; color: #f0f6f9 !important; } div[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 13px; overflow: hidden; } section[data-testid="stFileUploaderDropzone"] { background: #0d1b25 !important; border: 1px dashed #3c5b6c !important; border-radius: 15px !important; } section[data-testid="stFileUploaderDropzone"] * { color: #edf5f8 !important; } .admin-header { background: linear-gradient(135deg, rgba(98,173,255,.13), rgba(49,230,165,.09)); border: 1px solid rgba(98,173,255,.30); border-radius: 18px; padding: 18px; margin-bottom: 15px; } .admin-title { color: #ffffff; font-size: 24px; font-weight: 950; } .admin-subtitle { color: #afc1cc; font-size: 12px; margin-top: 5px; } .pitch-legend { display: flex; gap: 12px; flex-wrap: wrap; margin: 5px 0 12px; } .pitch-legend-item { color: #dce7ed; font-size: 11px; font-weight: 800; } .pitch-dot { display: inline-block; width: 11px; height: 11px; border-radius: 50%; margin-right: 5px; } .dot-red { background: #ff3d4d; } .dot-orange { background: #ff9d2e; } .dot-yellow { background: #ffd83d; } @media (max-width: 768px) { .block-container { padding-left: .55rem; padding-right: .55rem; } .brand { font-size: 20px; } .metric-card { min-height: 82px; } .metric-value { font-size: 21px; } .verdict-main { font-size: 20px; } h1 { font-size: 27px !important; } h2 { font-size: 22px !important; } h3 { font-size: 18px !important; } div[role="radiogroup"] { overflow-x: auto; flex-wrap: nowrap; padding-bottom: 5px; } div[role="radiogroup"] label { white-space: nowrap; } } </style> """,
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
    value = str(risk)
    if value.lower() == "low":
        cls = "green"
    elif value.lower() == "medium":
        cls = "yellow"
    else:
        cls = "red"
    return f'<span class="badge {cls}">{value}</span>'


# ============================================================
# FPL API
# ============================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_json(url):
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": f"FPL-HOME/{APP_VERSION}"},
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_fpl_data():
    return {
        "bootstrap": fetch_json(BOOTSTRAP_URL),
        "fixtures": fetch_json(FIXTURES_URL),
        "updated": utc_now(),
    }


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_player_summary(player_id):
    return fetch_json(f"{FPL_BASE}/element-summary/{int(player_id)}/")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_team_picks(team_id, gw):
    return fetch_json(
        f"{FPL_BASE}/entry/{int(team_id)}/event/{int(gw)}/picks/"
    )


def load_data_with_status():
    try:
        return load_fpl_data(), True, None
    except Exception as exc:
        return None, False, str(exc)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_data(raw):
    bootstrap = raw["bootstrap"]

    teams = {}
    for t in bootstrap.get("teams", []):
        teams[t["id"]] = {
            "id": t["id"],
            "name": t.get("name", ""),
            "short_name": t.get("short_name", ""),
            "strength": safe_float(t.get("strength")),
            "strength_defence_home": safe_float(
                t.get("strength_defence_home")
            ),
            "strength_defence_away": safe_float(
                t.get("strength_defence_away")
            ),
            "strength_attack_home": safe_float(
                t.get("strength_attack_home")
            ),
            "strength_attack_away": safe_float(
                t.get("strength_attack_away")
            ),
        }

    positions = {
        p["id"]: p.get("singular_name_short", "")
        for p in bootstrap.get("element_types", [])
    }

    players = []
    for p in bootstrap.get("elements", []):
        team_id = p.get("team")
        team = teams.get(team_id, {"name": "Unknown", "short_name": "UNK"})

        players.append({
            "id": p.get("id"),
            "name": f"{p.get('first_name', '')} {p.get('second_name', '')}".strip(),
            "web_name": p.get("web_name", ""),
            "team_id": team_id,
            "team": team.get("name", ""),
            "team_short": team.get("short_name", ""),
            "position": positions.get(p.get("element_type"), "?"),
            "price": safe_float(p.get("now_cost")) / 10,
            "total_points": safe_float(p.get("total_points")),
            "event_points": safe_float(p.get("event_points")),
            "form": safe_float(p.get("form")),
            "points_per_game": safe_float(p.get("points_per_game")),
            "selected_by": safe_float(p.get("selected_by_percent")),
            "minutes": safe_float(p.get("minutes")),
            "goals": safe_float(p.get("goals_scored")),
            "assists": safe_float(p.get("assists")),
            "clean_sheets": safe_float(p.get("clean_sheets")),
            "goals_conceded": safe_float(p.get("goals_conceded")),
            "saves": safe_float(p.get("saves")),
            "bonus": safe_float(p.get("bonus")),
            "bps": safe_float(p.get("bps")),
            "influence": safe_float(p.get("influence")),
            "creativity": safe_float(p.get("creativity")),
            "threat": safe_float(p.get("threat")),
            "ict_index": safe_float(p.get("ict_index")),
            "expected_goals": safe_float(p.get("expected_goals")),
            "expected_assists": safe_float(p.get("expected_assists")),
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
                p.get("chance_of_playing_next_round"), 100
            ),
            "status": p.get("status", "a"),
            "news": p.get("news", ""),
            "starts": safe_float(p.get("starts")),
        })

    events = []
    for e in bootstrap.get("events", []):
        events.append({
            "id": e.get("id"),
            "name": e.get("name"),
            "deadline": e.get("deadline_time"),
            "finished": e.get("finished"),
            "is_current": e.get("is_current"),
            "is_next": e.get("is_next"),
            "is_previous": e.get("is_previous"),
        })

    fixtures = []
    for f in raw.get("fixtures", []):
        fixtures.append({
            "id": f.get("id"),
            "event": f.get("event"),
            "team_h": f.get("team_h"),
            "team_a": f.get("team_a"),
            "team_h_score": f.get("team_h_score"),
            "team_a_score": f.get("team_a_score"),
            "finished": f.get("finished"),
            "difficulty_h": safe_int(f.get("team_h_difficulty")),
            "difficulty_a": safe_int(f.get("team_a_difficulty")),
            "kickoff": f.get("kickoff_time"),
        })

    return {
        "teams": teams,
        "players": players,
        "events": events,
        "fixtures": fixtures,
        "updated": raw.get("updated", utc_now()),
    }


# ============================================================
# GAMEWEEK / FIXTURES
# ============================================================

def get_current_gw(events):
    current = [e for e in events if e.get("is_current")]
    if current:
        return current[0]["id"]
    nxt = [e for e in events if e.get("is_next")]
    if nxt:
        return nxt[0]["id"]
    return 1


def get_next_gw(events):
    nxt = [e for e in events if e.get("is_next")]
    return nxt[0]["id"] if nxt else get_current_gw(events)


def selected_gameweek(events):
    value = st.session_state.get("selected_gw")
    valid = {e["id"] for e in events if e.get("id") is not None}
    try:
        value = int(value)
        if value in valid:
            return value
    except Exception:
        pass
    return get_next_gw(events)


def team_fixture_rows(data, team_id, gw=None, horizon=5):
    if gw is None:
        gw = selected_gameweek(data["events"])

    rows = []
    for f in data["fixtures"]:
        if f["event"] is None:
            continue
        if f["event"] < gw or f["event"] > gw + horizon - 1:
            continue

        if f["team_h"] == team_id:
            opponent = data["teams"].get(f["team_a"], {})
            rows.append({
                "gw": f["event"],
                "opponent": opponent.get("short_name", "?"),
                "opponent_id": f["team_a"],
                "home": True,
                "difficulty": f["difficulty_h"],
                "kickoff": f["kickoff"],
            })
        elif f["team_a"] == team_id:
            opponent = data["teams"].get(f["team_h"], {})
            rows.append({
                "gw": f["event"],
                "opponent": opponent.get("short_name", "?"),
                "opponent_id": f["team_h"],
                "home": False,
                "difficulty": f["difficulty_a"],
                "kickoff": f["kickoff"],
            })

    rows.sort(key=lambda x: (x["gw"], x["kickoff"] or ""))
    return rows


def fixture_score(fixtures):
    if not fixtures:
        return 50.0

    avg = sum(safe_float(x["difficulty"], 3) for x in fixtures) / len(fixtures)
    return clamp(100 - ((avg - 1) / 4) * 100, 0, 100)


def fixture_label(score):
    if score >= 75:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 45:
        return "Mixed"
    return "Difficult"


def fixture_text(fixtures, limit=5):
    return " | ".join(
        f"GW{x['gw']} {x['opponent']} {'H' if x['home'] else 'A'}"
        for x in fixtures[:limit]
    )


def fixture_swing(data, team_id):
    base = selected_gameweek(data["events"])
    a = fixture_score(
        team_fixture_rows(data, team_id, gw=base, horizon=5)
    )
    b = fixture_score(
        team_fixture_rows(data, team_id, gw=base + 5, horizon=5)
    )
    return {
        "current_score": a,
        "next_score": b,
        "swing": b - a,
    }


# ============================================================
# PLAYER ANALYTICS
# ============================================================

def minutes_score(player):
    chance = safe_float(player.get("chance_next_round"), 100)
    minutes = safe_float(player.get("minutes"))
    starts = safe_float(player.get("starts"))

    if minutes <= 0:
        base = 15
    else:
        base = min(100, 45 + min(55, minutes / 1200 * 55))

    if starts > 0 and minutes > 0:
        start_rate = clamp(starts / max(1, minutes / 90), 0, 1)
        base = base * 0.65 + start_rate * 100 * 0.35

    return clamp(base * chance / 100, 0, 100)


def risk_score(player):
    injury_risk = 100 - safe_float(
        player.get("chance_next_round"), 100
    )
    low_minutes = 100 - minutes_score(player)
    news_penalty = 15 if player.get("news") else 0

    return clamp(
        injury_risk * 0.45
        + low_minutes * 0.45
        + news_penalty * 0.10,
        0,
        100,
    )


def player_radar_score(player, data):
    fixtures = team_fixture_rows(data, player["team_id"], horizon=5)
    f_score = fixture_score(fixtures)
    form = clamp(safe_float(player["form"]) * 10, 0, 100)
    xgi = clamp(
        safe_float(player["expected_goal_involvements_per_90"]) * 100,
        0,
        100,
    )
    ict = clamp(safe_float(player["ict_index"]), 0, 100)
    mins = minutes_score(player)
    risk = risk_score(player)

    score = (
        form * 0.20
        + xgi * 0.25
        + ict * 0.15
        + mins * 0.20
        + f_score * 0.20
    )

    return clamp(score - risk * 0.15, 0, 100)


def captain_score(player, data):
    fixtures = team_fixture_rows(data, player["team_id"], horizon=3)
    f_score = fixture_score(fixtures)
    form = clamp(safe_float(player["form"]) * 10, 0, 100)
    xgi = clamp(
        safe_float(player["expected_goal_involvements_per_90"]) * 100,
        0,
        100,
    )
    mins = minutes_score(player)
    bonus = clamp(safe_float(player["bonus"]) / 10, 0, 100)
    home_bonus = 7 if fixtures and fixtures[0]["home"] else 0
    risk = risk_score(player)

    score = (
        xgi * 0.32
        + form * 0.20
        + f_score * 0.25
        + mins * 0.15
        + bonus * 0.08
        + home_bonus
    )

    return clamp(score - risk * 0.15, 0, 100)


def differential_score(player, data):
    radar = player_radar_score(player, data)
    ownership_score = clamp(
        100 - safe_float(player["selected_by"]) * 4,
        0,
        100,
    )
    xgi = clamp(
        safe_float(player["expected_goal_involvements_per_90"]) * 100,
        0,
        100,
    )
    minutes = minutes_score(player)

    return clamp(
        radar * 0.40
        + ownership_score * 0.25
        + xgi * 0.20
        + minutes * 0.15,
        0,
        100,
    )


def add_scores(players, data):
    result = []
    for player in players:
        p = dict(player)
        p["radar_score"] = player_radar_score(player, data)
        p["captain_score"] = captain_score(player, data)
        p["differential_score"] = differential_score(player, data)
        p["minutes_score"] = minutes_score(player)
        p["risk_score"] = risk_score(player)
        result.append(p)
    return result


# ============================================================
# DEFENSIVE DATA
# ============================================================

def get_enrichment():
    return st.session_state.get("defensive_enrichment", {})


def set_enrichment(value):
    st.session_state["defensive_enrichment"] = value


def default_defensive_profile(team, data):
    home = safe_float(team.get("strength_defence_home"))
    away = safe_float(team.get("strength_defence_away"))
    strength = (home + away) / 2

    all_strengths = [
        safe_float(t.get("strength_defence_home"))
        + safe_float(t.get("strength_defence_away"))
        for t in data["teams"].values()
    ]

    low = min(all_strengths) if all_strengths else 1
    high = max(all_strengths) if all_strengths else 100
    normalized = (strength * 2 - low) / max(1, high - low)
    vulnerability = clamp(100 - normalized * 100, 0, 100)

    return {
        "team_id": team["id"],
        "team": team["name"],
        "source": "FPL API proxy",
        "confidence": "Proxy",
        "defensive_strength": clamp(100 - vulnerability, 0, 100),
        "vulnerability": vulnerability,
        "left": clamp(vulnerability * 0.95 + (100 - home) * 0.05, 0, 100),
        "center": clamp(vulnerability * 1.08, 0, 100),
        "right": clamp(vulnerability * 0.92 + (100 - away) * 0.08, 0, 100),
    }


def merged_defensive_profile(team, data):
    base = default_defensive_profile(team, data)
    extra = get_enrichment().get(str(team["id"]))

    if not extra:
        return base

    merged = dict(base)

    for key in [
        "left",
        "center",
        "right",
        "vulnerability",
        "defensive_strength",
    ]:
        if extra.get(key) is not None:
            merged[key] = safe_float(extra[key], merged[key])

    merged["source"] = extra.get("source", "Owner enrichment")
    merged["confidence"] = extra.get("confidence", "Owner data")
    merged["gw"] = extra.get("gw")
    merged["notes"] = extra.get("notes", "")
    return merged


def defensive_zone_rank(profile):
    zones = {
        "LEFT": safe_float(profile.get("left")),
        "CENTER": safe_float(profile.get("center")),
        "RIGHT": safe_float(profile.get("right")),
    }
    return sorted(zones.items(), key=lambda x: x[1], reverse=True)


# ============================================================
# FOOTBALL PITCH VISUAL
# ============================================================

def draw_defensive_pitch(profile, team_name):
    values = {
        "LEFT": safe_float(profile.get("left")),
        "CENTER": safe_float(profile.get("center")),
        "RIGHT": safe_float(profile.get("right")),
    }

    ranked = sorted(values.items(), key=lambda x: x[1], reverse=True)

    colors = ["#ff3d4d", "#ff9d2e", "#ffd83d"]

    fig = go.Figure()

    # Pitch
    fig.add_shape(
        type="rect",
        x0=0, y0=0, x1=100, y1=60,
        line=dict(color="rgba(255,255,255,.75)", width=2),
        fillcolor="#137548",
    )

    # Halfway line
    fig.add_shape(
        type="line",
        x0=50, y0=0, x1=50, y1=60,
        line=dict(color="rgba(255,255,255,.60)", width=2),
    )

    # Centre circle
    fig.add_shape(
        type="circle",
        x0=42, y0=22, x1=58, y1=38,
        line=dict(color="rgba(255,255,255,.60)", width=2),
    )

    # Opponent goal / attack direction
    fig.add_shape(
        type="rect",
        x0=98.3, y0=24, x1=100, y1=36,
        line=dict(color="#ffffff", width=3),
        fillcolor="rgba(255,255,255,.15)",
    )

    # Penalty box
    fig.add_shape(
        type="rect",
        x0=72, y0=11, x1=100, y1=49,
        line=dict(color="rgba(255,255,255,.65)", width=2),
        fillcolor="rgba(255,255,255,.025)",
    )

    # Six-yard box
    fig.add_shape(
        type="rect",
        x0=88, y0=21, x1=100, y1=39,
        line=dict(color="rgba(255,255,255,.65)", width=2),
        fillcolor="rgba(255,255,255,.025)",
    )

    # Zone dividers
    for x in [33.33, 66.66]:
        fig.add_shape(
            type="line",
            x0=x, y0=0, x1=x, y1=60,
            line=dict(
                color="rgba(255,255,255,.22)",
                width=1,
                dash="dot",
            ),
        )

    zone_x = {"LEFT": 16.66, "CENTER": 50, "RIGHT": 83.33}

    # Labels
    for zone, value in values.items():
        fig.add_annotation(
            x=zone_x[zone],
            y=56,
            text=f"<b>{zone}</b><br>{value:.0f}/100",
            showarrow=False,
            font=dict(color="white", size=12),
            bgcolor="rgba(0,0,0,.35)",
            bordercolor="rgba(255,255,255,.22)",
            borderwidth=1,
            borderpad=5,
        )

    # Three ranked arrows toward goal
    start_positions = {
        "LEFT": 14,
        "CENTER": 50,
        "RIGHT": 84,
    }

    y_positions = [13, 30, 47]

    for rank, (zone, value) in enumerate(ranked[:3]):
        color = colors[rank]
        start_x = start_positions[zone]
        start_y = y_positions[rank]

        fig.add_annotation(
            x=96,
            y=start_y,
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

        fig.add_annotation(
            x=start_x,
            y=start_y,
            text=f"<b>#{rank + 1}</b>",
            showarrow=False,
            font=dict(color="#071018", size=11),
            bgcolor=color,
            bordercolor=color,
            borderwidth=1,
            borderpad=4,
        )

    fig.add_annotation(
        x=50,
        y=-4,
        text=f"<b>{team_name}</b> — Defensive Opportunity Map",
        showarrow=False,
        font=dict(color="white", size=14),
    )

    fig.update_layout(
        height=410,
        margin=dict(l=8, r=8, t=10, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#137548",
        xaxis=dict(visible=False, range=[0, 100], fixedrange=True),
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

def verdict_for_player(player, data, purpose="general"):
    if purpose == "captain":
        score = captain_score(player, data)
    elif purpose == "differential":
        score = differential_score(player, data)
    else:
        score = player_radar_score(player, data)

    risk = risk_score(player)

    risk_label = (
        "Low" if risk < 25
        else "Medium" if risk < 55
        else "High"
    )

    confidence = (
        "Very High" if score >= 80
        else "High" if score >= 70
        else "Medium" if score >= 60
        else "Low"
    )

    reasons = []

    if safe_float(player["form"]) >= 5:
        reasons.append("strong recent form")

    if safe_float(
        player["expected_goal_involvements_per_90"]
    ) >= 0.40:
        reasons.append("strong xGI/90")

    if minutes_score(player) >= 75:
        reasons.append("good minutes security")

    if fixture_score(
        team_fixture_rows(data, player["team_id"], horizon=3)
    ) >= 65:
        reasons.append("favorable fixtures")

    if not reasons:
        reasons.append("balanced profile")

    return {
        "score": score,
        "risk": risk_label,
        "confidence": confidence,
        "reason": ", ".join(reasons),
    }


def render_verdict(main, reason, confidence="Medium", risk="Medium", kicker="FPL HOME VERDICT"):
    st.markdown(
        f""" <div class="verdict"> <div class="verdict-kicker">{kicker}</div> <div class="verdict-main">{main}</div> <div> {risk_badge(risk)} <span class="badge blue">Confidence: {confidence}</span> </div> <div class="subtle" style="margin-top:8px">{reason}</div> </div> """,
        unsafe_allow_html=True,
    )


# ============================================================
# HOME
# ============================================================

def home(data):
    gw = selected_gameweek(data["events"])
    players = add_scores(data["players"], data)
    active = [p for p in players if p["status"] == "a"]

    ranked = sorted(
        [
            p for p in active
            if p["position"] in ["MID", "FWD"] and p["minutes"] > 250
        ],
        key=lambda p: p["captain_score"],
        reverse=True,
    )

    top = ranked[:3]

    best_teams = sorted(
        data["teams"].values(),
        key=lambda t: fixture_score(
            team_fixture_rows(data, t["id"], horizon=5)
        ),
        reverse=True,
    )[:3]

    st.markdown(
        f""" <div class="topbar"> <div class="brand">⚽ FPL <span>HOME</span></div> <div class="subtle">Decision Support · GW {gw}</div> </div> """,
        unsafe_allow_html=True,
    )

    st.title("🏠 Home")
    st.caption("Focus on the decisions that matter most this Gameweek.")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f""" <div class="metric-card"> <div class="metric-label">GAMEWEEK</div> <div class="metric-value">GW {gw}</div> <div class="metric-sub">selected planning point</div> </div> """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f""" <div class="metric-card"> <div class="metric-label">PLAYERS</div> <div class="metric-value">{len(active)}</div> <div class="metric-sub">active FPL players</div> </div> """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            """ <div class="metric-card"> <div class="metric-label">FPL DATA</div> <div class="metric-value">LIVE</div> <div class="metric-sub">public FPL API</div> </div> """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f""" <div class="metric-card"> <div class="metric-label">ENRICHMENT</div> <div class="metric-value">{len(get_enrichment())}</div> <div class="metric-sub">owner profiles</div> </div> """,
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
            key=lambda p: (
                p["expected_goal_involvements_per_90"],
                p["differential_score"],
            ),
            reverse=True,
        )[0]

        a, b = st.columns(2)

        with a:
            v = verdict_for_player(safe_pick, data, "captain")
            render_verdict(
                f"SAFE PICK · {safe_pick['name']}",
                f"{safe_pick['team_short']} · Captain Score {safe_pick['captain_score']:.1f}. {v['reason']}.",
                v["confidence"],
                v["risk"],
                "SAFE CAPTAIN",
            )

        with b:
            render_verdict(
                f"HIGH UPSIDE · {upside['name']}",
                f"{upside['team_short']} · xGI/90 {upside['expected_goal_involvements_per_90']:.2f}. Higher upside can come with more variance.",
                "Medium",
                "Medium",
                "HIGH UPSIDE",
            )

    st.markdown(
        '<div class="section-title">🛡️ Defensive Opportunity</div>',
        unsafe_allow_html=True,
    )

    zone_rows = []
    for team in data["teams"].values():
        profile = merged_defensive_profile(team, data)
        top_zone = defensive_zone_rank(profile)[0]
        zone_rows.append({
            "Team": team["name"],
            "Top Weak Zone": top_zone[0],
            "Vulnerability": round(top_zone[1], 0),
            "Data": profile["source"],
        })

    st.dataframe(
        pd.DataFrame(zone_rows).sort_values(
            "Vulnerability", ascending=False
        ).head(5),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        '<div class="section-title">📅 Fixture Edge</div>',
        unsafe_allow_html=True,
    )

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Team": team["name"],
                    "Fixture Score": round(
                        fixture_score(
                            team_fixture_rows(
                                data, team["id"], horizon=5
                            )
                        ),
                        0,
                    ),
                    "Run": fixture_text(
                        team_fixture_rows(
                            data, team["id"], horizon=5
                        )
                    ),
                }
                for team in best_teams
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        '<div class="disclaimer">Model scores are decision-support signals, not predicted FPL points or guarantees.</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# SEARCH
# ============================================================

def global_search(data):
    st.title("🔎 Search")

    query = st.text_input(
        "Search players or clubs",
        placeholder="e.g. Salah, Haaland, Liverpool...",
    ).strip().lower()

    if not query:
        st.info("Search any player or Premier League club.")
        return

    players = add_scores(data["players"], data)

    hits = [
        p for p in players
        if query in p["name"].lower()
        or query in p["web_name"].lower()
        or query in p["team"].lower()
        or query in p["team_short"].lower()
    ][:20]

    if hits:
        st.subheader("Players")

        for p in hits:
            st.markdown(
                f""" <div class="player-card"> <b>{p['name']}</b> · {p['team_short']} · {p['position']}<br> <span class="subtle"> {money(p['price'])} · Form {p['form']:.1f} · Radar {p['radar_score']:.1f} </span> </div> """,
                unsafe_allow_html=True,
            )

            if st.button(
                f"Open {p['web_name']}",
                key=f"search_{p['id']}",
            ):
                st.session_state["selected_player_id"] = p["id"]
                st.session_state["page"] = "Player Profile"
                st.rerun()

    teams = [
        t for t in data["teams"].values()
        if query in t["name"].lower()
        or query in t["short_name"].lower()
    ]

    if teams:
        st.subheader("Clubs")

        for team in teams:
            fixtures = team_fixture_rows(
                data, team["id"], horizon=5
            )
            st.markdown(
                f""" <div class="player-card"> <b>{team['name']}</b> · Fixture Score {fixture_score(fixtures):.0f}<br> <span class="subtle">{fixture_text(fixtures)}</span> </div> """,
                unsafe_allow_html=True,
            )

    if not hits and not teams:
        st.warning("No matching player or club found.")


# ============================================================
# PLAYER PROFILE
# ============================================================

def player_profile(data):
    st.title("👤 Player Profile")

    players = add_scores(data["players"], data)

    labels = {
        f"{p['name']} — {p['team_short']} — {money(p['price'])}": p["id"]
        for p in players
    }

    current_id = st.session_state.get("selected_player_id")
    index = 0

    if current_id:
        for i, pid in enumerate(labels.values()):
            if pid == current_id:
                index = i
                break

    selected = st.selectbox(
        "Player",
        list(labels.keys()),
        index=index,
    )

    player = next(
        p for p in players
        if p["id"] == labels[selected]
    )

    st.session_state["selected_player_id"] = player["id"]

    verdict = verdict_for_player(player, data)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Price", money(player["price"]))
    c2.metric("Form", f"{player['form']:.1f}")
    c3.metric(
        "xGI/90",
        f"{player['expected_goal_involvements_per_90']:.2f}",
    )
    c4.metric("Ownership", pct(player["selected_by"]))

    render_verdict(
        f"{player['name']} — Radar {verdict['score']:.1f}/100",
        f"{verdict['reason']}. Minutes score {player['minutes_score']:.0f}/100.",
        verdict["confidence"],
        verdict["risk"],
    )

    st.subheader("📊 Core FPL Data")

    core = pd.DataFrame(
        [
            {
                "Total Points": player["total_points"],
                "GW Points": player["event_points"],
                "PPG": player["points_per_game"],
                "Goals": player["goals"],
                "Assists": player["assists"],
                "Bonus": player["bonus"],
                "BPS": player["bps"],
                "Minutes": player["minutes"],
                "xG": player["expected_goals"],
                "xA": player["expected_assists"],
                "xGI": player["expected_goal_involvements"],
                "ICT": player["ict_index"],
            }
        ]
    )

    st.dataframe(
        core.round(2),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("📅 Fixtures")

    fixtures = team_fixture_rows(
        data, player["team_id"], horizon=5
    )

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "GW": f["gw"],
                    "Opponent": f["opponent"],
                    "H/A": "H" if f["home"] else "A",
                    "Difficulty": f["difficulty"],
                }
                for f in fixtures
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("📰 FPL Status / News")

    if player["news"]:
        st.warning(player["news"])
    else:
        st.success("No FPL news supplied by the API.")

    if st.button(
        "Load detailed player history",
        use_container_width=True,
    ):
        try:
            summary = load_player_summary(player["id"])
            history = summary.get("history", [])

            if history:
                df = pd.DataFrame(history)
                columns = [
                    c for c in [
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
                    df[columns].tail(10),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No detailed history returned.")
        except Exception as exc:
            st.error(f"Unable to load player history: {exc}")


# ============================================================
# DEFENSIVE RADAR
# ============================================================

def defensive_radar(data):
    st.title("🛡️ Defensive Radar")
    st.caption(
        "Football-pitch opportunity map. "
        "Arrows move toward the selected team's goal."
    )

    team_names = sorted(
        t["name"] for t in data["teams"].values()
    )

    selected_name = st.selectbox(
        "Select team",
        team_names,
    )

    team = next(
        t for t in data["teams"].values()
        if t["name"] == selected_name
    )

    profile = merged_defensive_profile(team, data)

    st.markdown(
        """ <div class="pitch-legend"> <div class="pitch-legend-item"> <span class="pitch-dot dot-red"></span> #1 Highest Opportunity </div> <div class="pitch-legend-item"> <span class="pitch-dot dot-orange"></span> #2 Highest Opportunity </div> <div class="pitch-legend-item"> <span class="pitch-dot dot-yellow"></span> #3 Highest Opportunity </div> </div> """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.35, 1])

    with left:
        st.plotly_chart(
            draw_defensive_pitch(profile, selected_name),
            use_container_width=True,
            config={
                "displayModeBar": False,
                "responsive": True,
            },
        )

    with right:
        st.markdown(
            f""" <div class="card"> <div class="section-title">Defensive Signal</div> <b>Data source:</b> {profile['source']}<br><br> <b>Confidence:</b> {profile.get('confidence', '')}<br><br> <b>Overall vulnerability:</b> {profile['vulnerability']:.0f}/100<br><br> <b>Defensive strength:</b> {profile['defensive_strength']:.0f}/100 </div> """,
            unsafe_allow_html=True,
        )

        if profile.get("notes"):
            st.info(profile["notes"])

    st.subheader("🎯 Top 3 Defensive Opportunity Zones")

    top3 = defensive_zone_rank(profile)[:3]
    columns = st.columns(3)

    for i, (column, item) in enumerate(zip(columns, top3)):
        zone, value = item
        icon = ["🟥", "🟧", "🟨"][i]

        with column:
            st.markdown(
                f""" <div class="zone-card"> <div class="metric-label">{icon} OPPORTUNITY #{i + 1}</div> <div class="metric-value">{zone}</div> <div class="metric-sub">Vulnerability {value:.0f}/100</div> </div> """,
                unsafe_allow_html=True,
            )

    st.warning(
        "If the source is FPL API proxy, the LEFT/CENTER/RIGHT "
        "values are analytical proxies from FPL team-strength fields. "
        "They are not claimed Opta or StatsBomb event data."
    )


# ============================================================
# FIXTURES
# ============================================================

def fixtures_page(data):
    gw = selected_gameweek(data["events"])

    st.title("🟢🟡🔴 Fixture Difficulty")
    st.caption(
        f"Fixture analysis starting from GW {gw}. "
        "Lower FPL fixture difficulty means a better fixture."
    )

    rows = []

    for team in data["teams"].values():
        fixtures = team_fixture_rows(
            data, team["id"], gw=gw, horizon=5
        )
        score = fixture_score(fixtures)
        swing = fixture_swing(data, team["id"])

        rows.append({
            "Team": team["name"],
            "Score": round(score, 1),
            "Verdict": fixture_label(score),
            "GW Run": fixture_text(fixtures),
            "Swing": round(swing["swing"], 1),
        })

    df = pd.DataFrame(rows).sort_values(
        "Score", ascending=False
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("🔄 Fixture Swing")

    st.dataframe(
        df.sort_values("Swing", ascending=False)[
            ["Team", "Score", "Swing", "GW Run"]
        ],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# CAPTAINCY
# ============================================================

def captaincy(data):
    st.title("👑 Captaincy")
    st.caption(
        "Safe Pick + High Upside. "
        "Scores are model signals, not projected points."
    )

    players = add_scores(data["players"], data)

    eligible = [
        p for p in players
        if p["status"] == "a"
        and p["position"] in ["MID", "FWD"]
        and p["minutes"] > 250
    ]

    ranked = sorted(
        eligible,
        key=lambda p: p["captain_score"],
        reverse=True,
    )

    if not ranked:
        st.warning("No eligible captain candidates.")
        return

    safe_pick = ranked[0]

    upside = sorted(
        ranked,
        key=lambda p: (
            p["expected_goal_involvements_per_90"] * 0.55
            + p["captain_score"] * 0.25
            + (100 - p["selected_by"] * 2) * 0.20
        ),
        reverse=True,
    )[0]

    a, b = st.columns(2)

    with a:
        v = verdict_for_player(safe_pick, data, "captain")
        render_verdict(
            f"{safe_pick['name']} · {safe_pick['captain_score']:.1f}",
            f"{safe_pick['team_short']} · {v['reason']}.",
            v["confidence"],
            v["risk"],
            "SAFE PICK",
        )

    with b:
        v = verdict_for_player(upside, data, "captain")
        render_verdict(
            f"{upside['name']} · {upside['captain_score']:.1f}",
            f"{upside['team_short']} · xGI/90 {upside['expected_goal_involvements_per_90']:.2f}.",
            v["confidence"],
            v["risk"],
            "HIGH UPSIDE",
        )

    st.subheader("Top captain candidates")

    rows = []
    for rank, p in enumerate(ranked[:20], 1):
        v = verdict_for_player(p, data, "captain")

        rows.append({
            "Rank": rank,
            "Player": p["name"],
            "Team": p["team_short"],
            "Fixture": fixture_text(
                team_fixture_rows(data, p["team_id"], horizon=3), 3
            ),
            "Price": money(p["price"]),
            "Form": p["form"],
            "xGI/90": round(
                p["expected_goal_involvements_per_90"], 2
            ),
            "Minutes": round(p["minutes_score"]),
            "Captain Score": round(p["captain_score"], 1),
            "Risk": v["risk"],
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
    st.title("🔄 Transfer Planner")
    st.caption(
        "Connect a public FPL Team ID or select your squad manually."
    )

    players = add_scores(data["players"], data)

    team_id = st.number_input(
        "FPL Team ID (optional)",
        min_value=0,
        value=int(st.session_state.get("fpl_team_id", 0)),
        step=1,
    )

    if st.button("🔗 Load FPL Squad", use_container_width=True):
        if team_id <= 0:
            st.warning("Enter a valid FPL Team ID.")
        else:
            try:
                gw = selected_gameweek(data["events"])
                picks = load_team_picks(team_id, gw)
                ids = {
                    item["element"]
                    for item in picks.get("picks", [])
                }

                if ids:
                    st.session_state["fpl_team_id"] = int(team_id)
                    st.session_state["transfer_current_ids"] = ids
                    st.success(
                        f"Loaded {len(ids)} players from GW {gw}."
                    )
                else:
                    st.warning("No squad players were returned.")
            except Exception as exc:
                st.error(f"Could not load squad: {exc}")

    current_ids = set(
        st.session_state.get("transfer_current_ids", set())
    )

    labels = {
        f"{p['name']} — {p['team_short']} — {money(p['price'])}": p["id"]
        for p in players
        if p["status"] == "a"
    }

    if not current_ids:
        selected = st.multiselect(
            "Your current squad",
            list(labels.keys()),
            max_selections=15,
        )
        current_ids = {labels[item] for item in selected}

    free_transfers = st.number_input(
        "Free Transfers", 1, 5, 1
    )

    bank = st.number_input(
        "Money in Bank (£m)",
        0.0,
        20.0,
        0.0,
        0.1,
    )

    if not current_ids:
        st.info("Connect your FPL Team ID or select your squad.")
        return

    current = [
        p for p in players
        if p["id"] in current_ids
    ]

    out_candidates = sorted(
        current,
        key=lambda p: p["radar_score"],
    )

    st.subheader("🔻 Suggested OUT")

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Player": p["name"],
                    "Team": p["team_short"],
                    "Price": money(p["price"]),
                    "Radar": round(p["radar_score"], 1),
                    "Risk": (
                        "Low" if p["risk_score"] < 25
                        else "Medium" if p["risk_score"] < 55
                        else "High"
                    ),
                }
                for p in out_candidates
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    candidates = [
        p for p in players
        if p["status"] == "a"
        and p["id"] not in current_ids
    ]

    suggestions = []

    for out_player in out_candidates[:5]:
        max_price = out_player["price"] + bank

        same_pos = [
            p for p in candidates
            if p["position"] == out_player["position"]
            and p["price"] <= max_price
        ]

        for candidate in sorted(
            same_pos,
            key=lambda p: p["radar_score"],
            reverse=True,
        )[:5]:
            gain = (
                candidate["radar_score"]
                - out_player["radar_score"]
            )

            if gain > 0:
                suggestions.append({
                    "OUT": out_player["name"],
                    "IN": candidate["name"],
                    "Position": candidate["position"],
                    "Price": money(candidate["price"]),
                    "Radar Gain": round(gain, 1),
                    "IN Radar": round(candidate["radar_score"], 1),
                    "Risk": (
                        "Low" if candidate["risk_score"] < 25
                        else "Medium" if candidate["risk_score"] < 55
                        else "High"
                    ),
                })

    suggestions.sort(
        key=lambda x: x["Radar Gain"],
        reverse=True,
    )

    st.subheader("🔺 Suggested IN")

    if suggestions:
        st.dataframe(
            pd.DataFrame(suggestions[:20]),
            use_container_width=True,
            hide_index=True,
        )

        best = suggestions[0]

        render_verdict(
            f"{best['OUT']} → {best['IN']}",
            f"Model Radar gain +{best['Radar Gain']:.1f}. Decision support only.",
            "Medium",
            best["Risk"],
            "TRANSFER IDEA",
        )
    else:
        st.info(
            "No positive-Radar upgrade found under the current constraints."
        )

    st.caption(
        f"Free transfers selected: {free_transfers}. "
        "The planner does not pretend to know future points."
    )


# ============================================================
# TEAM OPTIMIZER
# ============================================================

def team_optimizer(data):
    st.title("🧠 Team Optimizer")

    budget = st.number_input(
        "Total squad budget (£m)",
        50.0,
        120.0,
        100.0,
        0.1,
    )

    strategy = st.selectbox(
        "Strategy",
        ["Safe", "Balanced", "Differential"],
    )

    ownership_weight = {
        "Safe": 0.20,
        "Balanced": 0.10,
        "Differential": -0.05,
    }[strategy]

    players = add_scores(data["players"], data)

    for p in players:
        ownership_component = clamp(
            p["selected_by"] * 4, 0, 100
        )
        p["optimizer_score"] = (
            p["radar_score"] * 0.80
            + ownership_component * ownership_weight
        )

    requirements = {
        "GKP": 2,
        "DEF": 5,
        "MID": 5,
        "FWD": 3,
    }

    selected = []
    team_counts = {}
    remaining = budget

    for position, needed in requirements.items():
        pool = sorted(
            [
                p for p in players
                if p["position"] == position
                and p["status"] == "a"
                and p["minutes"] > 100
            ],
            key=lambda p: p["optimizer_score"],
            reverse=True,
        )

        count = 0

        for p in pool:
            if count >= needed:
                break

            if remaining - p["price"] < 0:
                continue

            if team_counts.get(p["team_id"], 0) >= 3:
                continue

            selected.append(p)
            remaining -= p["price"]
            team_counts[p["team_id"]] = (
                team_counts.get(p["team_id"], 0) + 1
            )
            count += 1

    st.subheader("Recommended Squad")

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Player": p["name"],
                    "Team": p["team_short"],
                    "Pos": p["position"],
                    "Price": money(p["price"]),
                    "Score": round(p["optimizer_score"], 1),
                    "Ownership": pct(p["selected_by"]),
                }
                for p in selected
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    total = sum(p["price"] for p in selected)

    st.metric(
        "Squad Cost",
        f"£{total:.1f}m",
        f"£{budget - total:.1f}m remaining",
    )

    if len(selected) < 15:
        st.warning(
            "The transparent heuristic could not fill all 15 slots "
            "under the selected constraints."
        )

    st.caption(
        "Transparent heuristic optimizer. "
        "It does not claim to be an exact mathematical optimizer."
    )


# ============================================================
# GEMINI
# ============================================================

def get_gemini_client():
    if not GEMINI_AVAILABLE:
        return None, "google-genai is not installed."

    key = get_secret("GEMINI_API_KEY")

    if not key:
        return None, "GEMINI_API_KEY is not configured in Streamlit Secrets."

    try:
        return genai.Client(api_key=key), None
    except Exception as exc:
        return None, str(exc)


def build_ai_context(data):
    players = add_scores(data["players"], data)

    top = sorted(
        players,
        key=lambda p: p["radar_score"],
        reverse=True,
    )[:40]

    player_context = []

    for p in top:
        player_context.append({
            "name": p["name"],
            "team": p["team_short"],
            "position": p["position"],
            "price": round(p["price"], 1),
            "ownership": round(p["selected_by"], 1),
            "form": round(p["form"], 2),
            "xgi90": round(
                p["expected_goal_involvements_per_90"], 2
            ),
            "radar": round(p["radar_score"], 1),
            "captain": round(p["captain_score"], 1),
            "risk": round(p["risk_score"], 1),
        })

    team_context = []

    for team in data["teams"].values():
        fixtures = team_fixture_rows(
            data, team["id"], horizon=5
        )

        team_context.append({
            "team": team["name"],
            "short": team["short_name"],
            "fixture_score": round(
                fixture_score(fixtures), 1
            ),
            "fixtures": [
                {
                    "gw": f["gw"],
                    "opponent": f["opponent"],
                    "home": f["home"],
                    "difficulty": f["difficulty"],
                }
                for f in fixtures
            ],
            "defensive_profile": merged_defensive_profile(
                team, data
            ),
        })

    return {
        "gameweek": selected_gameweek(data["events"]),
        "players": player_context,
        "teams": team_context,
    }


def ai_answer(question, data):
    client, error = get_gemini_client()

    if error:
        return error

    context = build_ai_context(data)

    prompt = f""" You are Ask FPL HOME, an expert Fantasy Premier League decision-support assistant. Rules: - FPL API is authoritative for core FPL numbers. - Owner enrichment is optional and must be labeled as owner data. - Gemini must never invent prices, points, ownership, fixtures or history. - Model scores are not projected points. - Give a practical verdict, reasons, risk and an alternative when useful. - Never guarantee FPL points. Question: {question} Structured data: {json.dumps(context, ensure_ascii=False)} Return: Verdict Why Risk Alternative """

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


def ask_fpl_home(data):
    st.title("🤖 Ask FPL HOME")
    st.caption(
        "AI interpretation of FPL HOME structured data. "
        "Gemini does not create the underlying FPL numbers."
    )

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    for message in st.session_state["chat_history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input(
        "e.g. Salah or Haaland captain this GW?"
    )

    if question:
        st.session_state["chat_history"].append(
            {"role": "user", "content": question}
        )

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Ask FPL HOME is analyzing..."):
                answer = ai_answer(question, data)
            st.markdown(answer)

        st.session_state["chat_history"].append(
            {"role": "assistant", "content": answer}
        )


# ============================================================
# DATA CENTER AUTH
# ============================================================

def owner_unlock():
    password_configured = bool(
        get_secret("OWNER_PASSWORD")
    )

    if not password_configured:
        st.error(
            "OWNER_PASSWORD is missing from Streamlit Secrets."
        )
        st.info(
            "Data Center is locked until OWNER_PASSWORD is configured."
        )
        return False

    if st.session_state.get("owner_unlocked"):
        return True

    password = st.text_input(
        "Owner password",
        type="password",
    )

    if st.button(
        "🔐 Unlock Data Center",
        use_container_width=True,
    ):
        if password == get_secret("OWNER_PASSWORD"):
            st.session_state["owner_unlocked"] = True
            st.success("Owner access enabled for this session.")
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False


# ============================================================
# GEMINI IMAGE EXTRACTION
# ============================================================

def gemini_image_to_structured( uploaded_file, team_hint, gw_hint, ):
    client, error = get_gemini_client()

    if error:
        return None, error

    image_bytes = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/jpeg"

    schema = {
        "team_name": "string or null",
        "gameweek": "integer or null",
        "left_vulnerability": "number 0-100 or null",
        "center_vulnerability": "number 0-100 or null",
        "right_vulnerability": "number 0-100 or null",
        "overall_vulnerability": "number 0-100 or null",
        "defensive_strength": "number 0-100 or null",
        "source_label": "string",
        "confidence": "High/Medium/Low/Unknown",
        "notes": "string",
    }

    prompt = f""" You are the image extraction layer inside FPL HOME. Analyze ONLY the uploaded image. Extract only values visibly present in the image. Do not invent or infer missing numbers. This is owner-supplied enrichment, not core FPL data. Team hint: {team_hint} Gameweek hint: {gw_hint} Return JSON matching this schema: {json.dumps(schema, indent=2)} """

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
                response_mime_type="application/json",
            ),
        )

        return json.loads(response.text), None

    except Exception as exc:
        return None, str(exc)


# ============================================================
# DATA CENTER
# ============================================================

def data_center(data):
    st.markdown(
        """ <div class="admin-header"> <div class="admin-title">🗄️ FPL HOME Data Center</div> <div class="admin-subtitle"> Owner-only enrichment center. Upload screenshots, extract visible tactical data with Gemini, review it, then publish it into FPL HOME. </div> </div> """,
        unsafe_allow_html=True,
    )

    if not owner_unlock():
        return

    st.success("Owner mode is active for this browser session.")

    st.subheader("📚 Data Architecture")

    st.markdown(
        """ <div class="card"> <b>FPL API</b><br> Core FPL numbers, players, teams and fixtures. <br><br> <b>Owner Enrichment</b><br> Optional defensive/tactical information from owner screenshots. <br><br> <b>Gemini</b><br> Image interpretation and structured extraction only. </div> """,
        unsafe_allow_html=True,
    )

    st.subheader("📸 1. Upload Image")

    team_names = sorted(
        t["name"] for t in data["teams"].values()
    )

    team_name = st.selectbox(
        "Team represented in the image",
        team_names,
    )

    gw = st.number_input(
        "Gameweek represented",
        min_value=1,
        max_value=50,
        value=selected_gameweek(data["events"]),
    )

    uploaded = st.file_uploader(
        "Upload defensive / tactical screenshot",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=False,
    )

    if uploaded:
        st.image(
            uploaded,
            caption="Uploaded source image",
            use_container_width=True,
        )

        if st.button(
            "🤖 2. Analyze Image with Gemini",
            use_container_width=True,
        ):
            with st.spinner(
                "Gemini is extracting visible structured data..."
            ):
                result, error = gemini_image_to_structured(
                    uploaded,
                    team_name,
                    gw,
                )

            if error:
                st.error(error)
            else:
                st.session_state["last_extracted_enrichment"] = result
                st.session_state["last_extracted_team"] = team_name
                st.session_state["last_extracted_gw"] = gw
                st.success("Image analyzed successfully.")

    extracted = st.session_state.get(
        "last_extracted_enrichment"
    )

    if extracted:
        st.divider()
        st.subheader("✏️ 3. Review & Edit")

        st.warning(
            "Review the extracted values before publishing. "
            "These values are owner enrichment, not core FPL truth."
        )

        editable = {
            "left": extracted.get("left_vulnerability"),
            "center": extracted.get("center_vulnerability"),
            "right": extracted.get("right_vulnerability"),
            "vulnerability": extracted.get("overall_vulnerability"),
            "defensive_strength": extracted.get("defensive_strength"),
        }

        cols = st.columns(5)

        for col, key in zip(
            cols,
            ["left", "center", "right", "vulnerability", "defensive_strength"],
        ):
            value = editable[key]
            value = safe_float(value, 0) if value is not None else 0

            with col:
                editable[key] = st.number_input(
                    key.replace("_", " ").title(),
                    min_value=0.0,
                    max_value=100.0,
                    value=float(value),
                    step=1.0,
                    key=f"dc_{key}",
                )

        notes = st.text_area(
            "Owner notes",
            extracted.get("notes", ""),
            key="dc_notes",
        )

        source_label = st.text_input(
            "Source label",
            extracted.get(
                "source_label",
                "Owner-uploaded image",
            ),
            key="dc_source",
        )

        confidence_options = [
            "High",
            "Medium",
            "Low",
            "Unknown",
        ]

        extracted_confidence = extracted.get(
            "confidence",
            "Unknown",
        )

        confidence_index = (
            confidence_options.index(extracted_confidence)
            if extracted_confidence in confidence_options
            else 3
        )

        confidence = st.selectbox(
            "Confidence",
            confidence_options,
            index=confidence_index,
            key="dc_confidence",
        )

        publish_team = st.session_state.get(
            "last_extracted_team",
            team_name,
        )

        if st.button(
            "✅ 4. Publish Enrichment",
            use_container_width=True,
        ):
            team = next(
                t for t in data["teams"].values()
                if t["name"] == publish_team
            )

            enrichment = get_enrichment()

            enrichment[str(team["id"])] = {
                **editable,
                "source": source_label or "Owner-uploaded image",
                "confidence": confidence,
                "notes": notes,
                "gw": int(
                    st.session_state.get(
                        "last_extracted_gw",
                        gw,
                    )
                ),
                "updated": utc_now(),
                "owner_enrichment": True,
            }

            set_enrichment(enrichment)

            st.session_state["last_extracted_enrichment"] = None

            st.success(
                f"Enrichment published for {publish_team}."
            )

            st.rerun()

    st.divider()
    st.subheader("📋 Published Enrichment")

    enrichment = get_enrichment()

    if enrichment:
        rows = []

        for team_id, item in enrichment.items():
            team = data["teams"].get(int(team_id), {})

            rows.append({
                "Team": team.get("name", team_id),
                "GW": item.get("gw"),
                "Left": item.get("left"),
                "Center": item.get("center"),
                "Right": item.get("right"),
                "Overall": item.get("vulnerability"),
                "Source": item.get("source"),
                "Confidence": item.get("confidence"),
                "Updated": item.get("updated", ""),
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

    if st.button(
        "🗑️ Clear all session enrichment",
        use_container_width=True,
    ):
        st.session_state["defensive_enrichment"] = {}
        st.rerun()

    st.markdown(
        '<div class="disclaimer">Published enrichment is session-based in this version and is not automatically persisted to a database.</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# DATA HEALTH
# ============================================================

def data_health_page(data, api_ok=True):
    st.title("🩺 Data Health")
    st.caption(
        "Transparent view of the data layers used by FPL HOME."
    )

    rows = [
        {
            "Layer": "FPL API",
            "Role": "Core FPL numbers, players, teams and fixtures",
            "Status": "Connected" if api_ok else "Error",
            "API Key": "Not required",
        },
        {
            "Layer": "Owner enrichment",
            "Role": "Optional defensive/tactical image enrichment",
            "Status": (
                f"{len(get_enrichment())} team profiles"
                if get_enrichment()
                else "None"
            ),
            "API Key": "Owner only",
        },
        {
            "Layer": "Gemini",
            "Role": "Image extraction and AI explanation",
            "Status": (
                "Configured"
                if get_secret("GEMINI_API_KEY")
                else "Not configured"
            ),
            "API Key": "Streamlit Secrets",
        },
    ]

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Teams", len(data["teams"]))
    c2.metric("Players", len(data["players"]))
    c3.metric("Fixtures", len(data["fixtures"]))

    st.subheader("Rules")
    st.markdown(
        """ - FPL API is the source of core FPL numbers. - Owner uploads are enrichment only. - Gemini interprets uploaded images and explains data. - Normal users do not upload data. - Normal users do not enter API keys. - No historical prices are invented. """
    )


# ============================================================
# NAVIGATION
# ============================================================

NAV_ITEMS = {
    "🏠 Home": "Home",
    "🔎 Search": "Search",
    "👤 Player": "Player Profile",
    "🛡️ Defensive Radar": "Defensive Radar",
    "📅 Fixtures": "Fixtures",
    "👑 Captaincy": "Captaincy",
    "🔄 Transfers": "Transfer Planner",
    "🧠 Optimizer": "Team Optimizer",
    "🤖 Ask FPL HOME": "Ask FPL HOME",
    "🗄️ Data Center": "Data Center",
    "🩺 Data Health": "Data Health",
}


def top_navigation(data):
    labels = list(NAV_ITEMS.keys())
    current_page = st.session_state.get("page", "Home")

    default_index = 0
    for i, page in enumerate(NAV_ITEMS.values()):
        if page == current_page:
            default_index = i
            break

    selected_nav = st.radio(
        "Navigation",
        labels,
        index=default_index,
        horizontal=True,
        label_visibility="collapsed",
    )

    st.session_state["page"] = NAV_ITEMS[selected_nav]

    gw_options = [
        e["id"] for e in data["events"]
        if e.get("id") is not None
    ]

    current_gw = selected_gameweek(data["events"])

    if gw_options:
        index = (
            gw_options.index(current_gw)
            if current_gw in gw_options
            else 0
        )

        selected_gw = st.selectbox(
            "Gameweek",
            gw_options,
            index=index,
            key="global_gw_selector",
        )

        st.session_state["selected_gw"] = selected_gw


# ============================================================
# MAIN
# ============================================================

def main():
    raw, api_ok, error = load_data_with_status()

    if not api_ok:
        st.error("Unable to load FPL API data.")
        st.code(str(error))

        if st.button("🔄 Retry"):
            st.cache_data.clear()
            st.rerun()

        return

    data = normalize_data(raw)

    top_navigation(data)

    if st.button("↻ Refresh", key="global_refresh"):
        st.cache_data.clear()
        st.rerun()

    page = st.session_state.get("page", "Home")

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
        data_health_page(data, api_ok=True)


if __name__ == "__main__":
    main()
