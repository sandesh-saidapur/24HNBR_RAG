"""Read-only access to the timing database (data/processed/timing.duckdb).

Every query here is parameterised. Numbers are returned exactly as stored, so the API
never rounds or recomputes official figures.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data/processed/timing.duckdb"


class TimingStore:
    def __init__(self, path: Path | str = DEFAULT_DB) -> None:
        self.path = Path(path)

    @property
    def available(self) -> bool:
        return self.path.exists()

    def _rows(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        with duckdb.connect(str(self.path), read_only=True) as con:
            cur = con.execute(sql, params or [])
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def tables(self) -> list[str]:
        return [r["table_name"] for r in self._rows(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'")]

    def cars(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM car_summary ORDER BY position NULLS LAST, car_number")

    def car(self, car_number: int) -> dict[str, Any] | None:
        rows = self._rows("SELECT * FROM car_summary WHERE car_number = ?", [car_number])
        return rows[0] if rows else None

    def car_laps(self, car_number: int, limit: int) -> list[dict[str, Any]]:
        return self._rows(
            """SELECT lap, lap_time_s, s1_s, s2_s, s3_s, s4_s, s5_s, s6_s, s7_s, s8_s, s9_s
               FROM sectors WHERE car_number = ? ORDER BY lap LIMIT ?""",
            [car_number, limit],
        )

    def penalties(self, car_number: int | None = None) -> list[dict[str, Any]]:
        if car_number is None:
            return self._rows("SELECT * FROM penalties ORDER BY car_number, steward_decision_no")
        return self._rows(
            "SELECT * FROM penalties WHERE car_number = ? ORDER BY steward_decision_no",
            [car_number],
        )

    def hours(self) -> list[int]:
        return [r["hour"] for r in self._rows(
            "SELECT DISTINCT hour FROM hourly_standings ORDER BY hour")]

    def standings(self, hour: int) -> list[dict[str, Any]]:
        return self._rows(
            "SELECT * FROM hourly_standings WHERE hour = ? ORDER BY overall_rank",
            [hour],
        )

    def media(self, on_course: bool | None, phase: str | None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if on_course is not None:
            clauses.append("on_course = ?")
            params.append(on_course)
        if phase is not None:
            clauses.append("phase = ?")
            params.append(phase)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return self._rows(f"SELECT * FROM media_timeline {where} ORDER BY race_elapsed_s", params)

    def running_order(self, race_elapsed_s: float, limit: int = 15) -> list[dict[str, Any]]:
        """Cars ranked at a race time: most laps completed first, then who completed them first.

        Laps are summed from the official per-lap times, starting from the race start.
        """
        return self._rows(
            """WITH cum AS (
                 SELECT car_number, lap,
                        SUM(lap_time_s) OVER (PARTITION BY car_number ORDER BY lap) AS end_s
                 FROM sectors WHERE lap_time_s IS NOT NULL),
               done AS (
                 SELECT car_number, max(lap) AS laps, max(end_s) AS last_end_s
                 FROM cum WHERE end_s <= ? GROUP BY car_number)
               SELECT d.car_number, d.laps, d.last_end_s, c.team, c.drivers,
                      d.last_end_s + COALESCE(c.penalty_seconds_listed, 0) AS adj_end_s
               FROM done d LEFT JOIN car_summary c USING (car_number)
               ORDER BY d.laps DESC, adj_end_s ASC
               LIMIT ?""",
            [race_elapsed_s, limit],
        )

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for table in ("classification", "penalties", "sectors", "media_timeline"):
            out[table] = self._rows(f"SELECT count(*) AS n FROM {table}")[0]["n"]
        return out
