"""Extract text from the official documents and split it into overlapping passages.

Sources are the organiser's race-control decisions, penalty lists, press releases, the schedule
and the decision on car 84. Large timing tables (lap, sector, full result) are not indexed:
they are queried from the database instead.
Writes data/processed/text_passages.json.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/official_timing"
OUT = ROOT / "data/processed/text_passages.json"
CHUNK = 700
OVERLAP = 100

SOURCE_GLOBS = [
    "race_control_decisions/*.pdf",
    "official_penalties/*.pdf",
    "*News and quotes*.pdf",
    "*Second-placed*.pdf",
    "*Winners*.pdf",
    "*Event in Figures*.pdf",
    "*dhlm*.pdf",
    "24h-Zeitplan*.pdf",
]


def pdf_text(path: Path) -> str:
    text = subprocess.run(
        ["pdftotext", str(path), "-"], check=True, capture_output=True, text=True
    ).stdout
    return re.sub(r"\s+", " ", text).strip()


def chunks(text: str) -> list[str]:
    out, start = [], 0
    while start < len(text):
        out.append(text[start : start + CHUNK])
        if start + CHUNK >= len(text):
            break
        start += CHUNK - OVERLAP
    return out


def main() -> None:
    files: list[Path] = []
    for pattern in SOURCE_GLOBS:
        files += sorted(RAW.glob(pattern))
    passages = []
    for path in dict.fromkeys(files):
        for index, piece in enumerate(chunks(pdf_text(path))):
            passages.append({
                "id": f"{path.stem[:40]}#{index}",
                "source": path.name,
                "text": piece,
            })
    OUT.write_text(json.dumps(passages, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"documents: {len(set(p['source'] for p in passages))}; passages: {len(passages)}")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
