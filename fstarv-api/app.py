import streamlit as st
from datetime import date
import requests, time, re, io
from bs4 import BeautifulSoup
import pandas as pd

# ========== League Tier Map ==========
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

# ========== Helpers ==========
def league_factor(lg:str)->float: return TIER_FACTOR.get(LEAGUE_TIER_MAP.get(lg,4),0.6)
def age_factor(bd:date)->float:
    age=(date.today()-bd).days//365
    return 1+0.02*(18-age) if age<18 else max(0.3,1-0.03*(age-18))

def google_scrape(query: str) -> str:
    try:
        html = requests.get(f"https://www.google.com/search?q={query}", headers=HEADERS, timeout=10).text
        match = re.search(r'(\d{1,3}(\.\d{1,2})?) ?m', html, re.IGNORECASE)
        return match.group(1) if match else "N/A"
    except:
        return "N/A"

# ========== Wikipedia fallback ==========
def find_league_via_wikipedia(player: str) -> str:
    try:
        r = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{player.replace(' ', '_')}", timeout=10).json()
        txt = r.get("extract", "")
        m = re.search(r'plays.*for.*?([A-Z][a-z]+ [A-Z][a-z]+)', txt)
        club = m.group(1).strip() if m else None
        return TEAM_TO_LEAGUE.get(club, "Unknown") if club else "Unknown"
    except:
        return "Unknown"

# ========== FBref scraping ==========
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
                assists = int(row.find("td",{"data-stat":"assists"}).text.strip().replace(",","") or 0)
                g_plus_a = goals + assists
                break
    return {"name":name,"birthdate":birthdate,"league":league,"minutes":mins or 2500,"g_plus_a":g_plus_a or 13}

def fetch_player(name:str)->dict:
    url=_find_fbref_url(name)
    if not url: raise ValueError("Player not found on FBref")
    time.sleep(1)
    parsed = _parse_fbref(url)
    if not parsed: raise ValueError("Could not parse player page correctly")
    return parsed

# ========== YSP‑75 ==========
WEIGHTS={"minutes":.20,"performance":.25,"physical":.10,"technical":.15,"tactical":.10,"mental":.10,"health":.10,"traits":.10}
def calculate_ysp75(p:dict)->dict:
    L=league_factor(p["league"]); A=age_factor(p["birthdate"])
    minutes_score=min(100,p["minutes"]/15); perf=min(100,p["g_plus_a"]*10)
    raw = (minutes_score*WEIGHTS["minutes"]*L*A + perf*WEIGHTS["performance"]*L*A + 75*.55)
    score = round(raw / 1.10, 1)
    tier = "Top Europe" if score>=75 else "High Upside" if score>=70 else "Prospect" if score>=60 else "Professional"
    return {"score":score, "tier":tier}

# ========== UI ==========
st.set_page_config(page_title="FstarVfootball", page_icon="⚽")
st.title("FstarVfootball – חיזוי הצלחת שחקנים צעירים (YSP‑75)")
st.markdown("הזן שם שחקן באנגלית (למשל **Lamine Yamal**)")

name = st.text_input("שם שחקן:")
if st.button("חשב מדד") and name:
    with st.spinner("טוען נתונים..."):
        try:
            prof = fetch_player(name)
            height = google_scrape(f"{name} height")
            age = (date.today() - prof["birthdate"]).days // 365
            res = calculate_ysp75(prof)
            st.success(f"{prof['name']} – YSP‑75: {res['score']} ({res['tier']})")
            st.caption(f"ליגה: {prof['league']} | גיל: {age} | גובה: {height} מ׳ | דקות:{prof['minutes']} | G+A:{prof['g_plus_a']}")
        except Exception as e:
            st.error(f"שגיאה: {e}")
