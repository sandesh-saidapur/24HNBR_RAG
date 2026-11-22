"""Attach race context to every media item.

Inputs : data/processed/media_race_clock.parquet      (race time, phase)
         data/processed/media_track_match.parquet     (nearest course section)
         data/processed/hourly_standings.parquet      (running order per split)
         data/processed/official_classification.parquet
Output : data/processed/media_context.parquet

For each item, the context is the latest hourly split at or before its race time,
which gives that split's leader, the number of cars running, and the car count.
Splits are cut at whole race hours (1h, 3h, ... 23h), so the lag is at most 2 h.
A photo before the first split (before 1 h) has no split context.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
CLOCK = ROOT / "data/processed/media_race_clock.parquet"
MATCH = ROOT / "data/processed/media_track_match.parquet"
STANDINGS = ROOT / "data/processed/hourly_standings.parquet"
CLASSIFICATION = ROOT / "data/processed/official_classification.parquet"
OUT = ROOT / "data/processed/media_context.parquet"


def main() -> None:
    clock = {r["file"]: r for r in pq.read_table(CLOCK).to_pylist()}
    match = {r["file"]: r for r in pq.read_table(MATCH).to_pylist()}
    standings = pq.read_table(STANDINGS).to_pylist()
    classes = {r["car_number"]: r for r in pq.read_table(CLASSIFICATION).to_pylist()}

    by_hour: dict[int, list[dict]] = {}
    for r in standings:
        by_hour.setdefault(r["hour"], []).append(r)
    hours = sorted(by_hour)

    cols: dict[str, list] = {k: [] for k in [
        "file", "phase", "race_elapsed_s", "split_hour", "leader_car", "leader_team",
        "cars_in_split", "leader_laps", "nearest_section", "distance_m", "on_course",
    ]}
    for f, c in clock.items():
        t = c["race_elapsed_s"]
        usable = [h for h in hours if h * 3600 <= t]
        split_hour = usable[-1] if usable else None
        leader = leader_team = None
        leader_laps = cars = None
        if split_hour is not None:
            rows = by_hour[split_hour]
            top = min(rows, key=lambda r: r["overall_rank"])
            leader = top["car_number"]
            leader_team = classes.get(leader, {}).get("team")
            leader_laps = top["laps"]
            cars = len(rows)
        m = match.get(f, {})
        cols["file"].append(f)
        cols["phase"].append(c["phase"])
        cols["race_elapsed_s"].append(t)
        cols["split_hour"].append(split_hour)
        cols["leader_car"].append(leader)
        cols["leader_team"].append(leader_team)
        cols["cars_in_split"].append(cars)
        cols["leader_laps"].append(leader_laps)
        cols["nearest_section"].append(m.get("nearest_section"))
        cols["distance_m"].append(m.get("distance_m"))
        cols["on_course"].append(m.get("on_course"))

    pq.write_table(pa.table(cols), OUT)
    with_ctx = sum(1 for h in cols["split_hour"] if h is not None)
    print(f"media items: {len(cols['file'])}; with split context: {with_ctx}; wrote {OUT.name}")
    for i in range(0, len(cols["file"]), max(1, len(cols["file"]) // 6)):
        print(f"  {cols['file'][i]}: t={cols['race_elapsed_s'][i]/3600:5.2f}h split={cols['split_hour'][i]}h "
              f"leader=#{cols['leader_car'][i]} ({cols['leader_team'][i]}) section={cols['nearest_section'][i]}")


if __name__ == "__main__":
    main()
