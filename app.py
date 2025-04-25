import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Fix for matplotlib in Streamlit
import matplotlib
matplotlib.use("Agg")

# === PAGE CONFIG + STYLE ===
st.set_page_config(page_title="ATP Guess Game", layout="centered")

# 🧠 Load Google Font for LaTeX Style
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

# 🎯 Player Guesses
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
    return [(start + timedelta(weeks=i)).strftime('%Y-%m-%d') 
            for i in range((today - start).days // 7 + 1)]

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

# === PLOTLY CHART WITH ANIMATION ===

colors = {
    "Viola": "#1A1A1A", "Adriano": "#0070F3", "Alessandro": "#555", "Federico": "#9CA3AF"
}

fig = go.Figure()

initial_length = 1  # Start with one data point

# Add initial traces for each player
for player, series in scores.items():
    fig.add_trace(go.Scatter(
        x=series.index[:initial_length],
        y=series.values[:initial_length],
        mode='lines+markers',
        name=player,
        line=dict(width=3, color=colors.get(player, "#000000")),
        marker=dict(size=6),
        hovertemplate='%{x|%b %d, %Y}<br><b>%{y:.2f}</b><extra>' + player + '</extra>'
    ))

# Create animation frames
frames = []
num_frames = len(df.index)

for i in range(initial_length + 1, num_frames + 1):
    frame_data = []
    for player, series in scores.items():
        frame_data.append(go.Scatter(
            x=series.index[:i],
            y=series.values[:i],
            mode='lines+markers',
            line=dict(width=3, color=colors.get(player, "#000000")),
            marker=dict(size=6),
            name=player,
            showlegend=False
        ))
    frames.append(go.Frame(data=frame_data, name=str(i)))

fig.frames = frames

# Final data ranges for axis scaling
all_x = df.index
all_y = np.concatenate([s.values for s in scores.values()])
y_min, y_max = np.nanmin(all_y), np.nanmax(all_y)

# Chart Layout with fixed axis ranges based on final data
fig.update_layout(
    updatemenus=[dict(
        type="buttons",
        showactive=False,
        buttons=[dict(
            label="Play",
            method="animate",
            args=[None, {
                "frame": {"duration": 100, "redraw": True},
                "fromcurrent": True,
                "transition": {"duration": 0}
            }]
        )],
        x=0.5,
        xanchor="center",
        y=-0.2,
        yanchor="top"
    )],
    xaxis=dict(
        title=dict(text="Week", font=dict(family="Computer Modern", size=16)),
        range=[all_x.min(), all_x.max()]
    ),
    yaxis=dict(
        title=dict(text="Average Euclidean Distance", font=dict(family="Computer Modern", size=16)),
        range=[y_min * 0.95, y_max * 1.05]
    ),
    template="plotly_white",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
    margin=dict(l=10, r=10, t=60, b=80),
    height=500,
    font=dict(size=14, family="Computer Modern")
)


# Display plot
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "displaylogo": False})


# === LEADER ===
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

# === FOOTER ===
st.markdown("---")
st.markdown("<small style='color: #aaa;'>In Rafa we trust</small>", unsafe_allow_html=True)
