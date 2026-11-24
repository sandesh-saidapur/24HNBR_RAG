"""Answer generation and verification. The model writes prose; the verifier checks that every
citation exists and every figure in the prose appears in the evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.rag.evidence import EvidenceBook
from src.rag.llm import TextLLM, model_for

SYSTEM = """You are Trackside 24, a race engineer for the 2026 24 Hours of Nürburgring.
Answer only from EVIDENCE. End each sentence with its evidence id, such as [E2].
Use only figures written in the evidence. Never calculate or infer a number.
If the evidence does not answer the question, say what is missing in one sentence.
If the question names a driver, answer for that driver's car, using the evidence names.
Stay on the question. Two or three sentences at most."""

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


_CACHE: dict[tuple[str, str], Answer] = {}
_CACHE_MAX = 256


def answer(question: str, book: EvidenceBook, llm: TextLLM) -> Answer:
    """Answer from the evidence. Identical questions over identical evidence reuse the earlier answer."""
    user = build_prompt(question, book)
    key = (model_for("text"), user)
    if key in _CACHE:
        return _CACHE[key]
    text = normalise(llm.complete(
        model=key[0],
        system=SYSTEM,
        user=user,
        max_tokens=300,
    ))
    result = Answer(text=text, verdict=verify(text, book, question))
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = result
    return result
