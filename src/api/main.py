"""FastAPI application for Trackside 24.

Run locally:  uvicorn src.api.main:app --reload
Set TRACKSIDE_DB_PATH to point at another timing database.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.api.schemas import Health
from src.indexing.tabular_store import DEFAULT_DB, TimingStore

FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def create_app(db_path: Path | str | None = None) -> FastAPI:
    path = db_path or os.environ.get("TRACKSIDE_DB_PATH") or DEFAULT_DB
    app = FastAPI(
        title="Trackside 24 API",
        version="0.2.0",
        description="Official 2026 24h Nürburgring timing, penalties and the photo timeline.",
    )
    app.state.store = TimingStore(path)
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
