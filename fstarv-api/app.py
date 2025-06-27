import streamlit as st
import pandas as pd

DATA_PATH = "players_data_2025.csv"

@st.cache_data
def load_players():
    df = pd.read_csv(DATA_PATH, low_memory=False)
    return df

def compute_ysp75(player):
    score = 0

    # גיל (הפוך) – ככל שצעיר יותר, ציון גבוה יותר
    age = player.get("age", 25)
    if age < 18:
        score += 30
    elif age <= 20:
        score += 25
    elif age <= 22:
        score += 20
    elif age <= 24:
        score += 10

    # ליגה – דירוג לפי ליגות בכירות
    top_55 = [
        'Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1',
        'Eredivisie', 'Primeira Liga', 'Championship', 'Süper Lig', 'MLS',
        'Brasileirão', 'Argentine Primera', 'Belgian Pro League', 'Swiss Super League'
    ]
    league = str(player.get("league_name", "")).strip()
    if league in top_55:
        score += 25
    elif len(league) > 0:
        score += 10

    # דקות משחק – מעיד על חשיבות השחקן
    minutes = player.get("minutes", 0)
    if minutes > 2000:
        score += 15
    elif minutes > 1000:
        score += 10
    elif minutes > 500:
        score += 5

    # תרומה ישירה – גולים ובישולים
    goals = player.get("goals", 0)
    assists = player.get("assists", 0)
    contributions = goals + assists
    if contributions >= 15:
        score += 20
    elif contributions >= 10:
        score += 15
    elif contributions >= 5:
        score += 10
    elif contributions >= 2:
        score += 5

    return round(score)

# --- אפליקציית Streamlit ---
st.set_page_config(page_title="🎯 FstarVfootball – YSP-75", layout="centered")
st.title("🎯 YSP-75 – מדד פוטנציאל לשחקן צעיר")

player_name = st.text_input("הכנס את שם השחקן")

if player_name:
    with st.spinner("מחפש שחקן..."):
        df = load_players()
        player_row = df[df["short_name"].str.lower() == player_name.lower()]

        if player_row.empty:
            st.error("שחקן לא נמצא בקובץ")
        else:
            player = player_row.iloc[0].to_dict()

            score = compute_ysp75(player)

            st.subheader(f"✳️ תוצאה: {score} נק׳ במדד YSP-75")
            if score >= 75:
                st.success("🌟 טופ אירופה")
            elif score >= 65:
                st.info("📈 כישרון בקנה מידה עולמי")
            elif score >= 55:
                st.warning("🔧 דרוש שיפור")
            else:
                st.error("⚠️ מתחת לסף")

            st.divider()
            st.markdown("### נתוני השחקן:")
            st.write({
                "שם": player.get("short_name"),
                "קבוצה": player.get("club_name"),
                "ליגה": player.get("league_name"),
                "גיל": player.get("age"),
                "גובה": player.get("height_cm"),
                "משחקים": player.get("appearances"),
                "דקות": player.get("minutes"),
                "גולים": player.get("goals"),
                "בישולים": player.get("assists"),
            })
