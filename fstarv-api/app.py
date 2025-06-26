import streamlit as st
from datetime import date
import requests, time, re, io
from bs4 import BeautifulSoup
import pandas as pd

# ================= League Tier Map =================
SPI_CSV_URL = "https://projects.fivethirtyeight.com/soccer-api/club/spi_global_rankings.csv"
@st.cache_data(ttl=86400)
def _build_league_map():
    try:
        df = pd.read_csv(io.BytesIO(requests.get(SPI_CSV_URL, timeout=20).content))
        league_avg = df.groupby("league")["spi"].mean().sort_values(ascending=False)
        tiers = {}
        for rank, lg in enumerate(league_avg.index, start=1):
            tiers[lg] = 0 if rank<=5 else 1 if rank<=10 else 2 if rank<=20 else 3 if rank<=30 else 4
        tiers.setdefault("Premier League",0)
        tiers.setdefault("La Liga",0)
        return tiers
    except:
        return {"Premier League":0,"La Liga":0,"Serie A":0,"Bundesliga":0,"Ligue 1":0}

LEAGUE_TIER_MAP = _build_league_map()
TIER_FACTOR = {0:1.0, 1:0.9, 2:0.8, 3:0.7, 4:0.6}
TEAM_TO_LEAGUE = {
    "Inter Miami": "Major League Soccer",
    "Barcelona": "La Liga", "Real Madrid": "La Liga",
    "Manchester City": "Premier League", "Arsenal": "Premier League", "Liverpool": "Premier League",
    "Paris Saint-Germain": "Ligue 1", "Juventus": "Serie A", "Bayern Munich": "Bundesliga",
    "Manchester United": "Premier League", "Benfica": "Primeira Liga", "Sporting CP": "Primeira Liga"
}
HEADERS = {"User-Agent":"Mozilla/5.0 (compatible; FstarV/1.0)"}

# ================= Helpers =================
def league_factor(lg:str)->float: return TIER_FACTOR.get(LEAGUE_TIER_MAP.get(lg,4),0.6)
def age_factor(bd:date)->float:
    age=(date.today()-bd).days//365
    return 1+0.02*(18-age) if age<18 else max(0.3,1-0.03*(age-18))

def google_scrape(query: str) -> str:
    try:
        html = requests.get(f"https://www.google.com/search?q={query}", headers=HEADERS, timeout=10).text
        m1 = re.search(r'(\d\.\d{2})\s?m', html)  # e.g. 1.79 m
        m2 = re.search(r'(\d{1,2})′(\d{1,2})″', html)  # e.g. 5′10″
        if m1:
            return m1.group(1)
        elif m2:
            feet = int(m2.group(1))
            inches = int(m2.group(2))
            meters = round((feet * 0.3048) + (inches * 0.0254), 2)
            return str(meters)
        return "N/A"
    except:
        return "N/A"

# ================= Wikipedia fallback =================
def find_league_via_wikipedia(player: str) -> str:
    try:
        r = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{player.replace(' ', '_')}", timeout=10).json()
        txt = r.get("extract", "")
        club_match = re.search(r'plays (as|in).*?for ([A-Z][a-zA-Z ]+)', txt)
        if club_match:
            club = club_match.group(2).strip()
            return TEAM_TO_LEAGUE.get(club, "Unknown")
        return "Unknown"
    except:
        return "Unknown"

# ================= FBref scraping =================
@st.cache_data(ttl=86400)
def _find_fbref_url(name:str)->str|None:
    q=name.strip().replace(" ","-")
    url=f"https://fbref.com/en/search/search.fcgi?search={q}"
    html=requests.get(url,headers=HEADERS,timeout=20).text
    m=re.search(r"/en/players/[a-f0-9]{8}/[A-Za-z0-9\\-]+",html)
    return f"https://fbref.com{m.group(0)}" if m else None

@st.cache_data(ttl=86400)
def _parse_fbref(url:str)->dict:
    html=requests.get(url,headers=HEADERS,timeout=20).text
    soup=BeautifulSoup(html,"html.parser")
    name_tag = soup.find("h1")
    birth_tag = soup.find("span",id="necro-birth")
    if not birth_tag:
        match = re.search(r'data-birth="(\\d{4}-\\d{2}-\\d{2})"', html)
        birth_str = match.group(1) if match else None
    else:
        birth_str = birth_tag["data-birth"]
    if not birth_str: return None
    birthdate = date.fromisoformat(birth_str)
    name = name_tag.text.strip() if name_tag else "Unknown"
    club_tag = soup.find("span",class_="fancy")
    team_name = club_tag.text.strip() if club_tag else ""
    league = club_tag.get("title","").split(" ")[-1] if club_tag and "title" in club_tag.attrs else TEAM_TO_LEAGUE.get(team_name,"Unknown")
    if league == "Unknown":
        league = find_league_via_wikipedia(name)
    stat_table = soup.find("table", id="stats_standard_dom_lg")
    mins=g_plus_a=0
    if stat_table:
        rows = stat_table.find("tbody").find_all("tr", class_=lambda x:x!="thead")
        for row in reversed(rows):
            comp = row.find("td", {"data-stat": "comp"})
            if comp and "league" in comp.text.lower():
                mins = int(row.find("td",{"data-stat":"minutes"}).text.strip().replace(",","") or 0)
                goals = int(row.find("td",{"data-stat":"goals"}).text.strip().replace(",","") or 0)
