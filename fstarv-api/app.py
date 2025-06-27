import streamlit as st
import pandas as pd
import os

# קריאת הנתונים מתוך הקובץ (באותה תיקייה של הקוד)
@st.cache_data
def load_players():
    DATA_PATH = os.path.join(os.path.dirname(__file__), "players_data-2024_2025.csv")
    cols = ["short_name", "age", "league_name", "club_name", "height_cm"]
    df = pd.read_csv(DATA_PATH, usecols=lambda c: c in cols, low_memory=False)
    return df

# דירוג לפי מדד אופ"א
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

TIER_FACTOR = {
    0: 1.0,
    1: 0.9,
    2: 0.8,
    3: 0.7,
    4: 0.6
}

WEIGHTS = {
    "age": 0.25,
    "league": 0.30,
    "minutes": 0.20,
    "impact": 0.25
}

def get_league_tier(league_name: str) -> int:
    for country, coeff in LEAGUE_COEFFICIENT.items():
        if country.lower() in league_name.lower():
            ratio = coeff / _BASE_COEFF
            if ratio >= 0.9:
                return 0
            elif ratio >= 0.75:
                return 1
            elif ratio >= 0.6:
                return 2
            elif ratio >= 0.4:
                return 3
            else:
                return 4
    return 4

def compute_ysp75_score(age: int, league: str, minutes_played: int = 2000, goals_plus_assists: int = 10) -> float:
    age_factor = 1 + 0.02 * (18 - age) if age <= 22 else 0.6
    league_tier = get_league_tier(league)
    league_factor = TIER_FACTOR.get(league_tier, 0.6)
    minutes_factor = min(1.0, minutes_played / 2700)
    impact_factor = min(1.0, goals_plus_assists / 20)

    score = (
        age_factor * WEIGHTS["age"] +
        league_factor * WEIGHTS["league"] +
        minutes_factor * WEIGHTS["minutes"] +
        impact_factor * WEIGHTS["impact"]
    ) * 100
    return round(score, 1)

def classify_score(score: float) -> str:
    if score >= 75:
        return "Top-Europe Ready"
    elif score >= 65:
        return "World-Class Potential"
    elif score >= 55:
        return "Needs Improvement"
    else:
        return "Below Threshold"

# UI
st.set_page_config(page_title="FstarV – YSP-75", page_icon="🎯")
st.title("🎯 YSP-75 – Combined Player Metric")

players_df = load_players()

player_name = st.text_input("Enter player name:")
player = players_df[players_df["short_name"].str.lower() == player_name.lower()]

if not player.empty:
    row = player.iloc[0]
    st.markdown(f"**Player:** {row['short_name']}")
    st.markdown(f"**Age:** {row['age']}")
    st.markdown(f"**Height (cm):** {row['height_cm']}")
    st.markdown(f"**Club:** {row['club_name']}")
    st.markdown(f"**League:** {row['league_name']}")

    # simulate some values
    minutes = st.slider("Minutes Played", 0, 3500, 2000, step=100)
    goals = st.slider("Goals", 0, 30, 6)
    assists = st.slider("Assists", 0, 30, 4)
    total_impact = goals + assists

    if st.button("Calculate YSP-75 Score"):
        score = compute_ysp75_score(row["age"], row["league_name"], minutes, total_impact)
        label = classify_score(score)
        st.success(f"YSP-75 Score: {score}/100")
        st.markdown(f"### 📊 Classification: **{label}**")
else:
    if player_name:
        st.warning("Player not found. Please check the spelling.")
