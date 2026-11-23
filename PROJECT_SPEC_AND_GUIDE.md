# Trackside 24: Project Scope and Specification

**Status:** living document, rewritten 22 November 2026 to match the agreed scope.
**Previous version:** `docs/archive_PROJECT_SPEC_AND_GUIDE_v1.md` (kept for history; superseded).

---

## 1. What the project is

Trackside 24 is a portfolio project: a multimodal RAG (retrieval-augmented generation) system for the **54th ADAC RAVENOL 24h Nürburgring** (14–17 May 2026; race start Saturday 16 May 15:00 CEST, finish Sunday 17 May 15:00 CEST).

It matches the author's own trackside photos and videos to the official race clock, the track section, and the official timing data, then answers questions about a photo or a moment of the race with cited evidence.

**Design rule:** every number comes from the database, never from a language model. The model explains and cites; it does not calculate or invent figures.

---

## 2. Agreed decisions

| Area | Decision |
|---|---|
| LLM providers | Two providers, split by job. **Groq** (free tier) writes the text answers. **Claude** reads photos (car identification). No Gemini, no OpenAI, no local LLM. |
| Models | Text answers: `openai/gpt-oss-120b` on Groq (set by `TEXT_MODEL`). Photo reading: `claude-sonnet-5-5` (`VISION_MODEL`). Offline judging: `claude-opus-5-5` (`JUDGE_MODEL`). Query routing is rule-based, so no router model is needed. |
| Numbers | Lap times, positions, penalties and totals come from SQL on the timing database. The model is never the source of a figure. |
| Public demo | Uses only the author's own media. Organiser material (PDFs, figures, quotes) is shown only after its usage terms are checked. |
| Backend | Python 3.10+, FastAPI, Pydantic v2, DuckDB (read-only at serve time). |
| Frontend | React 19, TypeScript, Vite. Built to be the strongest part of the project visually. |
| Open source | Every dependency is open source. The stack is named in the README to show it. |

---

## 3. Architecture

```
  INPUTS                                  PIPELINE (scripts/, run in order)
  ──────                                  ─────────────────────────────────
  Personal photos & videos  ──►  build_media_catalog.py       EXIF / QuickTime time + GPS
                            ──►  align_media_to_race_clock.py  capture time → race elapsed time
                            ──►  match_media_to_track.py       GPS → nearest named track section
                            ──►  parse_hourly_splits.py        hourly running order
  Organiser CSVs (wige)     ──►  parse_official_sources.py     results, lap & sector times, penalties
  Organiser penalty list    ──►  build_media_context.py        each photo + split leader + section
                            ──►  build_timing_database.py      all tables → data/processed/timing.duckdb
                                                                     │
                                                                     ▼
                                                   FastAPI  (src/api)  ──►  React app (frontend/)
                                                                     │
                                                   Phase 4: RAG engine (Groq text, Claude photos)
                                                     Rule router → SQL / vector / text retrieval
                                                     → Groq answer with citations, checked against the evidence
                                                     Claude vision reads car numbers from photos
```

### Storage

| Store | Holds | Status |
|---|---|---|
| `data/processed/timing.duckdb` | Classification, hourly standings, sector and lap rows, penalties, reconciliation, media timeline. Views: `media_timeline`, `car_summary`. | Built and tested |
| LanceDB (planned) | Image embeddings (SigLIP) and text chunks for vector search | Planned |
| BM25 index (planned) | Regulations, steward decisions, press releases | Planned |

---

## 4. Data sources and verification

Every source is recorded in `docs/data-sources.md`. The status below is the current state.

| Data | Source | Status |
|---|---|---|
| Final classification (159 entries: 110 classified, 44 DNF, 4 DNC, 1 DSQ) | Organiser final result PDF and CSV 534 | Verified: all 159 total times match |
| Lap and sector times (every car, every lap) | Organiser CSVs 535 and 536 | Verified: sector sums match lap times for all cars; lap counts match officials |
| Penalties (19 entries, car numbers given) | Organiser penalty list 539 | Verified: for 14 cars the lap-sum gap equals the listed penalty |
| Car 84 disqualification | Steward Decision no. 156 | Verified (organiser document) |
| Hourly standings (12 splits) | Organiser hourly split PDFs | Parsed; per-split counts vary (124–150), cause unexplained |
| Media capture time and GPS | Author's own files | Verified (99 items, all dated 17 May in the EXIF data) |
| Track sections | OpenStreetMap export (ODbL), named raceway ways | Used for matching; 63 sections. Not the organiser's trace |
| Circuit corner names and polygons (`configs/circuit_sectors.yaml`) | Hand-compiled | **Unverified.** Not used for geofencing |
| Dossier "Penalties and Sectors Report" | Unknown provenance | **Not used.** Contradicts the official result on cars 90 and 35 |

**Open items:** car 84 has an unexplained 118.8 s lap-sum gap after its listed penalty; car 35's DNF time includes time not in its three lap records; no 2026 race-control bulletins located yet.

---

## 5. Repository layout (current)

