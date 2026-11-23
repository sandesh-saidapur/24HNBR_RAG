"""Run car identification over the photo timeline with Claude vision.

Needs ANTHROPIC_API_KEY. Reads photos from media/ (not in git) and the sampled video frames
from data/processed/video_frames.json, then writes data/processed/car_identifications.json.
Requires pillow and pillow-heif for HEIC files.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import duckdb
from PIL import Image
from pillow_heif import register_heif_opener

from src.alignment.car_identifier import identify
from src.rag.llm import get_vision_llm

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "media"
DB = ROOT / "data/processed/timing.duckdb"
OUT = ROOT / "data/processed/car_identifications.json"
FRAMES = ROOT / "data/processed/video_frames.json"
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".heic"}
MAX_SIDE = 1280

register_heif_opener()


def as_jpeg(path: Path) -> bytes:
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()


def work_items() -> list[tuple[str, Path | None, bool]]:
    """(label, path, is_frame). Photos first, then every sampled video frame."""
    with duckdb.connect(str(DB), read_only=True) as con:
        photos = [
            r[0]
            for r in con.execute(
                "SELECT file FROM media_timeline WHERE media_type = 'photo' ORDER BY race_elapsed_s"
            ).fetchall()
        ]
    items: list[tuple[str, Path | None, bool]] = []
    for name in photos:
        path = MEDIA / name
        ok = path.suffix.lower() in PHOTO_EXT and path.exists()
        items.append((name, path if ok else None, False))
    for frame in json.loads(FRAMES.read_text(encoding="utf-8")):
        items.append((f"{frame['file']}#{frame['offset_s']}s", ROOT / frame["frame"], True))
    return items


def main() -> int:
    llm = get_vision_llm()
    if llm is None:
        print("ANTHROPIC_API_KEY is not set: nothing to run.")
        return 1
    with duckdb.connect(str(DB), read_only=True) as con:
        known = {r[0] for r in con.execute("SELECT car_number FROM classification").fetchall()}
    results = []
    for label, path, is_frame in work_items():
        if path is None or not path.exists():
            results.append({"file": label, "accepted": False, "reason": "not a readable image"})
            continue
        image = path.read_bytes() if is_frame else as_jpeg(path)
        sighting = identify(label, image, "image/jpeg", known, llm)
        results.append(sighting.as_dict())
        outcome = f"car {sighting.car_number}" if sighting.accepted else sighting.reason
        print(f"{label}: {outcome}")
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    accepted = sum(1 for r in results if r.get("accepted"))
    print(f"accepted {accepted} of {len(results)}; wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
