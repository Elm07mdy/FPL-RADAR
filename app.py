# ============================================================
# FPL HOME
# Your Fantasy Command Center
# Single-file Streamlit Application
# ============================================================

import os
import json
import math
import hashlib
from datetime import datetime, timezone

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

APP_NAME = "FPL HOME"
APP_VERSION = "4.0"

FPL_BASE = "https://fantasy.premierleague.com/api"
BOOTSTRAP_URL = f"{FPL_BASE}/bootstrap-static/"
FIXTURES_URL = f"{FPL_BASE}/fixtures/"
REQUEST_TIMEOUT = 20
CACHE_TTL = 300

# Change through Streamlit Secrets if needed:
# GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

st.set_page_config(
    page_title=APP_NAME,
    page_icon="Рџй",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# PREMIUM MOBILE-FIRST UI
# ============================================================

st.markdown(
    """ <style> :root{ --bg:#071018; --surface:#0d1822; --surface2:#111f2b; --line:#223544; --text:#f4f8fb; --muted:#91a3b2; --mint:#5ee6be; --mint2:#9af3d8; --warning:#f4c95d; --danger:#ff7d87; --blue:#7db7ff; } html, body, [class*="css"]{ font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; } .stApp{ background: radial-gradient(circle at 10% 0%, rgba(94,230,190,.09), transparent 28%), radial-gradient(circle at 90% 0%, rgba(125,183,255,.08), transparent 25%), var(--bg); color:var(--text); } .block-container{ max-width:1450px; padding:1rem .9rem 4rem; } h1,h2,h3,h4{ color:var(--text)!important; letter-spacing:-.02em; } p, label, .stMarkdown, .stCaption{ color:var(--text); } /* Brand */ .brand{ display:flex; align-items:center; gap:12px; margin:2px 0 16px; } .brand-mark{ width:46px;height:46px;border-radius:14px; display:flex;align-items:center;justify-content:center; background:linear-gradient(145deg,#132b36,#0b151e); border:1px solid #315162; font-size:25px; box-shadow:0 8px 30px rgba(0,0,0,.25); } .brand-name{font-size:25px;font-weight:900;line-height:1} .brand-tag{font-size:11px;color:var(--muted);margin-top:4px;letter-spacing:.11em} /* Top nav */ .nav-wrap{ display:flex; gap:7px; overflow-x:auto; padding:4px 2px 10px; margin-bottom:14px; scrollbar-width:none; } .nav-wrap::-webkit-scrollbar{display:none;} .nav-note{ font-size:11px;color:var(--muted);margin:0 0 8px 2px; } .nav-btn{ white-space:nowrap; border:1px solid var(--line); background:#0b151e; color:#b8c7d2; border-radius:12px; padding:9px 12px; font-weight:700; font-size:12px; } .nav-active{ color:#06120f; background:var(--mint); border-color:var(--mint); box-shadow:0 0 0 1px rgba(94,230,190,.15),0 8px 24px rgba(94,230,190,.12); } /* Page transition */ .page-fade{ animation:pageFade .22s ease-out; } @keyframes pageFade{ from{opacity:.45;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} } /* Sections / cards */ .section{ background:rgba(13,24,34,.86); border:1px solid var(--line); border-radius:18px; padding:18px; margin-bottom:15px; } .section-title{ font-size:12px; font-weight:900; letter-spacing:.1em; color:var(--mint2); text-transform:uppercase; margin-bottom:9px; } .hero{ background:linear-gradient(135deg,rgba(94,230,190,.12),rgba(17,31,43,.92)); border:1px solid #2b5b57; border-radius:20px; padding:22px; margin-bottom:16px; } .hero-kicker{font-size:12px;font-weight:900;letter-spacing:.1em;color:var(--mint)} .hero-main{font-size:28px;font-weight:900;margin:5px 0} .hero-sub{color:#aab9c5;font-size:14px;line-height:1.55} /* Metrics */ .metric{ background:#0d1822; border:1px solid var(--line); border-radius:15px; padding:14px; min-height:92px; } .metric-label{font-size:11px;color:var(--muted);font-weight:800;letter-spacing:.08em} .metric-value{font-size:25px;font-weight:900;margin-top:4px} .metric-sub{font-size:11px;color:#758895;margin-top:3px} /* Recommendation */ .rec{ background:#0a151e; border:1px solid #254252; border-radius:15px; padding:14px; margin:8px 0; } .rec-title{font-size:15px;font-weight:900} .rec-sub{font-size:12px;color:#91a3b2;margin-top:3px} /* Badges */ .badge{ display:inline-block; padding:4px 8px; border-radius:999px; font-size:10px; font-weight:900; margin-right:4px; } .good{background:rgba(94,230,190,.14);color:#72edc7} .warn{background:rgba(244,201,93,.14);color:#f6d778} .bad{background:rgba(255,125,135,.14);color:#ff9ca4} .info{background:rgba(125,183,255,.14);color:#9bc7ff} /* Search / tables */ div[data-testid="stDataFrame"]{ border:1px solid var(--line); border-radius:14px; overflow:hidden; } /* Progress */ .stProgress > div > div > div > div{ background:var(--mint); } /* Buttons */ .stButton > button{ border-radius:11px; border:1px solid #294454; background:#0d1b25; color:#f1f7fa; font-weight:800; } .stButton > button:hover{ border-color:var(--mint); color:var(--mint2); } /* Inputs */ input, textarea, [data-baseweb="select"] > div{ background:#0b151e!important; color:#f3f8fb!important; } /* Mobile */ @media(max-width:768px){ .block-container{padding:.65rem .65rem 3rem} .brand-name{font-size:22px} .hero-main{font-size:22px} .metric-value{font-size:20px} .section{padding:14px;border-radius:15px} h1{font-size:26px!important} h2{font-size:22px!important} h3{font-size:18px!important} } </style> """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def safe_float(v, default=0.0):
    try:
        return default if v is None else float(v)
    except Exception:
        return default


def safe_int(v, default=0):
    try:
        return default if v is None else int(v)
    except Exception:
        return default


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def money(v):
    return f"┬Б{safe_float(v):.1f}m"


def pct(v):
    return f"{safe_float(v):.1f}%"


def risk_label(score):
    score = safe_float(score)
    return "Low" if score < 25 else "Medium" if score < 55 else "High"


def risk_badge(risk):
    cls = "good" if risk == "Low" else "warn" if risk == "Medium" else "bad"
    return f'<span class="badge {cls}">{risk}</span>'


def confidence_label(score):
    return "Very High" if score >= 82 else "High" if score >= 70 else "Medium" if score >= 58 else "Low"


def conf_badge(conf):
    return f'<span class="badge info">Confidence: {conf}</span>'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# FPL DATA ENGINE
# ============================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_json(url):
    r = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": "FPL-HOME/4.0"},
    )
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_fpl_data():
    return {
        "bootstrap": fetch_json(BOOTSTRAP_URL),
        "fixtures": fetch_json(FIXTURES_URL),
        "updated": now_iso(),
    }


def normalize_data(raw):
    b = raw["bootstrap"]
    teams = {}
    for t in b.get("teams", []):
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

    positions = {p["id"]: p.get("singular_name_short", "") for p in b.get("element_types", [])}
    players = []

    for p in b.get("elements", []):
        team = teams.get(p.get("team"), {})
        players.append({
            "id": p.get("id"),
            "name": f"{p.get('first_name','')} {p.get('second_name','')}".strip(),
            "web_name": p.get("web_name", ""),
            "team_id": p.get("team"),
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
            "expected_goal_involvements_per_90": safe_float(p.get("expected_goal_involvements_per_90")),
            "chance_next_round": safe_float(p.get("chance_of_playing_next_round"), 100),
            "chance_this_round": safe_float(p.get("chance_of_playing_this_round"), 100),
            "status": p.get("status", "a"),
            "news": p.get("news", ""),
            "starts": safe_float(p.get("starts")),
            "clean_sheets_per_90": safe_float(p.get("clean_sheets_per_90")),
            "form_rank": safe_float(p.get("form_rank")),
            "points_per_game_rank": safe_float(p.get("points_per_game_rank")),
        })

    events = [{
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
    } for e in b.get("events", [])]

    fixtures = [{
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
    } for f in raw.get("fixtures", [])]

    return {"teams": teams, "players": players, "events": events, "fixtures": fixtures}


def get_current_gw(events):
    cur = [e for e in events if e.get("is_current")]
    if cur:
        return cur[0]["id"]
    nxt = [e for e in events if e.get("is_next")]
    return nxt[0]["id"] if nxt else 1


# ============================================================
# OPTIONAL PUBLIC FPL TEAM ID
# ============================================================

@st.cache_data(ttl=120, show_spinner=False)
def fetch_manager_team(team_id, gw):
    if not team_id:
        return None
    try:
        summary = fetch_json(f"{FPL_BASE}/entry/{int(team_id)}/")
        picks = fetch_json(f"{FPL_BASE}/entry/{int(team_id)}/event/{int(gw)}/picks/")
        return {"summary": summary, "picks": picks}
    except Exception:
        return None


# ============================================================
# FIXTURE ENGINE
# ============================================================

def team_fixture_rows(data, team_id, gw=None, horizon=5):
    gw = get_current_gw(data["events"]) if gw is None else gw
    rows = []
    for f in data["fixtures"]:
        if f["event"] is None or f["event"] < gw or f["event"] > gw + horizon - 1:
            continue
        if f["team_h"] == team_id:
            opp = data["teams"].get(f["team_a"], {})
            rows.append({"gw":f["event"],"opponent":opp.get("short_name","?"),
                          "opponent_id":f["team_a"],"home":True,
                          "difficulty":f["difficulty_h"],"kickoff":f["kickoff"]})
        elif f["team_a"] == team_id:
            opp = data["teams"].get(f["team_h"], {})
            rows.append({"gw":f["event"],"opponent":opp.get("short_name","?"),
                          "opponent_id":f["team_h"],"home":False,
                          "difficulty":f["difficulty_a"],"kickoff":f["kickoff"]})
    return sorted(rows, key=lambda x:(x["gw"],x["kickoff"] or ""))


def fixture_score(fixtures):
    if not fixtures:
        return 50
    avg = sum(safe_float(x["difficulty"],3) for x in fixtures) / len(fixtures)
    return clamp(100 - ((avg-1)/4)*100, 0, 100)


def fixture_label(score):
    return "Excellent" if score >= 75 else "Good" if score >= 60 else "Mixed" if score >= 45 else "Difficult"


def fixture_color_emoji(difficulty):
    d = safe_int(difficulty,3)
    return "­ЪЪб" if d <= 2 else "­ЪЪА" if d == 3 else "­Ъћ┤"


def fixture_run_text(fixtures):
    return " ┬и ".join(
        f"{fixture_color_emoji(x['difficulty'])} GW{x['gw']} {x['opponent']} {'H' if x['home'] else 'A'}"
        for x in fixtures
    )


# ============================================================
# PLAYER ANALYTICS
# ============================================================

def minutes_score(p):
    chance = safe_float(p["chance_next_round"],100)
    mins = safe_float(p["minutes"])
    starts = safe_float(p["starts"])
    base = 15 if mins <= 0 else min(100,45 + min(55,mins/1200*55))
    if starts > 0 and mins > 0:
        start_rate = clamp(starts/max(1,mins/90),0,1)
        base = base*.65 + start_rate*100*.35
    return clamp(base*chance/100,0,100)


def risk_score(p):
    injury = 100-safe_float(p["chance_next_round"],100)
    low_mins = 100-minutes_score(p)
    news_penalty = 15 if p.get("news") else 0
    return clamp(injury*.45+low_mins*.45+news_penalty*.10,0,100)


def player_radar_score(p,data):
    fs = fixture_score(team_fixture_rows(data,p["team_id"],horizon=5))
    form = clamp(p["form"]*10,0,100)
    xgi = clamp(p["expected_goal_involvements_per_90"]*100,0,100)
    ict = clamp(p["ict_index"],0,100)
    mins = minutes_score(p)
    risk = risk_score(p)
    return clamp(form*.20+xgi*.25+ict*.15+mins*.20+fs*.20-risk*.15,0,100)


def captain_score(p,data):
    fs = fixture_score(team_fixture_rows(data,p["team_id"],horizon=3))
    form = clamp(p["form"]*10,0,100)
    xgi = clamp(p["expected_goal_involvements_per_90"]*100,0,100)
    mins = minutes_score(p)
    bonus = clamp(p["bonus"]/10,0,100)
    home = 7 if team_fixture_rows(data,p["team_id"],horizon=1) and team_fixture_rows(data,p["team_id"],horizon=1)[0]["home"] else 0
    return clamp(xgi*.32+form*.20+fs*.25+mins*.15+bonus*.08+home-risk_score(p)*.15,0,100)


def differential_score(p,data):
    radar = player_radar_score(p,data)
    own_score = clamp(100-p["selected_by"]*4,0,100)
    xgi = clamp(p["expected_goal_involvements_per_90"]*100,0,100)
    return clamp(radar*.40+own_score*.25+xgi*.20+minutes_score(p)*.15,0,100)


def add_scores(players,data):
    out=[]
    for p in players:
        q=dict(p)
        q["radar_score"]=player_radar_score(p,data)
        q["captain_score"]=captain_score(p,data)
        q["differential_score"]=differential_score(p,data)
        q["minutes_score"]=minutes_score(p)
        q["risk_score"]=risk_score(p)
        q["risk"]=risk_label(q["risk_score"])
        q["confidence"]=confidence_label(max(q["radar_score"],q["captain_score"]))
        out.append(q)
    return out


# ============================================================
# DEFENSIVE INTELLIGENCE
# ============================================================

def team_defensive_profile(team,data):
    sh=safe_float(team["strength_defence_home"])
    sa=safe_float(team["strength_defence_away"])
    strength=(sh+sa)/2
    vals=[safe_float(t["strength_defence_home"])+safe_float(t["strength_defence_away"]) for t in data["teams"].values()]
    lo=min(vals) if vals else 1
    hi=max(vals) if vals else 100
    norm=(strength*2-lo)/max(1,hi-lo)
    vulnerability=clamp(100-norm*100,0,100)
    # Proxy only when no admin event-level data exists.
    left=clamp(vulnerability*.95+(100-sh)*.05,0,100)
    center=clamp(vulnerability*1.08,0,100)
    right=clamp(vulnerability*.92+(100-sa)*.08,0,100)
    return {"defensive_strength":100-vulnerability,"vulnerability":vulnerability,
            "left":left,"center":center,"right":right,
            "strength_home":sh,"strength_away":sa,"source":"FPL proxy"}


def load_enrichment():
    return st.session_state.get("admin_enrichment", {})


def save_enrichment(data):
    st.session_state["admin_enrichment"]=data


def enriched_defensive_profile(team,data):
    base=team_defensive_profile(team,data)
    extra=load_enrichment().get("teams",{}).get(str(team["id"]),{})
    if not extra:
        return base
    for k in ["left","center","right","vulnerability"]:
        if k in extra:
            base[k]=clamp(safe_float(extra[k]),0,100)
    base["source"]="Admin enrichment"
    base["confidence"]=extra.get("confidence","Admin supplied")
    base["top_chance_sources"]=extra.get("top_chance_sources",[])
    base["notes"]=extra.get("notes","")
    return base


def top_three_attack_zones(profile):
    zones={"Left":profile["left"],"Center":profile["center"],"Right":profile["right"]}
    return sorted(zones.items(),key=lambda x:x[1],reverse=True)[:3]


def draw_pitch(profile,team_name):
    fig=go.Figure()
    fig.add_shape(type="rect",x0=0,y0=0,x1=100,y1=60,line=dict(color="rgba(255,255,255,.45)",width=2),fillcolor="rgba(0,0,0,0)")
    for x in [33.33,66.66]:
        fig.add_shape(type="line",x0=x,y0=0,x1=x,y1=60,line=dict(color="rgba(255,255,255,.2)",width=1))
    zones=[(0,33.33,profile["left"],"LEFT"),(33.33,66.66,profile["center"],"CENTER"),(66.66,100,profile["right"],"RIGHT")]
    for x0,x1,val,label in zones:
        alpha=.12+val/100*.55
        fig.add_shape(type="rect",x0=x0,y0=0,x1=x1,y1=60,fillcolor=f"rgba(255,90,95,{alpha})",line=dict(width=0))
        fig.add_annotation(x=(x0+x1)/2,y=30,text=f"<b>{label}</b><br>{val:.0f}/100",showarrow=False,font=dict(size=15,color="white"))
    fig.update_layout(title=f"{team_name} Рђћ Chance / Vulnerability Zones",height=360,margin=dict(l=5,r=5,t=45,b=5),
                      paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False,range=[0,100]),yaxis=dict(visible=False,range=[0,60]),font=dict(color="white"))
    return fig


