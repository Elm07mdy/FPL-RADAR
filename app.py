import streamlit as st
import json
import os
import pandas as pd
from PIL import Image
from google import genai
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. Page Configuration & Improved UI Theme (High Contrast)
# ---------------------------------------------------------
st.set_page_config(
    page_title="FPL Radar",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #0b0f19; color: #f8fafc; }
    .stSelectbox label, .stMultiSelect label, .stSlider label { font-weight: bold; color: #00ff87 !important; font-size: 1.05rem; }
    
    /* تحسين تباين الكروت لضمان وضوح الكتابة وعدم طغيان الخلفية */
    .stat-card {
        background: rgba(30, 41, 59, 0.90);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-right: 5px solid #00ff87;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.6);
    }
    .stat-card h3, .stat-card h4 { color: #ffffff !important; }
    .stat-card p, .stat-card small { color: #e2e8f0 !important; }
    
    .badge-diff { background-color: #2563eb; color: #ffffff; padding: 3px 10px; border-radius: 6px; font-weight: bold; font-size: 0.8rem; }
    .badge-cap { background-color: #ca8a04; color: #ffffff; padding: 3px 10px; border-radius: 6px; font-weight: bold; font-size: 0.8rem; }
    .badge-target { background-color: #059669; color: #ffffff; padding: 3px 10px; border-radius: 6px; font-weight: bold; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

DB_FILE = "fpl_radar_db.json"

default_data = {
    "TOP4_TARGETS": {
        "title": "🔥 Top 4 Defensive Targets for Upcoming Gameweeks",
        "isTop4View": True,
        "topTeams": [
            {
                "name": "Ipswich Town", 
                "reason": "Conceded 5 Big Chances in latest match & high xGC (2.24)", 
                "targetPosition": "Left Wings & Central Playmakers (Zone 14)", 
                "recommendedPlayers": ["Saka (Arsenal)", "Palmer (Chelsea)"], 
                "capRating": "9.5/10"
            },
            {
                "name": "Everton", 
                "reason": "Exposed space behind Right Back against fast counter-attacks", 
                "targetPosition": "Left Wings & Pace Attackers", 
                "recommendedPlayers": ["Martinelli (Arsenal)", "Semenyo (Bournemouth)"], 
                "capRating": "8.2/10"
            }
        ]
    },
    "Ipswich": {
        "title": "Ipswich Town Defensive Weakness Analysis",
        "leftZone": {"level": "HIGH", "val": 85, "text": "Severely exploited left flank on crosses"},
        "centerZone": {"level": "HIGH", "val": 90, "text": "Zone 14: Conceded 13 shots inside penalty box"},
        "rightZone": {"level": "MED", "val": 50, "text": "Right Flank: Average coverage"},
        "xGConceded": "2.24",
        "bigChancesConceded": "5",
        "setPieceVulnerability": "Very High (4 aerial headers conceded)",
        "luckIndex": "Deservedly Conceded",
        "targetAdvice": "🎯 Target/Captain right-wingers or central playmakers facing Ipswich next.",
        "fixtures": ["vs Arsenal (H)", "vs Chelsea (A)"],
        "recommendedPlayers": [
            {"name": "Bukayo Saka", "team": "Arsenal", "pos": "MID", "price": "10.1m", "selectedBy": "34%", "isDiff": False},
            {"name": "Cole Palmer", "team": "Chelsea", "pos": "MID", "price": "10.8m", "selectedBy": "52%", "isDiff": False}
        ]
    },
    "Everton": {
        "title": "Everton Defensive Weakness Analysis",
        "leftZone": {"level": "LOW", "val": 25, "text": "Solid defensively on left flank"},
        "centerZone": {"level": "MED", "val": 55, "text": "Conceded 9 shots in central box area"},
        "rightZone": {"level": "HIGH", "val": 80, "text": "Clear vulnerability behind Right Back"},
        "xGConceded": "1.44",
        "bigChancesConceded": "1",
        "setPieceVulnerability": "Low",
        "luckIndex": "Good Luck Factor",
        "targetAdvice": "🎯 Target Left Wingers attacking Everton's right flank.",
        "fixtures": ["vs Man City (A)", "vs Fulham (H)"],
        "recommendedPlayers": [
            {"name": "Jeremy Doku", "team": "Man City", "pos": "MID", "price": "6.5m", "selectedBy": "4%", "isDiff": True},
            {"name": "Antoine Semenyo", "team": "Bournemouth", "pos": "MID", "price": "5.6m", "selectedBy": "12%", "isDiff": True}
        ]
    }
}

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default_data
    return default_data

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if "database" not in st.session_state:
    st.session_state.database = load_db()

# ---------------------------------------------------------
# 2. Advanced Professional Pitch Function (Plotly)
# ---------------------------------------------------------
def draw_interactive_pitch(left_val, center_val, right_val, team_name):
    fig = go.Figure()

    fig.add_shape(type="rect", x0=0, y0=0, x1=120, y1=80, fillcolor="#0f2b22", line=dict(color="white", width=2))
    fig.add_shape(type="line", x0=60, y0=0, x1=60, y1=80, line=dict(color="white", width=2))
    fig.add_shape(type="circle", x0=45, y0=25, x1=75, y1=55, line=dict(color="white", width=2), fillcolor="rgba(0,0,0,0)")
    fig.add_shape(type="rect", x0=102, y0=18, x1=120, y1=62, fillcolor="rgba(0,0,0,0)", line=dict(color="white", width=2))
    fig.add_shape(type="rect", x0=114, y0=30, x1=120, y1=50, fillcolor="rgba(0,0,0,0)", line=dict(color="white", width=2))

    get_color = lambda v: f"rgba(239, 68, 68, {v/120})" if v > 70 else (f"rgba(249, 115, 22, {v/120})" if v > 40 else "rgba(34, 197, 94, 0.3)")

    fig.add_shape(type="rect", x0=80, y0=53, x1=120, y1=80, fillcolor=get_color(left_val), line=dict(color="red" if left_val > 70 else "orange", width=1.5))
    fig.add_shape(type="rect", x0=80, y0=27, x1=120, y1=52, fillcolor=get_color(center_val), line=dict(color="red" if center_val > 70 else "orange", width=1.5))
    fig.add_shape(type="rect", x0=80, y0=0, x1=120, y1=26, fillcolor=get_color(right_val), line=dict(color="red" if right_val > 70 else "orange", width=1.5))

    fig.add_annotation(x=100, y=66, text=f"Left Flank<br>{left_val}%", showarrow=False, font=dict(color="white", size=12, family="Arial Black"))
    fig.add_annotation(x=100, y=40, text=f"Zone 14 / Center<br>{center_val}%", showarrow=False, font=dict(color="white", size=12, family="Arial Black"))
    fig.add_annotation(x=100, y=13, text=f"Right Flank<br>{right_val}%", showarrow=False, font=dict(color="white", size=12, family="Arial Black"))

    fig.update_layout(
        title=dict(text=f"Tactical Defensive Radar: {team_name}", font=dict(color="#00ff87", size=16)),
        xaxis=dict(visible=False, range=[-2, 122]),
        yaxis=dict(visible=False, range=[-2, 82]),
        height=380,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# ---------------------------------------------------------
# 3. Sidebar & AI Processing Configuration (Gemini 3.8)
# ---------------------------------------------------------
st.sidebar.title("🎯 FPL Radar Pro")
st.sidebar.caption("Interactive Tactical Fantasy Assistant")

api_key = st.sidebar.text_input("🔑 Gemini API Key", type="password")
uploaded_files = st.sidebar.file_uploader("📁 Upload Round Screenshots", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files and st.sidebar.button("⚡ Analyze Screenshots & Update Radar"):
    if not api_key:
        st.sidebar.error("Please enter a valid Gemini API Key!")
    else:
        with st.spinner("Analyzing tactical maps & stats via Gemini 3.8 AI..."):
            try:
                client = genai.Client(api_key=api_key)
                images = [Image.open(f) for f in uploaded_files]
                
                prompt = """
                Analyze FPL tactical stats images and extract defensive data in 100% English.
                Return ONLY a valid JSON object using this exact format without extra markdown text:
                {
                    "TOP4_TARGETS": {
                        "title": "Top 4 Defensive Targets", 
                        "isTop4View": true, 
                        "topTeams": [
                            {
                                "name": "Team Name", 
                                "reason": "reason here", 
                                "targetPosition": "Wings / Center", 
                                "recommendedPlayers": ["Player 1", "Player 2"], 
                                "capRating": "9.0/10"
                            }
                        ]
                    },
                    "TeamKeyWithoutSpaces": {
                        "title": "Team Full Name Defensive Weakness Analysis",
                        "leftZone": {"level": "HIGH", "val": 80, "text": "description"},
                        "centerZone": {"level": "HIGH", "val": 85, "text": "description"},
                        "rightZone": {"level": "MED", "val": 40, "text": "description"},
                        "xGConceded": "1.85",
                        "bigChancesConceded": "4",
                        "setPieceVulnerability": "Risk assessment",
                        "luckIndex": "Luck factor",
                        "targetAdvice": "Fantasy advice",
                        "fixtures": ["Fixture 1"],
                        "recommendedPlayers": [
                            {"name": "Player Name", "team": "Team", "pos": "MID", "price": "7.5m", "selectedBy": "15%", "isDiff": false}
                        ]
                    }
                }
                """
                # استدعاء أحدث نموذج gemini-3.8-flash
                res = client.models.generate_content(model="gemini-3.8-flash", contents=[prompt, *images])
                clean_json = res.text.replace("```json", "").replace("```", "").strip()
                new_data = json.loads(clean_json)
                
                for k, v in new_data.items():
                    st.session_state.database[k] = v
                    
                save_db(st.session_state.database)
                st.sidebar.success("✅ Radar updated successfully via Gemini 3.8!")
            except Exception as e:
                st.sidebar.error(f"Error processing images: {e}")

# ---------------------------------------------------------
# 4. Main Application Interface
# ---------------------------------------------------------
st.title("🎯 FPL Radar - Ultimate Fantasy Analytics")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Club Radar & Vulnerabilities", 
    "⚔️ Head-To-Head (H2H)", 
    "🚀 Differential Scout", 
    "👑 Captaincy Planner",
    "📱 Social Media Generator"
])

# TAB 1: Club Radar & Vulnerabilities
with tab1:
    teams_dict = {"🔥 Top 4 Defensive Targets": "TOP4_TARGETS"}
    for k in st.session_state.database.keys():
        if k != "TOP4_TARGETS":
            teams_dict[st.session_state.database[k].get("title", k)] = k

    selected_team_label = st.selectbox("Select View or Team Analysis:", list(teams_dict.keys()))
    selected_key = teams_dict[selected_team_label]
    team_data = st.session_state.database.get(selected_key, {})

    if team_data.get("isTop4View"):
        st.subheader(team_data["title"])
        for idx, t in enumerate(team_data.get("topTeams", []), 1):
            st.markdown(f"""
            <div class="stat-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0;">#{idx} {t['name']}</h3>
                    <span class="badge-cap">Captaincy Rating: {t.get('capRating', '9.0/10')}</span>
                </div>
                <p style="margin:10px 0;"><b>Tactical Reason:</b> {t['reason']}</p>
                <p style="margin:5px 0;"><b>Target Position:</b> <span class="badge-target">{t['targetPosition']}</span></p>
                <p style="margin:5px 0;"><b>Recommended Players:</b> {", ".join(t.get('recommendedPlayers', []))}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        col_left, col_right = st.columns([1.5, 1])
        
        with col_left:
            fig = draw_interactive_pitch(
                team_data.get('leftZone', {}).get('val', 50), 
                team_data.get('centerZone', {}).get('val', 50), 
                team_data.get('rightZone', {}).get('val', 50), 
                team_data.get('title', selected_key)
            )
            st.plotly_chart(fig, use_container_width=True)
            st.info(team_data.get("targetAdvice", ""))

        with col_right:
            st.write("### 📈 Tactical Indicators")
            st.markdown(f"""
            <div class="stat-card">
                <small>xG Conceded (xGC)</small>
                <h2 style="color:#00ff87; margin:0;">{team_data.get('xGConceded', 'N/A')}</h2>
            </div>
            <div class="stat-card">
                <small>Big Chances Conceded</small>
                <h2 style="color:#f97316; margin:0;">{team_data.get('bigChancesConceded', 'N/A')}</h2>
            </div>
            <div class="stat-card">
                <small>Set-Pieces & Aerial Risk</small>
                <p style="color:#f87171; margin:0; font-weight:bold;">{team_data.get('setPieceVulnerability', 'N/A')}</p>
            </div>
            <div class="stat-card">
                <small>Luck Index Factor</small>
                <p style="color:#38bdf8; margin:0; font-weight:bold;">{team_data.get('luckIndex', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.write("### 🎯 Recommended Target Players")
        rec_players = team_data.get("recommendedPlayers", [])
        if rec_players:
            p_cols = st.columns(len(rec_players))
            for idx, p in enumerate(rec_players):
                with p_cols[idx]:
                    st.markdown(f"""
                    <div class="stat-card" style="text-align:center;">
                        <h4 style="margin:0;">{p['name']}</h4>
                        <p style="margin:5px 0;">{p['team']} | {p['pos']}</p>
                        <p style="margin:5px 0;"><b>Price:</b> {p['price']} | <b>Owned By:</b> {p['selectedBy']}</p>
                        {'<span class="badge-diff">💎 Differential Gem</span>' if p.get('isDiff') else '<span class="badge-target">🔥 Premium Pick</span>'}
                    </div>
                    """, unsafe_allow_html=True)

# TAB 2: H2H Comparison
with tab2:
    st.subheader("⚔️ Direct Defensive H2H Comparison")
    avail_teams = [k for k in st.session_state.database.keys() if k != "TOP4_TARGETS"]
    
    if len(avail_teams) >= 2:
        c1, c2 = st.columns(2)
        with c1:
            t1 = st.selectbox("First Team:", avail_teams, index=0, key="h2h_t1")
        with c2:
            t2 = st.selectbox("Second Team:", avail_teams, index=1 if len(avail_teams)>1 else 0, key="h2h_t2")
            
        d1, d2 = st.session_state.database[t1], st.session_state.database[t2]
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(draw_interactive_pitch(d1['leftZone']['val'], d1['centerZone']['val'], d1['rightZone']['val'], t1), use_container_width=True)
            st.metric("xG Conceded", d1.get("xGConceded", "N/A"))
        with col_b:
            st.plotly_chart(draw_interactive_pitch(d2['leftZone']['val'], d2['centerZone']['val'], d2['rightZone']['val'], t2), use_container_width=True)
            st.metric("xG Conceded", d2.get("xGConceded", "N/A"))

# TAB 3: Differential Scout
with tab3:
    st.subheader("🚀 Hidden Differential Targets (Ownership < 15%)")
    diffs = []
    for k, v in st.session_state.database.items():
        if k != "TOP4_TARGETS":
            for p in v.get("recommendedPlayers", []):
                if p.get("isDiff"):
                    diffs.append({**p, "targetTeam": v.get("title", k)})
                    
    if diffs:
        for d in diffs:
            st.markdown(f"""
            <div class="stat-card">
                <span class="badge-diff">💎 Differential Gem</span>
                <h3 style="display:inline; margin-left:10px;">{d['name']} ({d['team']})</h3>
                <p style="margin:8px 0;"><b>Price:</b> {d['price']} | <b>Ownership:</b> {d['selectedBy']} | <b>Targeting:</b> {d['targetTeam']}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No differential players found yet. Upload screenshots to extract new recommendations.")

# TAB 4: Captaincy Planner
with tab4:
    st.subheader("👑 Expected Captaincy Planner")
    avail_targets = [k for k in st.session_state.database.keys() if k != "TOP4_TARGETS"]
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        p1_name = st.text_input("Player Name 1:", "Bukayo Saka", key="cap1_n")
        p1_form = st.slider("Attack Form (xGI):", 0.0, 2.0, 0.8, key="cap1_f")
        p1_target = st.selectbox("Opponent:", avail_targets, key="cap1_t")
    with col_c2:
        p2_name = st.text_input("Player Name 2:", "Cole Palmer", key="cap2_n")
        p2_form = st.slider("Attack Form (xGI):", 0.0, 2.0, 0.9, key="cap2_f")
        p2_target = st.selectbox("Opponent:", avail_targets, index=min(1, len(avail_targets)-1), key="cap2_t")
    with col_c3:
        p3_name = st.text_input("Player Name 3:", "Erling Haaland", key="cap3_n")
        p3_form = st.slider("Attack Form (xGI):", 0.0, 2.0, 1.2, key="cap3_f")
        p3_target = st.selectbox("Opponent:", avail_targets, key="cap3_t")

    if st.button("🧮 Calculate Best Captaincy Pick"):
        def calc_score(form, target_key):
            t_data = st.session_state.database.get(target_key, {})
            try: xgc = float(t_data.get("xGConceded", "1.5"))
            except: xgc = 1.5
            return round(min((form * 4.5) + (xgc * 3.0), 10.0), 1)

        res = [(p1_name, calc_score(p1_form, p1_target), p1_target),
               (p2_name, calc_score(p2_form, p2_target), p2_target),
               (p3_name, calc_score(p3_form, p3_target), p3_target)]
        res.sort(key=lambda x: x[1], reverse=True)
        st.success(f"🏆 **Recommended Captain:** **{res[0][0]}** with Rating **({res[0][1]}/10)** vs {res[0][2]}")

# TAB 5: Social Media Generator
with tab5:
    st.subheader("📱 Social Media Thread & Summary Generator")
    teams_list = [k for k in st.session_state.database.keys() if k != "TOP4_TARGETS"]
    if teams_list:
        selected_pub_team = st.selectbox("Select Team for Summary:", teams_list)
        pdata = st.session_state.database[selected_pub_team]
        tweet_text = f"""🎯 FPL Radar | Defensive Vulnerability Analysis: {pdata.get('title', selected_pub_team)} ⚽

📊 Defensive Stats:
• xG Conceded: {pdata.get('xGConceded', 'N/A')}
• Big Chances Conceded: {pdata.get('bigChancesConceded', 'N/A')}

💡 Fantasy Recommendations:
{pdata.get('targetAdvice', '')}

#FPL #FPLCommunity #FPL_Radar"""
        st.text_area("📋 Copy-Paste Ready Post:", tweet_text, height=200)
