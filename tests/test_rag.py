"""Phase 4 tests. They run offline: a stand-in model replaces Claude, and every figure
checked here comes from the real timing database."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.indexing.tabular_store import DEFAULT_DB, TimingStore
from src.rag.answer import verify
from src.rag.evidence import EvidenceBook, fmt_clock, fmt_seconds
from src.rag.pipeline import ask
from src.rag.router import route

needs_db = pytest.mark.skipif(not Path(DEFAULT_DB).exists(), reason="timing.duckdb not built")


@dataclass
class FakeLLM:
    reply: str

    def complete(self, *, model: str, system: str, user: str, max_tokens: int) -> str:
        assert "Never calculate" in system  # the grounding rule is always sent
        return self.reply


def test_clock_and_seconds_formatting() -> None:
    assert fmt_clock(86727.664) == "24:05:27.664"
    assert fmt_clock(327.5) == "5:27.500"
    assert fmt_clock(None) == "n/a"
    assert fmt_seconds(90.0) == "90 s"
    assert fmt_seconds(118.795) == "118.8 s"


@pytest.mark.parametrize(
    ("question", "kind", "car", "hour", "file"),
    [
        ("what happened to car #63?", "car", 63, None, None),
        ("penalties for no. 95", "car", 95, None, None),
        ("who led at split 13", "standings", None, 13, None),
        ("what is in photo IMG_0677.MOV", "media", None, None, "IMG_0677.MOV"),
        ("who won the race", "results", None, None, None),
    ],
)
def test_router_rules(
    question: str, kind: str, car: int | None, hour: int | None, file: str | None
) -> None:
    intent = route(question)
    assert (intent.kind, intent.car_number, intent.hour, intent.file) == (kind, car, hour, file)


def test_explicit_arguments_override_the_question_text() -> None:
    assert route("car 63", car_number=95).car_number == 95


def test_verifier_accepts_grounded_answer_and_flags_invented_figures() -> None:
    book = EvidenceBook()
    book.add("car", "official final result", "Car 63 finished at position 15 with 109 laps.")
    book.add("penalty", "official penalty list", "Car 63: 30 s (time_replacement).")
    assert verify("Car 63 had 109 laps [E1] and a 30 s penalty [E2].", book).ok
    bad = verify("Car 63 had 111 laps [E1].", book)
    assert not bad.ok and "figure not in evidence: 111" in bad.problems
    assert not verify("Car 63 had 109 laps.", book).ok  # no citation
    assert "citation E9 is not in the evidence" in verify("Fact [E9].", book).problems


@needs_db
def test_pipeline_gathers_car_and_penalties_from_the_database() -> None:
    store = TimingStore(DEFAULT_DB)
    result = ask(store, "what about car 63?", llm=None)
    texts = [e.text for e in result.book]
    assert any("109 laps" in t for t in texts)
    assert sum("penalty" in e.kind for e in result.book) == 2
    assert result.answer is None  # no model, so evidence only


@needs_db
def test_ask_endpoint_without_a_model_returns_evidence_only() -> None:
    client = TestClient(create_app(llm=None))
    body = client.post("/api/ask", json={"question": "tell me about car 63"}).json()
    assert body["status"] == "evidence_only"
    assert body["answer"] is None
    penalty_lines = [e["text"] for e in body["evidence"] if e["kind"] == "penalty"]
    assert len(penalty_lines) == 2
    assert sum("30 s" in t or "60 s" in t for t in penalty_lines) == 2


@needs_db
def test_ask_endpoint_with_grounded_model_reply_is_verified() -> None:
    reply = "Car 63 received penalties of 30 s and 60 s [E2][E3]."
    client = TestClient(create_app(llm=FakeLLM(reply)))
    body = client.post("/api/ask", json={"question": "what about car 63?"}).json()
    assert body["status"] == "answered"
    assert body["verified"] is True
    assert body["problems"] == []


@needs_db
def test_ask_endpoint_rejects_an_invented_figure() -> None:
    client = TestClient(create_app(llm=FakeLLM("Car 63 completed 999 laps [E1].")))
    body = client.post("/api/ask", json={"question": "car 63"}).json()
    assert body["verified"] is False
    assert "figure not in evidence: 999" in body["problems"]


@needs_db
def test_ask_endpoint_asks_for_a_subject_when_none_is_given() -> None:
    client = TestClient(create_app(llm=FakeLLM("Unused [E1].")))
    body = client.post("/api/ask", json={"question": "xyzzy plugh"}).json()
    assert body["status"] == "needs_question"
    assert body["notes"]


@needs_db
def test_overview_question_is_answered_from_official_documents() -> None:
    client = TestClient(create_app(llm=None))
    body = client.post("/api/ask", json={"question": "pit stop minimal time penalty"}).json()
    kinds = {e["kind"] for e in body["evidence"]}
    assert kinds == {"document"}


@needs_db
def test_ask_endpoint_photo_evidence_carries_race_time() -> None:
    client = TestClient(create_app(llm=None))
    body = client.post("/api/ask", json={"question": "photo", "file": "IMG_0677.MOV"}).json()
    assert body["intent"] == "media"
    assert "race time" in body["evidence"][0]["text"]


def test_winner_questions_route_to_results() -> None:
    assert route("Who won the 24 hours?").kind == "results"
    assert route("Which cars finished on the podium?").kind == "results"
    assert route("car 80 won?").kind == "car"


def test_figures_in_the_question_are_not_flagged() -> None:
    from src.rag.answer import verify
    from src.rag.evidence import EvidenceBook

    book = EvidenceBook()
    book.add("car", "official classification", "Winward Racing, car 80, position 1")
    text = "Car 80 finished first [E1]."
    assert verify(text, book, "Who won the 24 hours?").ok
    # A 24 that the user never typed and the evidence does not contain is still flagged.
    assert not verify("The race lasted 24 hours [E1].", book, "Who won?").ok


def test_full_width_citation_brackets_are_accepted() -> None:
    from src.rag.answer import normalise, verify
    from src.rag.evidence import EvidenceBook

    book = EvidenceBook()
    book.add("car", "official final result", "Car 80, position 1, total 24:05:27.664")
    text = normalise("Car 80 won the race【E1】.")
    assert "[E1]" in text
    assert verify(text, book, "Who won?").ok
