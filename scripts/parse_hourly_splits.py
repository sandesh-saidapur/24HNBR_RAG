"""Parse the organiser's hourly split PDFs into one table of car standings per hour.

Inputs : data/raw/official_timing/hr<N>.pdf (after N hours, by class)
         data/raw/official_timing/split after 3hr.pdf (after 3 hours, overall)
Output : data/processed/hourly_standings.parquet

Each car row ends with: laps, total elapsed time, best lap, lap of best lap.
Car number is the second token; the first token is the position in its class.
Overall rank per hour is derived from laps (desc) then elapsed time (asc), the
same rule the final classification uses.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/raw/official_timing"
OUT = ROOT / "data/processed/hourly_standings.parquet"

ROW = re.compile(
    r"^\s*(\d{1,3})\s+(\d{1,3})\s+\S.*?\s(\d{1,3})\s+"
    r"(\d{1,3}:\d{2}:\d{2}\.\d{3}|\d{1,3}:\d{2}\.\d{3})\s+"
    r"(\d{1,2}:\d{2}\.\d{3})\s+(\d+)\s*$"
)


def to_seconds(t: str) -> float:
    parts = t.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return int(parts[0]) * 60 + float(parts[1])


def parse_pdf(path: Path) -> list[dict]:
    text = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                          capture_output=True, text=True, check=True).stdout
    rows = []
    for line in text.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        rows.append({
            "class_position": int(m.group(1)),
            "car_number": m.group(2),
            "laps": int(m.group(3)),
            "elapsed_s": to_seconds(m.group(4)),
        })
    return rows


def hour_of(name: str) -> int:
    m = re.search(r"hr(\d+)", name) or re.search(r"after\s+(\d+)hr", name)
    return int(m.group(1))


def main() -> None:
    files = sorted(list(DIR.glob("hr*.pdf")) + list(DIR.glob("split after 3hr.pdf")), key=lambda p: hour_of(p.name))
    cols: dict[str, list] = {k: [] for k in ["hour", "car_number", "overall_rank", "class_position",
                                             "laps", "elapsed_s", "classified_in_split"]}
    for f in files:
        hour = hour_of(f.name)
        rows = parse_pdf(f)
        rows.sort(key=lambda r: (-r["laps"], r["elapsed_s"]))
        for rank, r in enumerate(rows, start=1):
            cols["hour"].append(hour)
            cols["car_number"].append(r["car_number"])
            cols["overall_rank"].append(rank)
            cols["class_position"].append(r["class_position"])
            cols["laps"].append(r["laps"])
            cols["elapsed_s"].append(r["elapsed_s"])
            cols["classified_in_split"].append(True)
        print(f"{f.name:28s} hour {hour:2d}: {len(rows)} car rows")
    pq.write_table(pa.table(cols), OUT)
    print(f"wrote {OUT.name}: {len(cols['hour'])} rows")


if __name__ == "__main__":
    main()
