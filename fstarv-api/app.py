# FstarVfootball – אפליקציית Streamlit למדד YSP‑75
# כולל 3 שכבות מידע: FBref > Understat > Wikipedia
# ותיקון שגיאה כאשר תאריך הלידה לא קיים

import streamlit as st
from datetime import date
import requests, re, io, json
from bs4 import BeautifulSoup
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0"}

@st.cache_data(ttl=86400)
def build_league_map():
    try:
        df = pd.read_csv(io.BytesIO(requests.get(
            "https://projects.fivethirtyeight.com/soccer-api/club/spi_global_rankings.csv", timeout=20).content))
        league_avg = df.groupby('league')['spi'].mean().sort_values(ascending=False)
        tiers = {lg: (0 if i <= 4 else 1 if i <= 9 else 2 if i <= 19 else 3 if i <= 29 else 4)
                 for i, lg in enumerate(league_avg.index)}
        tiers.setdefault('Premier League', 0)
        tiers.setdefault('La Liga', 0)
        return tiers
    except Exception:
        return {'Premier League': 0, 'La Liga': 0, 'Serie A': 0, 'Bundesliga': 0, 'Ligue 1': 0}

LEAGUE_TIER = build_league_map()
TIER_FACTOR = {i: 1 - 0.1 * i for i in range(5)}

TEAM_TO_LEAGUE = {
    'Manchester United': 'Premier League',
    'Manchester City': 'Premier League',
    'Arsenal': 'Premier League',
    'Liverpool': 'Premier League',
    'Barcelona': 'La Liga',
    'Real Madrid': 'La Liga',
    'Paris Saint-Germain': 'Ligue 1',
    'Juventus': 'Serie A',
    'Bayern Munich': 'Bundesliga',
    'Sporting CP': 'Primeira Liga',
    'Benfica': 'Primeira Liga',
    'Inter Miami': 'Major League Soccer'
}

def league_factor(lg: str) -> float:
    return TIER_FACTOR.get(LEAGUE_TIER.get(lg, 4), 0.6)

def age_factor(bd: date) -> float:
    if not bd:
        return 0.6
    age = (date.today() - bd).days // 365
    return 1 + 0.02 * (18 - age) if age < 18 else max(0.3, 1 - 0.03 * (age - 18))

def google_height(player: str) -> str:
    try:
        html = requests.get(
            f"https://www.google.com/search?q={player.replace(' ', '+')}+height",
            headers=HEADERS, timeout=10).text
        m = re.search(r'(\d\.\d{2})\s?m', html) or re.search(r'(\d{1,2})′(\d{1,2})″', html)
        if m and len(m.groups()) == 2:
            meters = round(int(m.group(1)) * 0.3048 + int(m.group(2)) * 0.0254, 2)
            return str(meters)
        elif m:
            return m.group(1)
    except:
        pass
    return 'N/A'

@st.cache_data(ttl=86400)
def fbref_search_url(name: str) -> str | None:
    q = name.strip().replace(' ', '-')
    page = requests.get(
        f"https://fbref.com/en/search/search.fcgi?search={q}", headers=HEADERS, timeout=20).text
    m = re.search(r"/en/players/[a-f0-9]{8}/[A-Za-z0-9\-]+", page)
    return f"https://fbref.com{m.group(0)}" if m else None

@st.cache_data(ttl=86400)
def fbref_parse(url: str):
    html = requests.get(url, headers=HEADERS, timeout=20).text
    soup = BeautifulSoup(html, 'html.parser')
    name = soup.find('h1').text.strip() if soup.find('h1') else 'Unknown'
    birth_match = re.search(r'data-birth="(\d{4}-\d{2}-\d{2})"', html)
    birth = date.fromisoformat(birth_match.group(1)) if birth_match else None
    club_tag = soup.find('span', class_='fancy')
    team = club_tag.text.strip() if club_tag else ''
    league = club_tag.get('title', '').split(' ')[-1] if club_tag and 'title' in club_tag.attrs else TEAM_TO_LEAGUE.get(team, 'Unknown')
    mins = g_plus_a = 0
    table = soup.find('table', id='stats_standard_dom_lg')
    if table:
        rows = table.find('tbody').find_all('tr', class_=lambda x: x != 'thead')
        for r in reversed(rows):
            comp = r.find('td', {'data-stat': 'comp'})
            if comp and 'league' in comp.text.lower():
                mins = int(r.find('td', {'data-stat': 'minutes'}).text.replace(',', '') or 0)
                goals = int(r.find('td', {'data-stat': 'goals'}).text.replace(',', '') or 0)
                ast = int(r.find('td', {'data-stat': 'assists'}).text.replace(',', '') or 0)
                g_plus_a = goals + ast
                break
    return {'name': name, 'birthdate': birth, 'league': league, 'minutes': mins, 'g_plus_a': g_plus_a}

