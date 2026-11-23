"""Photo vector index and search route. Uses a keyword embedder, so no model download is needed."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("lancedb")

from fastapi.testclient import TestClient  # noqa: E402

from src.api.main import create_app  # noqa: E402
from src.indexing.vector_store import PhotoIndex, PhotoItem  # noqa: E402

WORDS = ["grid", "pit", "rain", "night"]


def keyword_vector(text: str) -> list[float]:
    """Unit vector on the keyword axes found in the text; a neutral vector when none match."""
    lowered = text.lower()
    vector = [1.0 if word in lowered else 0.0 for word in WORDS]
    if not any(vector):
        return [0.5, 0.5, 0.5, 0.5]
    norm = sum(v * v for v in vector) ** 0.5
    return [v / norm for v in vector]


class KeywordEmbedder:
    def embed_images(self, paths: list[Path]) -> list[list[float]]:
        return [keyword_vector(p.name) for p in paths]

    def embed_text(self, texts: list[str]) -> list[list[float]]:
        return [keyword_vector(t) for t in texts]


def sample_items() -> list[PhotoItem]:
    return [
        PhotoItem("pit_01.jpg", "pit_01.jpg", Path("pit_01.jpg"), 3600.0, "Pit lane"),
        PhotoItem("rain_02.jpg", "rain_02.jpg", Path("rain_02.jpg"), 7200.0, "Brünnchen"),
        PhotoItem("night_03.jpg", "night_03.jpg", Path("night_03.jpg"), 40000.0, "Grid"),
    ]


def test_search_ranks_the_matching_photo_first(tmp_path: Path) -> None:
    index = PhotoIndex.build(tmp_path / "vs", sample_items(), KeywordEmbedder())
    top = index.search(keyword_vector("rain"), k=1)[0]
    assert top["file"] == "rain_02.jpg"
    assert top["race_elapsed_s"] == 7200.0
    assert top["score"] == pytest.approx(1.0, abs=1e-3)


def test_open_returns_none_when_no_index_exists(tmp_path: Path) -> None:
    assert PhotoIndex.open(tmp_path / "missing") is None


def test_open_reads_a_built_index(tmp_path: Path) -> None:
    PhotoIndex.build(tmp_path / "vs", sample_items(), KeywordEmbedder())
    reopened = PhotoIndex.open(tmp_path / "vs")
    assert reopened is not None
    assert len(reopened) == 3


def test_build_refuses_an_empty_list(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        PhotoIndex.build(tmp_path / "vs", [], KeywordEmbedder())


def test_search_route_returns_ranked_hits(tmp_path: Path) -> None:
    index = PhotoIndex.build(tmp_path / "vs", sample_items(), KeywordEmbedder())
    client = TestClient(
        create_app(db_path=tmp_path / "none.duckdb", photo_index=index, embedder=KeywordEmbedder())
    )
    hits = client.get("/api/search/photos", params={"q": "night photo", "k": 2}).json()
    assert hits[0]["file"] == "night_03.jpg"
    assert len(hits) == 2
    assert hits[0]["caption"] == "Grid"


def test_search_route_is_503_until_the_index_is_built(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            db_path=tmp_path / "none.duckdb",
            embedder=KeywordEmbedder(),
            vector_path=tmp_path / "not-built",
        )
    )
    response = client.get("/api/search/photos", params={"q": "pit lane"})
    assert response.status_code == 503
    assert "build_photo_index" in response.json()["detail"]


def test_search_route_validates_query_length(tmp_path: Path) -> None:
    index = PhotoIndex.build(tmp_path / "vs", sample_items(), KeywordEmbedder())
    client = TestClient(
        create_app(db_path=tmp_path / "none.duckdb", photo_index=index, embedder=KeywordEmbedder())
    )
    assert client.get("/api/search/photos", params={"q": "x"}).status_code == 422
