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


# Tracks that are not part of the racing circuit: paddock, pit lane, access roads, other events.
NON_CIRCUIT = ("Grand-Prix-Fahrerlager", "Offroad", "Anbindung", "Boxengasse", "Sprintstrecke",
               "Rallycross", "Variante")


def load_circuit(path: Path = GPX, min_points: int = 8) -> list[list[tuple[float, float]]]:
    """Polylines for the racing circuit, one per named section of the track."""
    if not path.exists():
        return []
    root = ET.parse(path).getroot()
    segments: list[list[tuple[float, float]]] = []
    for trk in root.iterfind("g:trk", NS):
        name = (trk.findtext("g:name", default="", namespaces=NS) or "").strip()
        if name.startswith("way/") or any(word in name for word in NON_CIRCUIT):
            continue
        points = [(float(p.attrib["lat"]), float(p.attrib["lon"]))
                  for p in trk.iterfind(".//g:trkpt", NS)]
        if len(points) >= min_points:
            segments.append(points)
    return segments
