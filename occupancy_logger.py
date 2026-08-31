#!/usr/bin/env python3
"""
VT RecSports Facility Occupancy Logger
========================================
Polls https://connect.recsports.vt.edu/facilityoccupancy (a public page --
no login needed) and appends one row per facility to a CSV log, so you can
later analyze trends and figure out the best time to hit the gym.

Meant to run on a schedule (e.g. GitHub Actions, every 30 min) -- see
README.md. It's a single lightweight GET request to a public page, so it's
safe to run this often.

Design choices:
- Everything is computed in America/New_York time regardless of what
  timezone the machine running this is in (important for GitHub Actions,
  which runs in UTC, and for daylight saving transitions).
- Tracks weekdays only, open-to-close, per the original spec -- weekends
  are skipped by default (flip WEEKEND_ENABLED below if you want them too).
- Skips anything outside each day's configured operating window.
- Skips any date listed in excluded_dates.txt (holidays/breaks), so those
  don't skew trend data.
- Fails loudly but harmlessly if the site is down or its HTML changes --
  it just skips that run rather than logging bad data.
"""
import csv
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

URL = "https://connect.recsports.vt.edu/facilityoccupancy"
LOCAL_TZ = ZoneInfo("America/New_York")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "occupancy_log.csv")
EXCLUDED_DATES_FILE = os.path.join(SCRIPT_DIR, "excluded_dates.txt")

# Set True if you want Saturday/Sunday tracked too (McComas is open
# weekends). Default is weekdays only, per the original spec.
WEEKEND_ENABLED = False

# Operating window per weekday, 24h local (America/New_York) time.
# 0=Monday ... 6=Sunday. Set a day to None to always skip it.
# These are approximate McComas Hall hours -- verify at
# https://recsports.vt.edu/facilities/mccomas.html and adjust for War
# Memorial Hall / Esports / Bouldering Wall if their hours differ, since
# this script currently applies ONE window to all facilities on the page.
OPERATING_HOURS = {
    0: ("05:00", "23:59"),  # Monday
    1: ("05:00", "23:59"),  # Tuesday
    2: ("05:00", "23:59"),  # Wednesday
    3: ("05:00", "23:59"),  # Thursday
    4: ("05:00", "23:59"),  # Friday
    5: ("08:00", "22:00") if WEEKEND_ENABLED else None,  # Saturday
    6: ("10:00", "23:59") if WEEKEND_ENABLED else None,  # Sunday
}


def load_excluded_dates():
    if not os.path.exists(EXCLUDED_DATES_FILE):
        return set()
    with open(EXCLUDED_DATES_FILE) as f:
        return {
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        }


def within_operating_hours(now):
    window = OPERATING_HOURS.get(now.weekday())
    if window is None:
        return False
    start = datetime.strptime(window[0], "%H:%M").time()
    end = datetime.strptime(window[1], "%H:%M").time()
    return start <= now.time() <= end


def fetch_occupancy():
    resp = requests.get(
        URL,
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0 (personal gym-occupancy logger; contact: arins@vt.edu)"},
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # The page renders the timestamp its numbers came from into #last-update
    # (e.g. "2:56 PM"). The occupancy figures are a snapshot, not live at
    # request time, so log this too -- it's the only way to tell a genuinely
    # unchanged reading apart from two polls that hit the same stale snapshot.
    last_el = soup.select_one("#last-update")
    last_update = last_el.get_text(strip=True) if last_el else ""

    results = []
    for card in soup.select(".occupancy-card"):
        name_el = card.select_one("h2 strong")
        hidden_el = card.select_one(".visually-hidden")
        if not name_el or not hidden_el:
            continue
        name = name_el.get_text(strip=True)
        text = hidden_el.get_text(strip=True)
        # text looks like: "Max Occupancy: 1200, Current Occupancy: 36%"
        try:
            max_part, cur_part = text.split(",")
            max_occ = int(max_part.split(":")[1].strip())
            cur_pct = int(cur_part.split(":")[1].strip().rstrip("%"))
        except (ValueError, IndexError):
            continue
        results.append({"facility": name, "max_occupancy": max_occ, "current_pct": cur_pct})
    return results, last_update


def main():
    now = datetime.now(LOCAL_TZ)
    today_str = now.strftime("%Y-%m-%d")

    if today_str in load_excluded_dates():
        print(f"{today_str} is in excluded_dates.txt (holiday/break) -- skipping.")
        return

    if not within_operating_hours(now):
        print(f"{now.strftime('%a %H:%M %Z')} is outside configured operating hours -- skipping.")
        return

    try:
        rows, last_update = fetch_occupancy()
    except requests.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return

    if not rows:
        print("No occupancy data parsed -- page structure may have changed.", file=sys.stderr)
        return

    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                ["timestamp", "date", "weekday", "time", "facility",
                 "max_occupancy", "current_pct", "estimated_count",
                 "source_updated_at"]
            )
        for row in rows:
            est_count = round(row["max_occupancy"] * row["current_pct"] / 100)
            writer.writerow([
                now.isoformat(timespec="seconds"),
                today_str,
                now.strftime("%A"),
                now.strftime("%H:%M"),
                row["facility"],
                row["max_occupancy"],
                row["current_pct"],
                est_count,
                last_update,
            ])

    print(f"Logged {len(rows)} facilities at {now.isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
