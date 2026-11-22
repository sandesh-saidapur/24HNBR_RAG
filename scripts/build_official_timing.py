"""Convert the official classification CSV into a typed parquet table.

Input:  data/raw/official_timing/race_classification_2026.csv
Output: data/processed/official_classification.parquet

Status: transcribed from the official result PDF by text extraction. Internal
consistency is checked here (contiguous positions, 110 classified). It is NOT
yet checked against the PDF itself, so verified_against_pdf is False.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/raw/official_timing/race_classification_2026.csv"
OUT = ROOT / "data/processed/official_classification.parquet"


def to_seconds(value: str) -> float | None:
    """Parse H:MM:SS.mmm or MM:SS.mmm into seconds."""
    value = value.strip()
    if not value:
        return None
    parts = value.split(":")
    try:
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        if len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
    except ValueError:
        return None
    return None


def main() -> None:
    with SRC.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    cols: dict[str, list] = {k: [] for k in [
        "position", "status", "car_number", "class", "team", "car_model",
        "laps", "total_time_s", "best_lap_s", "gap_or_interval", "drivers",
        "verified_against_pdf",
    ]}
    for r in rows:
        pos = r["position"].strip()
        if pos.isdigit():
            position, status = int(pos), "classified"
        else:
            position, status = None, pos
        cols["position"].append(position)
        cols["status"].append(status)
        cols["car_number"].append(r["car_number"].strip())
        cols["class"].append(r["class"].strip())
        cols["team"].append(r["team"].strip() or None)
        cols["car_model"].append(r["car_model"].strip())
        cols["laps"].append(int(r["laps"]) if r["laps"].strip().isdigit() else None)
        cols["total_time_s"].append(to_seconds(r["total_time"]))
        cols["best_lap_s"].append(to_seconds(r["best_lap"]))
        cols["gap_or_interval"].append(r["gap_or_interval"].strip() or None)
        cols["drivers"].append(r["drivers"].strip())
        cols["verified_against_pdf"].append(False)

    classified = [p for p in cols["position"] if p is not None]
    assert classified == list(range(1, len(classified) + 1)), "positions not contiguous"
    assert len(classified) == 110, f"expected 110 classified, got {len(classified)}"
    pq.write_table(pa.table(cols), OUT)
    print(f"wrote {OUT.name}: {len(rows)} rows, classified={len(classified)}, "
          f"not classified={len(rows) - len(classified)}")


if __name__ == "__main__":
    main()
