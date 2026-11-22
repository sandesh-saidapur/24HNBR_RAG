# Trackside 24: Multimodal Race Companion for the 2026 24h Nürburgring

*A retrieval-augmented system that matches personal trackside photos and videos to the official race clock, track sections and timing data, then answers questions with cited evidence.*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![DuckDB](https://img.shields.io/badge/SQL-DuckDB-yellow.svg)](https://duckdb.org/)
[![React](https://img.shields.io/badge/UI-React_19_%2B_TypeScript-61DAFB.svg)](https://react.dev/)
[![Claude](https://img.shields.io/badge/LLM-Claude-D97757.svg)](https://www.anthropic.com/)

---

## The idea

The 54th ADAC RAVENOL 24h Nürburgring ran from 14 to 17 May 2026, with the race from Saturday 16 May 15:00 CEST to Sunday 17 May 15:00 CEST. The official classification lists 159 entries, and the circuit is 25.378 km long.

Trackside 24 starts from a photo taken at the track. It reads the capture time and GPS from the file, converts the time to the race clock, finds the track section, and looks up the official timing for that moment. Then it answers questions about what was happening, citing each source.

Two rules shape the design:
- **Every figure comes from the database.** The language model explains and cites. It never calculates or invents a lap time, position or penalty.
- **Every source is checked.** Official timing is verified against the organiser's own final result, and unverified material is marked as such.

---

## Architecture

```
  Personal photos & videos ─┐
                            ├─► Pipeline (scripts/) ─► timing.duckdb ─► FastAPI ─► React app
  Organiser CSVs & penalties┘   time alignment,          verified         /api/*     (Vite, TS)
                                track matching,         tables and
                                reconciliation          views
                                                                │
                                                 RAG engine (Claude)
                                                 Haiku 5.5 routes the question
                                                 Sonnet 5.5 answers and reads photos
                                                 Opus 5.5 judges answers offline
```

## Verified so far

- Classification: all 159 official total times match the organiser's final result.
- Lap and sector times: every car's sector sums match its lap times, and lap counts match the official counts.
- Penalties: the official list (19 entries, with car numbers) explains the gap between lap sums and official totals for 14 cars, to the second.
- Media: 99 items placed on the race clock, 23 of them on the circuit, each assigned to a named section.

Open items are listed in [PROJECT_SPEC_AND_GUIDE.md](PROJECT_SPEC_AND_GUIDE.md#4-data-sources-and-verification).

---

## Quickstart

```bash
git clone https://github.com/<your-username>/24HNBR_RAG.git
cd 24HNBR_RAG
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Place your photos and videos in `data/raw/personal_media/`, and the organiser files in `data/raw/official_timing/`. Then build the database:

```bash
python scripts/build_media_catalog.py
python scripts/align_media_to_race_clock.py
python scripts/build_official_timing.py
python scripts/match_media_to_track.py
python scripts/parse_hourly_splits.py
python scripts/build_media_context.py
python scripts/parse_official_sources.py
python scripts/build_timing_database.py
```

Run the API and the tests:

```bash
uvicorn src.api.main:app --reload    # docs at http://127.0.0.1:8000/docs
pytest
```

The frontend (React, TypeScript, Vite) is in progress.

---

## Tech stack

| Layer | Tools |
|---|---|
| Data pipeline | Python, PyArrow, Pillow and pillow-heif (EXIF), pdftotext |
| Storage | DuckDB (verified timing), LanceDB and BM25 (planned) |
| API | FastAPI, Pydantic v2, Uvicorn |
| Frontend | React 19, TypeScript, Vite |
| LLM | Claude: Sonnet 5.5 (answers and vision), Haiku 5.5 (routing), Opus 5.5 (evaluation judge) |
| Testing | pytest, httpx |

---

## Documentation

- [PROJECT_SPEC_AND_GUIDE.md](PROJECT_SPEC_AND_GUIDE.md): scope, decisions, architecture and roadmap.
- [docs/data-sources.md](docs/data-sources.md): where each file came from and how it was checked.
- [docs/PROGRESS_FOR_SANDESH.md](docs/PROGRESS_FOR_SANDESH.md): running log of what has been done.
