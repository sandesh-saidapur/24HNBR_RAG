"""Circuit outline from the OpenStreetMap GPX export (ODbL: attribution required)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

GPX = Path(__file__).resolve().parents[2] / "data/raw/track_geometry/export.gpx"
ATTRIBUTION = "Track data © OpenStreetMap contributors (ODbL)"
MAX_POINTS = 800
NS = {"g": "http://www.topografix.com/GPX/1/1"}


def load_outline(path: Path = GPX, max_points: int = MAX_POINTS) -> list[tuple[float, float]]:
    if not path.exists():
        return []
    root = ET.parse(path).getroot()
    points = [
        (float(p.attrib["lat"]), float(p.attrib["lon"]))
        for p in root.iterfind(".//g:trkpt", NS)
    ]
    if len(points) <= max_points:
        return points
    step = len(points) / max_points
    return [points[int(i * step)] for i in range(max_points)]
