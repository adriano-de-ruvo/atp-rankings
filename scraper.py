import requests
from bs4 import BeautifulSoup
import pandas as pd

# Short → full name mapping
name_map = {
    "J. Sinner": "Jannik Sinner", "C. Alcaraz": "Carlos Alcaraz", "N. Djokovic": "Novak Djokovic",
    "A. Zverev": "Alexander Zverev", "D. Medvedev": "Daniil Medvedev", "T. Fritz": "Taylor Fritz",
    "C. Ruud": "Casper Ruud", "S. Tsitsipas": "Stefanos Tsitsipas", "A. Rublev": "Andrey Rublev",
    "A. de Minaur": "Alex de Minaur", "H. Rune": "Holger Rune", "J. Draper": "Jack Draper",
    "H. Hurkacz": "Hubert Hurkacz"
}
players_to_track = list(name_map.values())

# Hardcoded valid ATP Mondays from dropdown
def get_available_rank_dates():
    return [
        "2025-01-06", "2025-01-13", "2025-01-20", "2025-01-27",
        "2025-02-03", "2025-02-10", "2025-02-17", "2025-02-24",
        "2025-03-03", "2025-03-10", "2025-03-17", "2025-03-24", "2025-03-31",
        "2025-04-07", "2025-04-14", "2025-04-21"
    ]

def fetch_rankings_for_date(date_str):
    # Use both rankDate and dateWeek to force proper week load
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

if __name__ == "__main__":
    print("📅 Using hardcoded ATP dropdown dates...")
    ranking_dates = get_available_rank_dates()
    print(f"🔢 Fetching {len(ranking_dates)} weeks of real data...")

    all_rankings = []
    for date in ranking_dates:
        print(f"📥 Fetching rankings for {date}...")
        data = fetch_rankings_for_date(date)
        all_rankings.append(data)

    df = pd.DataFrame(all_rankings)
    df = df.sort_values("date").set_index("date")
    df.to_csv("atp_rankings_2025.csv")
    print("\n✅ Done! Rankings saved to 'atp_rankings_2025.csv'")
