"""Build the dashboard's static assets.

1. data/event.json: race-weekend figures, checked against the organiser's PDF text, and the
   official podium from the timing database. Post-race statements are the author's own short
   summaries, not the organiser's wording.
2. frontend/public/slideshow/: web-size JPEGs of the author's photos and sampled video frames,
   with captions from the photo timeline (photos are not committed to git).
"""

from __future__ import annotations

import io
import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
from PIL import Image, ImageFilter
from pillow_heif import register_heif_opener

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "data/raw/official_timing"
DB = ROOT / "data/processed/timing.duckdb"
MEDIA = ROOT / "media"
FRAMES = ROOT / "data/processed/video_frames.json"
PUBLIC = ROOT / "frontend/public"
SLIDES = PUBLIC / "slideshow"
MAX_SIDE = 1600
SLIDE_COUNT = 36
MIN_SIDE = 900
SOURCE_URL = "https://www.24h-rennen.de/en/2026/05/17/winners-press-conference-quotes-4/"

register_heif_opener()

FIGURES = [
    ("352,000", "spectators over the weekend"),
    ("584", "drivers taking part in the 24h race"),
    ("161", "cars, as the organiser counts them (the official classification lists 159)"),
    ("113,861", "overtaking manoeuvres recorded in the race"),
    ("over 17,000", "laps of the Nordschleife by all participants combined"),
    ("440,000 km", "distance covered, about eleven times round the Earth"),
    ("2,500", "full-time and volunteer staff from ADAC Nordrhein and Nürburgring 1927"),
    ("1,200 marshals", "positioned around the Nordschleife in 17 sections"),
    ("90 marshals", "deployed in the pit lane"),
    ("54 team", "DMSB safety members serving in shifts, in eleven safety vehicles"),
]

SUMMARIES = {
    80: [
        ("Maro Engel", "Winner",
         "Called the win incredible and thanked the fans, and the team that repaired his car after a qualifying accident."),
        ("Maxime Martin", "Winner",
         "Described a hard but fair fight with the sister car once the rain arrived, credited the tyre choice, and apologised to the other team for its technical setback."),
        ("Fabian Schiller", "Winner",
         "His first major endurance win, after years of near misses in GT racing; he credited Mercedes and his teammates."),
        ("Luca Stolz", "Winner",
         "Said the tyre call, wet tyres over intermediates, decided the race, and that the team brought the car home."),
    ],
    34: [
        ("Christian Krognes", "2nd official",
         "Had started to believe in a podium the evening before; said the team kept the car on track and earned the result."),
        ("Mattia Drudi", "2nd official",
         "Called the final stint very tough, and the switch to intermediates a brave call that paid off as the track got wetter."),
        ("Nicki Thiim", "2nd official",
         "The first podium for Aston Martin at the 24h Nürburgring, unexpected for a team that came only to take part."),
    ],
    84: [
        ("Mirko Bortolotti", "disqualified",
         "Described contact in the opening phase after a jump start by the sister car, and said the team never gave up."),
        ("Luca Engstler", "disqualified",
         "After taking pole, the car dropped to 49th on the opening lap; the team fought back."),
        ("Patric Niederhauser", "disqualified",
         "Counted the result among his greatest achievements, after a long fight back from the early phase."),
    ],
}


def official_text(path: Path) -> str:
    raw = subprocess.run(["pdftotext", str(path), "-"], check=True, capture_output=True, text=True)
    return re.sub(r"\s+", " ", raw.stdout)


def verified_figures() -> list[dict[str, str]]:
    text = official_text(next(OFFICIAL.glob("*Event in Figures*.pdf")))
    rows = []
    for value, label in FIGURES:
        core = value.replace("over ", "")
        if core not in text:
            raise SystemExit(f"figure not found in the organiser's text: {value}")
        rows.append({"value": value, "label": label})
    return rows


def podium() -> list[dict[str, object]]:
    with duckdb.connect(str(DB), read_only=True) as con:
        rows = con.execute(
            "SELECT position, car_number, status, team, drivers, total_time_s "
            "FROM classification WHERE position <= 3 OR car_number = 84 "
            "ORDER BY position NULLS LAST"
        ).fetchall()
    return [
        {"position": r[0], "car_number": r[1], "status": r[2], "team": r[3],
         "drivers": r[4], "total_time_s": r[5]}
        for r in rows
    ]


