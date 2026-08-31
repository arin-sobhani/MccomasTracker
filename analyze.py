#!/usr/bin/env python3
"""
Quick trend analysis over occupancy_log.csv.
Run this after you've collected a few weeks of data.
"""
import os
import sys

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "occupancy_log.csv")


def main():
    if not os.path.exists(LOG_FILE):
        print("No occupancy_log.csv yet -- run occupancy_logger.py a bunch first.")
        sys.exit(1)

    # Deliberately NOT parse_dates=["timestamp"]: the logger writes local
    # Eastern timestamps with an offset, so the column mixes -04:00 (EDT) and
    # -05:00 (EST) once the clocks change. pandas hands mixed offsets back as
    # an object column, and .dt.hour then blows up. The CSV already carries
    # the local wall-clock fields we actually want, so just use those.
    df = pd.read_csv(LOG_FILE)
    df["hour"] = df["time"].str.split(":").str[0].astype(int)
    df["weekday_name"] = df["weekday"]

    facilities = df["facility"].unique()
    print(f"Loaded {len(df)} rows across {df['date'].nunique()} days, "
          f"facilities: {', '.join(facilities)}\n")

    for facility in facilities:
        sub = df[df["facility"] == facility]
        print(f"=== {facility} ===")
        print("Average occupancy % by hour:")
        print(sub.groupby("hour")["current_pct"].mean().round(1).to_string())
        print("\nAverage occupancy % by weekday:")
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        by_wd = sub.groupby("weekday_name")["current_pct"].mean().reindex(weekday_order).dropna()
        print(by_wd.round(1).to_string())
        print()

    # Optional heatmap (hour x weekday) per facility, if matplotlib available
    try:
        import matplotlib.pyplot as plt

        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for facility in facilities:
            sub = df[df["facility"] == facility]
            pivot = sub.pivot_table(index="weekday_name", columns="hour",
                                     values="current_pct", aggfunc="mean")
            pivot = pivot.reindex(weekday_order)

            fig, ax = plt.subplots(figsize=(10, 4))
            im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=100)
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index)
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns)
            ax.set_xlabel("Hour of day")
            ax.set_title(f"{facility} -- average occupancy %")
            fig.colorbar(im, ax=ax, label="Occupancy %")
            fig.tight_layout()
            safe_name = facility.replace(" ", "_").replace("/", "-")
            out_path = os.path.join(SCRIPT_DIR, f"heatmap_{safe_name}.png")
            fig.savefig(out_path, dpi=150)
            plt.close(fig)
            print(f"Saved heatmap: {out_path}")
    except ImportError:
        print("(install matplotlib for a heatmap: pip install matplotlib)")


if __name__ == "__main__":
    main()
