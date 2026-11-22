"""Build data/processed/timing.duckdb, the single queryable store for the app and the RAG layer.

Loaded tables (current, verified sources only):
  official_classification   159 cars, status and total time (from the official final result)
  hourly_standings          running order at each hourly split
  official_sectors          sector and lap times per car per lap (organiser CSV 535)
  official_penalties        official Strafliste, with car numbers (organiser list 539)
  official_reconciliation   lap sums vs official totals, with penalties
  media_context             one row per photo/video: race time, split leader, track section
  media_race_clock          capture time and GPS for each media item

Superseded and deliberately NOT loaded: penalties.parquet, sector_laps.parquet and
lap_by_lap.parquet (all parsed from PDFs, replaced by the organiser CSVs).

Views:
  media_timeline   every media item with its capture time, race time, leader, section
  car_summary      one row per car: status, laps, total, penalties, lap-sum gap
"""

from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
DB = PROC / "timing.duckdb"

TABLES = {
    "classification": "official_classification.parquet",
    "hourly_standings": "hourly_standings.parquet",
    "sectors": "official_sectors.parquet",
    "penalties": "official_penalties.parquet",
    "reconciliation": "official_reconciliation.parquet",
    "media_context": "media_context.parquet",
    "media_clock": "media_race_clock.parquet",
}

VIEWS = {
    "media_timeline": """
        SELECT c.file, c.media_type, c.capture_utc, c.latitude, c.longitude,
               c.phase, c.race_elapsed_s, x.split_hour, x.leader_car, x.leader_team,
               x.nearest_section, x.distance_m, x.on_course
        FROM media_clock c
        JOIN media_context x USING (file)
        ORDER BY c.race_elapsed_s
    """,
    "car_summary": """
        SELECT k.*, r.lap_sum_minus_total_s, r.penalty_seconds_listed,
               r.sector_sum_mismatch_laps
        FROM classification k
        LEFT JOIN reconciliation r ON r.car_number = k.car_number
    """,
}


def main() -> None:
    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))
    # Car numbers are stored as integers in every table so joins and API types agree.
    casts = {
        "classification": "* REPLACE (TRY_CAST(car_number AS BIGINT) AS car_number)",
        "hourly_standings": "* REPLACE (TRY_CAST(car_number AS BIGINT) AS car_number)",
        "media_context": "* REPLACE (TRY_CAST(leader_car AS BIGINT) AS leader_car)",
    }
    for name, parquet in TABLES.items():
        select = casts.get(name, "*")
        con.execute(f"CREATE TABLE {name} AS SELECT {select} FROM read_parquet('{PROC / parquet}')")
    for name, sql in VIEWS.items():
        con.execute(f"CREATE VIEW {name} AS {sql}")

    checks = {
        "cars in classification": ("SELECT count(*) FROM classification", 159),
        "penalties loaded": ("SELECT count(*) FROM penalties", 19),
        "sector rows": ("SELECT count(*) FROM sectors", 17201),
        "media items": ("SELECT count(*) FROM media_timeline", 99),
        "on-course media": ("SELECT count(*) FROM media_timeline WHERE on_course", 23),
    }
    failures = []
    for label, (sql, expected) in checks.items():
        got = con.execute(sql).fetchone()[0]
        status = "ok" if got == expected else "FAIL"
        print(f"{status:4} {label}: {got} (expected {expected})")
        if got != expected:
            failures.append(label)

    # Each car's lap rows must equal its official lap count (the classification "laps" column).
    bad_laps = con.execute("""
        SELECT count(*) FROM (
            SELECT k.car_number, k.laps, count(s.lap) AS n
            FROM classification k LEFT JOIN sectors s USING (car_number)
            GROUP BY k.car_number, k.laps
        ) g WHERE g.n <> g.laps
    """).fetchone()[0]
    status = "ok" if bad_laps == 0 else "FAIL"
    print(f"{status:4} cars whose lap rows differ from official laps: {bad_laps}")
    if bad_laps:
        failures.append("lap counts")
    print("tables:", [r[0] for r in con.execute("SHOW TABLES").fetchall()])
    print("views: ", [r[0] for r in con.execute(
        "SELECT view_name FROM duckdb_views() WHERE NOT internal").fetchall()])
    con.close()
    if failures:
        raise SystemExit(f"checks failed: {failures}")
    print(f"wrote {DB.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
