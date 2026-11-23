"""A small BM25 keyword index. No dependencies, so the index is easy to read and to test."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

TOKEN_RE = re.compile(r"[a-zäöüß0-9]+")
STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it of on or that the this to was "
    "what which who with did does do".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


@dataclass(frozen=True)
class Passage:
    id: str
    source: str
    text: str


@dataclass(frozen=True)
class Hit:
    passage: Passage
    score: float


class BM25Index:
    def __init__(self, passages: list[Passage], k1: float = 1.5, b: float = 0.75) -> None:
        self.passages = passages
        self.k1 = k1
        self.b = b
        self._docs = [Counter(tokenize(p.text)) for p in passages]
        self._lengths = [sum(c.values()) for c in self._docs]
        self._avg = (sum(self._lengths) / len(self._lengths)) if self._lengths else 0.0
        df: Counter[str] = Counter()
        for doc in self._docs:
            df.update(doc.keys())
        n = len(self._docs)
        self._idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 3) -> list[Hit]:
        terms = set(tokenize(query))
        scored: list[Hit] = []
        for passage, doc, length in zip(self.passages, self._docs, self._lengths, strict=True):
            score = 0.0
            for term in terms:
                tf = doc.get(term, 0)
                if tf == 0:
                    continue
                norm = self.k1 * (1 - self.b + self.b * length / (self._avg or 1.0))
                score += self._idf[term] * tf * (self.k1 + 1) / (tf + norm)
            if score > 0:
                scored.append(Hit(passage, round(score, 4)))
        scored.sort(key=lambda h: (-h.score, h.passage.id))
        return scored[:k]
