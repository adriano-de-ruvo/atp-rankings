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

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #f7f8fa;
        color: #111;
    }
    h1 {
        font-size: 2.2rem;
        font-weight: 600;
        color: #111;
        margin-bottom: 0.2em;
    }
    h4 {
        font-weight: 400;
        font-size: 1.1rem;
        color: #555;
        margin-top: 0;
    }
    .metric-card {
        background: white;
        border-radius: 0.75rem;
        padding: 1.2rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        margin-top: 1.5rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)


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

st.markdown("<h1>ATP Guess Battle</h1>", unsafe_allow_html=True)
st.markdown("<h4>Tracking who predicted the 2025 ATP Top 10 best</h4>", unsafe_allow_html=True)
st.markdown("---")

# Load data
df = get_all_rankings()
scores = calculate_distances(df)

import plotly.graph_objects as go

# 📊 Plotly Interactive Chart
fig = go.Figure()

colors = {
    "Viola": "#1A1A1A",         # Jet black
    "Adriano": "#0070F3",       # Vercel blue
    "Alessandro": "#555",       # Medium gray
    "Federico": "#9CA3AF"       # Soft steel
}

for player, series in scores.items():
    fig.add_trace(go.Scatter(
        x=series.index,
        y=series.values,
        mode='lines+markers',
        name=player,
        line=dict(width=3, color=colors[player]),
        marker=dict(size=6),
        hovertemplate='%{x|%b %d, %Y}<br><b>%{y:.2f}</b><extra>' + player + '</extra>'
    ))

fig.update_layout(
    title=dict(
        text=" Weekly Accuracy (Euclidean Distance from ATP Rankings)",
        x=0.5,
        xanchor="center",
        font=dict(size=20, family="Segoe UI", color="#222")
    ),
    xaxis_title="Week",
    yaxis_title="Average Euclidean Distance",
    template="plotly_white",
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.2,
        xanchor="center",
        x=0.5,
        font=dict(size=12),
    ),
    margin=dict(l=10, r=10, t=60, b=80),  # Top and bottom space to fix overlapping
    autosize=True,
    height=500,
    font=dict(size=14),
)


st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# 🏆 Current Leader Highlight
latest_week = df.index.max()
latest_scores = {k: v.loc[latest_week] for k, v in scores.items()}
current_leader = min(latest_scores, key=latest_scores.get)
current_score = latest_scores[current_leader]

st.markdown(f"""
<div class='metric-card'>
    <div style='font-size: 0.9rem; color: #888;'>Current Leader</div>
    <div style='font-size: 1.5rem; font-weight: 600; color: #111;'>{current_leader}</div>
    <div style='font-size: 0.9rem; color: #666;'>Avg distance: {current_score:.2f} as of {latest_week.date()}</div>
</div>
""", unsafe_allow_html=True)

# 👟 Footer
st.markdown("---")
st.markdown("<small style='color: #aaa;'>In Rafa we trust</small>", unsafe_allow_html=True)
