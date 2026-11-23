"""Response models. Field names match the database; `class` is exposed under its own name."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Health(BaseModel):
    status: str
    database: str
    counts: dict[str, int]


class CarRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    position: int | None
    status: str
    car_number: int
    car_class: str | None = Field(alias="class")
    team: str | None
    car_model: str | None
    laps: int
    total_time_s: float | None
    best_lap_s: float | None
    gap_or_interval: str | None
    drivers: str | None
    penalty_seconds_listed: float | None
    lap_sum_minus_total_s: float | None
    sector_sum_mismatch_laps: int | None


class PenaltyRow(BaseModel):
    car_number: int
    penalty_seconds: float
    kind: str
    steward_decision_no: int | None
    offence_verbatim: str
    source_file: str


class CarDetail(CarRow):
    penalties: list[PenaltyRow]


class LapRow(BaseModel):
    lap: int
    lap_time_s: float | None
    s1_s: float | None
    s2_s: float | None
    s3_s: float | None
    s4_s: float | None
    s5_s: float | None
    s6_s: float | None
    s7_s: float | None
    s8_s: float | None
    s9_s: float | None


class StandingRow(BaseModel):
    hour: int
    car_number: int
    overall_rank: int | None
    class_position: int | None
    laps: int | None
    elapsed_s: float | None
    classified_in_split: bool | None


class MediaRow(BaseModel):
    file: str
    media_type: str
    capture_utc: datetime
    latitude: float | None
    longitude: float | None
    phase: str
    race_elapsed_s: float
    split_hour: int | None
    leader_car: int | None
    leader_team: str | None
    nearest_section: str | None
    distance_m: float | None
    on_course: bool | None


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    car_number: int | None = Field(default=None, ge=0, le=999)
    hour: int | None = Field(default=None, ge=1, le=23)
    file: str | None = Field(default=None, max_length=64)


class EvidenceItem(BaseModel):
    id: str
    kind: str
    source: str
    text: str


class AskResponse(BaseModel):
    status: str  # answered | evidence_only | needs_question
    intent: str
    evidence: list[EvidenceItem]
    answer: str | None
    verified: bool | None
    problems: list[str]
    notes: list[str]


class TrackOutline(BaseModel):
    attribution: str
    points: list[tuple[float, float]]


class PhotoHit(BaseModel):
    key: str
    file: str
    race_elapsed_s: float
    caption: str
    score: float


class CircuitSegments(BaseModel):
    attribution: str
    segments: list[list[tuple[float, float]]]