# ============================================================
# ADMIN-ONLY ENRICHMENT
# ============================================================

def admin_password():
    try:
        return str(st.secrets.get("ADMIN_PASSWORD",""))
    except Exception:
        return os.getenv("ADMIN_PASSWORD","")


def is_admin():
    return bool(st.session_state.get("admin_ok",False))


def admin_login():
    if is_admin():
        return True
    st.sidebar.markdown("### ­Ъћљ Owner")
    password=st.sidebar.text_input("Admin password",type="password",key="admin_password_input")
    if password:
        expected=admin_password()
        if expected and hashlib.sha256(password.encode()).hexdigest()==hashlib.sha256(expected.encode()).hexdigest():
            st.session_state["admin_ok"]=True
            st.rerun()
        elif expected and password:
            st.sidebar.error("Wrong password.")
        elif not expected:
            st.sidebar.warning("Set ADMIN_PASSWORD in Streamlit Secrets.")
    return is_admin()


def admin_panel(data):
    if not is_admin():
        st.warning("Admin-only area.")
        return

    st.title("РџЎ№ИЈ FPL HOME Control Center")
    st.caption("Owner-only. Users do not get access to enrichment uploads or system controls.")

    tab1,tab2,tab3=st.tabs(["­ЪЊЦ Defensive Enrichment","­ЪЕ║ Data Health","­ЪЊб App Controls"])

    with tab1:
        st.subheader("Feed extra defensive data")
        st.caption(
            "Upload screenshots containing defensive/chance-location data. "
            "Only the owner can upload them. Gemini converts them into structured enrichment; "
            "the FPL API remains the numerical base layer."
        )
        team_names={t["name"]:t["id"] for t in data["teams"].values()}
        team_name=st.selectbox("Team represented in the screenshot",sorted(team_names))
        files=st.file_uploader(
            "Upload image(s)",
            type=["png","jpg","jpeg","webp"],
            accept_multiple_files=True,
        )

        if st.button("­ЪДа Analyze & Save",disabled=not files):
            if not GEMINI_AVAILABLE:
                st.error("Install google-genai first.")
            elif not get_gemini_key():
                st.error("GEMINI_API_KEY is missing from server secrets.")
            else:
                with st.spinner("Extracting defensive intelligence..."):
                    result=analyze_admin_images(files,team_name,data)
                if result:
                    enrichment=load_enrichment()
                    enrichment.setdefault("teams",{})[str(team_names[team_name])]=result
                    save_enrichment(enrichment)
                    st.success("Defensive enrichment saved for this session.")
                    st.json(result)

        current=load_enrichment().get("teams",{}).get(str(team_names[team_name]),{})
        if current:
            st.markdown("#### Current enrichment")
            st.json(current)

    with tab2:
        st.success("FPL Data Connected")
        st.write(f"Teams: **{len(data['teams'])}**")
        st.write(f"Players: **{len(data['players'])}**")
        st.write(f"Fixtures: **{len(data['fixtures'])}**")
        st.write(f"Current GW: **{get_current_gw(data['events'])}**")
        st.write(f"Gemini: **{'Connected' if get_gemini_key() and GEMINI_AVAILABLE else 'Not configured'}**")
        st.write(f"Last FPL refresh: **{data.get('updated','')[:19]}**")

    with tab3:
        st.info("For production, keep the repository private and store ADMIN_PASSWORD / GEMINI_API_KEY in Streamlit Secrets.")
        if st.button("Clear enrichment from this session"):
            st.session_state["admin_enrichment"]={}
            st.success("Session enrichment cleared.")


