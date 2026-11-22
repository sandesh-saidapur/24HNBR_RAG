"""Build a metadata catalogue for trackside media.

Photos (HEIC, JPEG, PNG) are read with Pillow and pillow-heif (EXIF).
Videos (MOV, MP4) are read with ffprobe (container and stream tags).

One row per file. Anything the file does not contain stays null. Nothing is guessed.
Capture times are stored in UTC, and ``time_source`` records where each time came from.

Usage:
    python scripts/build_media_catalog.py --media-dir media \
        --out data/processed/media_catalog.parquet
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pillow_heif
import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image

pillow_heif.register_heif_opener()

EXIF_IFD = 0x8769
GPS_IFD = 0x8825
TAG_DATETIME = 0x0132
TAG_MAKE = 0x010F
TAG_MODEL = 0x0110
TAG_ORIENTATION = 0x0112
TAG_DATETIME_ORIGINAL = 0x9003
TAG_OFFSET_TIME_ORIGINAL = 0x9011
GPS_LAT_REF, GPS_LAT, GPS_LON_REF, GPS_LON, GPS_ALT_REF, GPS_ALT = 1, 2, 3, 4, 5, 6

PHOTO_EXTS = {".heic", ".jpg", ".jpeg", ".png"}
VIDEO_EXTS = {".mov", ".mp4"}
ISO6709 = re.compile(r"^([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)?/?$")
HDR_TRANSFERS = {"arib-std-b67": "HLG", "smpte2084": "PQ"}
CIRCUIT_CENTRE = (50.3356, 6.9475)  # rough centre of the Nürburgring, for sanity checks only
CAPTURE_TZ = ZoneInfo("Europe/Prague")


@dataclass
class MediaRecord:
    file: str
    media_type: str
    ext: str
    size_bytes: int
    make: str | None = None
    model: str | None = None
    width: int | None = None
    height: int | None = None
    orientation: int | None = None
    rotation_deg: int | None = None
    duration_s: float | None = None
    codec: str | None = None
    fps_avg: float | None = None
    hdr: str | None = None
    capture_utc: str | None = None
    capture_local_cest: str | None = None
    capture_local_naive: str | None = None
    utc_offset: str | None = None
    time_source: str = "none"
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    gps_source: str = "none"
    error: str | None = None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().strip("\x00").strip()
    return text or None


def _dms_to_degrees(values: Any, ref: Any) -> float:
    degrees, minutes, seconds = (float(v) for v in values)
    value = degrees + minutes / 60 + seconds / 3600
    return -value if _as_text(ref) in {"S", "W"} else value


def _exif_time(naive_text: str, offset_text: str | None, rec: MediaRecord) -> None:
    """Fill the time fields. A time without an offset is kept, but not converted to UTC."""
    naive = datetime.strptime(naive_text, "%Y:%m:%d %H:%M:%S")
    rec.capture_local_naive = naive.isoformat()
    if offset_text and re.fullmatch(r"[+-]\d{2}:\d{2}", offset_text):
        aware = datetime.fromisoformat(naive.isoformat() + offset_text)
        rec.capture_utc = aware.astimezone(timezone.utc).isoformat()
        rec.capture_local_cest = aware.astimezone(CAPTURE_TZ).isoformat()
        rec.utc_offset = offset_text
        rec.time_source = "exif_datetime_original"
    else:
        rec.time_source = "exif_no_offset"


def read_photo(path: Path, rec: MediaRecord) -> None:
    with Image.open(path) as img:
        exif = img.getexif()
        rec.width, rec.height = img.size
        rec.make = _as_text(exif.get(TAG_MAKE))
        rec.model = _as_text(exif.get(TAG_MODEL))
        orientation = exif.get(TAG_ORIENTATION)
        rec.orientation = int(orientation) if orientation is not None else None

        exif_ifd = exif.get_ifd(EXIF_IFD)
        original = _as_text(exif_ifd.get(TAG_DATETIME_ORIGINAL))
        if original:
            _exif_time(original, _as_text(exif_ifd.get(TAG_OFFSET_TIME_ORIGINAL)), rec)

        gps = exif.get_ifd(GPS_IFD)
        if gps and GPS_LAT in gps and GPS_LON in gps:
            rec.latitude = _dms_to_degrees(gps[GPS_LAT], gps.get(GPS_LAT_REF, "N"))
            rec.longitude = _dms_to_degrees(gps[GPS_LON], gps.get(GPS_LON_REF, "E"))
            if GPS_ALT in gps:
                altitude = float(gps[GPS_ALT])
                below_sea = gps.get(GPS_ALT_REF) in (1, b"\x01")
                rec.altitude_m = -altitude if below_sea else altitude
            rec.gps_source = "exif"


def _fraction_to_float(text: str | None) -> float | None:
    if not text or "/" not in text:
        return None
    numerator, denominator = text.split("/", 1)
    if float(denominator) == 0:
        return None
    return round(float(numerator) / float(denominator), 3)


def read_video(path: Path, rec: MediaRecord) -> None:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    fmt: dict[str, Any] = data.get("format", {})
    video: dict[str, Any] = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"), {}
    )
    tags: dict[str, Any] = {**fmt.get("tags", {}), **video.get("tags", {})}

    rec.width = video.get("width")
    rec.height = video.get("height")
    rec.codec = video.get("codec_name")
    rec.fps_avg = _fraction_to_float(video.get("avg_frame_rate"))
    rec.hdr = HDR_TRANSFERS.get(str(video.get("color_transfer", "")))
    if fmt.get("duration"):
        rec.duration_s = round(float(fmt["duration"]), 3)
    if "rotate" in tags:
        rec.rotation_deg = int(tags["rotate"]) % 360
    rec.make = _as_text(tags.get("com.apple.quicktime.make"))
    rec.model = _as_text(tags.get("com.apple.quicktime.model"))

    creation = _as_text(tags.get("creation_time"))
    if creation:
        aware = datetime.fromisoformat(creation.replace("Z", "+00:00"))
        rec.capture_utc = aware.astimezone(timezone.utc).isoformat()
        rec.capture_local_cest = aware.astimezone(CAPTURE_TZ).isoformat()
        rec.utc_offset = "+00:00"
        rec.time_source = "quicktime_creation_time"

    location = _as_text(tags.get("com.apple.quicktime.location.ISO6709"))
    match = ISO6709.match(location) if location else None
    if match:
        rec.latitude = float(match.group(1))
        rec.longitude = float(match.group(2))
        if match.group(3):
            rec.altitude_m = float(match.group(3))
        rec.gps_source = "quicktime_location"


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(a))


def build_records(media_dir: Path) -> list[MediaRecord]:
    records: list[MediaRecord] = []
    for path in sorted(media_dir.iterdir()):
        if path.name.startswith(".") or not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext in PHOTO_EXTS:
            media_type = "photo"
        elif ext in VIDEO_EXTS:
            media_type = "video"
        else:
            continue
        rec = MediaRecord(
            file=path.name,
            media_type=media_type,
            ext=ext,
            size_bytes=path.stat().st_size,
        )
        try:
            if media_type == "photo":
                read_photo(path, rec)
            else:
                read_video(path, rec)
        except Exception as exc:  # keep going: one bad file must not stop the catalogue
            rec.error = f"{type(exc).__name__}: {exc}"[:300]
        records.append(rec)
    return records


def print_summary(records: list[MediaRecord]) -> None:
    total = len(records)
    photos = sum(r.media_type == "photo" for r in records)
    videos = total - photos
    with_time = [r for r in records if r.capture_utc]
    with_gps = [r for r in records if r.latitude is not None]
    print(f"files: {total} (photos {photos}, videos {videos})")
    print(f"errors: {sum(r.error is not None for r in records)}")
    print(f"with UTC capture time: {len(with_time)}")
    print(f"with GPS: {len(with_gps)}")

    print("time sources:")
    for source in sorted({r.time_source for r in records}):
        print(f"  {source}: {sum(r.time_source == source for r in records)}")
    print("GPS sources:")
    for source in sorted({r.gps_source for r in records}):
        print(f"  {source}: {sum(r.gps_source == source for r in records)}")

    if with_time:
        local = sorted(r.capture_local_cest for r in with_time if r.capture_local_cest)
        print(f"capture range (Europe/Prague): {local[0]} .. {local[-1]}")
    if with_gps:
        lats = [r.latitude for r in with_gps if r.latitude is not None]
        lons = [r.longitude for r in with_gps if r.longitude is not None]
        print(
            f"GPS bounding box: lat {min(lats):.4f}..{max(lats):.4f}, "
            f"lon {min(lons):.4f}..{max(lons):.4f}"
        )
        far = [
            distance_km(r.latitude, r.longitude, *CIRCUIT_CENTRE)
            for r in with_gps
            if r.latitude is not None and r.longitude is not None
        ]
        print(
            "distance from approximate circuit centre (km): "
            f"<3: {sum(d < 3 for d in far)}, <10: {sum(d < 10 for d in far)}, "
            f"10+: {sum(d >= 10 for d in far)}"
        )
    print(f"HDR videos: {sum(r.hdr is not None for r in records)}")
    print(
        "rotations: "
        + ", ".join(
            f"{deg}°: {sum(r.rotation_deg == deg for r in records)}"
            for deg in sorted({r.rotation_deg for r in records if r.rotation_deg is not None})
        )
    )
    for rec in records:
        if rec.error:
            print(f"ERROR {rec.file}: {rec.error}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media-dir", type=Path, default=Path("media"))
    parser.add_argument("--out", type=Path, default=Path("data/processed/media_catalog.parquet"))
    args = parser.parse_args()

    records = build_records(args.media_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist([asdict(r) for r in records])
    pq.write_table(table, args.out)
    print(f"wrote {len(records)} rows to {args.out}")
    print_summary(records)


if __name__ == "__main__":
    main()
