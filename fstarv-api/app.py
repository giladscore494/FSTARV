import pandas as pd
import streamlit as st
from typing import Dict

DATA_PATH = "players_data-2024_2025.csv"

@st.cache_data
def load_players() -> pd.DataFrame:
    cols = ["Player", "Age", "Squad", "Comp", "Min", "Gls", "Ast", "SCA90", "Height"]
    df = pd.read_csv(DATA_PATH, usecols=lambda c: c in cols, low_memory=False)
    df.rename(columns={"Comp": "League", "Height": "Height_cm"}, inplace=True)
    return df

players_df = load_players()

LEAGUE_COEFFICIENT = {
    "England": 94.839, "Italy": 84.374, "Spain": 78.703, "Germany": 74.545, "France": 67.748,
    "Netherlands": 59.950, "Portugal": 53.866, "Belgium": 52.050, "Turkey": 42.000,
    "Czechia": 38.700, "Greece": 35.412, "Norway": 33.187, "Poland": 31.000, "Denmark": 29.856,
    "Austria": 29.750, "Switzerland": 28.500, "Scotland": 27.050, "Sweden": 24.625, "Israel": 24.625,
    "Cyprus": 23.537, "Croatia": 21.125, "Serbia": 20.000, "Hungary": 19.750, "Slovakia": 19.750,
    "Romania": 19.500, "Russia": 18.299, "Slovenia": 18.093, "Ukraine": 17.600, "Azerbaijan": 17.125,
    "Bulgaria": 15.875, "Moldova": 13.125, "Ireland": 13.093, "Iceland": 12.895, "Armenia": 10.875,
    "Latvia": 10.875, "Bosnia": 10.406, "Finland": 10.375, "Kosovo": 10.208, "Kazakhstan": 10.125,
    "Faroe": 8.000, "Liechtenstein": 7.500, "Malta": 7.000, "Lithuania": 6.625, "Estonia": 6.582,
    "Luxembourg": 5.875, "Albania": 5.875, "Montenegro": 5.583, "N. Ireland": 5.500, "Wales": 5.291,
    "Georgia": 4.875, "Andorra": 4.832, "Belarus": 4.500, "N. Macedonia": 4.416, "Gibraltar": 3.791,
    "San Marino": 1.998,
}
_BASE_COEFF = LEAGUE_COEFFICIENT["England"]
TIER_FACTOR = {0: 1.0, 1: 0.9, 2: 0.8, 3: 0.7, 4: 0.6}

WEIGHTS = {
    "age": 0.25,
    "league": 0.25,
    "minutes": 0.20,
    "impact": 0.20,
    "positive": 0.10
}

# 🧠 פונקציה חכמה לזיהוי מדינת ליגה
def country_from_league(league: str) -> str:
    league = league.lower()
    overrides = {
        "premier league": "England", "championship": "England", "bundesliga": "Germany",
        "la liga": "Spain", "serie a": "Italy", "ligue 1": "France", "eredivisie": "Netherlands",
        "primeira": "Portugal", "jupiler": "Belgium", "super lig": "Turkey",
        "austrian": "Austria", "swiss": "Switzerland", "allsvenskan": "Sweden",
        "ligat": "Israel", "eliteserien": "Norway", "ekstraklasa": "Poland", "superliga": "Denmark",
        "scottish": "Scotland", "cypriot": "Cyprus", "liga i": "Romania", "1. hnl": "Croatia",
        "greek": "Greece", "slovak": "Slovakia", "ukrainian": "Ukraine", "russian": "Russia",
        "israeli": "Israel"
    }
    for key, country in overrides.items():
        if key in league:
            return country
    return league.split()[-1].capitalize()

def get_league_tier(country: str) -> int:
    for name, coeff in LEAGUE_COEFFICIENT.items():
        if name.lower() in country.lower():
            ratio = coeff / _BASE_COEFF
            if ratio >= 0.9: return 0
            elif ratio >= 0.75: return 1
            elif ratio >= 0.6: return 2
            elif ratio >= 0.4: return 3
            else: return 4
    return 4

def compute_score(row: pd.Series) -> float:
    age_factor = 1 + 0.02 * (18 - row.Age) if row.Age <= 22 else 0.6
    country = country_from_league(row.League)
    league_factor = TIER_FACTOR.get(get_league_tier(country), 0.6)
    minutes_factor = min(1.0, row.Min / 2700)
    impact_factor = min(1.0, (row.Gls + row.Ast) / 20)
    positive_factor = min(1.0, row.SCA90 / 5) if not pd.isna(row.SCA90) else 0.5

    score = (
        age_factor * WEIGHTS["age"] +
        league_factor * WEIGHTS["league"] +
        minutes_factor * WEIGHTS["minutes"] +
        impact_factor * WEIGHTS["impact"] +
        positive_factor * WEIGHTS["positive"]
    ) * 100
    return round(score, 1), country

def classify(score: float) -> str:
    if score >= 75:
        return "Top-Europe Ready"
    elif score >= 65:
        return "World-Class Potential"
    elif score >= 55:
        return "Needs Improvement"
    else:
        return "Below Threshold"

# Streamlit UI
st.set_page_config(page_title="YSP-75 (2025)", page_icon="🎯")
st.title("🎯 YSP-75 – Season 2024/25")

name_query = st.text_input("Enter player name:")

if name_query:
    matches = players_df[players_df["Player"].str.contains(name_query, case=False, na=False)]
    if matches.empty:
        st.error("No player found.")
    else:
        selected = matches.iloc[0]
        score, country = compute_score(selected)
        label = classify(score)

        st.metric("YSP-75 Score", f"{score}/100")
        st.write(f"**{label}**")
        st.write(f"🌍 League Country Detected: `{country}`")
        st.write(f"Age: {selected.Age} | League: {selected.League} | Squad: {selected.Squad}")
        st.write(f"Minutes: {selected.Min} | Goals: {selected.Gls} | Assists: {selected.Ast} | SCA90: {selected.SCA90}")
        st.caption("Data source: FBref.com (CC BY)")
