# =============================
# FstarVfootball – single‑file Streamlit app
# v3 – FBref ➊  |  Understat ➋  |  Wikipedia ➌ fallbacks
# =============================
# • FBref (primary) – full league season stats
# • Understat (secondary) – JSON stats if FBref fails
# • Wikipedia summary (tertiary) – at least league & birth data
# -------------------------------------------------------------

import streamlit as st
from datetime import date
import requests, time, re, io, json
from bs4 import BeautifulSoup
import pandas as pd

HEADERS = {"User-Agent":"Mozilla/5.0 (compatible; FstarV/1.0)"}

###############################################################
# 1. Build league tier map from FiveThirtyEight SPI
###############################################################
SPI_CSV = "https://projects.fivethirtyeight.com/soccer-api/club/spi_global_rankings.csv"
@st.cache_data(ttl=86400)
def build_league_map():
    try:
        df = pd.read_csv(io.BytesIO(requests.get(SPI_CSV, timeout=20).content))
        league_avg = df.groupby('league')['spi'].mean().sort_values(ascending=False)
        tiers = {lg:(0 if i<=4 else 1 if i<=9 else 2 if i<=19 else 3 if i<=29 else 4)
                 for i,lg in enumerate(league_avg.index)}
        tiers.setdefault('Premier League',0); tiers.setdefault('La Liga',0)
        return tiers
    except Exception:
        return {'Premier League':0,'La Liga':0,'Serie A':0,'Bundesliga':0,'Ligue 1':0}
LEAGUE_TIER = build_league_map(); TIER_FACTOR={i:1-0.1*i for i in range(5)}
TEAM_TO_LEAGUE={'Manchester United':'Premier League','Manchester City':'Premier League','Arsenal':'Premier League','Liverpool':'Premier League','Inter Miami':'Major League Soccer','Barcelona':'La Liga','Real Madrid':'La Liga','Paris Saint-Germain':'Ligue 1','Juventus':'Serie A','Bayern Munich':'Bundesliga','Sporting CP':'Primeira Liga','Benfica':'Primeira Liga'}

def league_factor(lg:str)->float: return TIER_FACTOR.get(LEAGUE_TIER.get(lg,4),0.6)
###############################################################
# 2. Small helpers
###############################################################

def age_factor(bd:date)->float:
    age=(date.today()-bd).days//365
    return 1+0.02*(18-age) if age<18 else max(0.3,1-0.03*(age-18))

def google_height(player:str)->str:
    try:
        html=requests.get(f"https://www.google.com/search?q={player.replace(' ','+')}+height",headers=HEADERS,timeout=10).text
        m=re.search(r'(\d\.\d{2})\s?m',html) or re.search(r'(\d{1,2})′(\d{1,2})″',html)
        if m and len(m.groups())==2:  # feet+inches
            meters=round(int(m.group(1))*0.3048+int(m.group(2))*0.0254,2); return str(meters)
        elif m:
            return m.group(1)
    except: pass
    return 'N/A'

###############################################################
# 3. FBref primary fetcher
###############################################################
@st.cache_data(ttl=86400)
def fbref_search_url(name:str)->str|None:
    q=name.strip().replace(' ','-');page=requests.get(f"https://fbref.com/en/search/search.fcgi?search={q}",headers=HEADERS,timeout=20).text
    m=re.search(r"/en/players/[a-f0-9]{8}/[A-Za-z0-9\-]+",page)
    return f"https://fbref.com{m.group(0)}" if m else None

@st.cache_data(ttl=86400)
def fbref_parse(url:str):
    html=requests.get(url,headers=HEADERS,timeout=20).text
    soup=BeautifulSoup(html,'html.parser')
    name=soup.find('h1').text.strip() if soup.find('h1') else 'Unknown'
    birth_match=re.search(r'data-birth="(\d{4}-\d{2}-\d{2})"',html)
    if not birth_match: return None
    birth=date.fromisoformat(birth_match.group(1))
    club_tag=soup.find('span',class_='fancy');team=club_tag.text.strip() if club_tag else ''
    league=club_tag.get('title','').split(' ')[-1] if club_tag and 'title' in club_tag.attrs else TEAM_TO_LEAGUE.get(team,'Unknown')
    # stats
    mins=g_plus_a=0
    table=soup.find('table',id='stats_standard_dom_lg')
    if table:
        rows=table.find('tbody').find_all('tr',class_=lambda x:x!='thead')
        for r in reversed(rows):
            comp=r.find('td',{'data-stat':'comp'})
            if comp and 'league' in comp.text.lower():
                mins=int(r.find('td',{'data-stat':'minutes'}).text.replace(',','') or 0)
                goals=int(r.find('td',{'data-stat':'goals'}).text.replace(',','') or 0)
                ast=int(r.find('td',{'data-stat':'assists'}).text.replace(',','') or 0)
                g_plus_a=goals+ast;break
    return {'name':name,'birthdate':birth,'league':league,'minutes':mins,'g_plus_a':g_plus_a}

###############################################################
# 4. Understat secondary fetcher
###############################################################
@st.cache_data(ttl=86400)
def understat_fetch(name:str):
    try:
        search=requests.get(f"https://understat.com/search?query={name.replace(' ','%20')}",headers=HEADERS,timeout=15).json()
        if not search: return None
        player=search[0]  # top hit
        pid=player['id']; league=player.get('league','Unknown')
        page=requests.get(f"https://understat.com/player/{pid}",headers=HEADERS,timeout=15).text
        json_text=re.search(r'var\s+playerMatchesData\s*=\s*(\[.*?\]);',page)
        if not json_text: return None
        matches=json.loads(json_text.group(1))
        current=matches[-1]  # last match object (season)
        mins=sum(int(m['time']) for m in matches if m['season']==current['season'])
        goals=sum(int(m['goals']) for m in matches if m['season']==current['season'])
        assists=sum(int(m['assists']) for m in matches if m['season']==current['season'])
        return {'name':name,'birthdate':date.fromisoformat(player['birth_date']),'league':league,'minutes':mins,'g_plus_a':goals+assists}
    except Exception:
        return None

###############################################################
# 5. Wikipedia tertiary fetch (league + birth)
###############################################################

def wikipedia_basic(player:str):
    try:
        js=requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{player.replace(' ','_')}",timeout=10).json()
        birth=re.search(r'(\d{1,2})\s([A-Za-z]+)\s(\d{4})',js.get('extract',''))
        birthdate=date.fromisoformat(js['birthDate']) if 'birthDate' in js else None
        txt=js.get('extract','');club=re.search(r'for ([A-Z][A-Za-z ]+)',txt)
        league=TEAM_TO_LEAGUE.get(club.group(1),'Unknown') if club else 'Unknown'
        return {'name':js.get('title',player),'birthdate':birthdate,'league':league,'minutes':2500,'g_plus_a':13}
    except: return None

###############################################################
# 6. Unified fetch_player
###############################################################

def fetch_player(player:str):
    # ➊ FBref
    url=fbref_search_url(player)
    if url:
        data=fbref_parse(url)
        if data and data['league']!='Unknown': return data
    # ➋ Understat
    data=understat_fetch(player)
    if data and data['league']!='Unknown': return data
    # ➌ Wikipedia basic
    data=wikipedia_basic(player)
    if data: return data
    raise ValueError('Unable
