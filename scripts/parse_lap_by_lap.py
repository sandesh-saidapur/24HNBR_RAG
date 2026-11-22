"""Parse the official lap-by-lap PDF into one row per car per lap.

Input : data/raw/official_timing/lapbylap.pdf   (organiser, wige SOLUTIONS)
Output: data/processed/lap_by_lap.parquet

Each car block starts with "<car number> <team>". Each lap is a time followed by
a label: "N(driver)" for a normal lap, "pit(driver)" for a lap that ended in the
pit. Laps are read in order, so the lap index is the position in the block.
Checks: lap count per car against the classification, and the sum of lap times
against the official total time.
"""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/official_timing/lapbylap.pdf"
CLASSIFICATION = ROOT / "data/raw/official_timing/race_classification_2026.csv"
OUT = ROOT / "data/processed/lap_by_lap.parquet"

CAR_HEAD = re.compile(r"^\s{0,4}(\d{1,3})\s+(?:\d{1,3}\s+)?[A-Za-zÄÖÜäöüß]")
LAP = re.compile(r"(\d{1,2}:\d{2}\.\d{3}|\d{1,2}:\d{2}:\d{2}\.\d{3})\s+(\d+|pit)\((\d+)\)")


def to_seconds(t: str) -> float:
    parts = t.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return int(parts[0]) * 60 + float(parts[1])


def parse_text(text: str) -> dict[str, list[tuple[float, bool, int]]]:
    cars: dict[str, list[tuple[float, bool, int]]] = {}
    current: str | None = None
    for line in text.splitlines():
        head = CAR_HEAD.match(line)
        if head and not re.match(r"^\s*\d{1,2}:\d{2}", line):
            current = head.group(1)
            cars.setdefault(current, [])
            continue
        if current is None:
            continue
        for m in LAP.finditer(line):
            cars[current].append((to_seconds(m.group(1)), m.group(2) == "pit", int(m.group(3))))
    return cars


def main() -> None:
    text = subprocess.run(["pdftotext", "-layout", str(PDF), "-"],
                          capture_output=True, text=True, check=True).stdout
    cars = parse_text(text)
    cls = {r["car_number"]: r for r in csv.DictReader(CLASSIFICATION.open(encoding="utf-8"))}

    cols: dict[str, list] = {k: [] for k in ["car_number", "lap", "lap_time_s", "pit_lap", "driver_index", "cum_time_s"]}
    issues = []
    for car, laps in cars.items():
        cum = 0.0
        for i, (t, pit, drv) in enumerate(laps, start=1):
            cum += t
            cols["car_number"].append(car)
            cols["lap"].append(i)
            cols["lap_time_s"].append(t)
            cols["pit_lap"].append(pit)
            cols["driver_index"].append(drv)
            cols["cum_time_s"].append(cum)
        row = cls.get(car)
        if row is None:
            issues.append((car, "not in classification"))
            continue
        if row["laps"].strip() and int(row["laps"]) != len(laps):
            issues.append((car, f"laps parsed {len(laps)} vs classified {row['laps']}"))
        if row["total_time"].strip():
            total = to_seconds(row["total_time"].strip())
            if abs(cum - total) > 0.5 and int(row["laps"] or 0) == len(laps):
                issues.append((car, f"sum {cum:.3f}s vs official {total:.3f}s"))

    pq.write_table(pa.table(cols), OUT)
    print(f"cars parsed: {len(cars)}; lap rows: {len(cols['lap'])}; wrote {OUT.name}")
    print(f"issues: {len(issues)}")
    for i in issues[:25]:
        print("  ", i)


if __name__ == "__main__":
    main()
