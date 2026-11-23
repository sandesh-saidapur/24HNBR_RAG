"""Photo vector index in LanceDB.

Vectors come from an injected embedder; race times and captions come from the timing database
when the index is built. Nothing in this module creates a number that the model wrote.
Requires the optional "vector" extra (lancedb). Imports are local so the rest of the API still
works without it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

TABLE = "photos"


class Embedder(Protocol):
    """Maps images and text into one shared, unit-length vector space."""

    def embed_images(self, paths: Sequence[Path]) -> list[list[float]]: ...

    def embed_text(self, texts: Sequence[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class PhotoItem:
    """One indexed frame: a photo, or one sampled frame from a video."""

    key: str
    file: str
    path: Path
    race_elapsed_s: float
    caption: str


def _table_names(db: Any) -> list[str]:
    listing = getattr(db, "list_tables", None)
    if listing is None:  # older lancedb releases
        return list(db.table_names())
    result = listing()
    return list(getattr(result, "tables", result))


class PhotoIndex:
    def __init__(self, table: Any) -> None:
        self._table = table

    @classmethod
    def build(
        cls, path: Path | str, items: Sequence[PhotoItem], embedder: Embedder, batch_size: int = 32
    ) -> PhotoIndex:
        import lancedb

        if not items:
            raise ValueError("no photos to index")
        vectors: list[list[float]] = []
        for start in range(0, len(items), batch_size):
            chunk = items[start : start + batch_size]
            vectors.extend(embedder.embed_images([item.path for item in chunk]))
        rows = [
            {
                "vector": vector,
                "key": item.key,
                "file": item.file,
                "race_elapsed_s": float(item.race_elapsed_s),
                "caption": item.caption,
            }
            for item, vector in zip(items, vectors, strict=True)
        ]
        db = lancedb.connect(str(path))
        return cls(db.create_table(TABLE, data=rows, mode="overwrite"))

    @classmethod
    def open(cls, path: Path | str) -> PhotoIndex | None:
        import lancedb

        if not Path(path).exists():
            return None
        db = lancedb.connect(str(path))
        if TABLE not in _table_names(db):
            return None
        return cls(db.open_table(TABLE))

    def __len__(self) -> int:
        return int(self._table.count_rows())

    def search(self, vector: Sequence[float], k: int = 8) -> list[dict[str, Any]]:
        hits = self._table.search(list(vector)).metric("cosine").limit(k).to_list()
        return [
            {
                "key": hit["key"],
                "file": hit["file"],
                "race_elapsed_s": hit["race_elapsed_s"],
                "caption": hit["caption"],
                "score": round(1.0 - float(hit["_distance"]), 4),
            }
            for hit in hits
        ]
