import streamlit as st
import json
import os
import pandas as pd
from PIL import Image
from google import genai
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. Page Configuration & Custom Theme
# ---------------------------------------------------------
st.set_page_config(
    page_title="FPL Radar 🎯 - Ultimate Fantasy Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for FPL Dark Theme
st.markdown("""
<style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .stSelectbox label, .stMultiSelect label, .stSlider label { font-weight: bold; color: #00ff87 !important; font-size: 1.05rem; }
    .stat-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border-right: 4px solid #00ff87;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .badge-diff { background-color: #3b82f6; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    .badge-cap { background-color: #eab308; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    .badge-target { background-color: #00ff87; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

DB_FILE = "fpl_radar_db.json"

# ---------------------------------------------------------
# 2. Database Management & Persistence
# ---------------------------------------------------------
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
                "name": "Leicester City", 
                "reason": "Severe weakness against crosses and aerial duels", 
                "targetPosition": "Box Strikers & Right Wings", 
                "recommendedPlayers": ["Haaland (Man City)", "Watkins (Aston Villa)"], 
                "capRating": "9.0/10"
            },
            {
                "name": "Wolverhampton", 
                "reason": "Clear vulnerability in Zone 14 & long-range shots conceded", 
                "targetPosition": "Attacking Midfielders (CAM)", 
                "recommendedPlayers": ["Salah (Liverpool)", "Bruno (Man Utd)"], 
                "capRating": "8.8/10"
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
        "luckIndex": "Deservedly Conceded (No Luck Factor)",
        "targetAdvice": "🎯 Target/Captain right-wingers or central playmakers facing Ipswich next.",
        "fixtures": ["vs Arsenal (H)", "vs Chelsea (A)", "vs Everton (H)"],
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
        "setPieceVulnerability": "Low (Strong aerial duels)",
        "luckIndex": "Conceded fewer goals than xG (Good Luck)",
        "targetAdvice": "🎯 Target Left Wingers (LWM) attacking Everton's right flank.",
        "fixtures": ["vs Man City (A)", "vs Fulham (H)", "vs Newcastle (A)"],
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
# 3. Plotly Interactive Pitch Function
# ---------------------------------------------------------
def draw_interactive_pitch(left_val, center_val, right_val, team_name):
    fig = go.Figure()

    fig.add_shape(type="rect", x0=0, y0=0, x1=100, y1=100, fillcolor="#14532d", line=dict(color="white", width=2))
    fig.add_shape(type="rect", x0=0, y0=20, x1=20, y1=80, fillcolor="#14532d", line=dict(color="white", width=2))
    fig.add_shape(type="rect", x0=0, y0=35, x1=8, y1=65, fillcolor="#14532d", line=dict(color="white", width=2))

    get_color = lambda v: f"rgba(239, 68, 68, {v/100})" if v > 70 else (f"rgba(249, 115, 22, {v/100})" if v > 40 else "rgba(34, 197, 94, 0.5)")

    fig.add_shape(type="rect", x0=0, y0=66, x1=35, y1=100, fillcolor=get_color(left_val), line=dict(color="red" if left_val > 70 else "orange", width=1.5))
    fig.add_shape(type="rect", x0=0, y0=33, x1=35, y1=65, fillcolor=get_color(center_val), line=dict(color="red" if center_val > 70 else "orange", width=1.5))
    fig.add_shape(type="rect", x0=0, y0=0, x1=35, y1=32, fillcolor=get_color(right_val), line=dict(color="red" if right_val > 70 else "orange", width=1.5))

    fig.add_annotation(x=17.5, y=83, text=f"Left Flank ({left_val}%)", showarrow=False, font=dict(color="white", size=14, family="Arial Black"))
    fig.add_annotation(x=17.5, y=50, text=f"Zone 14 / Center ({center_val}%)", showarrow=False, font=dict(color="white", size=14, family="Arial Black"))
    fig.add_annotation(x=17.5, y=16, text=f"Right Flank ({right_val}%)", showarrow=False, font=dict(color="white", size=14, family="Arial Black"))

    fig.update_layout(
        title=dict(text=f"Defensive Vulnerability Radar: {team_name}", font=dict(color="#00ff87", size=18)),
        xaxis=dict(visible=False, range=[-5, 105]),
        yaxis=dict(visible=False, range=[-5, 105]),
        height=380,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# ---------------------------------------------------------
# 4. Sidebar Controls & AI Auto-Processing
# ---------------------------------------------------------
st.sidebar.title("🎯 FPL Radar Pro")
st.sidebar.caption("Interactive Tactical Fantasy Assistant")

api_key = st.sidebar.text_input("🔑 Gemini API Key", type="password")
uploaded_files = st.sidebar.file_uploader("📁 Upload Round Screenshots", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files and st.sidebar.button("⚡ Analyze Screenshots & Update Radar"):
    if not api_key:
        st.sidebar.error("Please enter a valid Gemini API Key!")
    else:
        with st.spinner("Analyzing tactical maps & stats via AI..."):
            try:
                client = genai.Client(api_key=api_key)
                images = [Image.open(f) for f in uploaded_files]
                
                prompt = """
                Analyze FPL tactical stats images and extract defensive data in 100% English.
                Return ONLY JSON using this exact format:
                {
                    "TOP4_TARGETS": {"title": "Top 4 Defensive Targets", "isTop4View": true, "topTeams": [...]},
                    "TeamNameInEnglish": {
                        "title": "Team Name Defensive Weakness Analysis",
                        "leftZone": {"level": "HIGH/MED/LOW", "val": 80, "text": "description"},
                        "centerZone": {"level": "HIGH/MED/LOW", "val": 85, "text": "description"},
                        "rightZone": {"level": "HIGH/MED/LOW", "val": 40, "text": "description"},
                        "xGConceded": "1.85",
                        "bigChancesConceded": "4",
                        "setPieceVulnerability": "Set piece risk assessment",
                        "luckIndex": "Luck index factor",
                        "targetAdvice": "Fantasy target recommendation",
                        "fixtures": ["Fixture 1", "Fixture 2"],
                        "recommendedPlayers": [
                            {"name": "Player Name", "team": "Team", "pos": "MID/FWD", "price": "7.5m", "selectedBy": "15%", "isDiff": false}
                        ]
                    }
                }
                """
                res = client.models.generate_content(model="gemini-3.8-flash", contents=[prompt, *images])
                clean_json = res.text.replace("```json", "").replace("```", "").strip()
                new_data = json.loads(clean_json)
                
                st.session_state.database.update(new_data)
                save_db(st.session_state.database)
                st.sidebar.success("✅ Radar updated successfully!")
            except Exception as e:
                st.sidebar.error(f"Error processing images: {e}")

# ---------------------------------------------------------
# 5. Main Application Tabs
# ---------------------------------------------------------
st.title("🎯 FPL Radar - Ultimate Fantasy Analytics")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Club Radar & Vulnerabilities", 
    "⚔️ Head-To-Head (H2H)", 
    "🚀 Differential Scout", 
    "👑 Captaincy Planner",
    "📱 Social Media Generator"
])

# ---------------------------------------------------------
# TAB 1: Club Radar & Vulnerabilities
# ---------------------------------------------------------
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
        for idx, t in enumerate(team_data["topTeams"], 1):
            st.markdown(f"""
            <div class="stat-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="color:#00ff87; margin:0;">#{idx} {t['name']}</h3>
                    <span class="badge-cap">Captaincy Rating: {t.get('capRating', '9.0/10')}</span>
                </div>
                <p style="margin:8px 0;"><b>Tactical Reason:</b> {t['reason']}</p>
                <p style="margin:5px 0;"><b>Target Position:</b> <span class="badge-target">{t['targetPosition']}</span></p>
                <p style="margin:5px 0;"><b>Recommended Players:</b> {", ".join(t.get('recommendedPlayers', []))}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        col_left, col_right = st.columns([1.5, 1])
        
        with col_left:
            fig = draw_interactive_pitch(
                team_data['leftZone']['val'], 
                team_data['centerZone']['val'], 
                team_data['rightZone']['val'], 
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
                <p style="color:#ef4444; margin:0; font-weight:bold;">{team_data.get('setPieceVulnerability', 'N/A')}</p>
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
                        <h4 style="color:#00ff87; margin:0;">{p['name']}</h4>
                        <p style="margin:3px 0;">{p['team']} | {p['pos']}</p>
                        <p style="margin:3px 0;"><b>Price:</b> {p['price']} | <b>Owned By:</b> {p['selectedBy']}</p>
                        {'<span class="badge-diff">💎 Differential Gem</span>' if p.get('isDiff') else '<span class="badge-target">🔥 Premium Pick</span>'}
                    </div>
                    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 2: Head-To-Head (H2H) Comparison
# ---------------------------------------------------------
with tab2:
    st.subheader("⚔️ Direct Defensive H2H Comparison")
    avail_teams = [k for k in st.session_state.database.keys() if k != "TOP4_TARGETS"]
    
    if len(avail_teams) >= 2:
        c1, c2 = st.columns(2)
        with c1:
            t1 = st.selectbox("First Team:", avail_teams, index=0)
        with c2:
            t2 = st.selectbox("Second Team:", avail_teams, index=1)
            
        d1, d2 = st.session_state.database[t1], st.session_state.database[t2]
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(draw_interactive_pitch(d1['leftZone']['val'], d1['centerZone']['val'], d1['rightZone']['val'], t1), use_container_width=True)
            st.metric("xG Conceded", d1.get("xGConceded", "N/A"))
            st.metric("Big Chances Conceded", d1.get("bigChancesConceded", "N/A"))
        with col_b:
            st.plotly_chart(draw_interactive_pitch(d2['leftZone']['val'], d2['centerZone']['val'], d2['rightZone']['val'], t2), use_container_width=True)
            st.metric("xG Conceded", d2.get("xGConceded", "N/A"))
            st.metric("Big Chances Conceded", d2.get("bigChancesConceded", "N/A"))

# ---------------------------------------------------------
# TAB 3: Differential Scout
# ---------------------------------------------------------
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
                <h3 style="color:#00ff87; display:inline; margin-left:10px;">{d['name']} ({d['team']})</h3>
                <p style="margin:5px 0;"><b>Price:</b> {d['price']} | <b>Ownership:</b> {d['selectedBy']} | <b>Targeting:</b> {d['targetTeam']}</p>
            </div>
            """, unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 4: Captaincy Planner
# ---------------------------------------------------------
with tab4:
    st.subheader("👑 Expected Captaincy Planner")
    st.write("Compare 3 captaincy choices based on player form vs opponent defensive vulnerability:")
    
    avail_targets = [k for k in st.session_state.database.keys() if k != "TOP4_TARGETS"]
    
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        st.markdown("#### Option 1 🥇")
        p1_name = st.text_input("Player Name 1:", "Bukayo Saka", key="cap1_n")
        p1_form = st.slider("Attack Form (Expected xGI):", 0.0, 2.0, 0.8, key="cap1_f")
        p1_target = st.selectbox("Opponent Team:", avail_targets, index=0 if len(avail_targets)>0 else 0, key="cap1_t")
        
    with col_c2:
        st.markdown("#### Option 2 🥈")
        p2_name = st.text_input("Player Name 2:", "Cole Palmer", key="cap2_n")
        p2_form = st.slider("Attack Form (Expected xGI):", 0.0, 2.0, 0.9, key="cap2_f")
        p2_target = st.selectbox("Opponent Team:", avail_targets, index=1 if len(avail_targets)>1 else 0, key="cap2_t")

    with col_c3:
        st.markdown("#### Option 3 🥉")
        p3_name = st.text_input("Player Name 3:", "Erling Haaland", key="cap3_n")
        p3_form = st.slider("Attack Form (Expected xGI):", 0.0, 2.0, 1.2, key="cap3_f")
        p3_target = st.selectbox("Opponent Team:", avail_targets, index=0 if len(avail_targets)>0 else 0, key="cap3_t")

    if st.button("🧮 Calculate Best Captaincy Pick"):
        def calc_score(form, target_key):
            t_data = st.session_state.database.get(target_key, {})
            try:
                xgc = float(t_data.get("xGConceded", "1.5"))
            except:
                xgc = 1.5
            score = (form * 4.5) + (xgc * 3.0)
            return round(min(score, 10.0), 1)

        s1 = calc_score(p1_form, p1_target)
        s2 = calc_score(p2_form, p2_target)
        s3 = calc_score(p3_form, p3_target)

        res = [(p1_name, s1, p1_target), (p2_name, s2, p2_target), (p3_name, s3, p3_target)]
        res.sort(key=lambda x: x[1], reverse=True)

        st.success(f"🏆 **Recommended Captain:** **{res[0][0]}** with Expected Rating **({res[0][1]}/10)** vs {res[0][2]}")
        st.markdown("---")
        for idx, (name, sc, target) in enumerate(res, 1):
            st.markdown(f"**#{idx} {name}** — Captain Rating: `<span style='color:#00ff87; font-weight:bold;'>{sc}/10</span>` (vs: {target})", unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 5: Social Media Generator
# ---------------------------------------------------------
with tab5:
    st.subheader("📱 Social Media Thread & Summary Generator")
    selected_pub_team = st.selectbox("Select Team for Summary:", [k for k in st.session_state.database.keys() if k != "TOP4_TARGETS"])
    
    if selected_pub_team:
        pdata = st.session_state.database[selected_pub_team]
        
        tweet_text = f"""🎯 FPL Radar | Defensive Vulnerability Analysis: {pdata.get('title', selected_pub_team)} ⚽

📊 Defensive Stats:
• xG Conceded: {pdata.get('xGConceded', 'N/A')}
• Big Chances Conceded: {pdata.get('bigChancesConceded', 'N/A')}

⚠️ Key Defensive Weakness:
• Left Flank: {pdata['leftZone']['text']}
• Zone 14 / Center: {pdata['centerZone']['text']}

💡 Fantasy Recommendations & Target Players:
{pdata.get('targetAdvice', '')}

#FPL #FPLCommunity #FPL_Radar"""

        st.text_area("📋 Copy-Paste Ready Post/Thread:", tweet_text, height=220)
