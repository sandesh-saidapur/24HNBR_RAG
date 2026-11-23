"""HTTP routes. Each route reads the timing database and returns official figures unchanged."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from src.api.schemas import (
    AskRequest,
    AskResponse,
    CarDetail,
    CarRow,
    LapRow,
    MediaRow,
    PenaltyRow,
    StandingRow,
    TrackOutline,
)
from src.api.track import ATTRIBUTION, load_outline
from src.indexing.tabular_store import TimingStore
from src.rag.pipeline import ask

router = APIRouter(prefix="/api")
CarNumber = Annotated[int, Query(ge=0, le=999)]


def store(request: Request) -> TimingStore:
    return request.app.state.store


def not_found(car_number: int) -> HTTPException:
    return HTTPException(
        status_code=404, detail=f"car {car_number} is not in the classification"
    )


@router.get("/cars", response_model=list[CarRow], response_model_by_alias=True)
def list_cars(request: Request) -> list[dict]:
    return store(request).cars()


@router.get("/cars/{car_number}", response_model=CarDetail, response_model_by_alias=True)
def get_car(car_number: int, request: Request) -> dict:
    db = store(request)
    car = db.car(car_number)
    if car is None:
        raise not_found(car_number)
    car["penalties"] = db.penalties(car_number)
    return car


@router.get("/cars/{car_number}/laps", response_model=list[LapRow])
def get_car_laps(
    car_number: int,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
) -> list[dict]:
    db = store(request)
    if db.car(car_number) is None:
        raise not_found(car_number)
    return db.car_laps(car_number, limit)


@router.get("/penalties", response_model=list[PenaltyRow])
def list_penalties(request: Request, car_number: CarNumber | None = None) -> list[dict]:
    return store(request).penalties(car_number)


@router.get("/standings/hours", response_model=list[int])
def list_split_hours(request: Request) -> list[int]:
    return store(request).hours()


@router.get("/standings/{hour}", response_model=list[StandingRow])
def get_standings(hour: int, request: Request) -> list[dict]:
    db = store(request)
    if hour not in db.hours():
        raise HTTPException(status_code=404, detail=f"no hourly split at hour {hour}")
    return db.standings(hour)


@router.get("/media", response_model=list[MediaRow])
def list_media(
    request: Request,
    on_course: bool | None = None,
    phase: Annotated[str | None, Query(pattern="^(pre_start|race|post_finish)$")] = None,
) -> list[dict]:
    return store(request).media(on_course, phase)


@router.post("/ask", response_model=AskResponse)
def ask_question(body: AskRequest, request: Request) -> AskResponse:
    result = ask(
        store(request),
        body.question,
        request.app.state.llm,
        car_number=body.car_number,
        hour=body.hour,
        file=body.file,
        index=request.app.state.text_index,
    )
    evidence = [
        {"id": e.id, "kind": e.kind, "source": e.source, "text": e.text} for e in result.book
    ]
    if result.answer is not None:
        status = "answered"
    elif not evidence:
        status = "needs_question"
    else:
        status = "evidence_only"
    verdict = result.answer.verdict if result.answer else None
    return AskResponse(
        status=status,
        intent=result.intent.kind,
        evidence=evidence,
        answer=result.answer.text if result.answer else None,
        verified=verdict.ok if verdict else None,
        problems=verdict.problems if verdict else [],
        notes=result.notes,
    )


@router.get("/track", response_model=TrackOutline)
def track_outline() -> dict:
    return {"attribution": ATTRIBUTION, "points": load_outline()}
