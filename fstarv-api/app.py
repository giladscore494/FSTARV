import requests
import streamlit as st
from typing import Dict

# משקלים
WEIGHTS = {
    "age": 0.25,
    "league": 0.30,
    "minutes": 0.20,
    "impact": 0.25
}

# דירוג ליגות לפי אופ"א
LEAGUE_COEFFICIENT = {
    "England": 94.839, "Italy": 84.374, "Spain": 78.703, "Germany": 74.545, "France": 67.748,
    "Netherlands": 59.950, "Portugal": 53.866, "Belgium": 52.050, "Turkey": 42.000,
    "Czechia": 38.700, "Greece": 35.412, "Norway": 33.187, "Poland": 31.000, "Denmark": 29.856,
    "Austria": 29.750, "Switzerland": 28.500, "Scotland": 27.050, "Sweden": 24.625,
    "Israel": 24.625, "Cyprus": 23.537, "Croatia": 21.125, "Serbia": 20.000,
    "Hungary": 19.750, "Slovakia": 19.750, "Romania": 19.500, "Russia": 18.299,
    "Slovenia": 18.093, "Ukraine": 17.600, "Azerbaijan": 17.125, "Bulgaria": 15.875,
    "Moldova": 13.125, "Ireland": 13.093, "Iceland": 12.895, "Armenia": 10.875,
    "Latvia": 10.875, "Bosnia": 10.406, "Finland": 10.375, "Kosovo": 10.208,
    "Kazakhstan": 10.125, "Faroe": 8.000, "Liechtenstein": 7.500, "Malta": 7.000,
    "Lithuania": 6.625, "Estonia": 6.582, "Luxembourg": 5.875, "Albania": 5.875,
    "Montenegro": 5.583, "N. Ireland": 5.500, "Wales": 5.291, "Georgia": 4.875,
    "Andorra": 4.832, "Belarus": 4.500, "N. Macedonia": 4.416, "Gibraltar": 3.791,
    "San Marino": 1.998,
}
TIER_FACTOR = {0: 1.0, 1: 0.9, 2: 0.8, 3: 0.7, 4: 0.6}
_BASE_COEFF = LEAGUE_COEFFICIENT["England"]

def get_league_tier(league_country: str) -> int:
    for name, coeff in LEAGUE_COEFFICIENT.items():
        if name.lower() in league_country.lower():
            ratio = coeff / _BASE_COEFF
            if ratio >= 0.9: return 0
            elif ratio >= 0.75: return 1
            elif ratio >= 0.6: return 2
            elif ratio >= 0.4: return 3
            else: return 4
    return 4

# שליפה מ־SOFIFA
def get_sofifa_player_info(name: str) -> Dict[str, str]:
    try:
        r = requests.get(f"https://sofifa.com/players?keyword={name}", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        r.raise_for_status()
        html = r.text
        row = html.split('data-playerid="')[1].split('</tr>')[0]
        age = int(row.split('Age</td><td>')[1].split('<')[0])
        club = row.split('club?')[1].split('">')[1].split('<')[0]
        league = row.split('league?')[1].split('">')[1].split('<')[0]
        return {"age": age, "club": club, "league": league}
    except:
        return {}

# שליפה מ־FOTMOB
def get_fotmob_id(name: str):
    try:
        res = requests.get(f"https://www.fotmob.com/api/search?q={name}", timeout=5)
        return res.json().get("players", [{}])[0].get("id")
    except: return None

def get_fotmob_player_data(pid: int) -> Dict:
    try:
        r = requests.get(f"https://www.fotmob.com/api/playerData?id={pid}", timeout=5)
        return r.json()
    except: return {}

# חישוב מדד
def compute_ysp75_score(age: int, league_country: str, minutes: int, impact: int) -> float:
    age_factor = 1 + 0.02 * (18 - age) if age <= 22 else 0.6
    league_tier = get_league_tier(league_country)
    league_factor = TIER_FACTOR.get(league_tier, 0.6)
    minutes_factor = min(1.0, minutes / 2700)
    impact_factor = min(1.0, impact / 20)
    score = (
        age_factor * WEIGHTS["age"] +
        league_factor * WEIGHTS["league"] +
        minutes_factor * WEIGHTS["minutes"] +
        impact_factor * WEIGHTS["impact"]
    ) * 100
    return round(score, 1)

def classify_score(score: float) -> str:
    if score >= 75: return "Top-Europe Ready"
    elif score >= 65: return "World-Class Potential"
    elif score >= 55: return "Needs Improvement"
    else: return "Below Threshold"

# ממשק Streamlit
st.set_page_config(page_title="YSP-75", page_icon="🎯")
st.title("🎯 YSP-75 – Combined Player Metric")

name = st.text_input("Enter player name:", "Lamine Yamal")

if st.button("Calculate YSP-75") and name.strip():
    with st.spinner("Fetching data..."):
        sofifa = get_sofifa_player_info(name)
        pid = get_fotmob_id(name)
        stats = get_fotmob_player_data(pid) if pid else {}

    if not sofifa:
        st.error("Could not retrieve data from SOFIFA.")
        st.stop()

    age = sofifa.get("age", 20)
    league = sofifa.get("league", "Unknown")
    goals = stats.get("stats", {}).get("summary", {}).get("goals", 0)
    assists = stats.get("stats", {}).get("summary", {}).get("assists", 0)
    minutes = stats.get("stats", {}).get("summary", {}).get("minutesPlayed", 800)

    score = compute_ysp75_score(age, league, minutes, goals + assists)
    label = classify_score(score)

    st.metric("YSP-75 Score", f"{score}/100")
    st.markdown(f"**Classification:** {label}")
    st.markdown(f"**Age:** {age}  \\\n**League:** {league}  \\\n**Minutes:** {minutes}  \\\n**Goals + Assists:** {goals + assists}")
    st.caption("Data: SOFIFA (age, league), FOTMOB (stats)")

