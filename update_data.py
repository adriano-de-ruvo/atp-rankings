#!/usr/bin/env python3
"""
use a headless browser (playwright) to scrape weekly atp rankings from
atptour.com by interacting with the date dropdown, then compute euclidean
distances between four friends' end-of-year predictions and the actual rankings.

run manually or via cron to keep data/rankings.json current:
  python3 update_data.py

cron example (every monday at 09:00):
  0 9 * * 1 cd /path/to/atp_rankings && python3 update_data.py
"""

import re
import os
import sys
import json
import math
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── predictions ──────────────────────────────────────────────────────────────

PREDICTIONS = {
    "adriano": [
        ("sinner",          1), ("alcaraz",         2), ("zverev",          3),
        ("de-minaur",       4), ("djokovic",         5), ("draper",          6),
        ("fritz",           7), ("shelton",          8), ("musetti",         9),
        ("medvedev",       10),
    ],
    "alessandro": [
        ("sinner",          1), ("alcaraz",          2), ("zverev",          3),
        ("fritz",           4), ("de-minaur",        5), ("musetti",         6),
        ("fonseca",         7), ("shelton",          8),
        ("auger-aliassime", 9), ("rublev",          10),
    ],
    "federico": [
        ("sinner",          1), ("alcaraz",          2), ("fritz",           3),
        ("shelton",         4), ("draper",           5), ("zverev",          6),
        ("djokovic",        7), ("de-minaur",        8), ("musetti",         9),
        ("fonseca",        10),
    ],
    "viola": [
        ("sinner",          1), ("alcaraz",          2), ("djokovic",        3),
        ("de-minaur",       4), ("zverev",           5), ("musetti",         6),
        ("auger-aliassime", 7), ("shelton",          8), ("fritz",           9),
        ("medvedev",       10),
    ],
}

DISPLAY_NAMES = {
    "sinner":           "Sinner",
    "alcaraz":          "Alcaraz",
    "zverev":           "Zverev",
    "de-minaur":        "De Minaur",
    "djokovic":         "Djokovic",
    "draper":           "Draper",
    "fritz":            "Fritz",
    "shelton":          "Shelton",
    "musetti":          "Musetti",
    "medvedev":         "Medvedev",
    "fonseca":          "Fonseca",
    "rublev":           "Rublev",
    "auger-aliassime":  "Auger-Aliassime",
}

PENALTY_RANK = 100
ATP_URL      = "https://www.atptour.com/en/rankings/singles?rankRange=1-100"

# ── helpers ───────────────────────────────────────────────────────────────────

def parse_rankings(html: str) -> dict[str, int]:
    """Extract {player-url-slug: rank} from a rendered ATP rankings page."""
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
    result: dict[str, int] = {}
    for row in rows:
        rank_m = re.search(r'class="rank bold[^"]*"[^>]*>(\d+)', row)
        slug_m = re.search(r'/en/players/([a-z0-9\-]+)/[a-z0-9]+/overview', row)
        if rank_m and slug_m:
            result[slug_m.group(1)] = int(rank_m.group(1))
    return result


def wait_for_render(page, timeout_ms: int = 30_000) -> bool:
    """Block until the date dropdown is populated AND the rankings table has
    rendered rows. Returns True once both are present, False on timeout.

    The page is server-rendered but the dropdown + historical table are filled
    in by JS, so a fixed sleep races the render and occasionally sees an empty
    page (which used to abort the whole CI run). Waiting on the actual DOM state
    is both faster and far more reliable."""
    try:
        page.wait_for_function(
            """() => {
                const sel = document.getElementById('dateWeek-filter');
                const hasDates = sel && sel.options.length > 1;
                const hasRows  =
                    document.querySelectorAll('a[href*="/overview"]').length > 5;
                return hasDates && hasRows;
            }""",
            timeout=timeout_ms,
        )
        return True
    except PWTimeout:
        return False


def get_rank(key: str, slug_ranks: dict[str, int]) -> int:
    for slug, rank in slug_ranks.items():
        if key in slug:
            return rank
    return PENALTY_RANK


def euclidean_distance(preds: list[tuple[str, int]],
                       slug_ranks: dict[str, int]) -> float:
    return round(math.sqrt(
        sum((pred - min(get_rank(key, slug_ranks), PENALTY_RANK)) ** 2
            for key, pred in preds)
    ), 4)


# ── scraper ───────────────────────────────────────────────────────────────────

