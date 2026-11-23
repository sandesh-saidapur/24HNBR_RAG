"""Build the photo vector index: SigLIP embeddings of photos and sampled video frames in LanceDB.

Run on a machine with the "vector" extra installed (pip install -e ".[vector]") and access to
Hugging Face for the one-time model download. Race times come from the timing database.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.indexing.embedders import SigLIPEmbedder
from src.indexing.vector_store import PhotoIndex, PhotoItem

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/processed/timing.duckdb"
MEDIA = ROOT / "media"
FRAMES = ROOT / "data/processed/video_frames.json"
OUT = ROOT / "data/processed/vector_store"


def items() -> list[PhotoItem]:
    with duckdb.connect(str(DB), read_only=True) as con:
        rows = con.execute(
            "SELECT file, media_type, race_elapsed_s, nearest_section FROM media_timeline "
            "ORDER BY race_elapsed_s"
        ).fetchall()
    frames: dict[str, list[dict]] = {}
    for frame in json.loads(FRAMES.read_text(encoding="utf-8")):
        frames.setdefault(frame["file"], []).append(frame)

    out: list[PhotoItem] = []
    for name, kind, race_s, section in rows:
        caption = section or "Nordschleife"
        if kind == "photo":
            if (MEDIA / name).exists():
                out.append(PhotoItem(name, name, MEDIA / name, float(race_s), caption))
            continue
        # Video: every sampled frame gets the clip's race time. Frame offsets are kept in the key.
        for frame in frames.get(name, []):
            key = f"{name}#{frame['offset_s']}s"
            out.append(PhotoItem(key, name, ROOT / frame["frame"], float(race_s), caption))
    return out


def main() -> None:
    photos = items()
    index = PhotoIndex.build(OUT, photos, SigLIPEmbedder())
    print(f"indexed {len(index)} frames and photos into {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
