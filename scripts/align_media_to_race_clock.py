"""Align each media item to the race clock and to a trackside cluster.

Reads data/processed/media_catalog.parquet and configs/race_calendar.yaml.
Writes data/processed/media_race_clock.parquet.

Race time uses the verified start (race_start) and finish (race_finish) from the
official schedule. No red flags are recorded for 2026, so elapsed time is
wall-clock time from the start.
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/processed/media_catalog.parquet"
CALENDAR = ROOT / "configs/race_calendar.yaml"
OUT = ROOT / "data/processed/media_race_clock.parquet"
CIRCUIT_CENTRE = (50.33556, 6.94750)  # Wikipedia coordinates, unverified; used only for distance labels
CLUSTER_METRES = 200.0


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def cluster(points: list[tuple[float, float]], threshold_km: float) -> list[int]:
    parent = list(range(len(points)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if haversine_km(points[i], points[j]) <= threshold_km:
                parent[find(i)] = find(j)
    roots: dict[int, int] = {}
    labels: list[int] = []
    for i in range(len(points)):
        root = find(i)
        roots.setdefault(root, len(roots) + 1)
        labels.append(roots[root])
    return labels


def main() -> None:
    cal = yaml.safe_load(CALENDAR.read_text(encoding="utf-8"))["schedule"]
    start = datetime.fromisoformat(cal["race_start"])
    finish = datetime.fromisoformat(cal["race_finish"])
    race_len_s = (finish - start).total_seconds()

    rows = pq.read_table(CATALOG).to_pylist()
    coords = [(r["latitude"], r["longitude"]) for r in rows]
    labels = cluster(coords, CLUSTER_METRES / 1000.0)

    out: dict[str, list] = {k: [] for k in [
        "file", "media_type", "capture_utc", "race_elapsed_s", "phase",
        "latitude", "longitude", "cluster_id", "dist_from_centre_km",
    ]}
    for r, label in zip(rows, labels, strict=True):
        t = datetime.fromisoformat(r["capture_utc"])
        elapsed = (t - start).total_seconds()
        if elapsed < 0:
            phase = "pre_start"
        elif elapsed <= race_len_s:
            phase = "race"
        else:
            phase = "post_finish"
        out["file"].append(r["file"])
        out["media_type"].append(r["media_type"])
        out["capture_utc"].append(t)
        out["race_elapsed_s"].append(elapsed)
        out["phase"].append(phase)
        out["latitude"].append(r["latitude"])
        out["longitude"].append(r["longitude"])
        out["cluster_id"].append(label)
        out["dist_from_centre_km"].append(
            haversine_km((r["latitude"], r["longitude"]), CIRCUIT_CENTRE)
        )

    table = pa.table(out)
    pq.write_table(table, OUT)
    phases = {p: out["phase"].count(p) for p in set(out["phase"])}
    print(f"wrote {OUT.name}: {table.num_rows} rows, phases={phases}")
    print(f"race length (s): {race_len_s:.0f}")
    for c in sorted(set(labels)):
        idx = [i for i, x in enumerate(labels) if x == c]
        el = [out["race_elapsed_s"][i] for i in idx]
        print(f"cluster {c}: n={len(idx)} elapsed {min(el)/3600:.2f}h..{max(el)/3600:.2f}h "
              f"dist_centre~{sum(out['dist_from_centre_km'][i] for i in idx)/len(idx):.2f}km")


if __name__ == "__main__":
    main()
