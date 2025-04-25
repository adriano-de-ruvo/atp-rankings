import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import plotly.graph_objects as go

import matplotlib
matplotlib.use("Agg")

# === PAGE CONFIG + STYLE ===
st.set_page_config(page_title="ATP Guess Game", layout="centered")

st.markdown("""
<link href="https://fonts.cdnfonts.com/css/computer-modern" rel="stylesheet">
<style>
    @import url('https://fonts.cdnfonts.com/css/computer-modern');

    html, body, [class*="css"], .stTextInput, .stSelectbox, .stSlider, .stButton, .stMarkdown, .stPlotlyChart {
        font-family: 'Computer Modern', serif !important;
    }

    h1, h2, h3, h4, h5, h6, .stTitle, .stHeader {
        font-family: 'Computer Modern', serif !important;
        font-weight: 500 !important;
    }

    .metric-card {
        background: white;
        border-radius: 0.75rem;
        padding: 1.2rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        margin-top: 1.5rem;
        margin-bottom: 2rem;
        font-family: 'Computer Modern', serif !important;
    }
</style>
""", unsafe_allow_html=True)

guesses = {
    "Adriano": ["Jannik Sinner", "Carlos Alcaraz", "Alexander Zverev", "Novak Djokovic", "Daniil Medvedev", "Taylor Fritz", "Holger Rune", "Andrey Rublev", "Jack Draper", "Alex de Minaur"],
    "Alessandro": ["Carlos Alcaraz", "Daniil Medvedev", "Jannik Sinner", "Alexander Zverev", "Novak Djokovic", "Taylor Fritz", "Casper Ruud", "Stefanos Tsitsipas", "Hubert Hurkacz", "Holger Rune"],
    "Federico": ["Carlos Alcaraz", "Jannik Sinner", "Taylor Fritz", "Alexander Zverev", "Daniil Medvedev", "Casper Ruud", "Andrey Rublev", "Holger Rune", "Stefanos Tsitsipas", "Hubert Hurkacz"],
    "Viola": ["Jannik Sinner", "Carlos Alcaraz", "Novak Djokovic", "Alexander Zverev", "Daniil Medvedev", "Taylor Fritz", "Casper Ruud", "Stefanos Tsitsipas", "Andrey Rublev", "Alex de Minaur"]
}

name_map = {
    "J. Sinner": "Jannik Sinner", "C. Alcaraz": "Carlos Alcaraz", "N. Djokovic": "Novak Djokovic",
    "A. Zverev": "Alexander Zverev", "D. Medvedev": "Daniil Medvedev", "T. Fritz": "Taylor Fritz",
    "C. Ruud": "Casper Ruud", "S. Tsitsipas": "Stefanos Tsitsipas", "A. Rublev": "Andrey Rublev",
    "A. de Minaur": "Alex de Minaur", "H. Rune": "Holger Rune", "J. Draper": "Jack Draper",
    "H. Hurkacz": "Hubert Hurkacz"
}
players_to_track = list(name_map.values())

def get_weeks():
    start = datetime(2025, 1, 6)
    today = datetime.today()
    return [(start + timedelta(weeks=i)).strftime('%Y-%m-%d') for i in range((today - start).days // 7 + 1)]

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

@st.cache_data
def get_all_rankings():
    weeks = get_weeks()
    data = [fetch_rankings_for_date(date) for date in weeks]
    df = pd.DataFrame(data).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df

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

    scores = {p: pd.Series(v, index=dates).interpolate() for p, v in scores.items()}
    return scores

# === PAGE CONTENT ===
st.markdown("<h1>ATP Guess Battle</h1>", unsafe_allow_html=True)
st.markdown("<h4>Tracking who predicted the 2025 ATP Top 10 best</h4>", unsafe_allow_html=True)
st.markdown("---")

# === LOAD & COMPUTE ===
df = get_all_rankings()
scores = calculate_distances(df)

# === PLOT ===
colors = {"Viola": "#1A1A1A", "Adriano": "#0070F3", "Alessandro": "#555", "Federico": "#9CA3AF"}
placeholder = st.empty()
for i in range(2, len(df.index) + 1):
    fig = go.Figure()
    for player, series in scores.items():
        fig.add_trace(go.Scatter(
            x=series.index[:i], y=series.values[:i],
            mode='lines+markers', name=player,
            line=dict(width=3, color=colors.get(player, "#000000")),
            marker=dict(size=6),
            hovertemplate='%{x|%b %d, %Y}<br><b>%{y:.2f}</b><extra>' + player + '</extra>'
        ))
    all_y = np.concatenate([s.values[:i] for s in scores.values()])
    y_min, y_max = np.nanmin(all_y), np.nanmax(all_y)
    fig.update_layout(
        xaxis=dict(title="Week", range=[df.index.min(), df.index.max()]),
        yaxis=dict(title="Average Euclidean Distance", range=[y_min * 0.95, y_max * 1.05]),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=60, b=80),
        height=500,
        font=dict(size=14, family="Computer Modern")
    )
    placeholder.plotly_chart(fig, use_container_width=True)
    import time; time.sleep(0.05)

# === LEADER STREAK + LOWEST DISTANCE ===
weekly_leaders = pd.Series(index=df.index, dtype=object)
for week in df.index:
    leader = min(scores, key=lambda p: scores[p].loc[week])
    weekly_leaders.loc[week] = leader

# Longest streak
longest_streak_holder = None
longest_streak_length = 0
current_holder = None
current_length = 0

for leader in weekly_leaders:
    if leader == current_holder:
        current_length += 1
    else:
        current_holder = leader
        current_length = 1
    if current_length > longest_streak_length:
        longest_streak_holder = current_holder
        longest_streak_length = current_length

# Lowest distance
min_distance = float('inf')
min_distance_player = None
min_distance_date = None

for player, series in scores.items():
    min_val = series.min()
    if min_val < min_distance:
        min_distance = min_val
        min_distance_player = player
        min_distance_date = series.idxmin()

# === METRICS ===
latest_week = df.index.max()
latest_scores = {k: v.loc[latest_week] for k, v in scores.items()}
current_leader = min(latest_scores, key=latest_scores.get)
current_score = latest_scores[current_leader]

st.markdown(f"""
<div class='metric-card'>
    <div style='font-size: 0.9rem; color: #888;'>Current leader:</div>
    <div style='font-size: 1.5rem; font-weight: 600; color: #111;'>{current_leader}</div>
    <div style='font-size: 0.9rem; color: #666;'>Average distance: {current_score:.2f}, as of {latest_week.date()}</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class='metric-card'>
    <div style='font-size: 0.9rem; color: #888;'>Longest streak as leader:</div>
    <div style='font-size: 1.5rem; font-weight: 600; color: #111;'>{longest_streak_holder}</div>
    <div style='font-size: 0.9rem; color: #666;'>{longest_streak_length} consecutive weeks as leader</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class='metric-card'>
    <div style='font-size: 0.9rem; color: #888;'>Lowest distance ever reached:</div>
    <div style='font-size: 1.5rem; font-weight: 600; color: #111;'>{min_distance_player}</div>
    <div style='font-size: 0.9rem; color: #666;'>Average distance: {min_distance:.2f} on {min_distance_date.date()}</div>
</div>
""", unsafe_allow_html=True)

# === FOOTER ===
st.markdown("---")
st.markdown("<small style='color: #aaa;'>In Rafa We Trust</small>", unsafe_allow_html=True)
