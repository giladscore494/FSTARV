# =============================
# FstarVfootball – Streamlit Version (app.py) with FBref scraping
# =============================

import streamlit as st
from datetime import date
import requests, time, re, io
from bs4 import BeautifulSoup
import pandas as pd

###############################
# 1. Dynamic League Tier map  #
###############################
SPI_CSV_URL = "https://projects.fivethirtyeight.com/soccer-api/club/spi_global_rankings.csv"

@st.cache_data(ttl=86400)
def _build_league_map():
    try:
        df = pd.read_csv(io.BytesIO(requests.get(SPI_CSV_URL, timeout=20).content))
        league_avg = df.groupby("league")["spi"].mean().sort_values(ascending=False)
        tiers = {}
        for rank, lg in enumerate(league_avg.index, start=1):
            tiers[lg] = 0 if rank<=5 else 1 if rank<=10 else 2 if rank<=20 else 3 if rank<=30 else 4
        # minimal fallback
        tiers.setdefault("Premier League",0)
        tiers.setdefault("La Liga",0)
        return tiers
    except Exception:
        return {"Premier League":0,"La Liga":0,"Serie A":0,"Bundesliga":0,"Ligue 1":0}

LEAGUE_TIER_MAP = _build_league_map()
TIER_FACTOR       = {0:1.0,1:0.9,2:0.8,3:0.7,4:0.6}

###############################
# 2. Helpers                 #
###############################
HEADERS = {"User-Agent":"Mozilla/5.0 (compatible; FstarV/1.0)"}

def league_factor(lg:str)->float: return TIER_FACTOR.get(LEAGUE_TIER_MAP.get(lg,4),0.6)

def age_factor(bd:date)->float:
    age=(date.today()-bd).days//365
    return 1+0.02*(18-age) if age<18 else max(0.3,1-0.03*(age-18))

###############################
# 3. FBref scraping          #
###############################
@st.cache_data(ttl=86400)
def _find_fbref_url(name:str)->str|None:
    q=name.strip().replace(" ","-")
    url=f"https://fbref.com/en/search/search.fcgi?search={q}"
    html=requests.get(url,headers=HEADERS,timeout=20).text
    m=re.search(r"/en/players/[a-f0-9]{8}/[A-Za-z0-9\-]+",html)
    return f"https://fbref.com{m.group(0)}" if m else None

@st.cache_data(ttl=86400)
def _parse_fbref(url:str)->dict:
    html=requests.get(url,headers=HEADERS,timeout=20).text
    soup=BeautifulSoup(html,"html.parser")
    name=soup.find("h1").text.strip()
    # birth
    birth_tag=soup.find("span",id="necro-birth")
    birthdate=date.fromisoformat(birth_tag["data-birth"])
    # height
    ht=soup.find(text=re.compile("cm"))
    # latest club + league
    club_tag=soup.find("span",class_="fancy")
    league="Unknown"
    if club_tag and "title" in club_tag.attrs:
        league=club_tag["title"].split(" ")[-1]
    # current season table
    mins=g_plus_a=0
    stat_table=soup.find("table",id="stats_standard_dom_lg")
    if stat_table:
        rows=stat_table.find("tbody").find_all("tr",class_=lambda x:x!="thead")
        if rows:
            latest=rows[-1]
            mins=int(latest.find("td",{"data-stat":"minutes"}).text or 0)
            goals=int(latest.find("td",{"data-stat":"goals"}).text or 0)
            ast=int(latest.find("td",{"data-stat":"assists"}).text or 0)
            g_plus_a=goals+ast
    return{"name":name,"birthdate":birthdate,"league":league,"minutes":mins or 2500,"g_plus_a":g_plus_a or 13,"position":"Unknown"}

def fetch_player(name:str)->dict:
    url=_find_fbref_url(name)
    if not url:
        raise ValueError("Player not found on FBref")
    time.sleep(1) # polite delay
    return _parse_fbref(url)

###############################
# 4. YSP‑75 calculation      #
###############################
WEIGHTS={"minutes":.20,"performance":.25,"physical":.10,"technical":.15,"tactical":.10,"mental":.10,"health":.10,"traits":.10}

def calculate_ysp75(p:dict)->dict:
    L=league_factor(p["league"]);A=age_factor(p["birthdate"])
    minutes_score=min(100,p["minutes"]/15);perf=min(100,p["g_plus_a"]*10)
    phys=tech=tact=ment=health=traits=75
    raw=(minutes_score*WEIGHTS["minutes"]*L*A+perf*WEIGHTS["performance"]*L*A+phys*WEIGHTS["physical"]+tech*WEIGHTS["technical"]+tact*WEIGHTS["tactical"]+ment*WEIGHTS["mental"]+health*WEIGHTS["health"]+traits*WEIGHTS["traits"])
    score=round(raw/1.10,1)
    tier="Top Europe" if score>=75 else "High Upside" if score>=70 else "Prospect" if score>=60 else "Professional"
    return{"score":score,"tier":tier}

###############################
# 5. Streamlit UI            #
###############################
st.set_page_config(page_title="FstarVfootball",page_icon="⚽")
st.title("FstarVfootball – חיזוי הצלחת שחקנים צעירים (מקור FBref)")
st.markdown("""הזן שם שחקן באנגלית (למשל **Lamine Yamal**) ולחץ *חשב*‎""")

name=st.text_input("שם שחקן:")
if st.button("חשב מדד") and name:
    with st.spinner("טוען נתונים מ‑FBref…"):
        try:
            prof=fetch_player(name)
            res=calculate_ysp75(prof)
            st.success(f"{prof['name']} – YSP‑75: {res['score']} ({res['tier']})")
            st.caption(f"ליגה: {prof['league']} | תאריך לידה: {prof['birthdate']} | דקות:{prof['minutes']} | G+A:{prof['g_plus_a']}")
        except Exception as e:
            st.error(f"שגיאה: {e}")
