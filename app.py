import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

# Fix for matplotlib in Streamlit
import matplotlib
matplotlib.use("Agg")

# Guesses
guesses = {
    "Viola": [
        "Jannik Sinner", "Carlos Alcaraz", "Novak Djokovic", "Alexander Zverev", "Daniil Medvedev",
        "Taylor Fritz", "Casper Ruud", "Stefanos Tsitsipas", "Andrey Rublev", "Alex de Minaur"
    ],
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

# Weeks (official ATP Mondays)
def get_weeks():
    return [
        "2025-01-06", "2025-01-13", "2025-01-20", "2025-01-27",
        "2025-02-03", "2025-02-10", "2025-02-17", "2025-02-24",
        "2025-03-03", "2025-03-10", "2025-03-17", "2025-03-24", "2025-03-31",
        "2025-04-07", "2025-04-14", "2025-04-21"
    ]

# Scrape ATP data for a given date
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

# Get data for all weeks
@st.cache_data
def get_all_rankings():
    data = []
    for date in get_weeks():
        data.append(fetch_rankings_for_date(date))
    df = pd.DataFrame(data).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df

# Calculate distances
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

    # Interpolate
    scores = {p: pd.Series(v, index=dates).interpolate() for p, v in scores.items()}
    return scores

# ==== STREAMLIT UI ====

st.set_page_config(page_title="ATP Guess Battle", layout="wide")
st.title("🎾 ATP Ranking Guess Battle Dashboard")
st.markdown("Compare each player's weekly accuracy (lower = better)")

df = get_all_rankings()
scores = calculate_distances(df)

# Plotting
fig, ax = plt.subplots(figsize=(12, 6))
for player, series in scores.items():
    ax.plot(series.index, series.values, label=player)
ax.set_title("📊 Average Euclidean Distance from Actual Rankings")
ax.set_ylabel("Avg Euclidean Distance")
ax.set_xlabel("Week")
ax.grid(True)
ax.legend()
st.pyplot(fig)
