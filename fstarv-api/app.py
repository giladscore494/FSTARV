import os
import streamlit as st
import pandas as pd

# קובץ נתונים חיצוני (חייב להיות באותה תיקייה כמו app.py)
DATA_PATH = "players_data_2025.csv"

@st.cache_data
def load_players():
    if not os.path.exists(DATA_PATH):
        st.error(f"שגיאה: הקובץ '{DATA_PATH}' לא נמצא בתיקייה של האפליקציה.")
        st.stop()
    cols = ["Player", "Age", "Comp", "Min", "Gls", "Ast", "xG", "xAG", "GCA", "SCA", "Tkl", "Int"]
    df = pd.read_csv(DATA_PATH, usecols=cols)
    return df

players_df = load_players()

# דירוג ליגות לפי מדד אופ"א
LEAGUE_COEFFICIENT = {
    "England": 94.839, "Italy": 84.374, "Spain": 78.703, "Germany": 74.545, "France": 67.748,
    "Netherlands": 59.950, "Portugal": 53.866, "Belgium": 52.050, "Turkey": 42.000,
    "Czechia": 38.700, "Greece": 35.412, "Norway": 33.187, "Poland": 31.000, "Denmark": 29.856,
    "Austria": 29.750, "Switzerland": 28.500, "Scotland": 27.050, "Sweden": 24.625,
    "Israel": 24.625, "Cyprus": 23.537, "Croatia": 21.125, "Serbia": 20.000,
    "Hungary": 19.750, "Slovakia": 19.750, "Romania": 19.500, "Russia": 18.299,
    "Slovenia": 18.093, "Ukraine": 17.600, "Azerbaijan": 17.125, "Bulgaria": 15.875,
    "Moldova": 13.125, "Iceland": 12.895, "Armenia": 10.875, "Latvia": 10.875,
    "Bosnia and Herzegovina": 10.406, "Finland": 10.375, "Kosovo": 10.208,
    "Kazakhstan": 10.125, "Faroe Islands": 8.000, "Liechtenstein": 7.500, "Malta": 7.000,
    "Lithuania": 6.625, "Estonia": 6.582, "Luxembourg": 5.875, "Albania": 5.875,
    "Montenegro": 5.583, "Northern Ireland": 5.500, "Wales": 5.291, "Georgia": 4.875,
    "Andorra": 4.832, "Belarus": 4.500, "North Macedonia": 4.416, "Gibraltar": 3.791,
    "San Marino": 1.998
}

TIER_FACTOR = {
    0: 1.0,
    1: 0.9,
    2: 0.8,
    3: 0.7,
    4: 0.6
}

_BASE_COEFF = LEAGUE_COEFFICIENT["England"]

def get_league_tier(league_country: str) -> int:
    for name, coeff in LEAGUE_COEFFICIENT.items():
        if name.lower() in league_country.lower():
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

def compute_ysp75_score(player_row: pd.Series) -> float:
    age = player_row["Age"]
    league_country = player_row["Comp"]
    minutes = player_row["Min"]
    impact = player_row["Gls"] + player_row["Ast"]

    age_factor = 1 + 0.02 * (18 - age) if age <= 22 else 0.6
    league_tier = get_league_tier(league_country)
    league_factor = TIER_FACTOR.get(league_tier, 0.6)
    minutes_factor = min(1.0, minutes / 2700)
    impact_factor = min(1.0, impact / 20)

    score = (
        age_factor * 0.25 +
        league_factor * 0.30 +
        minutes_factor * 0.20 +
        impact_factor * 0.25
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

# ממשק Streamlit
st.set_page_config(page_title="YSP-75 Metric", page_icon="🎯")
st.title("🎯 YSP-75 – Young Success Potential")

name_input = st.text_input("Enter player name:")

if name_input:
    matched = players_df[players_df["Player"].str.lower() == name_input.lower()]
    if matched.empty:
        st.error("שחקן לא נמצא בקובץ הנתונים.")
    else:
        player_row = matched.iloc[0]
        score = compute_ysp75_score(player_row)
        label = classify_score(score)

        st.subheader(f"{player_row['Player']} ({player_row['Age']} yrs) – {player_row['Comp']}")
        st.markdown(f"**Minutes Played:** {player_row['Min']}, **Goals + Assists:** {player_row['Gls'] + player_row['Ast']}")
        st.markdown(f"**YSP-75 Score:** `{score}`")
        st.markdown(f"### 📊 Classification: **{label}**")
