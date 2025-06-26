import streamlit as st
import requests, io, re
from datetime import date, datetime
import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON

HEADERS = {"User-Agent": "FstarVfootball/2.0 (open source demo)"}
SPI_CSV_URL = "https://projects.fivethirtyeight.com/soccer-api/club/spi_global_rankings.csv"

# -------- 1. Build league tier map (FiveThirtyEight) ----------------
@st.cache_data(ttl=86400)
def load_league_tiers():
    response = requests.get(SPI_CSV_URL, timeout=20)
    content = response.content.decode("utf-8", errors="ignore")
    df = pd.read_csv(io.StringIO(content))
    league_avg = df.groupby("league")["spi"].mean().sort_values(ascending=False)
    tiers = {}
    for idx, (lg, _) in enumerate(league_avg.items()):
        tiers[lg] = 0 if idx < 5 else 1 if idx < 10 else 2 if idx < 20 else 3 if idx < 30 else 4
    return tiers

LEAGUE_TIER = load_league_tiers()
TIER_FACTOR = {i: 1 - 0.1 * i for i in range(5)}

# -------- 2. Wikidata utilities -------------------------------------
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

@st.cache_data(ttl=86400)
def wikidata_id(player: str) -> str | None:
    url = ("https://www.wikidata.org/w/api.php?"
           f"action=wbsearchentities&search={player}&language=en&format=json&type=item")
    res = requests.get(url, headers=HEADERS, timeout=10).json()
    return res.get("search", [{}])[0].get("id") if res.get("search") else None

@st.cache_data(ttl=86400)
def fetch_player_wikidata(qid: str) -> dict | None:
    sparql = SPARQLWrapper(SPARQL_ENDPOINT, agent="FstarVfootball/2.0")
    query = f"""
    SELECT ?playerLabel ?dob ?height ?clubLabel ?leagueLabel WHERE {{
      wd:{qid} rdfs:label ?playerLabel; wdt:P569 ?dob. 
      OPTIONAL {{ wd:{qid} wdt:P2048 ?height. }}
      OPTIONAL {{ wd:{qid} wdt:P54 ?club.
                 ?club wdt:P118 ?league.
                 SERVICE wikibase:label {{ bd:serviceParam wikibase:language \"en\". }}
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language \"en\". }}
      FILTER (lang(?playerLabel) = \"en\")
    }} LIMIT 1"""
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    if not results["results"]["bindings"]:
        return None
    row = results["results"]["bindings"][0]
    def val(key):
        return row[key]["value"] if key in row else None
    return {
        "name": val("playerLabel"),
        "birthdate": datetime.strptime(val("dob"), "%Y-%m-%dT%H:%M:%SZ").date(),
        "height": round(float(val("height")) / 100, 2) if val("height") else None,
        "club": val("clubLabel"),
        "league": val("leagueLabel"),
    }

# -------- 3. Wikipedia height fallback ------------------------------
@st.cache_data(ttl=86400)
def wikipedia_height(name: str) -> str | None:
    try:
        js = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{name.replace(' ', '_')}",
            timeout=10).json()
        m = re.search(r"\\((\\d\\.\\d{2})\\sm\\)", js.get("extract", ""))
        return m.group(1) if m else None
    except:
        return None

# -------- 4. Compute YSP-75 ----------------------------------------
WEIGHTS = {"age": 0.25, "league": 0.30, "minutes": 0.20, "impact": 0.25}

def compute_score(birth: date, league: str, minutes: int = 2500, g_a: int = 10) -> float:
    age_factor = 1 + 0.02 * (18 - ((date.today() - birth).days // 365)) if birth else 0.6
    league_factor = TIER_FACTOR.get(LEAGUE_TIER.get(league, 4), 0.6)
    min_factor = min(1.0, minutes / 2700)
    imp_factor = min(1.0, g_a / 20)
    score = (age_factor * WEIGHTS["age"] +
             league_factor * WEIGHTS["league"] +
             min_factor * WEIGHTS["minutes"] +
             imp_factor * WEIGHTS["impact"]) * 100
    return round(score, 1)

# -------- 5. Unified fetch -----------------------------------------
@st.cache_data(ttl=86400)
def get_player(player: str) -> dict:
    qid = wikidata_id(player)
    if not qid:
        raise ValueError("Player not found on Wikidata")
    data = fetch_player_wikidata(qid)
    if not data:
        raise ValueError("Incomplete data on Wikidata")
    if not data["height"]:
        data["height"] = wikipedia_height(data["name"])
    return data

# -------- 6. Streamlit GUI -----------------------------------------
st.set_page_config(page_title="FstarVfootball", layout="centered", page_icon="⚽")
st.title("FstarVfootball – Clean API version")

player_name = st.text_input("Enter player name (English):", "Lamine Yamal")
minutes = st.number_input("Minutes played (season, optional)", 0, 4000, 2500)
goals_assists = st.number_input("Goals + Assists (season, optional)", 0, 50, 10)

if st.button("Compute YSP‑75") and player_name:
    try:
        p = get_player(player_name)
        score = compute_score(p["birthdate"], p["league"], minutes, goals_assists)
        tier = ("🔴 Top Europe" if score >= 75 else "🟠 High Upside" if score >= 70
                else "🟡 Prospect" if score >= 60 else "⚪ Professional")
        age = (date.today() - p["birthdate"]).days // 365 if p["birthdate"] else "Unknown"
        st.success(f"{p['name']} — YSP‑75: {score} ({tier})")
        st.write(f"**League:** {p['league']}  |  **Age:** {age}  |  **Height:** {p['height'] or 'N/A'} m\n"
                 f"**Minutes:** {minutes}  |  **G+A:** {goals_assists}")
    except Exception as e:
        st.error(str(e))

# Notes:
# All sources are legally accessible public APIs:
#  - Player data from Wikidata SPARQL
#  - League rankings from FiveThirtyEight SPI CSV
#  - Height fallback from Wikipedia REST

# Instructions:
# 1. Save as app.py
# 2. Create requirements.txt:
#    streamlit
#    requests
#    pandas
#    SPARQLWrapper
# 3. Run:
#    pip install -r requirements.txt
#    streamlit run app.py
# Or deploy to Streamlit Cloud with app.py as entry point.

