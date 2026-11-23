"""Decide which evidence a question needs. Rules first; the router model is only a fallback
for questions the rules cannot place, and is not needed for the offline tests."""

from __future__ import annotations

import re
from dataclasses import dataclass

CAR_RE = re.compile(r"(?:\bcar\b|#|\bno\.?)\s*(\d{1,3})\b", re.IGNORECASE)
HOUR_RE = re.compile(r"\b(?:split|hour)\s*(\d{1,2})\b", re.IGNORECASE)
FILE_RE = re.compile(r"\b(IMG_\d{4}\.(?:HEIC|MOV|MP4|JPG|JPEG|PNG))\b", re.IGNORECASE)


@dataclass(frozen=True)
class Intent:
    kind: str  # car | standings | media | overview
    car_number: int | None = None
    hour: int | None = None
    file: str | None = None


def route(
    question: str,
    *,
    car_number: int | None = None,
    hour: int | None = None,
    file: str | None = None,
) -> Intent:
    """Explicit arguments win over anything found in the question text."""
    file = file or (m.group(1).upper() if (m := FILE_RE.search(question)) else None)
    if file:
        return Intent("media", car_number=car_number, file=file)
    car = car_number or (int(m.group(1)) if (m := CAR_RE.search(question)) else None)
    if car is not None:
        return Intent("car", car_number=car)
    hour = hour or (int(m.group(1)) if (m := HOUR_RE.search(question)) else None)
    if hour is not None:
        return Intent("standings", hour=hour)
    return Intent("overview")
