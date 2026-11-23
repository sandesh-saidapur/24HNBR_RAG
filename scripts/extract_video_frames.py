"""Sample frames from each video in the photo timeline, one every two seconds.

Each frame is placed on the race clock: race_elapsed_s of the clip plus the frame's offset.
Assumes the QuickTime creation time is the start of the clip (to be confirmed).
Writes data/processed/frames/<clip>/NNNN.jpg and data/processed/video_frames.json.
Clips already extracted are skipped, so an interrupted run can be resumed.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "media"
DB = ROOT / "data/processed/timing.duckdb"
OUT_DIR = ROOT / "data/processed/frames"
MANIFEST = ROOT / "data/processed/video_frames.json"
INTERVAL_S = 2


def extract(src: Path, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-vf", f"fps=1/{INTERVAL_S},scale='min(1280,iw)':-2",
         "-q:v", "3", str(folder / "%04d.jpg")],
        check=True,
    )
    if not any(folder.glob("*.jpg")):  # very short clips can yield no sample: keep the first frame
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-frames:v", "1",
             "-vf", "scale='min(1280,iw)':-2", "-q:v", "3", str(folder / "0001.jpg")],
            check=True,
        )


def main() -> None:
    with duckdb.connect(str(DB), read_only=True) as con:
        clips = con.execute(
            "SELECT file, race_elapsed_s FROM media_timeline WHERE media_type = 'video' "
            "ORDER BY race_elapsed_s"
        ).fetchall()
    manifest: list[dict[str, object]] = []
    for name, race_start in clips:
        src = MEDIA / name
        if not src.exists():
            print(f"missing {name}")
            continue
        folder = OUT_DIR / Path(name).stem
        if not any(folder.glob("*.jpg")):
            extract(src, folder)
        frames = sorted(folder.glob("*.jpg"))
        for index, frame in enumerate(frames):
            offset = index * INTERVAL_S
            manifest.append({
                "file": name,
                "frame": str(frame.relative_to(ROOT)),
                "offset_s": offset,
                "race_elapsed_s": round(race_start + offset, 3),
            })
        print(f"{name}: {len(frames)} frames")
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"frames: {len(manifest)}; wrote {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