@st.cache_data(ttl=86400)
def understat_fetch(name: str):
    try:
        search = requests.get(f"https://understat.com/search?query={name.replace(' ', '%20')}",
                              headers=HEADERS, timeout=15).json()
        if not search:
            return None
        player = search[0]
        pid = player['id']
        league = player.get('league', 'Unknown')
        page = requests.get(f"https://understat.com/player/{pid}",
                            headers=HEADERS, timeout=15).text
        json_text = re.search(r'var\s+playerMatchesData\s*=\s*(\[.*?\]);', page)
        if not json_text:
            return None
        matches = json.loads(json_text.group(1))
        current = matches[-1]
        mins = sum(int(m['time']) for m in matches if m['season'] == current['season'])
        goals = sum(int(m['goals']) for m in matches if m['season'] == current['season'])
        assists = sum(int(m['assists']) for m in matches if m['season'] == current['season'])
        birth = date.fromisoformat(player['birth_date']) if player.get('birth_date') else None
        return {'name': name, 'birthdate': birth,
                'league': league, 'minutes': mins, 'g_plus_a': goals + assists}
    except:
        return None

def wikipedia_basic(player: str):
    try:
        js = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{player.replace(' ', '_')}", timeout=10).json()
        birthdate = date.fromisoformat(js['birthDate']) if 'birthDate' in js else None
        txt = js.get('extract', '')
        club = re.search(r'for ([A-Z][A-Za-z ]+)', txt)
        league = TEAM_TO_LEAGUE.get(club.group(1), 'Unknown') if club else 'Unknown'
        return {'name': js.get('title', player), 'birthdate': birthdate, 'league': league,
                'minutes': 2500, 'g_plus_a': 13}
    except:
        return None

def compute_score(p: dict) -> float:
    if not p: return 0
    score = league_factor(p['league']) * 30
    score += age_factor(p['birthdate']) * 25
    score += min(1, p['minutes'] / 2700) * 20
    score += min(1, p['g_plus_a'] / 20) * 25
    return round(score, 1)

def fetch_player(player: str):
    url = fbref_search_url(player)
    if url:
        data = fbref_parse(url)
        if data and data['league'] != 'Unknown':
            return data
    data = understat_fetch(player)
    if data and data['league'] != 'Unknown':
        return data
    data = wikipedia_basic(player)
    if data:
        return data
    raise ValueError("Unable to fetch player data from available sources")

# Streamlit UI
st.title("FstarVfootball – חיזוי הצלחת שחקנים צעירים")
name = st.text_input("🔍 הזן שם שחקן (באנגלית):", "Lamine Yamal")

if name:
    try:
        player = fetch_player(name)
        score = compute_score(player)
        height = google_height(name)
        tier = ("🔴 טופ עולמי" if score >= 75 else "🟠 פוטנציאל גבוה" if score >= 70 else "🟡 פרוספקט מבטיח" if score >= 60 else "⚪ מקצוען עם תקרה מוגבלת")
        if player['birthdate']:
            age = (date.today() - player['birthdate']).days // 365
        else:
            age = "לא ידוע"
        st.subheader(f"{player['name']} – YSP‑75: {score} ({tier})")
        st.markdown(f"**ליגה:** {player['league']} | **גיל:** {age} | **גובה:** {height} מ׳")
        st.markdown(f"**דקות משחק:** {player['minutes']} | **שערים + בישולים:** {player['g_plus_a']}")
    except Exception as e:
        st.error(f"שגיאה: {str(e)}")
