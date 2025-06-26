# (המשך הקוד נשאר זהה עד סוף הקובץ)

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
#    streamlit\nrequests\npandas\nSPARQLWrapper
# 3. Run:
#    pip install -r requirements.txt
#    streamlit run app.py
# Or deploy to Streamlit Cloud with app.py as entry point.
