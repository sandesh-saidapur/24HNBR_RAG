"""Extract timed penalty and disqualification entries from the organiser's summary PDFs.

Inputs : data/raw/official_timing/News and quotes after *.pdf (and 'from the Night',
         'after the finish'), read in full.
Output : data/processed/penalties.parquet

Each entry starts with a clock time ("16:36", "3:38 p.m.", "8:10 p.m."). The clock
time maps to exactly one race time in the 24 h window 15:00 16 May to 15:00 17 May,
so race_elapsed_s is (clock - 15:00) modulo 24 h. Car numbers come from "#NN" in the
text when present. Otherwise they are matched to surnames in the classification.
"""

from __future__ import annotations

import csv
import glob
import re
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/raw/official_timing"
CLASSIFICATION = DIR / "race_classification_2026.csv"
OUT = ROOT / "data/processed/penalties.parquet"

ENTRY = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*(a\.m\.|p\.m\.)?\s*(?:–|-)\s*(.*)$")
SECONDS = re.compile(r"(\d+)[- ]?second", re.I)
KIND = re.compile(r"(disqualif|permit|withdrawn|stop-and-go|time penalty|penalt|drive-through|speeding|overtak|too fast|minimum pit)", re.I)


def clock_to_race_s(h: int, m: int, ampm: str | None) -> float:
    if ampm:
        h = h % 12 + (12 if ampm.lower().startswith("p") else 0)
    minutes = (h * 60 + m) - (15 * 60)
    return float((minutes % (24 * 60)) * 60)


def main() -> None:
    cls = list(csv.DictReader(CLASSIFICATION.open(encoding="utf-8")))
    surnames = {}
    for r in cls:
        for name in re.split(r";", r["drivers"]):
            surname = name.strip().split(" ")[0]
            surnames.setdefault(surname.lower(), set()).add(r["car_number"])

    entries = []
    files = [f for f in glob.glob(str(DIR / "*.pdf")) if Path(f).name.lower().startswith(("news and quotes", "news and quotes from", "news and quotes after"))]
    for f in sorted(files):
        text = subprocess.run(["pdftotext", "-layout", f, "-"], capture_output=True, text=True, check=True).stdout
        current = None
        for line in text.splitlines():
            m = ENTRY.match(line)
            if m:
                if current:
                    entries.append(current)
                current = {"src": Path(f).name, "clock": f"{m.group(1)}:{m.group(2)}", "h": int(m.group(1)),
                           "m": int(m.group(2)), "ampm": m.group(3), "text": m.group(4).strip()}
            elif current and line.strip() and not line.strip().startswith(("Second-placed",)):
                current["text"] += " " + line.strip()
            elif current and not line.strip():
                entries.append(current)
                current = None
        if current:
            entries.append(current)

    seen = set()
    cols: dict[str, list] = {k: [] for k in ["source_file", "clock", "race_elapsed_s", "car_number_hint", "penalty_seconds", "text"]}
    for e in entries:
        if not (SECONDS.search(e["text"]) or re.search(r"disqualif|withdrawn", e["text"], re.I)):
            continue
        if not KIND.search(e["text"]):
            continue
        key = (e["clock"], e["text"][:80])
        if key in seen:
            continue
        seen.add(key)
        cars = re.findall(r"#(\d{1,3})", e["text"])
        if not cars:
            hits = set()
            for word in re.findall(r"[A-ZÄÖÜ][a-zäöüß]+", e["text"]):
                hits |= surnames.get(word.lower(), set())
            cars = sorted(hits) if len(hits) == 1 else []
        secs = [int(x) for x in SECONDS.findall(e["text"])]
        cols["source_file"].append(e["src"])
        cols["clock"].append(e["clock"] + ("" if not e["ampm"] else " " + e["ampm"]))
        cols["race_elapsed_s"].append(clock_to_race_s(e["h"], e["m"], e["ampm"]))
        cols["car_number_hint"].append(cars[0] if cars else None)
        cols["penalty_seconds"].append(sum(secs) if secs else None)
        cols["text"].append(e["text"][:400])

    pq.write_table(pa.table(cols), OUT)
    n = len(cols["text"])
    with_car = sum(1 for c in cols["car_number_hint"] if c)
    secs_total = sum(s for s in cols["penalty_seconds"] if s)
    print(f"penalty entries: {n}; with car number: {with_car}; total penalty seconds listed: {secs_total}")
    for i in range(min(8, n)):
        print(f"  {cols['clock'][i]:>10}  car={cols['car_number_hint'][i]}  s={cols['penalty_seconds'][i]}  {cols['text'][i][:110]}")


if __name__ == "__main__":
    main()
