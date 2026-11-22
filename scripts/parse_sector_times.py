"""Parse the organiser's sector-times PDF into one row per car per lap.

Input : data/raw/official_timing/sector times.pdf (wige SOLUTIONS, 633 pages)
Output: data/processed/sector_laps.parquet

Car block header: "<car number>  <driver names>  <car model>  theoretical besttime".
Lap row: "<lap> <driver index> <lap time> S1 V1 S2 V2 ... S8 V8 S9".
Speeds (V1-V8) are the speed-trap values in km/h. Sector 9 has no speed value.
Check: each lap time must equal the lap time in lap_by_lap.parquet for the same car and lap.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/official_timing/sector times.pdf"
OUT = ROOT / "data/processed/sector_laps.parquet"

HEADER = re.compile(r"^\s*(\d{1,3})\s{2,}\S.*theoretical besttime")
TIME = r"(?:\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3}|\d{1,2}\.\d{3}|\d{1,3}\.\d{3})"
LAP_ROW = re.compile(rf"^\s*(\d{{1,3}})\s+(\d)\s+({TIME})\s+(.*)$")


def to_seconds(t: str) -> float:
    parts = t.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(parts[0])


def main() -> None:
    text = subprocess.run(["pdftotext", "-layout", str(PDF), "-"],
                          capture_output=True, text=True, check=True).stdout
    cols: dict[str, list] = {k: [] for k in ["car_number", "lap", "driver_index", "lap_time_s"]}
    for i in range(1, 10):
        cols[f"s{i}_s"] = []
    for i in range(1, 9):
        cols[f"v{i}_kmh"] = []
    car = None
    rows = 0
    for line in text.splitlines():
        h = HEADER.match(line)
        if h:
            car = h.group(1)
            continue
        if car is None:
            continue
        m = LAP_ROW.match(line)
        if not m:
            continue
        lap, drv, lap_time, rest = m.group(1), m.group(2), m.group(3), m.group(4)
        tokens = rest.replace("#", " ").split()
        times = [t for t in tokens if re.fullmatch(TIME, t)]
        ints = [t for t in tokens if re.fullmatch(r"\d{2,3}", t)]
        if len(times) < 9 or len(ints) < 8:
            continue
        sectors = [to_seconds(t) for t in times[:9]]
        speeds = [int(v) for v in ints[:8]]
        cols["car_number"].append(car)
        cols["lap"].append(int(lap))
        cols["driver_index"].append(int(drv))
        cols["lap_time_s"].append(to_seconds(lap_time))
        for i in range(9):
            cols[f"s{i+1}_s"].append(sectors[i])
        for i in range(8):
            cols[f"v{i+1}_kmh"].append(speeds[i])
        rows += 1
    pq.write_table(pa.table(cols), OUT)
    print(f"car blocks seen; lap rows parsed: {rows}; wrote {OUT.name}")


if __name__ == "__main__":
    main()
