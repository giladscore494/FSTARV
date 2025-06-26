""" 
FstarVfootball – Final Metric App (PRO version)
===============================================
• Uses Wikipedia + FOTMOB for player data.
• Applies advanced metric: goals, rating, minutes, age, position, league multiplier.
• Formula: (goals×2.5 + rating×10 + minutes/80) × position × age × league
"""

import requests
import streamlit as st
from typing import Any, Dict

# UEFA Coefficients (55)
LEAGUE_COEFFICIENT = {
    "England": 94.839, "Italy": 84.374, "Spain": 78.703, "Germany": 74.545, "France": 67.748,
    "Netherlands": 59.950, "Portugal": 53.866, "Belgium": 52.050, "Turkey": 42.000,
    "Czechia": 38.700, "Greece": 35.412, "Norway": 33.187, "Poland": 31.000, "Denmark": 29.856,
    "Austria": 29.750, "Switzerland": 28.500, "Scotland": 27.050, "Sweden": 24.625,
    "Israel": 24.625, "Cyprus": 23.537, "Croatia": 21.125, "Serbia": 20.000,
    "Hungary": 19.750, "Slovakia": 19.750, "Romania": 19.500, "Russia": 18.299,
    "Slovenia": 18.093, "Ukraine": 17.600, "Azerbaijan": 17.125, "Bulgaria": 15.875,
    "Moldova": 13.125, "Republic of Ireland": 13.093, "Iceland": 12.895, "Armenia": 10.875,
    "Latvia": 10.875, "Bosnia and Herzegovina": 10.406, "Finland": 10.375, "Kosovo": 10.208,
    "Kazakhstan": 10.125, "Faroe Islands": 8.000, "Liechtenstein": 7.500, "Malta": 7.000,
    "Lithuania": 6.625, "Estonia": 6.582, "Luxembourg": 5.875, "Albania": 5.875,
    "Montenegro": 5.583, "Northern Ireland": 5.500, "Wales": 5.291, "Georgia": 4.875,
    "Andorra": 4.832, "Belarus": 4.500, "North Macedonia": 4.416, "Gibraltar": 3.791,
    "San Marino": 1.998,
}
_BASE_COEFF = LEAGUE_COEFFICIENT["England"]

def get_league_multiplier(league_or_country: str) -> float:
    for country, coeff in LEAGUE_COEFFICIENT.items():
        if country.lower() in league_or_country.lower():
            return round(coeff / _BASE_COEFF, 3)
    return 0.05

def get_basic_player_data(name: str) -> Dict[str, Any]:
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{name.replace(' ', '_')}"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
    except:
        return {}
    return {
        "name": data.get("title"),
        "description": data.get("description"),
        "extract": data.get("extract"),
        "image": data.get("thumbnail", {}).get("source"),
    }

def get_fotmob_id(name: str) -> int | None:
    try:
        res = requests.get(f"https://www.fotmob.com/api/search?q={name}", timeout=5)
        res.raise_for_status()
        return res.json().get("players", [{}])[0].get("id")
    except:
        return None

def get_fotmob_player_data(pid: int) -> Dict[str, Any]:
    try:
        r = requests.get(f"https://www.fotmob.com/api/playerData?id={pid}", timeout=5)
        r.raise_for_status()
        return r.json()
    except:
        return {}

def compute_fstar_score(goals: int, rating: float, minutes: int, age: int, position: str, league: str) -> float:
    age_factor = max(0.5, (27 - age) / 10)
    position_weight = 1.0 if "attacker" in position.lower() else 0.85 if "mid" in position.lower() else 0.7
    multiplier = get_league_multiplier(league)
    base = (goals * 2.5 + rating * 10 + minutes / 80) * position_weight * age_factor
    return round(base * multiplier, 2)

# ==== Streamlit App ====
st.set_page_config(page_title="FstarVfootball", page_icon="⚽")
st.title("FstarVfootball – Final Metric (PRO)")

player_name = st.text_input("Enter player name:", "Jude Bellingham")

if st.button("Analyze") and player_name.strip():
    with st.spinner("Fetching data…"):
        bio = get_basic_player_data(player_name)
        pid = get_fotmob_id(player_name)
        stats = get_fotmob_player_data(pid) if pid else {}

    if not bio:
        st.error("Player not found on Wikipedia.")
        st.stop()

    goals = stats.get("stats", {}).get("summary", {}).get("goals", 0)
    rating = stats.get("stats", {}).get("summary", {}).get("rating", 6.5)
    minutes = stats.get("stats", {}).get("summary", {}).get("minutesPlayed", 900)
    age = stats.get("player", {}).get("age", 24)
    position = stats.get("player", {}).get("position", "Midfielder")
    league = stats.get("club", {}).get("leagueName", "Spain")

    final = compute_fstar_score(goals, rating, minutes, age, position, league)

    col1, col2 = st.columns([1, 2])
    with col1:
        if bio.get("image"):
            st.image(bio["image"], width=160)
        st.metric("Fstar Score", final)
        st.caption(f"League Multiplier: {get_league_multiplier(league)}")
    with col2:
        st.subheader(bio.get("name"))
        st.write(bio.get("description", ""))
        st.write(bio.get("extract", ""))
        st.markdown(f"**Goals:** {goals}  \\\n"
                    f"**Rating:** {rating}  \\\n"
                    f"**Minutes:** {minutes}  \\\n"
                    f"**Age:** {age}  \\\n"
                    f"**Position:** {position}  \\\n"
                    f"**League:** {league}")
    st.info("Formula: (goals×2.5 + rating×10 + minutes/80) × position × age × league")
