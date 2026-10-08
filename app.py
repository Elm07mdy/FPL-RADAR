
# FPL HOME — Streamlit single-file application
# Built from the previous FPL Radar codebase.
#
# Core data contract:
# FPL API = source of core FPL numbers
# Owner files = optional defensive-data enrichment
# Gemini = image interpretation + explanation, never the source of core FPL numbers
#
# Suggested secrets:
# GEMINI_API_KEY = "..."
# OWNER_PASSWORD = "..."
#
# Run:
# pip install streamlit requests pandas plotly openpyxl google-genai
# streamlit run fpl_home.py

import os
import json
import math
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

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
APP_VERSION = "4.0"

FPL_BASE = "https://fantasy.premierleague.com/api"
BOOTSTRAP_URL = f"{FPL_BASE}/bootstrap-static/"
FIXTURES_URL = f"{FPL_BASE}/fixtures/"
REQUEST_TIMEOUT = 20
CACHE_TTL = 300

# Change this in Streamlit Secrets if desired.
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
# MOBILE-FIRST UI
# ============================================================

st.markdown(
    """ <style> :root { --bg: #071018; --surface: #0d1822; --surface-2: #101e2a; --border: #223545; --text: #f4f7fa; --muted: #a9b6c2; --green: #35d39a; --yellow: #f2c75c; --red: #ff7078; --blue: #68a9ff; } html, body, [class*="css"] { font-family: Inter, Arial, sans-serif; } .stApp { background: radial-gradient(circle at 5% 0%, rgba(53,211,154,.09), transparent 28%), radial-gradient(circle at 95% 10%, rgba(104,169,255,.08), transparent 30%), var(--bg); color: var(--text); } .block-container { max-width: 1380px; padding-top: .7rem; padding-bottom: 4rem; padding-left: .85rem; padding-right: .85rem; } section[data-testid="stSidebar"] { display: none; } .topbar { position: sticky; top: 0; z-index: 999; background: rgba(7,16,24,.92); backdrop-filter: blur(14px); border-bottom: 1px solid var(--border); padding: 9px 0 10px 0; margin-bottom: 18px; } .brand { font-size: 22px; font-weight: 900; letter-spacing: -.5px; } .brand span { color: var(--green); } .subtle { color: var(--muted); font-size: 12px; } .card { background: linear-gradient(145deg, rgba(16,30,42,.96), rgba(10,20,29,.96)); border: 1px solid var(--border); border-radius: 17px; padding: 16px; margin-bottom: 13px; } .metric-card { background: var(--surface); border: 1px solid var(--border); border-radius: 15px; padding: 14px; min-height: 94px; } .metric-label { color: var(--muted); font-size: 11px; font-weight: 800; letter-spacing: .7px; } .metric-value { font-size: 25px; font-weight: 900; margin-top: 5px; } .metric-sub { color: var(--muted); font-size: 11px; margin-top: 3px; } .verdict { border: 1px solid #2a624e; border-radius: 17px; padding: 17px; background: linear-gradient(135deg, rgba(53,211,154,.12), rgba(11,23,32,.96)); } .verdict-kicker { color: var(--green); font-size: 11px; font-weight: 900; letter-spacing: 1px; } .verdict-main { font-size: 24px; font-weight: 900; margin: 5px 0; } .badge { display: inline-block; border-radius: 999px; padding: 4px 8px; font-size: 10px; font-weight: 900; margin-right: 5px; } .green { background: rgba(53,211,154,.14); color: #71e8bd; } .yellow { background: rgba(242,199,92,.14); color: #f4d476; } .red { background: rgba(255,112,120,.14); color: #ff9ba0; } .blue { background: rgba(104,169,255,.14); color: #94c3ff; } .section-title { font-size: 18px; font-weight: 900; margin: 8px 0 11px; } .player-card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 13px; margin-bottom: 8px; } .zone-card { border: 1px solid var(--border); border-radius: 14px; padding: 13px; background: var(--surface); } .disclaimer { color: var(--muted); font-size: 11px; line-height: 1.5; } @media (max-width: 768px) { .block-container { padding-left: .65rem; padding-right: .65rem; } .brand { font-size: 19px; } .metric-card { min-height: 80px; } .metric-value { font-size: 21px; } .verdict-main { font-size: 20px; } h1 { font-size: 27px !important; } h2 { font-size: 22px !important; } h3 { font-size: 18px !important; } } </style> """,
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


def risk_badge(risk):
    risk = str(risk)
    cls = "green" if risk.lower() == "low" else "yellow" if risk.lower() == "medium" else "red"
    return f'<span class="badge {cls}">{risk}</span>'


def difficulty_badge(difficulty):
    d = safe_int(difficulty, 3)
    if d <= 2:
        return '<span class="badge green">EASY</span>'
    if d == 3:
        return '<span class="badge yellow">MIXED</span>'
    return '<span class="badge red">HARD</span>'


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


# ============================================================
# FPL API ENGINE
# ============================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_json(url: str):
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": "FPL-HOME/4.0"},
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
        "updated": utc_now(),
    }


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_player_summary(player_id: int):
    return fetch_json(f"{FPL_BASE}/element-summary/{player_id}/")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_fpl_team(team_id: int):
    entry = fetch_json(f"{FPL_BASE}/entry/{int(team_id)}/")
    history = None
    try:
        history = fetch_json(f"{FPL_BASE}/entry/{int(team_id)}/history/")
    except Exception:
        pass
    return {"entry": entry, "history": history}


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_fpl_team_picks(team_id: int, gw: int):
    return fetch_json(f"{FPL_BASE}/entry/{int(team_id)}/event/{int(gw)}/picks/")


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
            "code": t.get("code", 0),
            "strength": safe_float(t.get("strength")),
            "strength_attack_home": safe_float(t.get("strength_attack_home")),
            "strength_attack_away": safe_float(t.get("strength_attack_away")),
            "strength_defence_home": safe_float(t.get("strength_defence_home")),
            "strength_defence_away": safe_float(t.get("strength_defence_away")),
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
            "name": f"{p.get('first_name','')} {p.get('second_name','')}".strip(),
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
            "expected_goal_involvements": safe_float(p.get("expected_goal_involvements")),
            "expected_goals_per_90": safe_float(p.get("expected_goals_per_90")),
            "expected_assists_per_90": safe_float(p.get("expected_assists_per_90")),
            "expected_goal_involvements_per_90": safe_float(
                p.get("expected_goal_involvements_per_90")
            ),
            "chance_next_round": safe_float(p.get("chance_of_playing_next_round"), 100),
            "chance_this_round": safe_float(p.get("chance_of_playing_this_round"), 100),
            "status": p.get("status", "a"),
            "news": p.get("news", ""),
            "starts": safe_float(p.get("starts")),
            "clean_sheets_per_90": safe_float(p.get("clean_sheets_per_90")),
            "form_rank": safe_float(p.get("form_rank")),
            "points_per_game_rank": safe_float(p.get("points_per_game_rank")),
            # FPL API price movement fields. These are current API fields,
            # not invented historical prices.
            "cost_change_event": safe_float(p.get("cost_change_event")),
            "cost_change_start": safe_float(p.get("cost_change_start")),
            "cost_change_event_fall": safe_float(p.get("cost_change_event_fall")),
            "cost_change_start_fall": safe_float(p.get("cost_change_start_fall")),
            "transfers_in_event": safe_float(p.get("transfers_in_event")),
            "transfers_out_event": safe_float(p.get("transfers_out_event")),
            "transfers_in": safe_float(p.get("transfers_in")),
            "transfers_out": safe_float(p.get("transfers_out")),
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
            "average_score": e.get("average_entry_score"),
            "highest_score": e.get("highest_score"),
            "most_captained": e.get("most_captained"),
            "top_element": e.get("top_element"),
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
            "provisional_start_time": f.get("provisional_start_time"),
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


