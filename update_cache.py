#!/usr/bin/env python3
"""
Script to scrape ATP rankings data and save to JSON cache file.
Run this locally whenever you want to update the data.
"""

import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Same configuration as app.py
name_map = {
    "J. Sinner": "Jannik Sinner", "C. Alcaraz": "Carlos Alcaraz", "N. Djokovic": "Novak Djokovic",
    "A. Zverev": "Alexander Zverev", "D. Medvedev": "Daniil Medvedev", "T. Fritz": "Taylor Fritz",
    "C. Ruud": "Casper Ruud", "S. Tsitsipas": "Stefanos Tsitsipas", "A. Rublev": "Andrey Rublev",
    "A. de Minaur": "Alex de Minaur", "H. Rune": "Holger Rune", "J. Draper": "Jack Draper",
    "H. Hurkacz": "Hubert Hurkacz"
}
players_to_track = list(name_map.values())

# Setup session
_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})
_retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
_adapter = HTTPAdapter(max_retries=_retries, pool_connections=10, pool_maxsize=10)
_session.mount("https://", _adapter)

def get_weeks():
    start = datetime(2025, 1, 6)
    today = datetime.today()
    return [(start + timedelta(weeks=i)).strftime('%Y-%m-%d') for i in range((today - start).days // 7 + 1)]

def fetch_rankings_for_date(date_str):
    url = f"https://www.atptour.com/en/rankings/singles?rankDate={date_str}&dateWeek={date_str}&rankRange=0-100"
    try:
        response = _session.get(url, timeout=(5, 10))
        if response.status_code != 200:
            return {name: 150 for name in players_to_track} | {"date": date_str}
        
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
                    ranking_data[name_map[short_name]] = rank
            except:
                continue

        ranking_data["date"] = date_str
        return ranking_data
    except Exception as e:
        print(f"Error fetching {date_str}: {e}")
        return {name: 150 for name in players_to_track} | {"date": date_str}

if __name__ == "__main__":
    print("Scraping ATP rankings data...")
    weeks = get_weeks()
    print(f"Fetching {len(weeks)} weeks of data...")
    
    data = []
    completed = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_date = {executor.submit(fetch_rankings_for_date, date): date for date in weeks}
        
        for future in as_completed(future_to_date):
            result = future.result()
            data.append(result)
            completed += 1
            print(f"Progress: {completed}/{len(weeks)} weeks")
    
    # Sort by date
    data.sort(key=lambda x: x["date"])
    
    # Save to JSON
    output_file = "atp_rankings_cache.json"
    with open(output_file, 'w') as f:
        json.dump({
            "last_updated": datetime.now().isoformat(),
            "data": data
        }, f, indent=2)
    
    print(f"\n✅ Successfully saved {len(data)} weeks of data to {output_file}")
    print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nNow commit and push this file to GitHub:")
    print(f"  git add {output_file}")
    print(f'  git commit -m "Update ATP rankings cache"')
    print("  git push")