def get_gemini_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"])
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY","")


def analyze_admin_images(files,team_name,data):
    client=genai.Client(api_key=get_gemini_key())
    parts=[]
    for f in files:
        raw=f.getvalue()
        parts.append(types.Part.from_bytes(data=raw,mime_type=f.type or "image/png"))
    prompt=f""" You are the defensive-data extraction layer for FPL HOME. Team: {team_name} The images are owner-provided football/FPL analytical data. Extract ONLY what is visibly supported. Return JSON only: {{ "left": number 0-100, "center": number 0-100, "right": number 0-100, "vulnerability": number 0-100, "confidence": "High/Medium/Low", "top_chance_sources": [ {{"zone":"Left/Center/Right","description":"short description","value":number}} ], "notes":"short explanation" }} If the source gives percentages/counts rather than a 0-100 vulnerability score, normalize them consistently and explain in notes. Do not invent missing values. If a zone cannot be established, use the FPL proxy only by leaving that zone null. """
    try:
        response=client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt]+parts,
            config=types.GenerateContentConfig(response_mime_type="application/json",temperature=0.1,max_output_tokens=1200),
        )
        obj=json.loads(response.text)
        return obj
    except Exception as e:
        st.error(f"AI extraction error: {e}")
        return None


# ============================================================
# SEARCH + PLAYER PROFILE
# ============================================================

