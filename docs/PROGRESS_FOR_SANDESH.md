# Trackside 24: where the project stands

Written for you, Sandesh. It is updated after each step, so it stays a running record of what has been built, what was checked, and what is still open.

Last updated: 22 November 2026, 13:50 Prague time.

## What the project does

It matches your own photos and videos to the exact race time and track position, then uses the official timing record to say what was happening at that moment. Each step below only counts as done once its check has passed.

## Done

1. **Race times corrected.** The start is 16 May 2026 at 15:00 CEST and the finish is 17 May at 15:00 CEST. The config previously said 16:00. The official schedule PDF confirms both.
2. **Media catalogue.** All 99 files have timestamps, GPS, orientation and HDR flags. Output: `data/processed/media_catalog.parquet`.
3. **Race-clock alignment.** Each file has its race time. 94 were taken during the race and 5 after the finish. Output: `data/processed/media_race_clock.parquet`.
4. **Official final classification.** 110 classified cars, 49 not classified. Every car number and total time matches the final result PDF, which is the version printed 12 June after the Abt disqualification. Output: `data/processed/official_classification.parquet`.
5. **Lap-by-lap times.** All 159 cars, 17,200 laps. For 143 cars the lap sums match the official totals within half a second. Output: `data/processed/lap_by_lap.parquet`.
6. **Track geometry.** Your OpenStreetMap export has 63 named sections of the course. Each media file is matched to its nearest section, with the distance in metres. The 84-file grandstand group is nearest the pit lane, about 84 m away, which fits the view across the pit lane. Output: `data/processed/media_track_match.parquet`.
7. **Clock check.** The hourly split print times line up with the 15:00 start, within 1 to 20 minutes. The 21-hour split printed 68 minutes late, but its data matches the lap file exactly, so the clock is consistent.
8. **Hourly standings.** 12 splits (1 to 23 hours, plus the overall 3-hour split), 1,749 car rows, 151 cars. Overall rank is derived from laps, then elapsed time. Output: `data/processed/hourly_standings.parquet`.
9. **Sector times.** 14,599 lap rows with nine sector times and eight speed-trap values per lap. Each sector row sums to its lap time, and 14,598 of the 14,599 laps match the lap file. Output: `data/processed/sector_laps.parquet`.
10. **Penalties from the summaries.** 103 timed entries from the organiser's summary PDFs, each with a race time. Output: `data/processed/penalties.parquet`.
11. **Status correction.** Car 35 is DNF (3 laps, 37:09.499) and car 84 is DSQ (156 laps). I had these two swapped when I extracted the classification. The official PDF's section headers confirm the corrected statuses. The counts are unchanged: 110 classified, 49 not classified.
12. **Official penalties and sectors report (2 pages).** I checked it against the official final PDF. It says car 90 finished 35th, but the official PDF has it as a DNF after 130 laps. It says car 35 retired, which the official PDF supports, but it describes sector-row causes and a sector-layout I can't verify. I haven't used its claims. The sector gap for cars 84, 90 and 35 is still open.
13. **Photo timeline.** Each of the 99 media items has its race time, the leader at its most recent hourly split (the leader is #3 or #80, both Winward Racing), and its nearest course section. 23 items are on the course; the rest are off it or after the finish. Output: `data/processed/media_context.parquet`.
14. **Cleanup.** The 99 race files were removed from Downloads after each was checked against its project copy by name and size. The project's `.DS_Store` files, Python cache, and superseded `requirements.txt` are removed.

## Known gaps and what they mean

- **Hourly standings:** 124 to 150 cars per split, not all 159. The difference is probably cars that had not yet crossed the line at the cut-off, or ones that retired. I haven't confirmed which.
- **Penalties:** only 17 of 103 entries name a car number. The rest name a driver or team, and team names are shared between cars, so matching by name isn't reliable yet.
- **Whole-second gaps:** 15 cars have official totals that exceed their lap sums by whole seconds. For 14 cars with a listed penalty, the penalty is already in the lap times, so there's no gap. The 15 unexplained gaps still need the official penalty list.
- **Stoppages:** no group stoppage shows in the lap data. Code 60 periods don't stop the clock, so long laps alone can't identify a red flag. Race-control bulletins for the 24h race itself haven't been found.
- **Sector-times PDF:** parsed, with a gap. The sector times add up to the lap time on every row. For 156 cars the sector laps match the lap file. Cars 84, 90 and 35 are incomplete or differ by one lap, and the cause isn't known yet.
- **Track sector names:** the names come from OpenStreetMap, not from the organiser's own track map.

## Next steps (updated, 22 Nov 2026)

Done since the last list: penalty mapping (solved by the official list), sector gaps (solved by the organiser CSV), and the photo timeline. Phase 2 of the roadmap is complete, with one data store: `data/processed/timing.duckdb`.

1. Serve the database through FastAPI (cars, classification, laps, penalties, media timeline), with the OpenAPI schema.
2. Identify the car in each photo with Claude vision, then check it against the lap and sector data.
3. Build the React + TypeScript frontend on that API: a circuit map with photo pins, a 24-hour scrubber and the classification.
4. Check the usage terms of the organiser's PDFs and figures before showing them on the public demo.

Note: the spec's roadmap (PROJECT_SPEC_AND_GUIDE.md, section 5) still names Streamlit, Gemini and Claude 3.5. It needs updating to the current decisions: React, FastAPI and Claude only.

## Things to decide

- Publishing the organiser's quotes, figures and penalty data on a public demo. Check the usage terms before showing them.

## How to re-run the pipeline

Run the scripts in `scripts/` in this order: `build_media_catalog.py`, `align_media_to_race_clock.py`, `build_official_timing.py`, `match_media_to_track.py`, `parse_hourly_splits.py`, `build_media_context.py`, `parse_official_sources.py`, `build_timing_database.py`. They read from `data/raw/` and write to `data/processed/`. The PDF-based parsers `parse_lap_by_lap.py`, `parse_penalties.py` and `parse_sector_times.py` are superseded and no longer needed.

## Update: official race files found and loaded (22 Nov 2026, afternoon)

The official race files were in the downloads zip `virtueller_aushang_dokumente_…SYSGEN.zip` (extracted to `docs/`). They are now in the project and the download copies have been removed.

What was added (all byte-verified against the download):
- `data/raw/official_timing/official_penalties/539_24h_Race_Penalty_List_Final.pdf`: official Strafliste, with car numbers (19 entries).
- `data/raw/official_timing/official_penalties/515_…Car_84_Disqualification…pdf`: Decision no. 156 (car 84 disqualified).
- `data/raw/official_timing/official_csv_wige/534_…RESULT.CSV`, `535_…SEKTORZEITEN.CSV`, `536_…LAPS.CSV`: official timing-service CSVs (per car, per lap, nine sectors plus speed traps).
- `data/raw/official_timing/official_csv_wige/537_…`, `538_…`: final race result and class result.
- `data/raw/official_timing/race_control_decisions/`: 17 individual steward decisions (LOG_A).

Scripts and outputs:
- `scripts/parse_official_sources.py`, writing `data/processed/official_penalties.parquet` (19 rows), `official_sectors.parquet` (17,201 rows, 159 cars) and `official_reconciliation.parquet`.

Results:
1. **Penalty mapping is solved.** The official list gives car numbers, so no guessing is needed. For 14 cars, the gap between the sum of lap times and the official total equals the listed penalty to the second. The 15 "unexplained" gap cars are explained by penalties.
2. **Sector gaps are solved.** The official CSV has every sector row. Sector sums match lap times for all 159 cars. The earlier gaps for cars 84, 90 and 35 came from our PDF extraction, not from the organiser's data.
3. **Classification verified against the official CSV.** All 159 total times match, with no missing or extra cars.

Open points (still unexplained):
- Car 84: the lap-sum gap is 204.8 s, against a listed 86 s stop-and-go penalty. The other 118.8 s is not explained yet. Decision no. 156 disqualified the car from the classification.
- Car 35: the lap-sum gap is 527.3 s over 3 laps. The DNF time probably includes time on track after its last recorded lap. This is not yet confirmed.

Housekeeping:
- Deleted from Downloads: the 157 MB zip, its extracted `docs/` folder (about 460 files, mostly regulations, bulletins and provisional results), and four duplicates (`export.gpx`, the circuit SVG, the schedule PDF and the dossier PDF). Each duplicate was byte-identical to its project copy.
- Not touched: unrelated files in Downloads (coursework, hackathon, `secrets.json`, screenshots).

## Update: timing database (22 Nov 2026)

- `scripts/parse_official_sources.py` (organiser CSVs and penalty list) and `scripts/build_timing_database.py` (single DuckDB store) are now part of the pipeline.
- `data/processed/timing.duckdb` holds the verified tables: 159-car classification, hourly standings, sector and lap rows, the 19-row penalty list, the reconciliation, and the 99-item media timeline. Two views: `media_timeline` and `car_summary`.
- The build checks counts and lap totals on every run. All checks pass.
- Superseded and not loaded: `penalties.parquet`, `sector_laps.parquet`, `lap_by_lap.parquet` (all parsed from PDFs, replaced by the organiser CSVs). They can be deleted.

## Update: scope rewritten and API built (22 Nov 2026)

- **Scope:** `PROJECT_SPEC_AND_GUIDE.md` is rewritten to the agreed decisions: Claude only (Sonnet 5.5 answers and vision, Haiku 5.5 routing, Opus 5.5 offline judging), FastAPI, DuckDB, React 19 with TypeScript and Vite. The previous version is archived in `docs/`. The README is rewritten to match and corrected: 159 entries, a 25.378 km circuit, and no unverified figures.
- **API (Phase 3):** `src/api/` provides `/api/health`, `/api/cars`, `/api/cars/{n}`, `/api/cars/{n}/laps`, `/api/penalties`, `/api/standings/hours`, `/api/standings/{hour}` and `/api/media`. It is read-only and reads `timing.duckdb` through `src/indexing/tabular_store.py`.
- **Tests:** 9 pytest tests against the real database. All pass.
- **Database fix:** car numbers are integers in every table, so joins and API types agree.
- **Packaging:** `pyproject.toml` added, with dependencies and build settings.
- **Not yet done:** Phase 4 (RAG engine with Claude), the car-identification step, the LanceDB and BM25 indexes, and the frontend.

## Update: Phase 4 started, RAG answer layer (23 Nov 2026)

- `src/rag/evidence.py`: builds evidence from the database. Every figure is formatted in code, so the model never has to write one.
- `src/rag/router.py`: rule-based routing for car, split, photo and overview questions. Explicit arguments override the question text.
- `src/rag/answer.py`: grounded prompt plus a verifier. It rejects answers with no citations, unknown citations, or any figure not in the evidence.
- `src/rag/llm.py`: Claude is the only provider. Models: Haiku 5.5 (router), Sonnet 5.5 (answers), Opus 5.5 (judge). Live calls need `ANTHROPIC_API_KEY`.
- `POST /api/ask`: returns evidence always, and an answer when a key is set. Status is `answered`, `evidence_only` or `needs_question`.
- `.env.example` now lists Claude only. The Gemini, OpenAI and Streamlit entries are removed.
- Tests: 23 passed, offline. Lint clean.
- Not done: a live Claude call (no API key here), the Haiku fallback for unclear questions, car identification from photos, and the LanceDB and BM25 indexes.

## Update: provider split and car identification (23 Nov 2026)

- Decision: Groq (free tier) writes the text answers. Claude reads the photos. Live testing is planned for near the end of the project.
- `src/rag/llm.py`: `GroqClient` (`GROQ_API_KEY`), `ClaudeClient` with vision (`ANTHROPIC_API_KEY`), and model overrides `TEXT_MODEL`, `VISION_MODEL`, `JUDGE_MODEL`. The default text model is `llama-3.3-70b-versatile`; check Groq's current model list before the live test.
- `src/alignment/car_identifier.py`: a photo is accepted only if the car number is in the official classification, the model's own digit reading agrees, and confidence is at least 0.6. Rejected sightings are kept with the reason.
- `scripts/identify_cars.py`: runs over the photo timeline and writes `data/processed/car_identifications.json`. Photos only; video frames come later. Needs `ANTHROPIC_API_KEY`, so it has not been run.
- `.env.example` lists both provider keys and the model overrides. Lint is clean, and the 23 existing tests still pass.
- Not yet done: live Groq and Claude calls (waiting for keys), the end-to-end test, video frame extraction, and the search indexes.

## Update: video frames, document search, frontend (23 Nov 2026)

- **Video frames:** 39 clips sampled every 2 s, giving 175 frames on the race clock (`scripts/extract_video_frames.py`). Frames are kept out of git. Assumes the QuickTime time is the clip start (to confirm).
- **Car identification:** now reads photos and video frames (`scripts/identify_cars.py`). Needs `ANTHROPIC_API_KEY`; not yet run.
- **Document search:** a keyword (BM25) index over 17 official documents, 315 passages (`scripts/build_text_index.py`, `src/indexing/bm25.py`). Questions with no named car, split or photo are answered from these documents. Press releases are indexed for internal use only until their terms are checked.
- **Circuit outline:** `GET /api/track` serves the OpenStreetMap track with attribution.
- **Frontend:** React 19 + TypeScript + Vite in `frontend/`. It has a classification table with search and class filter, a car panel with penalties and lap-time trend, a circuit map with photo pins, a 24-hour scrubber, and an ask panel that shows evidence and the verification result. The production build and type check pass. Not yet opened in a browser.
- **Tests:** 24 offline tests pass. Lint is clean.
- **Still to do:** live Groq and Claude calls (need keys), the vector index (SigLIP and LanceDB, not started), browser testing, and the end-to-end test near the end.

## Update: dashboard (23 Nov 2026)

- Deleted `scripts/generate_pdf_report.py` and `scripts/parse_noticeboard.py` (unused).
- `scripts/build_dashboard_assets.py` writes `frontend/public/data/event.json` and `slideshow.json`, and 99 web-size images to `frontend/public/slideshow/` (not in git).
- The 10 weekend figures are checked against the organiser's PDF text before they are written. The organiser counts 161 cars; the official classification lists 159.
- The podium comes from the official result. Car 84 is shown as disqualified, since its press-conference podium was later overturned.
- Post-race statements are the author's own short summaries, not the organiser's wording. The source is cited on the page.
- Dashboard: a hero with the photo slideshow behind the headline, then the figures, the podium and statements, and the interactive panels. Dark palette. Type-checks and builds; not yet opened in a browser.
- Fixed: the photo type label is `photo`, not `image`. The car-identification script had the same bug and would have skipped all photos.
- Fixed: one short clip (IMG_0731) had no frames. It now gets a first-frame fallback.
