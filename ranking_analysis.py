import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load the actual rankings CSV
df = pd.read_csv("atp_rankings_2025.csv", index_col="date")
df.index = pd.to_datetime(df.index)

# Player guesses
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

# Compute the average Euclidean distance for each week (ignoring weeks with missing players)
scores = {name: [] for name in guesses}
dates = []

for date, row in df.iterrows():
    actual_ranks = row.to_dict()
    dates.append(date)

    for player, prediction in guesses.items():
        predicted_positions = {name: i+1 for i, name in enumerate(prediction)}
        actual_positions = [actual_ranks.get(name, 150) for name in prediction]

        if 150 in actual_positions:
            # Treat this week as missing if any player's rank is unknown
            scores[player].append(np.nan)
            continue

        predicted_order = [predicted_positions[name] for name in prediction]
        dist = np.linalg.norm(np.array(actual_positions) - np.array(predicted_order))
        avg_dist = dist / 10
        scores[player].append(avg_dist)

# Interpolate missing values to draw continuous lines
scores = {player: pd.Series(score_list, index=dates).interpolate() for player, score_list in scores.items()}

# Plotting the results
plt.figure(figsize=(12, 6))
for player, score_list in scores.items():
    plt.plot(dates, score_list, label=player)

plt.title("📊 Weekly Accuracy: Average Euclidean Distance from Actual ATP Rankings")
plt.ylabel("Average Euclidean Distance")
plt.xlabel("Week")
plt.xticks(rotation=45)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