def global_search(data):
    st.markdown('<div class="section-title">Global Search</div>',unsafe_allow_html=True)
    q=st.text_input("Search player, team or GW",placeholder="e.g. Haaland, Arsenal, GW 8",label_visibility="collapsed")
    if not q:
        return None

    ql=q.lower().strip()
    players=data["players"]
    matches=[p for p in players if ql in p["name"].lower() or ql in p["web_name"].lower() or ql in p["team"].lower()]
    teams=[t for t in data["teams"].values() if ql in t["name"].lower() or ql in t["short_name"].lower()]
    if ql.startswith("gw"):
        try:
            gw=int("".join(ch for ch in ql if ch.isdigit()))
            st.session_state["selected_gw"]=gw
            st.info(f"Gameweek {gw} selected.")
        except Exception:
            pass

    if matches:
        labels=[f"{p['name']} Рђћ {p['team_short']} Рђћ {money(p['price'])}" for p in matches[:20]]
        selected=st.selectbox("Players",labels)
        pid=next(p["id"] for p in matches if f"{p['name']} Рђћ {p['team_short']} Рђћ {money(p['price'])}"==selected)
        return ("player",pid)
    if teams:
        labels=[f"{t['name']} Рђћ {t['short_name']}" for t in teams]
        selected=st.selectbox("Teams",labels)
        tid=next(t["id"] for t in teams if f"{t['name']} Рђћ {t['short_name']}"==selected)
        return ("team",tid)
    st.caption("No matching player or team.")
    return None


def player_profile(data,player_id):
    scored=add_scores(data["players"],data)
    p=next((x for x in scored if x["id"]==player_id),None)
    if not p:
        st.warning("Player not found.")
        return
    fixtures=team_fixture_rows(data,p["team_id"],horizon=5)
    st.title(f"­ЪЉц {p['name']}")
    st.caption(f"{p['team']} ┬и {p['position']} ┬и {money(p['price'])}")

    c1,c2,c3,c4=st.columns(4)
    with c1:
        st.markdown(f'<div class="metric"><div class="metric-label">RADAR</div><div class="metric-value">{p["radar_score"]:.0f}</div><div class="metric-sub">{confidence_label(p["radar_score"])}</div></div>',unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric"><div class="metric-label">FORM</div><div class="metric-value">{p["form"]:.1f}</div><div class="metric-sub">{p["points_per_game"]:.1f} PPG</div></div>',unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric"><div class="metric-label">OWNERSHIP</div><div class="metric-value">{p["selected_by"]:.1f}%</div><div class="metric-sub">{p["total_points"]:.0f} total pts</div></div>',unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric"><div class="metric-label">MINUTES</div><div class="metric-value">{p["minutes_score"]:.0f}</div><div class="metric-sub">{risk_label(p["risk_score"])} risk</div></div>',unsafe_allow_html=True)

    st.markdown('<div class="section">',unsafe_allow_html=True)
    st.subheader("Why")
    reasons=[]
    if p["form"]>=5: reasons.append("strong recent form")
    if p["expected_goal_involvements_per_90"]>=.4: reasons.append("strong xGI/90")
    if p["minutes_score"]>=75: reasons.append("good minutes security")
    if fixture_score(fixtures)>=65: reasons.append("favorable fixtures")
    st.write(" ┬и ".join(reasons) if reasons else "Balanced profile.")
    st.write(f"**Risk:** {risk_label(p['risk_score'])} ┬и **Confidence:** {confidence_label(p['radar_score'])}")
    st.write(f"**xGI/90:** {p['expected_goal_involvements_per_90']:.2f} ┬и **ICT:** {p['ict_index']:.1f} ┬и **BPS:** {p['bps']:.0f}")
    st.markdown("</div>",unsafe_allow_html=True)

    st.subheader("Fixture Run")
    st.write(fixture_run_text(fixtures))
    st.subheader("What to watch")
    if p["news"]:
        st.warning(p["news"])
    else:
        st.success("No current FPL news flag in the data feed.")


