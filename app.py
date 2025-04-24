import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Fix for matplotlib in Streamlit
import matplotlib
matplotlib.use("Agg")

# Guesses
guesses = {
    "Adriano": [
        "Jannik Sinner", "Carlos Alcaraz", "Alexander Zverev", "Novak Djokovic", "Daniil Medvedev",
        "Taylor Fritz", "Holger Rune", "Andrey Rublev", "Jack Draper", "Alex de Minaur"
    ],
    "Alessandro": [
        "Carlos Alcaraz", "Daniil Medvedev", "Jannik Sinner", "Alexander Zverev", "Novak Djokovic",
        "Taylor Fritz", "Casper Ruud", "Stefanos Tsitsipas", "Hubert Hurkacz", "Holger Rune"
    ],
    "Federico": [
        "Carlos Alcaraz", "Jannik Sinner", "Taylor Fritz", "Alexander Zverev", "Daniil Medvedev",
        "Casper Ruud", "Andrey Rublev", "Holger Rune", "Stefanos Tsitsipas", "Hubert Hurkacz"
    ],
    "Viola": [
        "Jannik Sinner", "Carlos Alcaraz", "Novak Djokovic", "Alexander Zverev", "Daniil Medvedev",
        "Taylor Fritz", "Casper Ruud", "Stefanos Tsitsipas", "Andrey Rublev", "Alex de Minaur"
    ]
}

# Name mapping
name_map = {
    "J. Sinner": "Jannik Sinner", "C. Alcaraz": "Carlos Alcaraz", "N. Djokovic": "Novak Djokovic",
    "A. Zverev": "Alexander Zverev", "D. Medvedev": "Daniil Medvedev", "T. Fritz": "Taylor Fritz",
    "C. Ruud": "Casper Ruud", "S. Tsitsipas": "Stefanos Tsitsipas", "A. Rublev": "Andrey Rublev",
    "A. de Minaur": "Alex de Minaur", "H. Rune": "Holger Rune", "J. Draper": "Jack Draper",
    "H. Hurkacz": "Hubert Hurkacz"
}
players_to_track = list(name_map.values())

# === Auto-generate ATP Mondays from 2025-01-06 to today
def get_weeks():
    start = datetime(2025, 1, 6)
    today = datetime.today()
    return [(start + timedelta(weeks=i)).strftime('%Y-%m-%d') 
            for i in range((today - start).days // 7 + 1)]

# Scrape ATP rankings for one week
def fetch_rankings_for_date(date_str):
    url = f"https://www.atptour.com/en/rankings/singles?rankDate={date_str}&dateWeek={date_str}&rankRange=0-100"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    ranking_data = {name: 150 for name in players_to_track}
    rows = soup.select("table.mega-table tbody tr")

    for row in rows:
        try:
            rank_cell = row.find("td", class_="rank")
            name_cell = row.find("td", class_="player")
            if not (rank_cell and name_cell):
                continue
            rank = int(rank_cell.text.strip())
            short_name = name_cell.find("span", class_="lastName").text.strip()
            if short_name in name_map:
                full_name = name_map[short_name]
                ranking_data[full_name] = rank
        except:
            continue

    ranking_data["date"] = date_str
    return ranking_data

# Get all weekly rankings
@st.cache_data
def get_all_rankings():
    weeks = get_weeks()
    data = [fetch_rankings_for_date(date) for date in weeks]
    df = pd.DataFrame(data).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df

# Compute average Euclidean distances
def calculate_distances(df):
    scores = {name: [] for name in guesses}
    dates = df.index.tolist()

    for date, row in df.iterrows():
        actual_ranks = row.to_dict()

        for player, prediction in guesses.items():
            predicted_positions = {name: i+1 for i, name in enumerate(prediction)}
            actual_positions = [actual_ranks.get(name, 150) for name in prediction]

            if 150 in actual_positions:
                scores[player].append(np.nan)
                continue

            predicted_order = [predicted_positions[name] for name in prediction]
            dist = np.linalg.norm(np.array(actual_positions) - np.array(predicted_order))
            avg_dist = dist / 10
            scores[player].append(avg_dist)

    # Interpolate missing data
    scores = {p: pd.Series(v, index=dates).interpolate() for p, v in scores.items()}
    return scores

# ==== STREAMLIT UI ====

st.set_page_config(page_title="ATP Guess Game", layout="centered")

# 👋 Header
st.markdown("""
<style>
    .main {
        background-color: #fafafa;
    }
    h1 {
        font-family: 'Segoe UI', sans-serif;
        font-weight: 700;
        font-size: 2.8rem;
        color: #111;
        margin-bottom: 0.2em;
    }
    h4 {
        font-family: 'Segoe UI', sans-serif;
        font-weight: 400;
        font-size: 1.1rem;
        color: #555;
        margin-top: 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>🎾 ATP Guess Game</h1>", unsafe_allow_html=True)
st.markdown("<h4>Tracking who predicted the 2025 ATP Top 10 best</h4>", unsafe_allow_html=True)
st.markdown("---")

# Load data
df = get_all_rankings()
scores = calculate_distances(df)

# 📈 Plot
fig, ax = plt.subplots(figsize=(10, 5))
colors = {
    "Viola": "#E63946",
    "Adriano": "#457B9D",
    "Alessandro": "#2A9D8F",
    "Federico": "#F4A261"
}

for player, series in scores.items():
    ax.plot(series.index, series.values, label=player, linewidth=2.5, color=colors[player])

ax.set_title("📊 Weekly Accuracy (Avg Euclidean Distance)", fontsize=16, fontweight='bold')
ax.set_ylabel("Average Distance", fontsize=12)
ax.set_xlabel("Week", fontsize=12)
ax.grid(True, linestyle='--', alpha=0.3)
ax.legend(frameon=False)
fig.tight_layout()

st.pyplot(fig)

# 👇 Footer
st.markdown("---")
st.markdown("<small style='color: #aaa;'>Built with ❤️ by friends who take tennis way too seriously</small>", unsafe_allow_html=True)
