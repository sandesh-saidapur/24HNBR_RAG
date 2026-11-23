"""One entry point for a question: route it, gather evidence, then answer and verify."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.indexing.bm25 import BM25Index
from src.indexing.tabular_store import TimingStore
from src.rag import evidence as ev
from src.rag.answer import Answer, answer
from src.rag.evidence import EvidenceBook
from src.rag.llm import TextLLM
from src.rag.router import Intent, route


@dataclass
class Result:
    intent: Intent
    book: EvidenceBook
    answer: Answer | None = None
    notes: list[str] = field(default_factory=list)


def gather(store: TimingStore, intent: Intent) -> tuple[EvidenceBook, list[str]]:
    book = EvidenceBook()
    notes: list[str] = []
    if intent.kind == "car" and intent.car_number is not None:
        if ev.add_car(store, book, intent.car_number):
            ev.add_penalties(store, book, intent.car_number)
        else:
            notes.append(f"car {intent.car_number} is not in the classification")
    elif intent.kind == "results":
        podium = sorted(
            (c for c in store.cars() if c["position"] and c["position"] <= 3),
            key=lambda c: c["position"],
        )
        for car in podium:
            ev.add_car(store, book, car["car_number"])
        if not podium:
            notes.append("no official classification is loaded")
    elif intent.kind == "standings" and intent.hour is not None:
        if not ev.add_standings(store, book, intent.hour):
            notes.append(f"no split at hour {intent.hour}")
    elif intent.kind == "media" and intent.file is not None:
        if not ev.add_media(store, book, intent.file):
            notes.append(f"{intent.file} is not in the photo timeline")
    return book, notes


def driver_car(store: TimingStore, question: str) -> int | None:
    """The car of a driver whose surname appears in the question (for example 'Verstappen')."""
    for car in store.cars():
        for name in (car.get("drivers") or "").split(";"):
            surname = name.strip().split(" ")[0] if name.strip() else ""
            if len(surname) >= 4 and re.search(rf"\b{re.escape(surname)}\b", question, re.IGNORECASE):
                return int(car["car_number"])
    return None


def ask(
    store: TimingStore,
    question: str,
    llm: TextLLM | None,
    *,
    car_number: int | None = None,
    hour: int | None = None,
    file: str | None = None,
    index: BM25Index | None = None,
) -> Result:
    if car_number is None:
        car_number = driver_car(store, question)
    intent = route(question, car_number=car_number, hour=hour, file=file)
    book, notes = gather(store, intent)
    if intent.kind == "overview":
        hits = index.search(question, k=3) if index is not None else []
        for hit in hits:
            ev.add_document(book, hit)
        if not hits:
            notes.append("no car, split or photo was named, and no document matched")
    result = Result(intent=intent, book=book, notes=notes)
    if llm is not None and len(book) > 0:
        result.answer = answer(question, book, llm)
    return result
