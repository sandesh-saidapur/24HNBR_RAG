"""FastAPI application for Trackside 24.

Run locally:  uvicorn src.api.main:app --reload
Set TRACKSIDE_DB_PATH to point at another timing database.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.api.schemas import Health
from src.indexing.bm25 import BM25Index, Passage
from src.indexing.tabular_store import DEFAULT_DB, TimingStore
from src.rag.llm import TextLLM, get_text_llm

FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
PASSAGES = Path(__file__).resolve().parents[2] / "data/processed/text_passages.json"


def load_text_index(path: Path = PASSAGES) -> BM25Index | None:
    if not path.exists():
        return None
    rows = json.loads(path.read_text(encoding="utf-8"))
    return BM25Index([Passage(r["id"], r["source"], r["text"]) for r in rows])


def create_app(db_path: Path | str | None = None, llm: TextLLM | None = None) -> FastAPI:
    path = db_path or os.environ.get("TRACKSIDE_DB_PATH") or DEFAULT_DB
    app = FastAPI(
        title="Trackside 24 API",
        version="0.2.0",
        description="Official 2026 24h Nürburgring timing, penalties and the photo timeline.",
    )
    app.state.store = TimingStore(path)
    app.state.llm = llm if llm is not None else get_text_llm()
    app.state.text_index = load_text_index()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=FRONTEND_ORIGINS,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/api/health", response_model=Health, tags=["meta"])
    def health() -> Health:
        store: TimingStore = app.state.store
        if not store.available:
            return Health(status="degraded", database=f"missing: {store.path.name}", counts={})
        return Health(status="ok", database=store.path.name, counts=store.counts())

    return app


app = create_app()
