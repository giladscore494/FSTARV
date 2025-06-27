import streamlit as st
import pandas as pd

# הגדרות משקלות לרכיבי המדד
WEIGHTS = {
    "age": 0.20,
    "league": 0.20,
    "minutes": 0.15,
    "actual_impact": 0.15,
    "expected_impact": 0.15,
    "attack_build": 0.075,
    "defense": 0.075
}

# דירוג טיר לליגות אופ"א לפי מקדם
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

TIER_FACTOR = {
    0: 1.0,
    1: 0.9,
    2: 0.8,
    3: 0.7,
    4: 0.6
}

@st.cache_data
def load_players():
    cols = [
        "Player", "Age", "Comp", "Min", "Gls", "Ast",
        "xG", "xAG", "GCA", "SCA", "Tkl", "Int"
    ]
    df = pd.read_csv("players_data-2024_2025.csv", usecols=cols, low_memory=False)
    df["Player"] = df["Player"].astype(str).str.strip()
    df["Comp"] = df["Comp"].astype(str).str.strip()
    df = df.dropna(subset=["Player", "Age", "Comp", "Min"])

    df["total_impact"] = df["Gls"] + df["Ast"]
    df["expected_impact"] = df["xG"] + df["xAG"]
    df["attack_build"] = df["GCA"] + df["SCA"]
    df["defense_total"] = df["Tkl"] + df["Int"]
    return df

def compute_ysp75_score(row) -> float:
    age = row["Age"]
    minutes = row["Min"]
    impact = row["total_impact"]
    expected = row["expected_impact"]
    attack = row["attack_build"]
    defense = row["defense_total"]
    league_tier = get_league_tier(row["Comp"])
    league_factor = TIER_FACTOR.get(league_tier, 0.6)

    age_factor = 1 + 0.02 * (18 - age) if age <= 22 else 0.6
    minutes_factor = min(1.0, minutes / 2700)
    actual_impact = min(1.0, impact / 20)
    expected_impact = min(1.0, expected / 20)
    attack_factor = min(1.0, attack / 40)
    defense_factor = min(1.0, defense / 40)

    score = (
        age_factor * WEIGHTS["age"] +
        league_factor * WEIGHTS["league"] +
        minutes_factor * WEIGHTS["minutes"] +
        actual_impact * WEIGHTS["actual_impact"] +
        expected_impact * WEIGHTS["expected_impact"] +
        attack_factor * WEIGHTS["attack_build"] +
        defense_factor * WEIGHTS["defense"]
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
st.set_page_config(page_title="YSP-75 Metric", page_icon="🎯")
st.title("🎯 YSP-75 – Combined Player Metric")
player_name = st.text_input("Enter player name:")

players_df = load_players()

if player_name:
    player = players_df[players_df["Player"].str.lower() == player_name.lower()]
    if not player.empty:
        row = player.iloc[0]
        score = compute_ysp75_score(row)
        label = classify_score(score)

        st.success(f"YSP-75 Score: {score}/100")
        st.markdown(f"### Classification: **{label}**")
        st.markdown("---")
        st.subheader("📊 Player Data")
        st.write(row[["Age", "Comp", "Min", "Gls", "Ast", "xG", "xAG", "GCA", "SCA", "Tkl", "Int"]])
    else:
        st.warning("Player not found.")
