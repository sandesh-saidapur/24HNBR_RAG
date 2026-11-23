"""Evidence gathering. Every figure in an evidence line is formatted from the database,
so the language model never has to produce a number itself."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.indexing.tabular_store import TimingStore


def fmt_clock(seconds: float | None) -> str:
    """Seconds to a race clock: 86727.664 -> '24:05:27.664', 327.5 -> '5:27.500'."""
    if seconds is None:
        return "n/a"
    total_ms = round(seconds * 1000)
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}.{ms:03d}"
    return f"{minutes}:{secs:02d}.{ms:03d}"


def fmt_seconds(seconds: float) -> str:
    """Penalty and gap values: 90.0 -> '90 s', 118.795 -> '118.8 s'."""
    return f"{seconds:g} s" if float(seconds).is_integer() else f"{seconds:.1f} s"


@dataclass(frozen=True)
class Evidence:
    id: str
    kind: str
    source: str
    text: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceBook:
    items: list[Evidence] = field(default_factory=list)

    def add(self, kind: str, source: str, text: str, data: dict[str, Any] | None = None) -> None:
        self.items.append(Evidence(f"E{len(self.items) + 1}", kind, source, text, data or {}))

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)


def add_car(store: TimingStore, book: EvidenceBook, car_number: int) -> bool:
    car = store.car(car_number)
    if car is None:
        return False
    position = f"position {car['position']}" if car["position"] else "not classified"
    book.add(
        "car",
        "official final result",
        f"Car {car_number} ({car['team']}, class {car['class']}, drivers "
        f"{(car.get('drivers') or 'not listed').replace(';', ', ')}): status {car['status']}, "
        f"{position}, {car['laps']} laps, total {fmt_clock(car['total_time_s'])}.",
        {"car_number": car_number},
    )
    return True


def add_penalties(store: TimingStore, book: EvidenceBook, car_number: int) -> None:
    for pen in store.penalties(car_number):
        decision = (
            f"steward decision no. {pen['steward_decision_no']}"
            if pen["steward_decision_no"]
            else "penalty list entry"
        )
        book.add(
            "penalty",
            "official penalty list",
            f"Car {car_number}: {fmt_seconds(pen['penalty_seconds'])} ({pen['kind']}), "
            f"{decision}: {pen['offence_verbatim']}",
            {"car_number": car_number, "penalty_seconds": pen["penalty_seconds"]},
        )


def add_standings(store: TimingStore, book: EvidenceBook, hour: int, top: int = 3) -> bool:
    rows = store.standings(hour)
    if not rows:
        return False
    for row in rows[:top]:
        book.add(
            "standings",
            f"hourly split at {hour} h",
            f"At the {hour} h split, car {row['car_number']} was P{row['overall_rank']} "
            f"with {row['laps']} laps and elapsed time {fmt_clock(row['elapsed_s'])}.",
            {"car_number": row["car_number"], "hour": hour},
        )
    return True


def add_document(book: EvidenceBook, hit: object) -> None:
    """Add one search hit from the official documents (a BM25 Hit with .passage and .score)."""
    passage = hit.passage  # type: ignore[attr-defined]
    book.add(
        "document",
        f"official document: {passage.source}",
        passage.text[:500],
        {"passage_id": passage.id, "score": hit.score},  # type: ignore[attr-defined]
    )


def add_media(store: TimingStore, book: EvidenceBook, file: str) -> bool:
    match = next((m for m in store.media(None, None) if m["file"] == file), None)
    if match is None:
        return False
    on_course = "on the circuit" if match["on_course"] else "off the circuit"
    distance = f"{match['distance_m']:.0f} m" if match["distance_m"] is not None else "n/a"
    book.add(
        "media",
        "photo timeline",
        f"{file} was captured at race time {fmt_clock(match['race_elapsed_s'])} "
        f"({match['phase']}), {on_course}; nearest section {match['nearest_section']} "
        f"at {distance}; split leader car {match['leader_car']} ({match['leader_team']}).",
        {"file": file, "race_elapsed_s": match["race_elapsed_s"]},
    )
    return True