def scrape_all_weeks() -> list[dict]:
    weeks: list[dict] = []
    all_keys = {key for preds in PREDICTIONS.values() for key, _ in preds}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        # keep per-action waits short so a slow/blocked page fails fast instead
        # of stalling the whole run (CI runs used to balloon to ~20 min)
        page.set_default_timeout(20_000)

        # ── initial load ──────────────────────────────────────────────────────
        # retry the load a few times: the dropdown + table are JS-rendered and
        # occasionally aren't ready yet, which would otherwise leave us with an
        # empty dropdown and abort the entire run.
        print("  loading atp rankings page …")
        for attempt in range(1, 4):
            page.goto(ATP_URL, wait_until="domcontentloaded", timeout=30_000)
            if wait_for_render(page):
                break
            print(f"    page not rendered yet (attempt {attempt}/3), retrying …")
            time.sleep(3)
        else:
            print("  page never rendered (empty dropdown/table after 3 attempts)")
            browser.close()
            return weeks   # empty → main() exits non-zero and CI fails loudly

        # ── collect 2026 dates from the date dropdown ──────────────────────
        dates_2026: list[str] = page.evaluate("""() => {
            const sel = document.getElementById('dateWeek-filter');
            if (!sel) return [];
            return Array.from(sel.options)
                .map(o => o.value)
                .filter(v => v.startsWith('2026-'));
        }""")

        # also grab "Current Week" if it falls in 2026
        current_label: str = page.evaluate("""() => {
            const sel = document.getElementById('dateWeek-filter');
            if (!sel) return '';
            const curr = Array.from(sel.options).find(o => o.value === 'Current Week');
            return curr ? curr.value : (sel.options[0] ? sel.options[0].value : '');
        }""")

        # normalize: "Current Week" → use today's date label
        today_label = datetime.now().strftime("%Y-%m-%d")
        if current_label == "Current Week":
            current_label = today_label

        print(f"  2026 dates in dropdown: {dates_2026}")

        def record_week(date_label: str):
            html = page.content()
            slug_ranks = parse_rankings(html)
            if not slug_ranks:
                print(f"    WARNING: no data parsed for {date_label}")
                return
            actuals   = {k: get_rank(k, slug_ranks) for k in all_keys}
            distances = {name: euclidean_distance(preds, slug_ranks)
                         for name, preds in PREDICTIONS.items()}
            leader    = min(distances, key=distances.get)
            top3 = list(slug_ranks.items())[:3]
            print(f"    {date_label}: top3={[s for _,s in [(v,k) for k,v in sorted(slug_ranks.items(), key=lambda x: x[1])[:3]]]}  → {leader} leads")
            weeks.append({"date": date_label, "distances": distances, "actuals": actuals})

        # ── record current week first ─────────────────────────────────────────
        # figure out which date is currently selected
        selected_value: str = page.evaluate("""() => {
            const sel = document.getElementById('dateWeek-filter');
            return sel ? sel.value : '';
        }""")
        # "Current Week" or a date string
        if selected_value == "Current Week":
            current_date_str = today_label
        else:
            current_date_str = selected_value if selected_value.startswith("2026-") else today_label

        print(f"  selected in dropdown: '{selected_value}' → labeling as {current_date_str}")
        record_week(current_date_str)

        # ── iterate over historical 2026 dates ────────────────────────────────
        for date_str in sorted(dates_2026):
            if date_str == current_date_str:
                continue  # already recorded
            print(f"  selecting {date_str} …")
            try:
                page.select_option('#dateWeek-filter', value=date_str)
                time.sleep(4)   # wait for JS to reload rankings
                record_week(date_str)
            except PWTimeout:
                print(f"    TIMEOUT for {date_str}")
            except Exception as e:
                print(f"    ERROR for {date_str}: {e}")

        browser.close()

    return sorted(weeks, key=lambda w: w["date"])


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("── updating atp rankings data ──")

    weeks = scrape_all_weeks()
    if not weeks:
        # exit non-zero so the scheduled job fails LOUDLY instead of silently
        # leaving stale data in place (e.g. when the page is blocked / changed).
        print("no data collected — failing so the freeze is visible")
        sys.exit(1)

    # merge with existing data so weeks that drop out of the ATP dropdown
    # are not silently lost on the next run
    path = os.path.join("data", "rankings.json")
    existing: dict[str, dict] = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                old = json.load(f)
            existing = {w["date"]: w for w in old.get("weeks", [])}
        except Exception:
            pass

    merged = {**existing, **{w["date"]: w for w in weeks}}
    weeks = sorted(merged.values(), key=lambda w: w["date"])

    output = {
        "updated":      datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "penalty_rank": PENALTY_RANK,
        "predictions": {
            name: [{"player": DISPLAY_NAMES.get(k, k), "predicted_rank": r}
                   for k, r in preds]
            for name, preds in PREDICTIONS.items()
        },
        "players": {k: DISPLAY_NAMES.get(k, k) for k in
                    {k for preds in PREDICTIONS.values() for k, _ in preds}},
        "weeks": weeks,
    }

    os.makedirs("data", exist_ok=True)
    with open(path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ wrote {len(weeks)} weeks → {path}")
    print(f"  range: {weeks[0]['date']} → {weeks[-1]['date']}")


if __name__ == "__main__":
    main()