def team_fixture_rows(data, team_id, gw=None, horizon=5):
    if gw is None:
        gw = get_next_gw(data["events"])

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
    return " · ".join(
        f"GW{x['gw']} {x['opponent']} {'H' if x['home'] else 'A'}"
        for x in fixtures[:limit]
    )


def fixture_swing(data, team_id):
    upcoming = team_fixture_rows(data, team_id, horizon=5)
    later = team_fixture_rows(
        data,
        team_id,
        gw=get_next_gw(data["events"]) + 5,
        horizon=5,
    )
    a = fixture_score(upcoming)
    b = fixture_score(later)
    return {
        "current_score": a,
        "next_score": b,
        "swing": b - a,
        "current_label": fixture_label(a),
        "next_label": fixture_label(b),
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
        base = base * .65 + start_rate * 100 * .35

    return clamp(base * chance / 100, 0, 100)


def risk_score(player):
    injury_risk = 100 - safe_float(player.get("chance_next_round"), 100)
    low_minutes = 100 - minutes_score(player)
    news_penalty = 15 if player.get("news") else 0
    return clamp(
        injury_risk * .45 + low_minutes * .45 + news_penalty * .10,
        0,
        100,
    )


def player_radar_score(player, data):
    fixtures = team_fixture_rows(data, player["team_id"], horizon=5)
    f_score = fixture_score(fixtures)
    form = clamp(safe_float(player["form"]) * 10, 0, 100)
    xgi = clamp(safe_float(player["expected_goal_involvements_per_90"]) * 100, 0, 100)
    ict = clamp(safe_float(player["ict_index"]), 0, 100)
    mins = minutes_score(player)
    risk = risk_score(player)

    score = (
        form * .20
        + xgi * .25
        + ict * .15
        + mins * .20
        + f_score * .20
    )
    return clamp(score - risk * .15, 0, 100)


def captain_score(player, data):
    fixtures = team_fixture_rows(data, player["team_id"], horizon=3)
    f_score = fixture_score(fixtures)
    form = clamp(safe_float(player["form"]) * 10, 0, 100)
    xgi = clamp(safe_float(player["expected_goal_involvements_per_90"]) * 100, 0, 100)
    mins = minutes_score(player)
    bonus = clamp(safe_float(player["bonus"]) / 10, 0, 100)
    home_bonus = 7 if fixtures and fixtures[0]["home"] else 0
    risk = risk_score(player)

    score = (
        xgi * .32
        + form * .20
        + f_score * .25
        + mins * .15
        + bonus * .08
        + home_bonus
    )
    return clamp(score - risk * .15, 0, 100)


def differential_score(player, data):
    radar = player_radar_score(player, data)
    ownership_score = clamp(100 - safe_float(player["selected_by"]) * 4, 0, 100)
    xgi = clamp(safe_float(player["expected_goal_involvements_per_90"]) * 100, 0, 100)
    minutes = minutes_score(player)
    return clamp(radar * .40 + ownership_score * .25 + xgi * .20 + minutes * .15, 0, 100)


def add_scores(players, data):
    out = []
    for p in players:
        row = dict(p)
        row["radar_score"] = player_radar_score(p, data)
        row["captain_score"] = captain_score(p, data)
        row["differential_score"] = differential_score(p, data)
        row["minutes_score"] = minutes_score(p)
        row["risk_score"] = risk_score(p)
        out.append(row)
    return out


# ============================================================
# DEFENSIVE DATA + OWNER ENRICHMENT
# ============================================================

def default_defensive_profile(team, data):
    strength_home = safe_float(team.get("strength_defence_home"))
    strength_away = safe_float(team.get("strength_defence_away"))
    strength = (strength_home + strength_away) / 2

    strengths = [
        safe_float(t.get("strength_defence_home")) +
        safe_float(t.get("strength_defence_away"))
        for t in data["teams"].values()
    ]

    min_s = min(strengths) if strengths else 1
    max_s = max(strengths) if strengths else 100
    normalized = (strength * 2 - min_s) / max(1, max_s - min_s)
    vulnerability = clamp(100 - normalized * 100, 0, 100)

    # These are explicitly proxies. They are NOT Opta/event data.
    return {
        "team_id": team["id"],
        "team": team["name"],
        "source": "FPL API proxy",
        "defensive_strength": clamp(100 - vulnerability, 0, 100),
        "vulnerability": vulnerability,
        "left": clamp(vulnerability * .95 + (100 - strength_home) * .05, 0, 100),
        "center": clamp(vulnerability * 1.08, 0, 100),
        "right": clamp(vulnerability * .92 + (100 - strength_away) * .08, 0, 100),
        "confidence": "Proxy",
    }


def get_enrichment():
    return st.session_state.get("defensive_enrichment", {})


def set_enrichment(enrichment):
    st.session_state["defensive_enrichment"] = enrichment


def merged_defensive_profile(team, data):
    base = default_defensive_profile(team, data)
    enriched = get_enrichment().get(str(team["id"]))

    if not enriched:
        return base

    result = dict(base)
    for key in ["left", "center", "right", "vulnerability", "defensive_strength"]:
        if key in enriched and enriched[key] is not None:
            result[key] = safe_float(enriched[key], result[key])

    result["source"] = enriched.get("source", "Owner enrichment")
    result["confidence"] = enriched.get("confidence", "Owner data")
    result["gw"] = enriched.get("gw")
    result["notes"] = enriched.get("notes", "")
    return result


def defensive_zone_rank(profile):
    zones = {
        "Left": safe_float(profile.get("left")),
        "Center": safe_float(profile.get("center")),
        "Right": safe_float(profile.get("right")),
    }
    return sorted(zones.items(), key=lambda x: x[1], reverse=True)


# ============================================================
# PITCH
# ============================================================

def draw_pitch(left_val, center_val, right_val, team_name):
    fig = go.Figure()
    fig.add_shape(
        type="rect", x0=0, y0=0, x1=100, y1=60,
        line=dict(color="rgba(255,255,255,.35)", width=2),
        fillcolor="rgba(0,0,0,0)",
    )

    for x in [33.33, 66.66]:
        fig.add_shape(
            type="line", x0=x, y0=0, x1=x, y1=60,
            line=dict(color="rgba(255,255,255,.20)", width=1),
        )

    zones = [
        (0, 33.33, left_val, "LEFT"),
        (33.33, 66.66, center_val, "CENTER"),
        (66.66, 100, right_val, "RIGHT"),
    ]

    for x0, x1, value, label in zones:
        alpha = .12 + value / 100 * .58
        fig.add_shape(
            type="rect", x0=x0, y0=0, x1=x1, y1=60,
            fillcolor=f"rgba(255,80,80,{alpha})",
            line=dict(width=0),
        )
        fig.add_annotation(
            x=(x0 + x1) / 2,
            y=30,
            text=f"<b>{label}</b><br>{value:.0f}/100",
            showarrow=False,
            font=dict(size=15, color="white"),
        )

    fig.update_layout(
        title=f"{team_name} — Defensive Vulnerability",
        height=380,
        margin=dict(l=5, r=5, t=45, b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, range=[0, 100]),
        yaxis=dict(visible=False, range=[0, 60]),
        font=dict(color="white"),
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
    risk_label = "Low" if risk < 25 else "Medium" if risk < 55 else "High"

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
    if safe_float(player["expected_goal_involvements_per_90"]) >= .40:
        reasons.append("strong xGI/90")
    if minutes_score(player) >= 75:
        reasons.append("good minutes security")
    if fixture_score(team_fixture_rows(data, player["team_id"], horizon=3)) >= 65:
        reasons.append("favorable upcoming fixtures")
    if not reasons:
        reasons.append("balanced underlying profile")

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
# GLOBAL SEARCH
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
    player_hits = [
        p for p in players
        if query in p["name"].lower()
        or query in p["web_name"].lower()
        or query in p["team"].lower()
        or query in p["team_short"].lower()
    ][:20]

    if player_hits:
        st.subheader("Players")
        for p in player_hits:
            st.markdown(
                f""" <div class="player-card"> <b>{p['name']}</b> · {p['team_short']} · {p['position']} <br><span class="subtle">{money(p['price'])} · Form {p['form']:.1f} · Radar {p['radar_score']:.1f}</span> </div> """,
                unsafe_allow_html=True,
            )
            if st.button(f"Open {p['web_name']}", key=f"search_{p['id']}"):
                st.session_state["selected_player_id"] = p["id"]
                st.session_state["page"] = "Player Profile"
                st.rerun()

    team_hits = [
        t for t in data["teams"].values()
        if query in t["name"].lower() or query in t["short_name"].lower()
    ]
    if team_hits:
        st.subheader("Clubs")
        for t in team_hits:
            fs = fixture_score(team_fixture_rows(data, t["id"], horizon=5))
            st.markdown(
                f""" <div class="player-card"> <b>{t['name']}</b> · Fixture Score {fs:.0f} <br><span class="subtle">{fixture_text(team_fixture_rows(data, t['id'], horizon=5))}</span> </div> """,
                unsafe_allow_html=True,
            )

    if not player_hits and not team_hits:
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

    default_id = st.session_state.get("selected_player_id")
    default_index = 0
    if default_id:
        for i, pid in enumerate(labels.values()):
            if pid == default_id:
                default_index = i
                break

    selected = st.selectbox("Player", list(labels.keys()), index=default_index)
    player = next(p for p in players if p["id"] == labels[selected])
    st.session_state["selected_player_id"] = player["id"]

    v = verdict_for_player(player, data)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Price", money(player["price"]))
    with c2:
        st.metric("Form", f"{player['form']:.1f}")
    with c3:
        st.metric("xGI/90", f"{player['expected_goal_involvements_per_90']:.2f}")
    with c4:
        st.metric("Ownership", pct(player["selected_by"]))

    render_verdict(
        f"{player['name']} — Radar {v['score']:.1f}/100",
        f"{v['reason']}. Minutes score {player['minutes_score']:.0f}/100.",
        v["confidence"],
        v["risk"],
    )

    st.subheader("📊 Core FPL Data")
    core = pd.DataFrame([{
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
    }])
    st.dataframe(core.round(2), use_container_width=True, hide_index=True)

    fixtures = team_fixture_rows(data, player["team_id"], horizon=5)
    st.subheader("📅 Fixtures")
    st.dataframe(
        pd.DataFrame([{
            "GW": f["gw"],
            "Opponent": f["opponent"],
            "H/A": "H" if f["home"] else "A",
            "Difficulty": f["difficulty"],
        } for f in fixtures]),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("📰 FPL Status / News")
    if player["news"]:
        st.warning(player["news"])
    else:
        st.success("No FPL news supplied by the API.")

    if st.button("Load detailed player history", use_container_width=True):
        try:
            summary = load_player_summary(int(player["id"]))
            histories = summary.get("history", [])
            if histories:
                df = pd.DataFrame(histories)
                cols = [c for c in [
                    "round", "minutes", "total_points", "goals_scored",
                    "assists", "clean_sheets", "bonus", "bps",
                    "expected_goals", "expected_assists"
                ] if c in df.columns]
                st.dataframe(df[cols].tail(10), use_container_width=True, hide_index=True)
            else:
                st.info("No detailed history returned.")
        except Exception as exc:
            st.error(f"Unable to load player history: {exc}")


# ============================================================
# HOME
# ============================================================

def home(data):
    next_gw = get_next_gw(data["events"])
    players = add_scores(data["players"], data)
    active = [p for p in players if p["status"] == "a"]

    captain_rank = sorted(
        [p for p in active if p["position"] in ["MID", "FWD"] and p["minutes"] > 250],
        key=lambda p: p["captain_score"],
        reverse=True,
    )

    top = captain_rank[:3]
    best_fixture_teams = sorted(
        data["teams"].values(),
        key=lambda t: fixture_score(team_fixture_rows(data, t["id"], horizon=5)),
        reverse=True,
    )[:3]

    st.markdown(
        f""" <div class="topbar"> <div class="brand">⚽ FPL <span>HOME</span></div> <div class="subtle">The next FPL decision — GW {next_gw}</div> </div> """,
        unsafe_allow_html=True,
    )

    st.title("🏠 Home")
    st.caption("Minimal view. Focus on the decisions that matter most this Gameweek.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">GAMEWEEK</div><div class="metric-value">GW {next_gw}</div><div class="metric-sub">next planning point</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">PLAYERS</div><div class="metric-value">{len(active)}</div><div class="metric-sub">active FPL players</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">FPL DATA</div><div class="metric-value">LIVE</div><div class="metric-sub">public FPL API</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        linked = st.session_state.get("fpl_team_id")
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">MY TEAM</div><div class="metric-value">{"LINKED" if linked else "NOT LINKED"}</div><div class="metric-sub">optional FPL Team ID</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">👑 Captain decision</div>', unsafe_allow_html=True)
    if top:
        safe_pick = top[0]
        upside = sorted(top, key=lambda p: (p["expected_goal_involvements_per_90"], p["differential_score"]), reverse=True)[0]
        col1, col2 = st.columns(2)
        with col1:
            render_verdict(
                f"SAFE PICK · {safe_pick['name']}",
                f"{safe_pick['team_short']} · Captain Score {safe_pick['captain_score']:.1f}. {verdict_for_player(safe_pick, data, 'captain')['reason']}.",
                verdict_for_player(safe_pick, data, "captain")["confidence"],
                verdict_for_player(safe_pick, data, "captain")["risk"],
                "SAFE CAPTAIN",
            )
        with col2:
            render_verdict(
                f"HIGH UPSIDE · {upside['name']}",
                f"{upside['team_short']} · xGI/90 {upside['expected_goal_involvements_per_90']:.2f}. Higher upside can come with more variance.",
                "Medium",
                "Medium",
                "HIGH UPSIDE",
            )
    else:
        st.info("Not enough eligible players for a captain recommendation.")

    st.markdown('<div class="section-title">🛡️ Defensive opportunity</div>', unsafe_allow_html=True)
    zone_rows = []
    for t in data["teams"].values():
        profile = merged_defensive_profile(t, data)
        zones = defensive_zone_rank(profile)
        zone_rows.append({
            "Team": t["name"],
            "Top Weak Zone": zones[0][0],
            "Vulnerability": round(zones[0][1], 0),
            "Data": profile["source"],
        })

    zone_df = pd.DataFrame(zone_rows).sort_values("Vulnerability", ascending=False)
    st.dataframe(zone_df.head(3), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">📅 Fixture edge</div>', unsafe_allow_html=True)
    st.dataframe(
        pd.DataFrame([{
            "Team": t["name"],
            "Fixture Score": round(fixture_score(team_fixture_rows(data, t["id"], horizon=5)), 0),
            "Run": fixture_text(team_fixture_rows(data, t["id"], horizon=5)),
        } for t in best_fixture_teams]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        '<div class="disclaimer">Model scores are decision-support signals, not predicted FPL points or guarantees.</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# DEFENSIVE RADAR
# ============================================================

def defensive_radar(data):
    st.title("🛡️ Defensive Radar")
    st.caption("Core FPL API strength + optional owner-only defensive enrichment.")

    teams = data["teams"]
    names = sorted(t["name"] for t in teams.values())
    selected_name = st.selectbox("Select team", names)
    team = next(t for t in teams.values() if t["name"] == selected_name)
    profile = merged_defensive_profile(team, data)

    c1, c2 = st.columns([1.15, 1])
    with c1:
        st.plotly_chart(
            draw_pitch(profile["left"], profile["center"], profile["right"], selected_name),
            use_container_width=True,
        )
    with c2:
        st.markdown(
            f""" <div class="card"> <b>Data source:</b> {profile['source']}<br> <b>Confidence:</b> {profile.get('confidence','')}<br> <b>Overall vulnerability:</b> {profile['vulnerability']:.0f}/100<br> <b>Defensive strength:</b> {profile['defensive_strength']:.0f}/100 </div> """,
            unsafe_allow_html=True,
        )
        if profile.get("notes"):
            st.info(profile["notes"])

    st.subheader("🎯 Top 3 Defensive Opportunity Zones")
    top3 = defensive_zone_rank(profile)[:3]
    cols = st.columns(3)
    for col, (zone, value) in zip(cols, top3):
        with col:
            st.markdown(
                f""" <div class="zone-card"> <div class="metric-label">OPPORTUNITY #{top3.index((zone,value))+1}</div> <div class="metric-value">{zone}</div> <div class="metric-sub">Vulnerability {value:.0f}/100</div> </div> """,
                unsafe_allow_html=True,
            )

    st.subheader("📌 Important data distinction")
    st.warning(
        "If the profile says FPL API proxy, the left/center/right zones are analytical proxies "
        "derived from FPL team-strength fields. They are not claimed Opta/StatsBomb event data."
    )


# ============================================================
# FIXTURE DIFFICULTY / SWING
# ============================================================

def fixtures_page(data):
    st.title("🟢🟡🔴 Fixture Difficulty")
    st.caption("Lower FPL fixture difficulty means a better fixture. Scores are normalized for comparison.")

    rows = []
    for team in data["teams"].values():
        fixtures = team_fixture_rows(data, team["id"], horizon=5)
        score = fixture_score(fixtures)
        swing = fixture_swing(data, team["id"])
        rows.append({
            "Team": team["name"],
            "Score": round(score, 1),
            "Verdict": fixture_label(score),
            "GW Run": fixture_text(fixtures),
            "Swing": round(swing["swing"], 1),
        })

    df = pd.DataFrame(rows).sort_values("Score", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("🔄 Fixture Swing")
    st.caption("Compares the next five fixtures with the following five. Positive = easier later run.")
    st.dataframe(
        df.sort_values("Swing", ascending=False)[
            ["Team", "Score", "Swing", "GW Run"]
        ],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# WHAT CHANGED / PRICE WATCH
# ============================================================

def what_changed(data):
    st.title("📈 What Changed")
    st.caption("Only changes exposed by the current FPL API are shown. No invented player history.")

    players = add_scores(data["players"], data)
    rows = []
    for p in players:
        if (
            p["cost_change_event"] != 0
            or p["transfers_in_event"] != 0
            or p["transfers_out_event"] != 0
            or p["news"]
            or p["status"] != "a"
        ):
            rows.append({
                "Player": p["name"],
                "Team": p["team_short"],
                "Price": money(p["price"]),
                "GW Price Δ": p["cost_change_event"],
                "GW Transfers In": int(p["transfers_in_event"]),
                "GW Transfers Out": int(p["transfers_out_event"]),
                "Status": p["status"],
                "News": p["news"][:80],
            })

    if rows:
        st.dataframe(
            pd.DataFrame(rows).sort_values(
                ["GW Price Δ", "GW Transfers In"],
                ascending=[False, False],
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No API-exposed changes match the current filters.")

    st.info(
        "The app does not manufacture a historical comparison when the FPL API does not provide it. "
        "For deeper historical player-by-player analysis, use the Player Profile history endpoint."
    )


def price_watch(data):
    st.title("💰 Price Watch")
    st.caption("Current price movement from FPL API fields. Historical prices are not fabricated.")

    players = add_scores(data["players"], data)
    rows = []
    for p in players:
        delta = p["cost_change_event"]
        if delta != 0:
            rows.append({
                "Player": p["name"],
                "Team": p["team_short"],
                "Current Price": money(p["price"]),
                "Current GW Δ": delta,
                "Season Δ": p["cost_change_start"],
                "Transfers In GW": int(p["transfers_in_event"]),
                "Transfers Out GW": int(p["transfers_out_event"]),
            })

    if rows:
        st.dataframe(
            pd.DataFrame(rows).sort_values("Current GW Δ", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No current price movements exposed by the API.")

    st.markdown(
        '<div class="disclaimer">Historical daily prices are intentionally not invented. If a historical-price source is added later, it will be labeled separately.</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# CAPTAINCY
# ============================================================

def captaincy(data):
    st.title("👑 Captaincy")
    st.caption("Safe Pick + High Upside. Scores are model signals, not projected points.")

    players = add_scores(data["players"], data)
    eligible = [
        p for p in players
        if p["status"] == "a"
        and p["position"] in ["MID", "FWD"]
        and p["minutes"] > 250
    ]
    ranked = sorted(eligible, key=lambda p: p["captain_score"], reverse=True)

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

    c1, c2 = st.columns(2)
    with c1:
        v = verdict_for_player(safe_pick, data, "captain")
        render_verdict(
            f"{safe_pick['name']} · {safe_pick['captain_score']:.1f}",
            f"{safe_pick['team_short']} · {v['reason']}.",
            v["confidence"], v["risk"], "SAFE PICK",
        )
    with c2:
        v = verdict_for_player(upside, data, "captain")
        render_verdict(
            f"{upside['name']} · {upside['captain_score']:.1f}",
            f"{upside['team_short']} · xGI/90 {upside['expected_goal_involvements_per_90']:.2f}.",
            v["confidence"], v["risk"], "HIGH UPSIDE",
        )

    st.subheader("Top captain candidates")
    rows = []
    for i, p in enumerate(ranked[:20], 1):
        v = verdict_for_player(p, data, "captain")
        rows.append({
            "Rank": i,
            "Player": p["name"],
            "Team": p["team_short"],
            "Fixture": fixture_text(team_fixture_rows(data, p["team_id"], horizon=3), 3),
            "Price": money(p["price"]),
            "Form": p["form"],
            "xGI/90": round(p["expected_goal_involvements_per_90"], 2),
            "Minutes": round(p["minutes_score"]),
            "Captain Score": round(p["captain_score"], 1),
            "Risk": v["risk"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ============================================================
# TRANSFER PLANNER
# ============================================================

def transfer_planner(data):
    st.title("🔄 Transfer Planner")
    st.caption("Use your linked FPL team when available, or select a squad manually.")

    players = add_scores(data["players"], data)
    linked = st.session_state.get("fpl_team_id")

    current_ids = set()

    if linked:
        st.success(f"Linked FPL Team ID: {linked}")
        gw = get_current_gw(data["events"])
        try:
            picks = load_fpl_team_picks(int(linked), gw)
            current_ids = {x["element"] for x in picks.get("picks", [])}
            st.caption(f"Loaded {len(current_ids)} players from GW {gw}.")
        except Exception as exc:
            st.warning(f"Could not load linked squad: {exc}")

    labels = {
        f"{p['name']} — {p['team_short']} — {money(p['price'])}": p["id"]
        for p in players if p["status"] == "a"
    }

    if not current_ids:
        selected = st.multiselect("Your current squad", list(labels.keys()), max_selections=15)
        current_ids = {labels[x] for x in selected}

    free_transfers = st.number_input("Free Transfers", 1, 5, 1)
    bank = st.number_input("Money in Bank (£m)", 0.0, 20.0, 0.0, .1)

    if not current_ids:
        st.info("Link your FPL Team ID or select your squad.")
        return

    current = [p for p in players if p["id"] in current_ids]
    out_candidates = sorted(current, key=lambda p: p["radar_score"])

    st.subheader("🔻 Suggested OUT")
    st.dataframe(
        pd.DataFrame([{
            "Player": p["name"],
            "Team": p["team_short"],
            "Price": money(p["price"]),
            "Radar": round(p["radar_score"], 1),
            "Risk": "Low" if p["risk_score"] < 25 else "Medium" if p["risk_score"] < 55 else "High",
        } for p in out_candidates]),
        use_container_width=True,
        hide_index=True,
    )

    candidates = [
        p for p in players
        if p["status"] == "a" and p["id"] not in current_ids
    ]

    suggestions = []
    for out_player in out_candidates[:5]:
        max_price = out_player["price"] + bank
        same_pos = [
            p for p in candidates
            if p["position"] == out_player["position"]
            and p["price"] <= max_price
        ]
        for candidate in sorted(same_pos, key=lambda p: p["radar_score"], reverse=True)[:5]:
            gain = candidate["radar_score"] - out_player["radar_score"]
            if gain > 0:
                suggestions.append({
                    "OUT": out_player["name"],
                    "IN": candidate["name"],
                    "Position": candidate["position"],
                    "Price": money(candidate["price"]),
                    "Radar Gain": round(gain, 1),
                    "IN Radar": round(candidate["radar_score"], 1),
                    "Risk": "Low" if candidate["risk_score"] < 25 else "Medium" if candidate["risk_score"] < 55 else "High",
                })

    suggestions.sort(key=lambda x: x["Radar Gain"], reverse=True)
    st.subheader("🔺 Suggested IN")
    if suggestions:
        st.dataframe(pd.DataFrame(suggestions[:20]), use_container_width=True, hide_index=True)
        best = suggestions[0]
        render_verdict(
            f"{best['OUT']} → {best['IN']}",
            f"Model Radar gain +{best['Radar Gain']:.1f}. This is decision support, not a guarantee.",
            "Medium",
            best["Risk"],
            "TRANSFER IDEA",
        )
    else:
        st.info("No positive-Radar upgrade found under the current budget constraints.")

    st.caption(
        f"Free transfers selected: {free_transfers}. The planner does not pretend to know future points."
    )


# ============================================================
# TEAM OPTIMIZER
# ============================================================

def team_optimizer(data):
    st.title("🧠 Team Optimizer")
    budget = st.number_input("Total squad budget (£m)", 50.0, 120.0, 100.0, .1)
    strategy = st.selectbox("Strategy", ["Safe", "Balanced", "Differential"])

    ownership_weight = {"Safe": .20, "Balanced": .10, "Differential": -.05}[strategy]
    players = add_scores(data["players"], data)

    for p in players:
        ownership_component = clamp(p["selected_by"] * 4, 0, 100)
        p["optimizer_score"] = p["radar_score"] * .80 + ownership_component * ownership_weight

    requirements = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
    selected = []
    team_counts = {}
    remaining = budget

    # Transparent greedy optimizer retained from old app, but clearly labeled.
    for pos, count_needed in requirements.items():
        pool = sorted(
            [
                p for p in players
                if p["position"] == pos
                and p["status"] == "a"
                and p["minutes"] > 100
            ],
            key=lambda x: x["optimizer_score"],
            reverse=True,
        )

        count = 0
        for p in pool:
            if count >= count_needed:
                break
            if remaining - p["price"] < 0:
                continue
            if team_counts.get(p["team_id"], 0) >= 3:
                continue
            selected.append(p)
            remaining -= p["price"]
            team_counts[p["team_id"]] = team_counts.get(p["team_id"], 0) + 1
            count += 1

    st.subheader("Recommended Squad")
    st.dataframe(
        pd.DataFrame([{
            "Player": p["name"],
            "Team": p["team_short"],
            "Pos": p["position"],
            "Price": money(p["price"]),
            "Score": round(p["optimizer_score"], 1),
            "Ownership": pct(p["selected_by"]),
        } for p in selected]),
        use_container_width=True,
        hide_index=True,
    )

    total = sum(p["price"] for p in selected)
    st.metric("Squad Cost", f"£{total:.1f}m", f"£{budget-total:.1f}m remaining")

    if len(selected) < 15:
        st.warning(
            "The transparent greedy optimizer could not fill all 15 slots under the selected budget/team constraints. "
            "It will not pretend the squad is valid."
        )
    st.caption("For a production-grade exact optimizer, an ILP/OR-Tools solver can replace this transparent heuristic.")


# ============================================================
# FPL TEAM LINK
# ============================================================

def my_team(data):
    st.title("👤 My FPL Team")
    st.caption("Optional: connect a public FPL Team ID. No API key is required.")

    current = st.session_state.get("fpl_team_id")
    team_id = st.number_input(
        "FPL Team ID",
        min_value=1,
        value=int(current or 1),
        step=1,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔗 Connect Team", use_container_width=True):
            try:
                result = load_fpl_team(int(team_id))
                st.session_state["fpl_team_id"] = int(team_id)
                st.session_state["fpl_team_entry"] = result
                st.success("FPL Team connected.")
            except Exception as exc:
                st.error(f"Unable to connect this Team ID: {exc}")

    with c2:
        if st.button("Disconnect", use_container_width=True):
            st.session_state.pop("fpl_team_id", None)
            st.session_state.pop("fpl_team_entry", None)
            st.rerun()

    if not current and "fpl_team_entry" not in st.session_state:
        st.info("Enter your FPL Team ID to load and analyze your squad.")
        return

    try:
        result = st.session_state.get("fpl_team_entry") or load_fpl_team(int(st.session_state["fpl_team_id"]))
        entry = result["entry"]
        st.subheader(entry.get("name", "My FPL Team"))

        c1, c2, c3 = st.columns(3)
        c1.metric("Overall Rank", entry.get("summary_overall_rank", "—"))
        c2.metric("Total Points", entry.get("summary_overall_points", "—"))
        c3.metric("Team ID", entry.get("id", "—"))

        gw = get_current_gw(data["events"])
        picks = load_fpl_team_picks(int(st.session_state["fpl_team_id"]), gw)
        st.subheader(f"GW {gw} Squad")

        player_map = {p["id"]: p for p in data["players"]}
        rows = []
        for pick in picks.get("picks", []):
            p = player_map.get(pick.get("element"))
            if not p:
                continue
            rows.append({
                "Player": p["name"],
                "Team": p["team_short"],
                "Pos": p["position"],
                "Price": money(p["price"]),
                "Captain": "C" if pick.get("is_captain") else "VC" if pick.get("is_vice_captain") else "",
                "Multiplier": pick.get("multiplier", 1),
                "GW Points": p["event_points"],
                "Radar": round(player_radar_score(p, data), 1),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    except Exception as exc:
        st.error(f"Unable to analyze the linked team: {exc}")


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
    top = sorted(players, key=lambda p: p["radar_score"], reverse=True)[:40]

    player_context = []
    for p in top:
        player_context.append({
            "id": p["id"],
            "name": p["name"],
            "team": p["team_short"],
            "position": p["position"],
            "price": round(p["price"], 1),
            "ownership": round(p["selected_by"], 1),
            "form": round(p["form"], 2),
            "xgi90": round(p["expected_goal_involvements_per_90"], 2),
            "minutes_score": round(p["minutes_score"], 1),
            "radar": round(p["radar_score"], 1),
            "captain": round(p["captain_score"], 1),
            "risk": round(p["risk_score"], 1),
        })

    team_context = []
    for team in data["teams"].values():
        fixtures = team_fixture_rows(data, team["id"], horizon=5)
        team_context.append({
            "team": team["name"],
            "short": team["short_name"],
            "fixture_score": round(fixture_score(fixtures), 1),
            "fixtures": [
                {
                    "gw": f["gw"],
                    "opp": f["opponent"],
                    "home": f["home"],
                    "difficulty": f["difficulty"],
                }
                for f in fixtures
            ],
            "defensive_enrichment": merged_defensive_profile(team, data),
        })

    return {
        "gameweek": get_next_gw(data["events"]),
        "top_players": player_context,
        "teams": team_context,
        "linked_team_id": st.session_state.get("fpl_team_id"),
    }


def ai_answer(question, data):
    client, error = get_gemini_client()
    if error:
        return error

    context = build_ai_context(data)
    prompt = f""" You are Ask FPL HOME, an expert Fantasy Premier League decision-support assistant. DATA RULES: 1. FPL API data is the authoritative source for core FPL numbers supplied here. 2. Owner enrichment is optional and must be described as owner-supplied enrichment. 3. Gemini is NOT a source of FPL numbers. Never invent prices, ownership, fixtures, points or historical values. 4. If a number is absent, say that it is unavailable. 5. Clearly distinguish model scores from actual FPL points. 6. Give a practical verdict, explain why, mention risk, and provide an alternative when useful. 7. Never claim a recommendation guarantees points. QUESTION: {question} STRUCTURED DATA: {json.dumps(context, ensure_ascii=False)} Return: Verdict Why Risk Alternative (if relevant) """

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
    st.caption("AI interpretation of FPL HOME's structured data. Gemini does not create the underlying FPL numbers.")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("e.g. Salah or Haaland captain this GW?")
    if question:
        st.session_state["chat_history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Ask FPL HOME is analyzing..."):
                answer = ai_answer(question, data)
            st.markdown(answer)

        st.session_state["chat_history"].append({"role": "assistant", "content": answer})


# ============================================================
# OWNER CONTROL CENTER
# ============================================================

def owner_unlock():
    configured = bool(get_secret("OWNER_PASSWORD"))
    if not configured:
        st.error("OWNER_PASSWORD is missing from Streamlit Secrets.")
        st.info("Owner-only tools remain locked until OWNER_PASSWORD is configured.")
        return False

    if st.session_state.get("owner_unlocked"):
        return True

    password = st.text_input("Owner password", type="password")
    if st.button("Unlock Owner Control Center", use_container_width=True):
        if password == get_secret("OWNER_PASSWORD"):
            st.session_state["owner_unlocked"] = True
            st.success("Owner access enabled for this session.")
            st.rerun()
        else:
            st.error("Incorrect password.")
    return st.session_state.get("owner_unlocked", False)


def gemini_image_to_structured(uploaded_file, team_hint=None, gw_hint=None):
    client, error = get_gemini_client()
    if error:
        return None, error

    image_bytes = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/jpeg"

    schema = {
        "team_name": "string or null",
        "team_id": "integer or null",
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

    prompt = f""" You are the data-extraction layer inside FPL HOME. Analyze ONLY the uploaded image and convert visible defensive/tactical information into structured JSON. This is OWNER-SUPPLIED DATA ENRICHMENT. Do not invent values. If a value is not visible, return null. Do not infer a number from general football knowledge. Preserve the source label if visible. Team hint: {team_hint or "none"} Gameweek hint: {gw_hint or "none"} Return JSON matching this schema: {json.dumps(schema, indent=2)} """

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime),
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


def owner_control_center(data):
    st.title("🔐 Owner Control Center")
    st.caption("Owner-only area for defensive-data enrichment. Normal users cannot upload data.")

    if not owner_unlock():
        return

    st.success("Owner mode is active for this browser session.")

    st.subheader("📸 Defensive Data Enrichment")
    st.write(
        "Upload your own screenshot. Gemini will read visible values and convert them to structured data. "
        "The resulting values remain labeled as owner enrichment."
    )

    team_names = sorted(t["name"] for t in data["teams"].values())
    team_name = st.selectbox("Team represented in the image", team_names)
    team = next(t for t in data["teams"].values() if t["name"] == team_name)
    gw = st.number_input("Gameweek represented", min_value=1, max_value=50, value=get_next_gw(data["events"]))
    uploaded = st.file_uploader(
        "Upload defensive/tactical screenshot",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=False,
    )

    if uploaded and st.button("🤖 Analyze Image", use_container_width=True):
        with st.spinner("Gemini is extracting structured defensive data..."):
            result, error = gemini_image_to_structured(uploaded, team_name, gw)

        if error:
            st.error(error)
        else:
            st.subheader("Extracted structured data")
            st.json(result)
            st.session_state["last_extracted_enrichment"] = result
            st.session_state["last_extracted_team_id"] = team["id"]
            st.session_state["last_extracted_gw"] = gw

    extracted = st.session_state.get("last_extracted_enrichment")
    if extracted:
        st.divider()
        st.subheader("Review & publish")
        st.warning("Review the extracted values before publishing. Publishing changes this app session's enrichment layer.")

        editable = {
            "left": safe_float(extracted.get("left_vulnerability"), 0) if extracted.get("left_vulnerability") is not None else None,
            "center": safe_float(extracted.get("center_vulnerability"), 0) if extracted.get("center_vulnerability") is not None else None,
            "right": safe_float(extracted.get("right_vulnerability"), 0) if extracted.get("right_vulnerability") is not None else None,
            "vulnerability": safe_float(extracted.get("overall_vulnerability"), 0) if extracted.get("overall_vulnerability") is not None else None,
            "defensive_strength": safe_float(extracted.get("defensive_strength"), 0) if extracted.get("defensive_strength") is not None else None,
        }

        cols = st.columns(5)
        keys = ["left", "center", "right", "vulnerability", "defensive_strength"]
        for col, key in zip(cols, keys):
            with col:
                editable[key] = st.number_input(
                    key.replace("_", " ").title(),
                    min_value=0.0,
                    max_value=100.0,
                    value=float(editable[key] if editable[key] is not None else 0),
                    step=1.0,
                )

        notes = st.text_area("Owner notes", extracted.get("notes", ""))
        source_label = st.text_input(
            "Source label",
            extracted.get("source_label", "Owner-uploaded image"),
        )

        if st.button("✅ Publish Enrichment", use_container_width=True):
            enrichment = get_enrichment()
            enrichment[str(team["id"])] = {
                **editable,
                "source": source_label or "Owner-uploaded image",
                "confidence": extracted.get("confidence", "Unknown"),
                "notes": notes,
                "gw": int(gw),
                "updated": utc_now(),
            }
            set_enrichment(enrichment)
            st.success(f"Defensive enrichment published for {team_name}.")

    st.divider()
    st.subheader("Current enrichment")
    enrichment = get_enrichment()
    if enrichment:
        rows = []
        for tid, item in enrichment.items():
            team = data["teams"].get(int(tid), {})
            rows.append({
                "Team": team.get("name", tid),
                "GW": item.get("gw"),
                "Left": item.get("left"),
                "Center": item.get("center"),
                "Right": item.get("right"),
                "Source": item.get("source"),
                "Updated": item.get("updated", ""),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No owner enrichment has been published in this session.")

    if st.button("🗑️ Clear all session enrichment", use_container_width=True):
        st.session_state["defensive_enrichment"] = {}
        st.rerun()


# ============================================================
# DATA HEALTH
# ============================================================

def data_health_page(data, api_ok=True):
    st.title("🩺 Data Health")
    st.caption("Transparent view of which layer supplies each data type.")

    rows = [
        {
            "Layer": "FPL API",
            "Role": "Core FPL numbers, players, teams, fixtures",
            "Status": "Connected" if api_ok else "Error",
            "API Key": "Not required",
        },
        {
            "Layer": "Owner enrichment",
            "Role": "Optional defensive/tactical enrichment from your files/images",
            "Status": f"{len(get_enrichment())} team profiles" if get_enrichment() else "None",
            "API Key": "Owner only",
        },
        {
            "Layer": "Gemini",
            "Role": "Image interpretation + AI explanation",
            "Status": "Configured" if get_secret("GEMINI_API_KEY") else "Not configured",
            "API Key": "Streamlit Secrets only",
        },
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Teams", len(data["teams"]))
    c2.metric("Players", len(data["players"]))
    c3.metric("Fixtures", len(data["fixtures"]))

    st.subheader("Rules")
    st.markdown(
        """ - **FPL API = source of core numbers** - **Owner uploads = data enrichment** - **Gemini = interpretation/extraction, not the source of FPL numbers** - **No user API-key input** - **No invented historical prices** """
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
    "📈 What Changed": "What Changed",
    "💰 Price Watch": "Price Watch",
    "👑 Captaincy": "Captaincy",
    "🔄 Transfers": "Transfer Planner",
    "🧠 Optimizer": "Team Optimizer",
    "👤 My Team": "My Team",
    "🤖 Ask FPL HOME": "Ask FPL HOME",
    "🔐 Owner": "Owner Control Center",
    "🩺 Data Health": "Data Health",
}


def top_navigation(data):
    # Gameweek selector lives in the top navigation area, not a sidebar.
    labels = list(NAV_ITEMS.keys())
    current_page = st.session_state.get("page", "Home")

    default_idx = 0
    for i, value in enumerate(NAV_ITEMS.values()):
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
    st.session_state["page"] = NAV_ITEMS[nav]

    gw_options = [e["id"] for e in data["events"]]
    current_gw = get_next_gw(data["events"])
    if gw_options:
        selected_gw = st.selectbox(
            "Gameweek",
            gw_options,
            index=gw_options.index(current_gw) if current_gw in gw_options else 0,
            key="global_gw",
        )
        st.session_state["selected_gw"] = selected_gw


# ============================================================
# MAIN
# ============================================================

def main():
    raw, ok, error = load_data_with_status()

    if not ok:
        st.error("❌ Unable to load FPL API data.")
        st.code(str(error))
        if st.button("🔄 Retry"):
            st.cache_data.clear()
            st.rerun()
        return

    data = normalize_data(raw)

    top_navigation(data)

    # Small global actions
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("↻ Refresh"):
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
    elif page == "What Changed":
        what_changed(data)
    elif page == "Price Watch":
        price_watch(data)
    elif page == "Captaincy":
        captaincy(data)
    elif page == "Transfer Planner":
        transfer_planner(data)
    elif page == "Team Optimizer":
        team_optimizer(data)
    elif page == "My Team":
        my_team(data)
    elif page == "Ask FPL HOME":
        ask_fpl_home(data)
    elif page == "Owner Control Center":
        owner_control_center(data)
    elif page == "Data Health":
        data_health_page(data, api_ok=True)


if __name__ == "__main__":
    main()
