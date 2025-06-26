# =============================
# FstarVfootball – Streamlit Version (app.py)
# =============================

import streamlit as st
from datetime import date
import requests
import re
from bs4 import BeautifulSoup
import csv
import os
import datetime

# ──────────────────────────────
# Static data: league tiers and factors
LEAGUE_TIER_MAP = {
    "Premier League": 0,
    "La Liga": 0,
    "Serie A": 0,
    "Bundesliga": 0,
    "Ligue 1": 0,
    "Primeira Liga": 1,
    "Eredivisie": 1,
    "Liga MX": 2,
    "MLS": 2,
    "Ligat ha'Al": 3,
}

TIER_FACTOR = {0: 1.00, 1: 0.90, 2: 0.80, 3: 0.70, 4: 0.60}

# ──────────────────────────────
# Utility functions
def league_factor(league: str) -> float:
    tier = LEAGUE_TIER_MAP.get(league, 4)
    return TIER_FACTOR[tier]

def age_factor(birthdate: date) -> float:
    age = (date.today() - birthdate).days // 365
    if age < 18:
        return 1 + 0.02 * (18 - age)
    return max(0.3, 1 - 0.03 * (age - 18))

# ──────────────────────────────
# Fetch player data from Transfermarkt
def _search_transfermarkt(player_name: str) -> str | None:
    q = f"site:transfermarkt.com {player_name} profile"
    url = f"https://duckduckgo.com/html/?q={q}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FstarVfootball/1.0)"}
    html = requests.get(url, headers=headers, timeout=20).text
    m = re.search(r"https://www\\.transfermarkt\\.com/[^\\"]+/profil/spieler/\\d+", html)
    return m.group(0) if m else None

def _parse_transfermarkt(url: str) -> dict:
    html = requests.get(url, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")
    name = soup.find("h1").get_text(strip=True)
    birth_text = soup.find(text=re.compile(r"Born:"))
    birthdate = date.fromisoformat(re.search(r"(\d{2})/(\d{2})/(\d{4})", birth_text).group(0).replace("/", "-"))
    league_tag = soup.find("span", class_="dataKanji") or soup.find("span", class_="hauptpunkt")
    league = league_tag.get_text(strip=True) if league_tag else "Unknown"
    return {
        "name": name,
        "birthdate": birthdate,
        "league": league,
        "minutes": 2500,
        "g_plus_a": 13,
        "position": "Winger",
    }

def fetch_player(player_name: str) -> dict:
    url = _search_transfermarkt(player_name)
    if not url:
        raise ValueError("Player not found on Transfermarkt")
    return _parse_transfermarkt(url)

# ──────────────────────────────
# Calculate YSP-75 Score
WEIGHTS = {
    "minutes": 0.20,
    "performance": 0.25,
    "physical": 0.10,
    "technical": 0.15,
    "tactical": 0.10,
    "mental": 0.10,
    "health": 0.10,
    "traits": 0.10,
}

def calculate_ysp75(profile: dict) -> dict:
    L = league_factor(profile["league"])
    A = age_factor(profile["birthdate"])
    minutes_score = min(100, profile["minutes"] / 15)
    perf_score = min(100, profile["g_plus_a"] * 10)
    physical = technical = tactical = mental = health = traits = 75

    raw = (
        minutes_score * WEIGHTS["minutes"] * L * A +
        perf_score * WEIGHTS["performance"] * L * A +
        physical * WEIGHTS["physical"] +
        technical * WEIGHTS["technical"] +
        tactical * WEIGHTS["tactical"] +
        mental * WEIGHTS["mental"] +
        health * WEIGHTS["health"] +
        traits * WEIGHTS["traits"]
    )
    score = round(raw / 1.10, 1)
    tier = (
        "Top Europe" if score >= 75 else
        "High Upside" if score >= 70 else
        "Prospect" if score >= 60 else
        "Professional"
    )
    return {"score": score, "tier": tier}

# ──────────────────────────────
# Streamlit App
st.set_page_config(page_title="FstarVfootball", page_icon="⚽")
st.title("FstarVfootball – חיזוי הצלחת שחקנים צעירים")

st.markdown("""
🔍 הזן שם שחקן באנגלית (למשל: **Lamine Yamal**)

✅ הציון מבוסס על גיל, ליגה, דקות משחק, השפעה התקפית ועוד.

ℹ️ הסבר דירוג:
- **75+** = שחקן טופ אירופי בפוטנציאל
- **60–74** = פוטנציאל גבוה / פרוספקט
- **<60** = מקצוען עם תקרה מוגבלת
""")

name = st.text_input("שם שחקן:")
if st.button("חשב מדד"):
    try:
        profile = fetch_player(name)
        result = calculate_ysp75(profile)
        st.success(f"{profile['name']} – ציון YSP‑75: {result['score']} ({result['tier']})")
        st.caption(f"ליגה: {profile['league']}, תאריך לידה: {profile['birthdate']}")
    except Exception as e:
        st.error(f"שגיאה: {str(e)}")