RACE_START = datetime(2026, 5, 16, 15, 0)  # 15:00 CEST, Saturday 16 May 2026


def local_time(seconds: float) -> str:
    """Race elapsed seconds to the local time of day, e.g. 'Sat 16 May · 19:10'."""
    moment = RACE_START + timedelta(seconds=seconds)
    return moment.strftime("%a %d %b · %H:%M")


def sharpness(img: Image.Image) -> float:
    """Edge energy of a small grey copy. Blurry frames score low."""
    grey = img.convert("L")
    grey.thumbnail((480, 480))
    values = grey.filter(ImageFilter.FIND_EDGES).tobytes()
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


EXCLUDE_FILES = {"IMG_0679.HEIC"}  # leaflet for the 24h fan bus, not a photo of the race
YELLOW_SLOTS = 4
TRACK_SLOTS = 8
DUPLICATE_BITS = 10  # dHash distance at or below this counts as the same picture


def dhash(img: Image.Image) -> int:
    px = list(img.convert("L").resize((9, 8), Image.LANCZOS).tobytes())
    bits = 0
    for r in range(8):
        for c in range(8):
            bits = (bits << 1) | (px[r * 9 + c] > px[r * 9 + c + 1])
    return bits


def yellow_share(img: Image.Image) -> float:
    """Share of pixels that read as yellow paint (bright red and green, little blue)."""
    small = img.convert("RGB").copy()
    small.thumbnail((160, 160))
    pixels = small.getdata()
    hits = sum(1 for r, g, b in pixels if r > 170 and g > 150 and b < 110 and abs(r - g) < 60)
    return hits / len(pixels)


