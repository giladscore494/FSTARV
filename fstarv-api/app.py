"""
FstarVfootball / GiladScore – single‑file Streamlit demo
======================================================
• Fetches basic bio from Wikipedia REST API.
• Pulls live stats from FOTMOB (unofficial endpoint).
• Applies UEFA league‑strength multiplier (55 associations, 2 Jun 2025 coefficients).

How to run locally:
```bash
pip install -r requirements.txt
streamlit run app.py
```
"""

from __future__ import annotations
import requests
import streamlit as st
from typing import Any, Dict

# -----------------------------------------------------
# UEFA MEN’S ASSOCIATION COEFFICIENTS (updated 2 Jun 2025)
# -----------------------------------------------------
LEAGUE_COEFFICIENT: Dict[str, float] = {
    "England": 94.839,
    "Italy": 84.374,
    "Spain": 78.703,
    "Germany": 74.545,
    "France": 67.748,
    "Netherlands": 59.950,
    "Portugal": 53.866,
    "Belgium": 52.050,
    "Turkey": 42.000,
    "Czechia": 38.700,
    "Greece": 35.412,
    "Norway": 33.187,
    "Poland": 31.000,
    "Denmark": 29.856,
    "Austria": 29.750,
    "Switzerland": 28.500,
    "Scotland": 27.050,
    "Sweden": 24.625,
    "Israel": 24.625,
    "Cyprus": 23.537,
    "Croatia": 21.125,
    "Serbia": 20.000,
    "Hungary": 19.750,
    "Slovakia": 19.750,
    "Romania": 19.500,
    "Russia": 18.299,
    "Slovenia": 18.093,
    "Ukraine": 17.600,
    "Azerbaijan": 17.125,
    "Bulgaria": 15.875,
    "Moldova": 13.125,
    "Republic of Ireland": 13.093,
    "Iceland": 12.895,
    "Armenia": 10.875,
    "Latvia": 10.875,
    "Bosnia and Herzegovina": 10.406,
    "Finland": 10.375,
    "Kosovo": 10.208,
    "Kazakhstan": 10.125,
    "Faroe Islands": 8.000,
    "Liechtenstein": 7.500,
    "Malta": 7.000,
    "Lithuania": 6.625,
    "Estonia": 6.582,
    "Luxembourg": 5.875,
    "Albania": 5.875,
    "Montenegro": 5.583,
    "Northern Ireland": 5.500,
    "Wales": 5.291,
    "Georgia": 4.875,
    "Andorra": 4.832,
    "Belarus": 4.500,
    "North Macedonia": 4.416,
    "Gibraltar": 3.791,
    "San Marino": 1.998,
}
_BASE_COEFF: float = LEAGUE_COEFFICIENT["England"]

# -----------------------------------------------------
# Helper functions
# -----------------------------------------------------

def get_league_multiplier(league_or_country: str) -> float:
    """Return multiplier (0–1) based on UEFA coefficient."""
    for country, coeff in LEAGUE_COEFFICIENT.items():
        if country.lower() in league_or_country.lower():
            return round(coeff / _BASE_COEFF, 3)
    return 0.05  # default

# ---- Wikipedia REST API ----

def get_basic_player_data(name: str) -> Dict[str, Any]:
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{name.replace(' ', '_')}"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException:
        return {}
    return {
        "name": data.get("title"),
        "description": data.get("description"),
        "extract": data.get("extract"),
        "image": data.get("thumbnail", {}).get("source"),
    }

# ---- FOTMOB unofficial endpoints ----

def get_fotmob_id(name: str) -> int | None:
    try:
        res = requests.get(f"https://www.fotmob.com/api/search?q={name}", timeout=5)
        res.raise_for_status()
        data = res.json()
    except requests.RequestException:
        return None
    players = data.get("players") or []
    return players[0]["id"] if players else None

def get_fotmob_player_data(pid: int) -> Dict[str, Any]:
    try:
        res = requests.get(f"https://www.fotmob.com/api/playerData?id={pid}", timeout=5)
        res.raise_for_status()
        return res.json()
    except requests.RequestException:
        return {}

# ---- Metric calculation ----

def compute_raw_score(goals: int, rating: float, age: int) -> float:
    age = max(age, 1)
    return (goals * 2 + rating * 10) / age

def calculate_final_score(goals: int, rating: float, age: int, league: str) -> float:
    raw = compute_raw_score(goals, rating, age)
    mult = get_league_multiplier(league)
    return round(raw * mult, 2)

# -----------------------------------------------------
# Streamlit UI
# -----------------------------------------------------
st.set_page_config(page_title="FstarVfootball Demo", page_icon="⚽")
st.title("⚽ FstarVfootball – Player Metric Demo")

player_name = st.text_input("Enter player name:", "Lionel Messi")
if st.button("Calculate Metric") and player_name.strip():
    with st.spinner("Fetching information…"):
        bio = get_basic_player_data(player_name)
        pid = get_fotmob_id(player_name)
        stats = get_fotmob_player_data(pid) if pid else {}

    if not bio:
        st.error("Player not found on Wikipedia.")
        st.stop()

    # ---- parse minimal stats ----
    goals = 0
    rating = 6.5
    age = 25
    league = "Unknown"

    try:
        #  current season summary usually under stats -> summary -> keyStats
        cs = stats.get("stats", {}).get("summary", {})
        goals = cs.get("goals", goals)
        rating = cs.get("rating", rating)
        age = stats.get("player", {}).get("age", age)
        league = stats.get("club", {}).get("leagueName", league)
    except Exception:
        pass

    final_score = calculate_final_score(goals, rating, age, league)

    # ---- Display ----
    col1, col2 = st.columns([1, 2])
    with col1:
        if bio.get("image"):
            st.image(bio["image"], width=150)
        st.metric("Final Score", final_score)
        st.write(f"**League Multiplier:** {get_league_multiplier(league)}")
    with col2:
        st.subheader(bio.get("name", player_name))
        st.caption(bio.get("description", ""))
        st.write(bio.get("extract", ""))
        st.markdown(
            f"**Goals (season)**: {goals}  \
            **Average Rating**: {rating}  \
            **Age**: {age}  \
            **League**: {league}"
        )

    st.info("Formula demo: (goals*2 + rating*10)/age × league‑multiplier")
