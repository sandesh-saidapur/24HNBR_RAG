"""Browser-playable copies of every video in the media timeline: H.264 + AAC MP4, at most 720 px tall.
Output: frontend/public/videos/. The originals are never changed."""

from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/processed/timing.duckdb"
MEDIA = ROOT / "media"
OUT = ROOT / "frontend/public/videos"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DB), read_only=True) as con:
        names = [r[0] for r in con.execute(
            "SELECT file FROM media_timeline WHERE media_type <> 'photo' ORDER BY file").fetchall()]
    done = failed = 0
    for name in names:
        src = MEDIA / name
        dst = OUT / f"{Path(name).stem}.mp4"
        if not src.exists():
            print("missing", name); failed += 1; continue
        if dst.exists() and dst.stat().st_size > 0:
            done += 1; continue
        part = dst.with_suffix(".part.mp4")
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", "scale=-2:'min(720,ih)'", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "27", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
            "-movflags", "+faststart", str(part),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not part.exists() or part.stat().st_size < 10_000:
            print("failed", name, result.stderr[-200:]); failed += 1
            part.unlink(missing_ok=True)
        else:
            part.replace(dst)
            done += 1
    print(f"videos: {done} ready, {failed} failed")


if __name__ == "__main__":
    main()