# ============================================================
# HOME
# ============================================================

def get_user_team(data,gw):
    team_id=st.session_state.get("fpl_team_id")
    if not team_id:
        return None
    return fetch_manager_team(team_id,gw)


def home(data):
    current=get_current_gw(data["events"])
    gw=st.session_state.get("selected_gw",current)
    players=add_scores(data["players"],data)
    active=[p for p in players if p["status"]=="a"]

    cap=sorted([p for p in active if p["position"] in ["MID","FWD"]],key=lambda x:x["captain_score"],reverse=True)
    cap=cap[0] if cap else None

    team=get_user_team(data,gw)
    team_points=None
    rank=None
    if team:
        team_points=team["picks"].get("entry_history",{}).get("points")
        rank=team["summary"].get("summary_overall_rank")

    st.markdown(
        f""" <div class="brand"> <div class="brand-mark">РЎЏРџй</div> <div><div class="brand-name">FPL HOME</div><div class="brand-tag">YOUR FANTASY COMMAND CENTER</div></div> </div> """,unsafe_allow_html=True)

    deadline=next((e["deadline"] for e in data["events"] if e["id"]==gw),None)
    deadline_text=deadline[:16].replace("T"," ") if deadline else "Рђћ"

    if cap:
        st.markdown(f""" <div class="hero page-fade"> <div class="hero-kicker">GAMEWEEK VERDICT ┬и GW {gw}</div> <div class="hero-main">­ЪЉЉ {cap["name"]}</div> <div class="hero-sub">Best current captain profile ┬и Radar {cap["captain_score"]:.0f} ┬и {risk_label(cap["risk_score"])} risk ┬и {confidence_label(cap["captain_score"])} confidence</div> </div> """,unsafe_allow_html=True)

    c1,c2,c3,c4=st.columns(4)
    with c1:
        value=f"{team_points}" if team_points is not None else "Рђћ"
        st.markdown(f'<div class="metric"><div class="metric-label">MY GW POINTS</div><div class="metric-value">{value}</div><div class="metric-sub">connect FPL Team ID</div></div>',unsafe_allow_html=True)
    with c2:
        value=f"{rank:,}" if rank else "Рђћ"
        st.markdown(f'<div class="metric"><div class="metric-label">OVERALL RANK</div><div class="metric-value">{value}</div><div class="metric-sub">personalized when linked</div></div>',unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric"><div class="metric-label">CAPTAIN RADAR</div><div class="metric-value">{cap["captain_score"]:.0f}' if cap else '<div class="metric"><div class="metric-label">CAPTAIN RADAR</div><div class="metric-value">Рђћ',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with c4:
        alerts=sum(1 for p in active if p["risk_score"]>=55)
        st.markdown(f'<div class="metric"><div class="metric-label">RISK FLAGS</div><div class="metric-value">{alerts}</div><div class="metric-sub">high-risk players</div></div>',unsafe_allow_html=True)

    st.markdown('<div class="section page-fade">',unsafe_allow_html=True)
    st.markdown('<div class="section-title">Most important decision</div>',unsafe_allow_html=True)
    if cap:
        st.markdown(f'<div class="rec"><div class="rec-title">­ЪЉЉ Captain: {cap["name"]}</div><div class="rec-sub">Radar {cap["captain_score"]:.0f} ┬и xGI/90 {cap["expected_goal_involvements_per_90"]:.2f} ┬и {risk_label(cap["risk_score"])} risk</div></div>',unsafe_allow_html=True)
    st.markdown(f'<div class="rec"><div class="rec-title">РЈ▒ Deadline</div><div class="rec-sub">{deadline_text}</div></div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

    if not team:
        st.info("­ЪњА Want a personalized Home? Enter your FPL Team ID in the Settings tab. No FPL password is required.")
    else:
        st.success(f"Personalized team connected: #{team['summary'].get('id', 'Рђћ')}.")


# ============================================================
# DEFENSIVE RADAR
# ============================================================

def defensive_radar(data):
    st.title("­ЪЏА Defensive Radar")
    st.caption("Free FPL data first. Owner-provided event/chance data enriches the model when available.")

    names={t["name"]:t["id"] for t in data["teams"].values()}
    selected=st.selectbox("Team",sorted(names))
    team=data["teams"][names[selected]]
    profile=enriched_defensive_profile(team,data)

    left,right=st.columns([1.15,1])
    with left:
        st.plotly_chart(draw_pitch(profile,selected),use_container_width=True)
    with right:
        st.subheader("Defensive profile")
        for label,key in [("Left zone","left"),("Center zone","center"),("Right zone","right"),("Overall vulnerability","vulnerability")]:
            st.progress(int(profile[key]))
            st.caption(f"{label}: {profile[key]:.0f}/100")
        st.caption(f"Source: {profile.get('source','FPL proxy')}")

    top=top_three_attack_zones(profile)
    st.subheader("­Ъј» Top 3 opportunity zones")
    for i,(zone,val) in enumerate(top,1):
        st.markdown(f'<div class="rec"><div class="rec-title">#{i} {zone} ┬и {val:.0f}/100</div><div class="rec-sub">Higher score = greater modeled vulnerability / opportunity.</div></div>',unsafe_allow_html=True)

    if profile.get("top_chance_sources"):
        st.subheader("­ЪЊЇ Owner-supplied chance evidence")
        st.dataframe(pd.DataFrame(profile["top_chance_sources"]),use_container_width=True,hide_index=True)

    st.subheader("РџА Players who can exploit the matchup")
    players=add_scores(data["players"],data)
    pool=[p for p in players if p["team_id"]!=team["id"] and p["position"] in ["MID","FWD"] and p["status"]=="a"]
    rows=[]
    for p in sorted(pool,key=lambda x:x["radar_score"],reverse=True)[:20]:
        rows.append({"Player":p["name"],"Team":p["team_short"],"Pos":p["position"],"Price":money(p["price"]),
                     "Own %":round(p["selected_by"],1),"xGI/90":round(p["expected_goal_involvements_per_90"],2),
                     "Minutes":round(p["minutes_score"]), "Radar":round(p["radar_score"],1),
                     "Risk":p["risk"]})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)


# ============================================================
# H2H
# ============================================================

def h2h(data):
    st.title("Рџћ Head-to-Head")
    names=sorted(t["name"] for t in data["teams"].values())
    a_name,b_name=st.columns(2)
    with a_name: a=st.selectbox("Team A",names,key="h2h_a")
    with b_name: b=st.selectbox("Team B",names,index=min(1,len(names)-1),key="h2h_b")
    if a==b:
        st.warning("Select two different teams.")
        return
    ta=next(t for t in data["teams"].values() if t["name"]==a)
    tb=next(t for t in data["teams"].values() if t["name"]==b)
    pa=enriched_defensive_profile(ta,data)
    pb=enriched_defensive_profile(tb,data)
    players=add_scores(data["players"],data)
    aa=[p for p in players if p["team_id"]==ta["id"] and p["status"]=="a"]
    bb=[p for p in players if p["team_id"]==tb["id"] and p["status"]=="a"]
    attack_a=sum(sorted([p["radar_score"] for p in aa],reverse=True)[:5])/max(1,min(5,len(aa)))
    attack_b=sum(sorted([p["radar_score"] for p in bb],reverse=True)[:5])/max(1,min(5,len(bb)))
    fa=fixture_score(team_fixture_rows(data,ta["id"],horizon=5))
    fb=fixture_score(team_fixture_rows(data,tb["id"],horizon=5))
    st.dataframe(pd.DataFrame({
        "Metric":["Defensive Strength","Vulnerability","Attack Radar","Fixture Score","Left","Center","Right"],
        a:[pa["defensive_strength"],pa["vulnerability"],attack_a,fa,pa["left"],pa["center"],pa["right"]],
        b:[pb["defensive_strength"],pb["vulnerability"],attack_b,fb,pb["left"],pb["center"],pb["right"]],
    }).round(1),use_container_width=True,hide_index=True)
    winner=a if attack_a>=attack_b else b
    st.success(f"Current model edge: **{winner}**. This is a model comparison, not a points guarantee.")


# ============================================================
# DIFFERENTIAL
# ============================================================

def differential_scout(data):
    st.title("­Ъњј Differential Scout")
    c1,c2,c3=st.columns(3)
    with c1: own=st.slider("Max ownership %",1.0,30.0,10.0,.5)
    with c2: price=st.slider("Minimum price",3.5,15.0,5.0,.1)
    with c3: pos=st.multiselect("Positions",["GKP","DEF","MID","FWD"],["MID","FWD"])
    players=add_scores(data["players"],data)
    pool=[p for p in players if p["status"]=="a" and p["selected_by"]<=own and p["price"]>=price and p["position"] in pos and p["minutes"]>100]
    pool=sorted(pool,key=lambda x:x["differential_score"],reverse=True)
    if not pool:
        st.info("No players match these filters.")
        return
    rows=[{"Rank":i+1,"Player":p["name"],"Team":p["team_short"],"Pos":p["position"],"Price":money(p["price"]),
           "Own %":round(p["selected_by"],1),"Form":p["form"],"xGI/90":round(p["expected_goal_involvements_per_90"],2),
           "Radar":round(p["differential_score"],1),"Minutes":round(p["minutes_score"]),"Risk":p["risk"],
           "Confidence":p["confidence"]} for i,p in enumerate(pool[:30])]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    p=pool[0]
    st.success(f"Best current differential: **{p['name']}** Рђћ {p['differential_score']:.0f}/100. Why: ownership {p['selected_by']:.1f}%, xGI/90 {p['expected_goal_involvements_per_90']:.2f}, {p['risk']} risk.")


# ============================================================
# CAPTAINCY
# ============================================================

def captaincy(data):
    st.title("­ЪЉЉ Captaincy Planner")
    players=add_scores(data["players"],data)
    eligible=[p for p in players if p["status"]=="a" and p["position"] in ["MID","FWD"] and p["minutes"]>250]
    ranked=sorted(eligible,key=lambda x:x["captain_score"],reverse=True)[:25]
    rows=[]
    for i,p in enumerate(ranked,1):
        fx=team_fixture_rows(data,p["team_id"],horizon=3)
        rows.append({"Rank":i,"Player":p["name"],"Team":p["team_short"],"Fixture Run":fixture_run_text(fx),
                     "Price":money(p["price"]),"Form":p["form"],"xGI/90":round(p["expected_goal_involvements_per_90"],2),
                     "Captain":round(p["captain_score"],1),"Risk":p["risk"],"Confidence":p["confidence"]})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    if ranked:
        safe=sorted(ranked,key=lambda x:(x["risk_score"],-x["captain_score"]))[0]
        upside=sorted(ranked,key=lambda x:(x["captain_score"]+max(0,30-x["selected_by"])),reverse=True)[0]
        c1,c2=st.columns(2)
        with c1:
            st.markdown(f'<div class="section"><div class="section-title">Safe Pick</div><h3>­ЪЉЉ {safe["name"]}</h3><p>Captain {safe["captain_score"]:.0f} ┬и {safe["risk"]} risk ┬и {safe["confidence"]} confidence</p></div>',unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="section"><div class="section-title">High Upside</div><h3>­Ъџђ {upside["name"]}</h3><p>Captain {upside["captain_score"]:.0f} ┬и Ownership {upside["selected_by"]:.1f}%</p></div>',unsafe_allow_html=True)


# ============================================================
# TRANSFER PLANNER
# ============================================================

def transfer_planner(data):
    st.title("­Ъћё Transfer Planner")
    st.caption("Personalized mode uses your public FPL Team ID; manual mode remains available.")
    team_id=st.number_input("FPL Team ID (optional)",min_value=0,value=int(st.session_state.get("fpl_team_id") or 0),step=1)
    if team_id:
        st.session_state["fpl_team_id"]=team_id

    gw=st.session_state.get("selected_gw",get_current_gw(data["events"]))
    manager=get_user_team(data,gw)

    players=add_scores(data["players"],data)
    if manager:
        ids={x["element"] for x in manager["picks"].get("picks",[])}
        current=[p for p in players if p["id"] in ids]
        st.success(f"Loaded {len(current)} players from Team ID.")
    else:
        labels={f"{p['name']} Рђћ {p['team_short']} Рђћ {money(p['price'])}":p["id"] for p in players if p["status"]=="a"}
        selected=st.multiselect("Current squad",list(labels),max_selections=15)
        current=[p for p in players if p["id"] in {labels[x] for x in selected}]

    if not current:
        st.info("Connect Team ID or select your current squad.")
        return

    bank=st.number_input("Money in Bank (┬Бm)",0.0,20.0,0.0,.1)
    out=sorted(current,key=lambda x:x["radar_score"])[:8]
    candidates=[p for p in players if p["status"]=="a" and p["id"] not in {x["id"] for x in current}]
    suggestions=[]
    for op in out:
        pool=[p for p in candidates if p["position"]==op["position"] and p["price"]<=op["price"]+bank]
        for ip in sorted(pool,key=lambda x:x["radar_score"],reverse=True)[:4]:
            gain=ip["radar_score"]-op["radar_score"]
            if gain>0:
                fixture_gain=fixture_score(team_fixture_rows(data,ip["team_id"],horizon=5))-fixture_score(team_fixture_rows(data,op["team_id"],horizon=5))
                suggestions.append({"OUT":op["name"],"IN":ip["name"],"Price":money(ip["price"]),"Radar Gain":round(gain,1),
                                    "Fixture Gain":round(fixture_gain,1),"Minutes Security":round(ip["minutes_score"]),
                                    "Risk":ip["risk"],"Confidence":confidence_label(gain+60)})
    suggestions=sorted(suggestions,key=lambda x:x["Radar Gain"]+x["Fixture Gain"]*.25,reverse=True)
    st.dataframe(pd.DataFrame(suggestions[:25]),use_container_width=True,hide_index=True)
    if suggestions:
        s=suggestions[0]
        st.success(f"Best current move: **{s['OUT']} Рєњ {s['IN']}** ┬и Radar +{s['Radar Gain']} ┬и Fixture +{s['Fixture Gain']} ┬и {s['Risk']} risk.")


# ============================================================
# TEAM OPTIMIZER
# ============================================================

def team_optimizer(data):
    st.title("­ЪДа Team Optimizer")
    budget=st.number_input("Squad budget (┬Бm)",50.0,120.0,100.0,.1)
    strategy=st.selectbox("Strategy",["Safe","Balanced","Differential"])
    players=add_scores(data["players"],data)
    ownership_weight={"Safe":.20,"Balanced":.10,"Differential":-.05}[strategy]
    for p in players:
        p["optimizer_score"]=p["radar_score"]*.80+clamp(p["selected_by"]*4,0,100)*ownership_weight
    positions={"GKP":2,"DEF":5,"MID":5,"FWD":3}
    selected=[]; counts={}; remaining=budget
    for pos,n in positions.items():
        pool=sorted([p for p in players if p["position"]==pos and p["status"]=="a" and p["minutes"]>100],key=lambda x:x["optimizer_score"],reverse=True)
        for p in pool:
            if sum(1 for x in selected if x["position"]==pos)>=n: break
            if remaining-p["price"]<0 or counts.get(p["team_id"],0)>=3: continue
            selected.append(p); remaining-=p["price"]; counts[p["team_id"]]=counts.get(p["team_id"],0)+1
    st.dataframe(pd.DataFrame([{"Player":p["name"],"Team":p["team_short"],"Pos":p["position"],"Price":money(p["price"]),"Score":round(p["optimizer_score"],1),"Risk":p["risk"]} for p in selected]),use_container_width=True,hide_index=True)
    st.metric("Squad Cost",money(budget-remaining),f"{remaining:.1f}m remaining")


# ============================================================
# WHAT CHANGED + FIXTURE SWING + PRICE WATCH
# ============================================================

def what_changed(data):
    st.title("­ЪЊѕ What Changed?")
    players=add_scores(data["players"],data)
    rising=sorted(players,key=lambda x:x["form"],reverse=True)[:10]
    falling=sorted(players,key=lambda x:x["form"])[:10]
    c1,c2=st.columns(2)
    with c1:
        st.subheader("Risers by current form")
        st.dataframe(pd.DataFrame([{"Player":p["name"],"Team":p["team_short"],"Form":p["form"],"Radar":round(p["radar_score"],1)} for p in rising]),use_container_width=True,hide_index=True)
    with c2:
        st.subheader("Watch / falling form")
        st.dataframe(pd.DataFrame([{"Player":p["name"],"Team":p["team_short"],"Form":p["form"],"Risk":p["risk"]} for p in falling]),use_container_width=True,hide_index=True)

    st.subheader("Fixture Swing")
    rows=[]
    gw=get_current_gw(data["events"])
    for t in data["teams"].values():
        now=fixture_score(team_fixture_rows(data,t["id"],gw,horizon=3))
        nxt=fixture_score(team_fixture_rows(data,t["id"],gw+3,horizon=3))
        rows.append({"Team":t["name"],"Current 3GW":round(now,1),"Next 3GW":round(nxt,1),"Swing":round(nxt-now,1)})
    st.dataframe(pd.DataFrame(rows).sort_values("Swing",ascending=False),use_container_width=True,hide_index=True)

    st.subheader("­Ъњ░ Price Watch")
    st.caption("Current FPL price is available. Historical price movement requires a historical source; no fake change is shown.")
    st.dataframe(pd.DataFrame([{"Player":p["name"],"Team":p["team_short"],"Price":money(p["price"]),"Ownership":pct(p["selected_by"]),"Form":p["form"]} for p in sorted(players,key=lambda x:x["price"],reverse=True)[:25]]),use_container_width=True,hide_index=True)


# ============================================================
# SETTINGS
# ============================================================

def settings_page(data):
    st.title("РџЎ№ИЈ Settings")
    st.subheader("Personal FPL Team")
    team_id=st.number_input("FPL Team ID",min_value=0,value=int(st.session_state.get("fpl_team_id") or 0),step=1)
    if team_id:
        st.session_state["fpl_team_id"]=team_id
        st.success("Team ID saved for this session.")
    st.caption("The FPL public endpoints are used for team summary/picks where available. No FPL password is stored.")

    st.subheader("Data sources")
    st.write("Рђб FPL public API: automatic, no user API key required.")
    st.write("Рђб Owner enrichment: screenshots/images only from the owner.")
    st.write("Рђб Gemini: explanation/extraction layer; core FPL numbers remain in the structured engine.")

    st.subheader("Refresh")
    if st.button("­Ъћё Refresh FPL data"):
        st.cache_data.clear()
        st.rerun()


# ============================================================
# ASK FPL HOME
# ============================================================

def ai_answer(question,data):
    if not GEMINI_AVAILABLE:
        return "Gemini SDK is not installed. Run: pip install -U google-genai"
    key=get_gemini_key()
    if not key:
        return "AI is not configured on the server. Core FPL HOME analytics remain available."

    client=genai.Client(api_key=key)
    players=add_scores(data["players"],data)
    top=sorted(players,key=lambda x:x["radar_score"],reverse=True)[:60]
    context={
        "gameweek":get_current_gw(data["events"]),
        "players":[{"name":p["name"],"team":p["team_short"],"pos":p["position"],"price":p["price"],"ownership":p["selected_by"],
                    "form":p["form"],"xgi90":p["expected_goal_involvements_per_90"],"minutes":p["minutes_score"],
                    "radar":p["radar_score"],"captain":p["captain_score"],"risk":p["risk_score"]} for p in top],
        "defensive_enrichment":load_enrichment(),
    }
    prompt=f""" You are FPL HOME, an expert Fantasy Premier League decision assistant. Rules: - Numerical claims must come only from supplied data. - Never invent xG, xA, chance locations, ownership, price or fixtures. - Clearly label owner-enriched defensive data versus FPL API data. - Radar scores are model scores, not actual FPL points. - Give a verdict, why, risk, and alternative where useful. - Be concise and practical. Question: {question} DATA: {json.dumps(context,ensure_ascii=False)} """
    try:
        response=client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=.2,max_output_tokens=1000),
        )
        return response.text
    except Exception as e:
        return f"Gemini error: {e}"


