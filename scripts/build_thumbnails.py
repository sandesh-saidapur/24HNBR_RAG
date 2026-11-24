"""Small thumbnails for every media item, for the Moments page. Photos use the photo itself;
videos use the middle frame extracted by the frame step. Output: frontend/public/thumbs/."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
from PIL import Image
from pillow_heif import register_heif_opener

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/processed/timing.duckdb"
MEDIA = ROOT / "media"
FRAMES = ROOT / "data/processed/video_frames.json"
OUT = ROOT / "frontend/public/thumbs"
SIDE = 480

register_heif_opener()


def frames_by_file() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for f in json.loads(FRAMES.read_text(encoding="utf-8")):
        out.setdefault(f["file"], []).append(f["frame"])
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames = frames_by_file()
    with duckdb.connect(str(DB), read_only=True) as con:
        items = con.execute("SELECT file, media_type FROM media_timeline ORDER BY race_elapsed_s").fetchall()
    done = missing = 0
    for name, kind in items:
        if kind == "photo":
            source = MEDIA / name
        else:
            options = frames.get(name, [])
            source = ROOT / options[len(options) // 2] if options else None
        if source is None or not source.exists():
            missing += 1
            continue
        with Image.open(source) as img:
            image = img.convert("RGB")
        image.thumbnail((SIDE, SIDE), Image.LANCZOS)
        image.save(OUT / f"{Path(name).stem}.jpg", format="JPEG", quality=82)
        done += 1
    print(f"thumbnails: {done} written, {missing} without a source")


if __name__ == "__main__":
    main()
