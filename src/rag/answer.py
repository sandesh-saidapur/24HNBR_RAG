"""Answer generation and verification. The model writes prose; the verifier checks that every
citation exists and every figure in the prose appears in the evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.rag.evidence import EvidenceBook
from src.rag.llm import TextLLM, model_for

SYSTEM = """You are Trackside 24, a race engineer for the 2026 24 Hours of Nürburgring.
Answer only from the EVIDENCE list. End every sentence with the id of its
evidence, such as [E2].
Use only figures that appear in the evidence, exactly as written. Never calculate, estimate
or infer a number. If the evidence does not answer the question, say what is missing.
Answer the question that was asked, in its own terms. If it names a driver, give that
driver's car and result, using the names exactly as the evidence writes them. Do not
describe other cars or topics unless the question asks for them.
Keep the answer short: one paragraph or a few bullet points."""

CITE_RE = re.compile(r"\[(E\d+)\]")
FIGURE_RE = re.compile(r"\d+(?:[.:]\d+)*")


@dataclass(frozen=True)
class Verdict:
    ok: bool
    problems: list[str]


@dataclass(frozen=True)
class Answer:
    text: str
    verdict: Verdict


BRACKETS = str.maketrans({"【": "[", "】": "]", "［": "[", "］": "]", "〔": "[", "〕": "]"})


def normalise(text: str) -> str:
    """Models sometimes write citations with full-width or CJK brackets; map them to [E1]."""
    return text.translate(BRACKETS)


def build_prompt(question: str, book: EvidenceBook) -> str:
    lines = [f"[{e.id}] ({e.kind}, {e.source}) {e.text}" for e in book]
    return "EVIDENCE:\n" + "\n".join(lines) + f"\n\nQUESTION: {question}"


def verify(text: str, book: EvidenceBook, question: str = "") -> Verdict:
    problems: list[str] = []
    cited = set(CITE_RE.findall(text))
    known = {e.id for e in book}
    if not cited:
        problems.append("no citations")
    for ident in sorted(cited - known):
        problems.append(f"citation {ident} is not in the evidence")
    # Figures the user typed (such as the 24 in \"24 hours\") are not new claims.
    allowed: set[str] = set(FIGURE_RE.findall(question))
    for item in book:
        allowed.update(FIGURE_RE.findall(item.text))
    prose = CITE_RE.sub("", text)
    for figure in FIGURE_RE.findall(prose):
        if figure not in allowed:
            problems.append(f"figure not in evidence: {figure}")
    return Verdict(ok=not problems, problems=problems)


def answer(question: str, book: EvidenceBook, llm: TextLLM) -> Answer:
    text = normalise(llm.complete(
        model=model_for("text"),
        system=SYSTEM,
        user=build_prompt(question, book),
        max_tokens=700,
    ))
    return Answer(text=text, verdict=verify(text, book, question))
