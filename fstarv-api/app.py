# =============================
# FstarVfootball – Single-file Version (app.py)
# Deployable with no external files
# =============================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
from datetime import date
import requests
import re
import csv
import os
import datetime
from bs4 import BeautifulSoup

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

def _parse_transfermarkt(url: str) -> Dict[str, Any]:
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

def fetch_player(player_name: str) -> Dict[str, Any]:
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

def calculate_ysp75(profile: Dict[str, Any]) -> Dict[str, Any]:
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
# Log predictions to CSV
SHEET_PATH = os.getenv("FSTARV_CSV", "portfolio.csv")

def log_prediction(entry: Dict):
    entry["timestamp"] = datetime.datetime.utcnow().isoformat()
    header = list(entry.keys())
    file_exists = os.path.isfile(SHEET_PATH)
    with open(SHEET_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)

# ──────────────────────────────
# FastAPI app
app = FastAPI(title="FstarVfootball API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

@app.get("/api/ysp75")
async def ysp75(name: str):
    try:
        profile = fetch_player(name)
        result = calculate_ysp75(profile)
        log_prediction({"name": name, **result})
        return {"player": profile["name"], **result}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
