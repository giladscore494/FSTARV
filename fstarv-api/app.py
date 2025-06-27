import streamlit as st
import pandas as pd
from datetime import datetime, date

# --------------------
# הגדרות כלליות
# --------------------
DATA_PATH = "players_data_2025.csv"  # שם הקובץ החדש
TIERS_55 = {
    "Premier League": 0,
    "La Liga": 0,
    "Bundesliga": 0,
    "Serie A": 0,
    "Ligue 1": 0,
    "Eredivisie": 1,
    "Primeira Liga": 1,
    "Championship": 2,
    "Belgian Pro League": 2,
    "Brazil Serie A": 1,
    "Argentine Primera": 1,
    # המשך הוספת ליגות עד 55...
}

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


# --------------------
# טוען את הקובץ פעם אחת
# --------------------
@st.cache_data
def load_players():
    cols = ["short_name", "age", "league_name", "minutes_played", "goals", "assists"]
    df = pd.read_csv(DATA_PATH, usecols=cols)
    df["impact"] = df["goals"].fillna(0) + df["assists"].fillna(0)
    return df


# --------------------
# חישוב מדד YSP-75
# --------------------
def compute_ysp75_score(age, league, minutes_played, impact):
    age_factor = 1 + 0.02 * (18 - age) if age <= 22 else 0.6
    tier = TIERS_55.get(league, 4)
    league_factor = TIER_FACTOR.get(tier, 0.6)
    minutes_factor = min(1.0, minutes_played / 2700)
    impact_factor = min(1.0, impact / 20)

    score = (
        age_factor * WEIGHTS["age"] +
        league_factor * WEIGHTS["league"] +
        minutes_factor * WEIGHTS["minutes"] +
        impact_factor * WEIGHTS["impact"]
    ) * 100

    return round(score, 1)


# --------------------
# Streamlit UI
# --------------------
st.set_page_config(page_title="FSTARV - YSP-75", layout="centered")
st.title("🎯 YSP-75 – Combined Player Metric")
player_name = st.text_input("Enter player name:")

if player_name:
    players_df = load_players()
    player_row = players_df[players_df["short_name"].str.lower() == player_name.lower()]

    if player_row.empty:
        st.error("Player not found in dataset.")
    else:
        player = player_row.iloc[0]
        score = compute_ysp75_score(
            age=player["age"],
            league=player["league_name"],
            minutes_played=player["minutes_played"],
            impact=player["impact"]
        )

        st.success(f"✅ YSP-75 Score for {player['short_name']}: **{score}**")

        if score >= 75:
            st.markdown("🏆 **Top European Prospect**")
        elif score >= 65:
            st.markdown("🌍 **Global-level Potential Talent**")
        elif score >= 55:
            st.markdown("🧪 **Developing Player – Needs Improvement**")
        else:
            st.markdown("📉 **Not a High Prospect at This Stage**")

        with st.expander("📊 Raw Player Data"):
            st.write(player)
