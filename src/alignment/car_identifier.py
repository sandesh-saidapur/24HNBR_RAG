"""Identify the race car in a photo with Claude vision.

The model proposes a car number. Nothing is accepted unless the number is in the official 2026
classification, the model's own reading of the digits agrees, and its confidence is high enough.
Rejected sightings are kept with the reason, so the gaps are visible rather than hidden."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

from src.rag.llm import VisionLLM, model_for

MIN_CONFIDENCE = 0.6

SYSTEM = """You read race car numbers in motorsport photos from the 2026 24 Hours of Nürburgring.
Reply with a single JSON object and nothing else."""

PROMPT = """Look at this photo and identify the race car, if one is clearly visible.
Reply with JSON only, in this shape:
{"car_number": <integer or null>, "visible_number_text": <digits you can read on the car or null>,
 "make": <manufacturer or null>, "livery": <short colour and sponsor description or null>,
 "confidence": <number from 0 to 1>}
Use null for anything you cannot read clearly. Never guess a car number."""


@dataclass(frozen=True)
class Sighting:
    file: str
    car_number: int | None
    make: str | None
    livery: str | None
    confidence: float
    accepted: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def parse_reply(text: str) -> dict[str, object]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def validate(file: str, reply: dict[str, object], known_cars: set[int]) -> Sighting:
    raw_car = reply.get("car_number")
    make = reply.get("make") if isinstance(reply.get("make"), str) else None
    livery = reply.get("livery") if isinstance(reply.get("livery"), str) else None
    try:
        confidence = min(max(float(reply.get("confidence") or 0.0), 0.0), 1.0)
    except (TypeError, ValueError):
        confidence = 0.0

    def reject(car: int | None, reason: str) -> Sighting:
        return Sighting(file, car, make, livery, confidence, accepted=False, reason=reason)

    if raw_car is None:
        return reject(None, "no car number read")
    try:
        car = int(raw_car)
    except (TypeError, ValueError):
        return reject(None, "car number was not an integer")
    if car not in known_cars:
        return reject(car, "number is not in the 2026 classification")
    visible = reply.get("visible_number_text")
    if visible is not None and str(visible).strip() != str(car):
        return reject(car, "the model's digit reading disagrees with its number")
    if confidence < MIN_CONFIDENCE:
        return reject(car, f"confidence {confidence:.2f} is below {MIN_CONFIDENCE}")
    return Sighting(file, car, make, livery, confidence, accepted=True, reason="accepted")


def identify(
    file: str,
    image: bytes,
    media_type: str,
    known_cars: set[int],
    llm: VisionLLM,
) -> Sighting:
    text = llm.describe_image(
        model=model_for("vision"),
        system=SYSTEM,
        user=PROMPT,
        image=image,
        media_type=media_type,
        max_tokens=300,
    )
    return validate(file, parse_reply(text), known_cars)