def ask_home(data):
    st.title("­Ъцќ Ask FPL HOME")
    st.caption("The AI explains the numbers. It does not replace the structured FPL data engine.")
    if "chat" not in st.session_state:
        st.session_state["chat"]=[]
    for m in st.session_state["chat"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    q=st.chat_input("Salah or Haaland captain? Which team has the best fixture swing?")
    if q:
        st.session_state["chat"].append({"role":"user","content":q})
        with st.chat_message("assistant"):
            with st.spinner("FPL HOME is analyzing..."):
                a=ai_answer(q,data)
            st.markdown(a)
        st.session_state["chat"].append({"role":"assistant","content":a})


# ============================================================
# NAVIGATION
# ============================================================

PAGES=[
    ("­ЪЈа","Home"),
    ("­ЪЏА","Defensive"),
    ("Рџћ","H2H"),
    ("­Ъњј","Differentials"),
    ("­ЪЉЉ","Captain"),
    ("­Ъћё","Transfers"),
    ("­ЪДа","Optimizer"),
    ("­ЪЊѕ","Changes"),
    ("­Ъцќ","Ask AI"),
    ("РџЎ","Settings"),
]


def render_nav():
    current=st.session_state.get("page","Home")
    cols=st.columns(len(PAGES))
    for col,(icon,label) in zip(cols,PAGES):
        with col:
            active=current==label
            if st.button(f"{icon} {label}",key=f"nav_{label}",use_container_width=True):
                st.session_state["page"]=label
                st.rerun()


# ============================================================
# MAIN
# ============================================================

def main():
    raw=None
    try:
        raw=load_fpl_data()
        data=normalize_data(raw)
    except Exception as e:
        st.error("Unable to load FPL data.")
        st.code(str(e))
        if st.button("Retry"):
            st.cache_data.clear()
            st.rerun()
        return

    if "page" not in st.session_state:
        st.session_state["page"]="Home"
    if "selected_gw" not in st.session_state:
        st.session_state["selected_gw"]=get_current_gw(data["events"])

    st.markdown(
        f'<div class="nav-note">GW {st.session_state["selected_gw"]} ┬и Live FPL data ┬и updated {data["updated"][:16].replace("T"," ")}</div>',
        unsafe_allow_html=True,
    )
    render_nav()

    # Compact global search lives below navigation.
    search_result=global_search(data)
    if search_result:
        kind,obj=search_result
        if kind=="player":
            player_profile(data,obj)
            return
        if kind=="team":
            st.session_state["page"]="Defensive"
            st.rerun()

    page=st.session_state["page"]

    if page=="Home":
        home(data)
    elif page=="Defensive":
        defensive_radar(data)
    elif page=="H2H":
        h2h(data)
    elif page=="Differentials":
        differential_scout(data)
    elif page=="Captain":
        captaincy(data)
    elif page=="Transfers":
        transfer_planner(data)
    elif page=="Optimizer":
        team_optimizer(data)
    elif page=="Changes":
        what_changed(data)
    elif page=="Ask AI":
        ask_home(data)
    elif page=="Settings":
        settings_page(data)

    # Owner controls are not in normal navigation.
    with st.sidebar:
        if st.button("­Ъћљ Owner Control Center",use_container_width=True):
            st.session_state["page"]="Admin"
            st.rerun()

    if st.session_state.get("page")=="Admin":
        admin_login()
        if is_admin():
            admin_panel(data)


if __name__=="__main__":
    main()