def slideshow(keep: int = SLIDE_COUNT) -> list[dict]:
    """Choose the slideshow: sharp, distinct, and including track-side and yellow-car photos.

    Pass one scores every source and keeps only numbers. Duplicates (burst shots) are dropped by
    perceptual hash, keeping the sharpest of each group. Each video clip contributes one frame.
    Pass two reopens only the chosen files.
    """
    SLIDES.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DB), read_only=True) as con:
        items = con.execute(
            "SELECT file, media_type, race_elapsed_s, nearest_section, on_course "
            "FROM media_timeline ORDER BY race_elapsed_s"
        ).fetchall()
    frames: dict[str, list[str]] = {}
    for f in json.loads(FRAMES.read_text(encoding="utf-8")):
        frames.setdefault(f["file"], []).append(f["frame"])

    def source_path(name: str, kind: str) -> Path | None:
        if kind == "photo":
            return MEDIA / name if (MEDIA / name).exists() else None
        options = frames.get(name, [])
        return ROOT / options[len(options) // 2] if options else None

    scored = []
    for name, kind, race_s, section, on_course in items:
        if name in EXCLUDE_FILES:
            continue
        path = source_path(name, kind)
        if path is None:
            continue
        with Image.open(path) as img:
            rgb = img.convert("RGB")
            if min(rgb.size) < MIN_SIDE:
                continue
            scored.append({
                "sharp": sharpness(rgb), "name": name, "kind": kind, "race_s": race_s,
                "section": section, "path": path, "on_course": bool(on_course),
                "hash": dhash(rgb), "yellow": yellow_share(rgb),
            })

    scored.sort(key=lambda c: c["sharp"], reverse=True)
    distinct: list[dict] = []
    for cand in scored:
        if any(bin(cand["hash"] ^ kept["hash"]).count("1") <= DUPLICATE_BITS for kept in distinct):
            continue
        distinct.append(cand)

    chosen: list[dict] = []

    def take(pool: list[dict], count: int) -> None:
        for cand in pool:
            if len([c for c in chosen if c is not None]) >= keep or count <= 0:
                return
            if cand in chosen:
                continue
            chosen.append(cand)
            count -= 1

    yellow_pool = sorted((c for c in distinct if c["kind"] == "photo"), key=lambda c: c["yellow"], reverse=True)
    take([c for c in yellow_pool if c["yellow"] >= 0.04], YELLOW_SLOTS)
    take([c for c in distinct if c["on_course"]], TRACK_SLOTS)
    take(distinct, keep - len(chosen))
    print(f"distinct after duplicates: {len(distinct)} of {len(scored)}; "
          f"yellow picks: {sum(1 for c in chosen if c['yellow'] >= 0.04)}; "
          f"track-side picks: {sum(1 for c in chosen if c['on_course'])}")

    manifest = []
    for cand in sorted(chosen, key=lambda c: c["race_s"]):
        with Image.open(cand["path"]) as img:
            image = img.convert("RGB")
        image.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        out = SLIDES / f"{Path(cand['name']).stem}.jpg"
        image.save(out, format="JPEG", quality=86)
        manifest.append({
            "src": f"/slideshow/{out.name}",
            "caption": f"{cand['section'] or 'Nordschleife'} · {local_time(cand['race_s'])}",
            "kind": cand["kind"],
            "file": cand["name"],
            "race_elapsed_s": round(cand["race_s"], 1),
            "width": image.width,
            "height": image.height,
            "sharpness": round(cand["sharp"], 1),
        })
    return manifest

def pace() -> dict[str, list[float]]:
    """Lap times per car, in lap order, for the pace sparklines (organiser sector CSV 535)."""
    with duckdb.connect(str(DB), read_only=True) as con:
        rows = con.execute(
            "SELECT car_number, lap_time_s FROM sectors "
            "WHERE lap_time_s IS NOT NULL ORDER BY car_number, lap"
        ).fetchall()
    series: dict[str, list[float]] = {}
    for car, lap_s in rows:
        series.setdefault(str(car), []).append(round(float(lap_s), 2))
    return series


def car_photos(manifest: list[dict]) -> dict[str, list[dict]]:
    """Photos and video frames that the photo pass identified as each car.

    Only accepted sightings count. Entries come from the car-identification output, which is
    produced by scripts/identify_cars.py. With no output yet, the result is empty.
    """
    path = ROOT / "data/processed/car_identifications.json"
    if not path.exists():
        return {}
    by_file = {m["file"]: m for m in manifest}
    grouped: dict[str, list[dict]] = {}
    seen: set[tuple[str, str]] = set()
    for sighting in json.loads(path.read_text(encoding="utf-8")):
        if not sighting.get("accepted"):
            continue
        base = str(sighting.get("file", "")).split("#")[0]
        slide = by_file.get(base)
        car = sighting.get("car_number")
        if slide is None or car is None:
            continue
        key = (str(car), slide["src"])
        if key in seen:
            continue
        seen.add(key)
        grouped.setdefault(str(car), []).append(
            {"src": slide["src"], "caption": slide["caption"], "kind": slide["kind"]}
        )
    return grouped


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    event = {
        "title": "54th ADAC RAVENOL 24h Nürburgring",
        "dates": "14–17 May 2026",
        "figures": verified_figures(),
        "podium": podium(),
        "statements": [
            {"car_number": car, "people": [
                {"name": n, "role": r, "summary": s} for n, r, s in people
            ]}
            for car, people in SUMMARIES.items()
        ],
        "sources": [
            "The Event in Figures, ADAC RAVENOL 24h Nürburgring (24h-rennen.de)",
            "Winners' Press Conference Quotes, 17 May 2026 (" + SOURCE_URL + ")",
            "Official final result, 54th ADAC RAVENOL 24h Nürburgring (wige timing)",
            "Second-placed Abt-Lamborghini subsequently disqualified (organiser news)",
        ],
        "note": "Statements are the author's short summaries of the press-conference remarks, "
                "given before the disqualification of car 84.",
    }
    (PUBLIC / "data/event.json").write_text(json.dumps(event, indent=1, ensure_ascii=False), encoding="utf-8")
    manifest = slideshow()
    (PUBLIC / "data/slideshow.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (PUBLIC / "data/pace.json").write_text(json.dumps(pace()), encoding="utf-8")
    photos = car_photos(manifest)
    (PUBLIC / "data/car_photos.json").write_text(json.dumps(photos, indent=1), encoding="utf-8")
    print(f"cars with identified photos: {len(photos)}")
    print(f"figures: {len(event['figures'])}; podium rows: {len(event['podium'])}")
    print(f"slideshow images: {len(manifest)}")


if __name__ == "__main__":
    main()
