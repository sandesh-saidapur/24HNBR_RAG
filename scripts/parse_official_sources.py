"""Parse the organiser's own race files (wige timing service) into typed tables.

Inputs (data/raw/official_timing/):
  official_penalties/539_24h_Race_Penalty_List_Final.pdf   Strafliste (car numbers given)
  official_csv_wige/534_*RESULT.CSV                          result per car (GESAMTZEIT etc.)
  official_csv_wige/535_*SEKTORZEITEN.CSV                    sector times per car per lap
Outputs (data/processed/):
  official_penalties.parquet, official_sectors.parquet, official_reconciliation.parquet
"""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/official_timing"
OUT = ROOT / "data/processed"
PENALTY_PDF = next((RAW / "official_penalties").glob("539_*.pdf"))
RESULT_CSV = next((RAW / "official_csv_wige").glob("534_*.CSV"))
SECTOR_CSV = next((RAW / "official_csv_wige").glob("535_*.CSV"))


def to_seconds(text: str) -> float | None:
    """'1:27.000' -> 87.0, '8:34.000' -> 514.0, '24:12:06.213' -> 87126.213."""
    text = text.strip()
    if not text or text in {"00.000", "0.000"}:
        return 0.0 if text else None
    parts = text.split(":")
    total = 0.0
    for part in parts:
        total = total * 60 + float(part)
    return total


def parse_penalties() -> list[dict]:
    raw = subprocess.run(
        ["pdftotext", "-layout", str(PENALTY_PDF), "-"],
        check=True, capture_output=True, text=True,
    ).stdout
    rows: list[dict] = []
    row_re = re.compile(r"^\s{1,8}(\d{1,3})\s+((?:\d+:)?\d+\.\d{3})\s+(\S.*)$")
    for line in raw.splitlines():
        m = row_re.match(line)
        if m:
            car, amount, text = m.groups()
            rows.append({"car_number": int(car), "penalty_text_raw": amount, "text": text.strip()})
        elif rows and line.strip() and line.startswith(" " * 15):
            rows[-1]["text"] += " " + line.strip()
    out = []
    for r in rows:
        text = r["text"]
        decision = re.search(r"Steward Decision no\.\s*(\d+)", text)
        if "replacement penalty" in text:
            kind = "time_replacement"
        elif "Stop-and-Go" in text:
            kind = "stop_and_go"
        elif "Disqualif" in text:
            kind = "disqualification_related"
        elif "Exceeding of power limits" in text:
            kind = "technical_inspection"
        else:
            kind = "other"
        out.append({
            "car_number": r["car_number"],
            "penalty_seconds": to_seconds(r["penalty_text_raw"]) or 0.0,
            "kind": kind,
            "steward_decision_no": int(decision.group(1)) if decision else None,
            "offence_verbatim": text,
            "source_file": PENALTY_PDF.name,
        })
    return out


def read_semicolon_csv(path: Path) -> list[dict]:
    with path.open(encoding="cp1252", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def parse_sectors(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        rec = {
            "car_number": int(r["STNR"]),
            "lap": int(r["RUNDE_NR"]),
            "lap_time_s": to_seconds(r["RUNDENZEIT"]) if r["RUNDENZEIT"] else None,
        }
        for n in range(1, 10):
            v = r.get(f"SEKTOR{n}_ZEIT", "").strip()
            rec[f"s{n}_s"] = to_seconds(v) if v else None
        for n in range(1, 9):
            v = r.get(f"SEKTOR{n}_KMH", "").strip()
            rec[f"v{n}_kmh"] = float(v.replace(",", ".")) if v else None
        out.append(rec)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    penalties = parse_penalties()
    result = read_semicolon_csv(RESULT_CSV)
    sector_raw = read_semicolon_csv(SECTOR_CSV)
    sectors = parse_sectors(sector_raw)

    # Result: official total per car and number of laps.
    official = {}
    for r in result:
        car = int(r["STNR"])
        official[car] = {"total_s": to_seconds(r["GESAMTZEIT"]), "laps": int(r["RUNDEN"] or 0),
                         "name": r["KUERZEL"].strip()}

    # Sector sums vs lap time (tolerance 0.5 s).
    sum_mismatch: dict[int, int] = {}
    per_car_lap_sum: dict[int, float] = {}
    per_car_laps: dict[int, int] = {}
    for s in sectors:
        if None not in [s[f"s{n}_s"] for n in range(1, 10)] and s["lap_time_s"] is not None:
            total = sum(s[f"s{n}_s"] for n in range(1, 10))
            if abs(total - s["lap_time_s"]) > 0.5:
                sum_mismatch[s["car_number"]] = sum_mismatch.get(s["car_number"], 0) + 1
        if s["lap_time_s"] is not None:
            car = s["car_number"]
            per_car_lap_sum[car] = per_car_lap_sum.get(car, 0.0) + s["lap_time_s"]
            per_car_laps[s["car_number"]] = per_car_laps.get(s["car_number"], 0) + 1

    penalty_by_car: dict[int, float] = {}
    for p in penalties:
        car = p["car_number"]
        penalty_by_car[car] = penalty_by_car.get(car, 0.0) + p["penalty_seconds"]

    recon = []
    for car, o in sorted(official.items()):
        lap_sum = per_car_lap_sum.get(car)
        diff = None if lap_sum is None or o["total_s"] is None else round(lap_sum - o["total_s"], 3)
        recon.append({
            "car_number": car,
            "official_laps": o["laps"],
            "csv_laps_with_time": per_car_laps.get(car, 0),
            "official_total_s": o["total_s"],
            "sum_of_lap_times_s": None if lap_sum is None else round(lap_sum, 3),
            "lap_sum_minus_total_s": diff,
            "penalty_seconds_listed": penalty_by_car.get(car, 0.0),
            "sector_sum_mismatch_laps": sum_mismatch.get(car, 0),
        })

    pq.write_table(pa.Table.from_pylist(penalties), OUT / "official_penalties.parquet")
    pq.write_table(pa.Table.from_pylist(sectors), OUT / "official_sectors.parquet")
    pq.write_table(pa.Table.from_pylist(recon), OUT / "official_reconciliation.parquet")

    print(f"penalties: {len(penalties)} rows, cars {sorted({p['car_number'] for p in penalties})}")
    print(f"sectors:   {len(sectors)} rows, cars {len({s['car_number'] for s in sectors})}")
    print(f"sector sums over 0.5 s: {sum_mismatch or 'none'}")
    print("cars with lap-sum vs official total off by more than 1 s:")
    for r in recon:
        d = r["lap_sum_minus_total_s"]
        if d is not None and abs(d) > 1:
            print(
                f"  #{r['car_number']:>3} diff={d:>9.3f}s "
                f"penalties={r['penalty_seconds_listed']:>6.1f}s "
                f"laps={r['csv_laps_with_time']}/{r['official_laps']}"
            )


if __name__ == "__main__":
    main()
