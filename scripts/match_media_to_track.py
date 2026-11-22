"""Match each media item to the nearest named section of the 24h course.

Inputs:
  data/raw/track_geometry/export.gpx   OpenStreetMap export (overpass-turbo), ODbL
  data/processed/media_race_clock.parquet
Output:
  data/processed/media_track_match.parquet

Only OSM ways tagged highway=raceway with a name are used. Sprint, rallycross,
paddock and parking ways are excluded because the 24h race does not run on them.
Distances are metres from the photo to the nearest point on the named way.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
GPX = ROOT / "data/raw/track_geometry/export.gpx"
MEDIA = ROOT / "data/processed/media_race_clock.parquet"
OUT = ROOT / "data/processed/media_track_match.parquet"
NS = {"g": "http://www.topografix.com/GPX/1/1"}
EXCLUDE = ("Sprintstrecke", "Rallycross", "Offroad", "Fahrerlager", "Anbindung zur Sprintstrecke",
           "Anbindung zur Müllenbachschleife", "Müllenbachschleife")
OFF_TRACK_M = 50.0


def load_sections() -> list[tuple[str, list[tuple[float, float]]]]:
    sections = []
    for trk in ET.parse(GPX).getroot().findall("g:trk", NS):
        name = (trk.findtext("g:name", default="", namespaces=NS) or "").strip()
        desc = trk.findtext("g:desc", default="", namespaces=NS) or ""
        tags = dict(line.split("=", 1) for line in desc.splitlines() if "=" in line)
        if tags.get("highway") != "raceway" or tags.get("sport") != "motor":
            continue
        if not name or name.startswith("way/") or any(e in name for e in EXCLUDE):
            continue
        pts = [(float(p.get("lat")), float(p.get("lon")))
               for seg in trk.findall("g:trkseg", NS) for p in seg.findall("g:trkpt", NS)]
        if len(pts) >= 2:
            sections.append((name, pts))
    return sections


def dist_m_to_segment(p, a, b, lat0: float) -> float:
    """Planar distance in metres, local equirectangular projection around lat0."""
    kx = 111320.0 * math.cos(math.radians(lat0))
    ky = 110540.0
    px, py = p[1] * kx, p[0] * ky
    ax, ay = a[1] * kx, a[0] * ky
    bx, by = b[1] * kx, b[0] * ky
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def nearest_section(p, sections) -> tuple[str, float]:
    best_name, best_d = "", float("inf")
    for name, pts in sections:
        for a, b in zip(pts, pts[1:]):
            d = dist_m_to_segment(p, a, b, p[0])
            if d < best_d:
                best_name, best_d = name, d
    return best_name, best_d


def main() -> None:
    sections = load_sections()
    media = pq.read_table(MEDIA).to_pylist()
    cols: dict[str, list] = {k: [] for k in [
        "file", "phase", "race_elapsed_s", "cluster_id", "latitude", "longitude",
        "nearest_section", "distance_m", "on_course",
    ]}
    for m in media:
        p = (m["latitude"], m["longitude"])
        name, d = nearest_section(p, sections)
        for k, v in [("file", m["file"]), ("phase", m["phase"]), ("race_elapsed_s", m["race_elapsed_s"]),
                     ("cluster_id", m["cluster_id"]), ("latitude", p[0]), ("longitude", p[1]),
                     ("nearest_section", name), ("distance_m", d), ("on_course", d <= OFF_TRACK_M)]:
            cols[k].append(v)
    pq.write_table(pa.table(cols), OUT)
    print(f"sections used: {len(sections)}; media: {len(media)}; wrote {OUT.name}")
    by_cluster: dict[int, list[int]] = {}
    for i, c in enumerate(cols["cluster_id"]):
        by_cluster.setdefault(c, []).append(i)
    for c in sorted(by_cluster):
        idx = by_cluster[c]
        names: dict[str, int] = {}
        for i in idx:
            names[cols["nearest_section"][i]] = names.get(cols["nearest_section"][i], 0) + 1
        top = sorted(names.items(), key=lambda kv: -kv[1])[:6]
        on = sum(cols["on_course"][i] for i in idx)
        med = sorted(cols["distance_m"][i] for i in idx)[len(idx) // 2]
        print(f"cluster {c}: n={len(idx)} on_course={on} median_dist={med:.0f}m top={top}")


if __name__ == "__main__":
    main()
