import pandas as pd
import streamlit as st

# משקל לכל רכיב במדד
WEIGHTS = {
    "age": 0.25,
    "league": 0.30,
    "minutes": 0.20,
    "impact": 0.25
}

# דירוג אופ״א לפי מקדמים (לפי ליגת המדינה)
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

@st.cache_data
def load_players(file):
    cols = ["short_name", "age", "league_name", "minutes", "goals", "assists"]
    df = pd.read_csv(file, usecols=lambda c: c in cols, low_memory=False)
    df = df.dropna(subset=["short_name", "age", "league_name"])
    df["impact"] = df[["goals", "assists"]].sum(axis=1)
    return df

def compute_ysp75_score(age, league, minutes_played, goals_plus_assists):
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

def classify_score(score):
    if score >= 75:
        return "Top-Europe Ready"
    elif score >= 65:
        return "World-Class Potential"
    elif score >= 55:
        return "Needs Improvement"
    else:
        return "Below Threshold"

# ---------------------- UI ----------------------

st.set_page_config(page_title="YSP-75 (2025)", page_icon="🎯")
st.title("🎯 YSP-75 – Young Success Potential")

uploaded_file = st.file_uploader("העלה את קובץ השחקנים (CSV)", type="csv")

if uploaded_file:
    players_df = load_players(uploaded_file)
    player_names = sorted(players_df["short_name"].unique())
    selected_player = st.selectbox("בחר שחקן", player_names)

    player_data = players_df[players_df["short_name"] == selected_player].iloc[0]
    age = int(player_data["age"])
    league = player_data["league_name"]
    minutes = int(player_data["minutes"]) if not pd.isna(player_data["minutes"]) else 0
    impact = int(player_data["impact"]) if not pd.isna(player_data["impact"]) else 0

    score = compute_ysp75_score(age, league, minutes, impact)
    label = classify_score(score)

    st.markdown(f"## 🧠 נתוני שחקן")
    st.markdown(f"- גיל: **{age}**")
    st.markdown(f"- ליגה: **{league}**")
    st.markdown(f"- דקות משחק: **{minutes}**")
    st.markdown(f"- תרומה התקפית: **{impact}**")

    st.markdown("---")
    st.markdown(f"### 🏅 ציון YSP-75: **{score}/100**")
    st.markdown(f"### 📊 סיווג: **{label}**")
else:
    st.info("יש להעלות קובץ CSV עם הנתונים (עמודות: short_name, age, league_name, minutes, goals, assists)")