```
24HNBR_RAG/
├── README.md
├── PROJECT_SPEC_AND_GUIDE.md          # this file
├── pyproject.toml                     # dependencies, pytest and ruff settings
├── .env.example
├── configs/
│   ├── race_calendar.yaml             # race start/finish, schedule (verified)
│   └── circuit_sectors.yaml           # corner names (UNVERIFIED)
├── data/
│   ├── raw/                           # official downloads and the author's media (not in git)
│   └── processed/                     # pipeline outputs, incl. timing.duckdb
├── docs/                              # data-sources.md, progress log, archived spec
├── scripts/                           # pipeline scripts (see section 6)
├── src/
│   ├── api/                           # FastAPI app: main.py, routes.py, schemas.py
│   ├── indexing/tabular_store.py      # read-only DuckDB access
│   ├── rag/                           # Phase 4 (not started)
│   └── ui/                            # superseded by frontend/ (see section 7)
├── frontend/                          # React 19 + TypeScript + Vite (Phase 5, not started)
└── tests/                             # pytest, runs against the built database
```

---

## 6. Pipeline

Run in this order. Each step reads `data/raw/` and writes `data/processed/`.

1. `build_media_catalog.py`: EXIF and QuickTime metadata for each file.
2. `align_media_to_race_clock.py`: race elapsed time per item (`pre_start`, `race`, `post_finish`).
3. `build_official_timing.py`: classification from the verified CSV.
4. `match_media_to_track.py`: nearest named section; `on_course` if within 50 m.
5. `parse_hourly_splits.py`: hourly standings.
6. `build_media_context.py`: each item joined to its split leader and section.
7. `parse_official_sources.py`: organiser CSVs and penalty list, plus the reconciliation.
8. `build_timing_database.py`: builds `timing.duckdb` and runs count and lap checks.

Superseded and not in the pipeline: `parse_lap_by_lap.py`, `parse_penalties.py`, `parse_sector_times.py`. They parsed PDFs and are replaced by step 7.

---

## 7. API and frontend

### API (built, Phase 3)

Run locally: `uvicorn src.api.main:app --reload`. Interactive docs at `/docs`.

| Route | Returns |
|---|---|
| `GET /api/health` | Status and table counts |
| `GET /api/cars` | Classification in official order |
| `GET /api/cars/{n}` | One car, with its penalties |
| `GET /api/cars/{n}/laps` | Lap and sector times |
| `GET /api/penalties` | All penalties, optionally by car |
| `GET /api/standings/hours` | Available split hours |
| `GET /api/standings/{hour}` | Running order at a split |
| `GET /api/media` | Photo timeline; filter by `on_course` and `phase` |
| `GET /api/track` | Circuit outline (OpenStreetMap, ODbL attribution included) |
| `POST /api/ask` | Routes a question, gathers evidence, answers via Groq, and checks every figure against the evidence |

Tests: `pytest` (9 tests against the real database).

### Frontend (Phase 5, planned)

React 19, TypeScript, Vite. Planned views:
- circuit map with photo pins (Leaflet or MapLibre, open source),
- a 24-hour scrubber linked to the timeline and the running order,
- the classification and per-car lap charts,
- a chat panel for the RAG answers, with citations that open the source row.

Design direction: dark motorsport theme, token-based CSS, responsive layout.

---

## 8. Roadmap and status

| Phase | Scope | Status |
|---|---|---|
| 1 | Scaffolding and environment | Done |
| 2 | Ingestion, alignment and the timing database | Done |
| 3 | API over the database | Done (9 tests) |
| 4 | RAG engine: rule-based routing, SQL retrieval, keyword search over official documents, Groq answers with citations, Claude photo reading and video frames | Built and offline-tested (24 tests). Live Groq and Claude calls wait for keys. Vector index (SigLIP and LanceDB) not built | Partly done: evidence, routing, grounded answers and verification built, with Groq for text. Car identification built (Claude vision). Live calls wait for API keys; testing is planned for near the end. Search indexes still to build |
| 5 | React 19 + TypeScript + Vite frontend: classification, car panel, circuit map with photo pins, 24-hour scrubber, ask panel | Built and type-checked (production build passes). Browser testing near the end |
| 6 | Evaluation (Opus 5.5 judge), README polish, short demo recording | Planned |

Still needed for Phase 4: the car-identification step (Sonnet 5.5 vision on each photo, checked against the lap data), and the LanceDB and BM25 indexes.

---

## 9. Evaluation

- `evaluation/test_queries.json`: 25–50 questions with reference answers taken from the official data.
- Metrics: exact match for numbers (SQL result), citation coverage, and an Opus 5.5 judge for answer quality. The judge runs offline only.

---

## 10. Usage and licensing

- Code: MIT is planned. There is no `LICENSE` file yet; it needs the author's full name.
- OpenStreetMap track data: ODbL, attribution required.
- Organiser documents, figures and quotes: check the terms before any public display. Until then, they stay in the private build.
- Personal media: shown only on the author's own demo.

---

## 11. What the spec no longer contains

The v1 spec described Streamlit, Gemini 1.5 Flash, Claude 3.5 Sonnet, a Florence-2 option and a 16:00 race start. All were wrong or superseded. The race starts at 15:00 CEST. The UI is React, not Streamlit. The model stack is Claude only.
