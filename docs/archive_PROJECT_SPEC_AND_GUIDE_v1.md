# Trackside 24: Multimodal Spatio-Temporal Race Companion (24h Nürburgring 2026 RAG)
## Master Project Specification, Architecture Blueprint & Plain-English Guide (2026 Edition)

---

## 1. Executive Summary & Plain-English Overview

### What is this project?
**Trackside 24** is an intelligent, multimodal Retrieval-Augmented Generation (RAG) system built around the **2026 ADAC RAVENOL 24 Hours of Nürburgring** (held May 14–17, 2026). 

Unlike ordinary RAG projects that simply index PDFs or documentation, this project connects your **real personal experience** (photos, videos, audio recorded on your phone trackside during the 2026 event) with **official motorsport intelligence** (timing sheets, steward incident bulletins, regulations, live telemetry, and live commentary).

### How does it work in simple terms?
Imagine taking a photo at 02:45 AM from the fence at *Brünnchen* with glowing brake rotors and mist rolling through the trees. Months later, you upload that photo to this app and ask:
> *"What car is this, who was behind the wheel, and what was happening on track at that exact moment?"*

The system:
1. **Reads the photo's digital memory (EXIF metadata):** Extracts the exact second it was taken (`2026-05-17 02:45:12`) and the GPS coordinates.
2. **Synchronizes time:** Translates your phone's clock to the **Official 2026 Race Clock** (e.g., *Race Hour 10, Lap 48* from the Saturday 16:00:00 CEST start).
3. **Locates the track sector:** Uses GPS geofencing to determine you were standing at *Brünnchen (Sector 14)*.
4. **Looks at the photo (Vision AI):** Identifies the car's livery, brand (e.g., Porsche 911 GT3 R), and racing number (`#911 Manthey 'Grello'`).
5. **Retrieves race context (RAG Engine):**
   * Checks the timing database: Who was driving? (Kévin Estre). What position were they in? (P2, hunting down P1).
   * Checks the race control log: Was there a yellow flag or Code 60 nearby?
   * Checks the commentary transcript: What were the commentators saying at 02:45 AM?
6. **Synthesizes a complete answer:** Delivers an engaging, historically accurate breakdown citing official timing and rule bulletins, complete with a timeline view.

---

## 2. System Architecture & Information Flow

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   INPUT SOURCES                                        │
├──────────────────────────────┬─────────────────────────────┬───────────────────────────┤
│    Personal Fan Media        │   Official Race Documents   │   Timing & Commentary     │
│  - Photos (JPEG/HEIC/PNG)    │  - Regulations (PDF)        │  - wige Lap Sheets (CSV)  │
│  - Videos (MP4/MOV)          │  - Steward Bulletins (PDF)  │  - Official Results (PDF) │
│  - EXIF (Time, GPS, Camera)  │  - Race Control Decisions   │  - Whisper Transcripts    │
└──────────────┬───────────────┴──────────────┬──────────────┴─────────────┬─────────────┘
               │                              │                            │
               ▼                              ▼                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION & NORMALIZATION PIPELINE                         │
├──────────────────────────────┬─────────────────────────────┬───────────────────────────┤
│     Media Preprocessor       │     Docling / PDF Parser    │     Audio & Data Tables   │
│  - EXIF Date & GPS extraction│  - Extract tables from wige │  - Timestamped chunks of  │
│  - Video keyframe sampling   │    PDF reports into clean   │    commentary (30s spans) │
│  - SigLIP visual embeddings  │    structured Markdown/JSON │  - DuckDB tabular ingestion│
└──────────────┬───────────────┴──────────────┬──────────────┴─────────────┬─────────────┘
               │                              │                            │
               ▼                              ▼                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     SPATIO-TEMPORAL ALIGNMENT ENGINE (THE GLUE)                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  - Time Synchronization: Align EXIF local time -> UTC/CEST -> Official Race Clock     │
│  - Red Flag / Suspension Offset: Account for race pauses / neutralized hours           │
│  - Geospatial Geofence: Map GPS lat/lon -> Nordschleife corner names (170+ turns)      │
│  - Visual Car Identification: Zero-shot Vision LLM extraction (Car #, Make, Livery)   │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                       HYBRID STORAGE & RETRIEVAL LAYER                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  1. Vector DB (LanceDB): Multimodal SigLIP embeddings (Photos + Video Frames + Text)  │
│  2. Text & Document Index: BM25 + Dense vector search for bulletins & regulations      │
│  3. Relational Table (DuckDB / SQLite): Fast SQL queries for lap deltas, driver stints │
│  4. Hybrid Ranker / Reranker (FlashRank): Merges vector, temporal, and tabular scores │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        AGENTIC RAG ORCHESTRATOR & LLM                                  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  - Intent Classifier: Identifies if query is Visual, Historical, Telemetric, or Rules  │
│  - Context Assembler: Merges personal photo metadata + lap data + steward reports      │
│  - Synthesizer (Gemini / Claude / Local LLM): Generates natural language analysis      │
│  - Grounding & Source Citation: Verifies claim accuracy with confidence scoring        │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE (Streamlit / Next.js)                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  - Interactive Nürburgring Circuit Map (Leaflet / Mapbox with GPS photo pins)         │
│  - Chronological 24-Hour Scroller (Syncs personal media with race milestones)          │
│  - Multimodal Chat Interface (Drag-and-drop photos, ask questions, inspect citations)  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Directory & File Map Structure (Ready for Claude/Developers)

This tree structure provides the exact blueprint for building the codebase cleanly and modularly.

```
24HNBR_RAG/
├── README.md                           # GitHub showcase, setup, architecture summary
├── PROJECT_SPEC_AND_GUIDE.md           # This master documentation file
├── pyproject.toml                      # Poetry / pip dependency configuration
├── requirements.txt                    # Python runtime dependencies
├── Makefile                            # One-command ingestion, testing, and UI startup
├── .env.example                        # API keys, data paths, model choices
├── docker-compose.yml                  # Container configuration for LanceDB/FastAPI/UI
│
├── configs/
│   ├── circuit_sectors.yaml            # Coordinates, GPS polygons & KM markers of corners
│   ├── race_calendar.yaml              # Race start timestamp, red flag periods, classes
│   └── rag_config.yaml                 # Embedding models, chunk sizes, top-k parameters
│
├── data/                               # Local data store (ignored in git except samples)
│   ├── raw/
│   │   ├── personal_media/             # User's photos (.jpg, .heic) and videos (.mp4)
│   │   ├── official_timing/            # Downloaded PDFs and CSVs (wige timing, grid)
│   │   ├── bulletins/                  # Steward decisions, penalties, BoP sheets
│   │   ├── transcripts/                # Transcribed YouTube or radio commentary
│   │   └── regulations/                # Official ADAC/DMSB rulebooks
│   ├── processed/
│   │   ├── media_catalog.parquet       # Media metadata (EXIF, time, GPS, detected car)
│   │   ├── timing_database.duckdb      # Structured lap-by-lap timing tables
│   │   ├── incidents.jsonl             # Structured chronological incidents
│   │   └── circuit_map.geojson         # Nordschleife track layout & corner polygons
│   └── vector_store/                   # LanceDB local storage directory
│
├── src/
│   ├── __init__.py
│   │
│   ├── ingestion/                      # Step 1: Ingest raw files
│   │   ├── __init__.py
│   │   ├── exif_extractor.py           # Extracts EXIF (DateTimeOriginal, GPS, Lens)
│   │   ├── media_preprocessor.py       # Resizes images, extracts video keyframes via OpenCV
│   │   ├── timing_parser.py            # Converts wige PDF tables & CSVs into clean dataframes
│   │   ├── bulletin_parser.py          # Extracts penalties and race director notices
│   │   └── transcript_chunker.py       # Chunks commentary text into time-stamped windows
│   │
│   ├── alignment/                      # Step 2: Harmonize spatial & temporal dimensions
│   │   ├── __init__.py
│   │   ├── time_synchronizer.py        # Maps camera timestamp -> official race elapsed clock
│   │   ├── track_locator.py            # Point-in-polygon / nearest neighbor GPS -> Corner name
│   │   └── car_identifier.py           # Vision LLM prompt for car number, livery, brand
│   │
│   ├── indexing/                       # Step 3: Embed and store in databases
│   │   ├── __init__.py
│   │   ├── multimodal_embedder.py      # SigLIP / OpenCLIP embeddings for images and text
│   │   ├── text_embedder.py            # Dense embeddings for documents/commentary
│   │   ├── vector_store.py             # LanceDB table initialization, indexing & search
│   │   └── tabular_store.py            # DuckDB connection & parameterized SQL queries
│   │
│   ├── rag/                            # Step 4: The Intelligent RAG Core
│   │   ├── __init__.py
│   │   ├── router.py                   # Categorizes incoming query (Visual / SQL / Document)
│   │   ├── hybrid_retriever.py         # Combines vector similarity, BM25, and metadata filters
│   │   ├── context_assembler.py        # Formats retrieved data into structured LLM prompts
│   │   ├── generator.py                # LLM response generation with streaming support
│   │   └── verifier.py                 # Fact-checking against timing data & confidence score
│   │
│   ├── api/                            # Step 5: Backend API (FastAPI)
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI application endpoints
│   │   ├── routes_query.py             # /query, /query/image endpoints
│   │   ├── routes_media.py             # /media, /timeline endpoints
│   │   └── schemas.py                  # Pydantic models for request & response validation
│   │
│   └── ui/                             # Step 6: Frontend Interface (Streamlit / Web)
│       ├── app.py                      # Main UI application
│       ├── components/
│       │   ├── circuit_map.py          # Leaflet map showing track layout and photo locations
│       │   ├── timeline_slider.py      # 24-hour interactive race timeline
│       │   └── chat_interface.py       # Chat window with image upload and citation previews
│       └── static/
│           └── styles.css              # Dark mode motorsport-themed CSS
│
├── tests/                              # Automated test suite
│   ├── test_exif_extractor.py
│   ├── test_time_synchronizer.py
│   ├── test_track_locator.py
│   ├── test_retrieval.py
│   └── test_rag_generation.py
│
├── evaluation/                         # Benchmarking & Quality flywheels
│   ├── test_queries.json               # 25-50 curated test queries with ground-truth answers
│   └── run_eval.py                     # Ragas / LLM-as-a-judge precision & recall evaluation
│
└── scripts/                            # Operational utility scripts
    ├── ingest_all.py                   # One-click command to process all data from raw to DB
    ├── download_sample_data.py         # Downloads public 24h NBR results & regulations
    └── export_github_demo.py           # Prepares demo screenshots and anonymized samples
```

---

## 4. Deep-Dive Component Technical Specifications

### 4.1 Ingestion & EXIF Extraction (`src/ingestion/exif_extractor.py`)
* **Inputs:** Raw image files (`.jpg`, `.jpeg`, `.heic`, `.png`) or video clips (`.mp4`, `.mov`).
* **Processing:**
  * Uses `exifread` or `Pillow` to extract `DateTimeOriginal`, `OffsetTime` (timezone offset), and `GPSInfo` (Latitude, Longitude, Altitude).
  * Video handling: Uses `ffmpeg-python` or `opencv-python` to extract creation metadata (`creation_time`) and samples keyframes at 1 frame per 2 seconds.
* **Outputs:** A structured dictionary per media item:
  ```json
  {
    "file_id": "IMG_4921",
    "filename": "IMG_4921.JPG",
    "timestamp_raw": "2026-05-16 21:14:03",
    "latitude": 50.3682,
    "longitude": 7.0091,
    "camera_make": "Apple",
    "camera_model": "iPhone 15 Pro",
    "media_type": "image"
  }
  ```

### 4.2 Spatio-Temporal Alignment (`src/alignment/`)
This is the scientific foundation that makes the project unique.

#### Time Synchronizer (`time_synchronizer.py`):
* Translates wall-clock time into **Elapsed Race Time (ERT)**.
* Accounts for timezone differences between the user's phone (e.g. UTC, GMT, EST) and Nürburgring local time (CEST, UTC+2).
* Handles race interruptions (e.g., Red Flags due to fog/crashes) by tracking both **Total Clock Time** and **Effective Green Flag Race Time**.

#### Track Locator (`track_locator.py`):
* Uses standard Nordschleife sector definitions (e.g., *T13, Hatzenbach, Hocheichen, Quiddelbacher Höhe, Flugplatz, Schwedenkreuz, Aremberg, Fuchsröhre, Adenauer Forst, Metzgesfeld, Kallenhard, Wehrseifen, Breidscheid, Ex-Mühle, Bergwerk, Kesselchen, Klostertal, Steilstrecke, Karussell, Hohe Acht, Wippermann, Eschbach, Brünnchen, Pflanzgarten, Schwalbenschwanz, Döttinger Höhe, Tiergarten*).
* Checks if GPS coordinates fall inside predefined polygon geofences (defined in `configs/circuit_sectors.yaml`) or performs nearest-point projection along the track spline.

#### Car Identification (`car_identifier.py`):
* Runs a fast Vision-Language model (e.g., Gemini 1.5 Flash / Claude 3.5 Sonnet / localized Florence-2) with a constrained prompt:
  * *"Detect race car racing numbers, team livery colors, primary sponsor logos, and car manufacturer from this motorsport photo."*
* Returns structured JSON: `{"car_number": 911, "make": "Porsche", "livery": "Yellow/Green Grello", "confidence": 0.94}`.

### 4.3 Database Architecture (`src/indexing/`)

#### 1. Multimodal Vector Store (LanceDB):
* **Why LanceDB?** It runs locally with serverless disk storage, has zero cloud dependencies, supports zero-copy reading in Python, and handles vector search + SQL filtering natively.
* **Schema:**
  * `media_id` (string)
  * `vector` (SigLIP 768-dim float array)
  * `timestamp_epoch` (int64)
  * `race_hour` (float)
  * `track_corner` (string)
  * `car_number` (int, nullable)
  * `description` (text)

#### 2. Relational Timing Store (DuckDB):
* Stores official lap timing sheets converted from CSVs:
  * Table: `lap_times` (`car_no`, `lap_no`, `driver_name`, `lap_time_seconds`, `timestamp_crossing`, `position_overall`, `position_class`)
  * Table: `steward_bulletins` (`bulletin_no`, `timestamp`, `car_no`, `infringement`, `penalty`, `status`)
  * Table: `commentary_transcripts` (`timestamp_start`, `timestamp_end`, `speaker`, `transcript_text`)

### 4.4 Hybrid RAG & Context Assembler (`src/rag/`)

When a query arrives, the **Router** selects the retrieval pattern:

```
                  ┌───────────────────────┐
                  │    Incoming Query     │
                  └──────────┬────────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
     [Visual Match]   [Telemetry/Stats] [Rules/Story]
     (Image uploaded) (Who was P1? Lap delta) (Why was red flag?)
            │                │                │
            ▼                ▼                ▼
     LanceDB Vector    DuckDB SQL       BM25 + Dense Doc
     Search (SigLIP)   Execution        Search
            │                │                │
            └────────────────┼────────────────┘
                             ▼
                 [ Reciprocal Rank Fusion ]
                             ▼
                 [ Context Assembly Prompt ]
                             ▼
                     [ LLM Generation ]
```

* **Context Assembler Prompt Template:**
  ```text
  You are Trackside 24, an expert motorsport race engineer and historian for the 24 Hours of Nürburgring.
  
  EVIDENCE PROVIDED:
  1. User Media Info: Photo taken at {timestamp_cest} at {track_corner}.
  2. Detected Visuals: Car #{car_number} ({make}), Livery: {livery}.
  3. Official Timing Data:
     - Lap {lap_no}, Driver: {driver_name}, Current Position: {position_overall} (P{position_class} in {class_name}).
     - Gap to car ahead: {gap_ahead}s.
  4. Track Condition & Steward Bulletins:
     - Flag Status: {flag_status} at {sector}.
     - Recent bulletins: {bulletin_summary}.
  5. Live Commentary Excerpt:
     - "{commentary_quote}"
  
  USER QUERY: {user_query}
  
  TASK:
  Provide an accurate, exciting, and technically grounded answer. Cite specific laps, times, and official decisions. If something is uncertain, state the confidence level clearly.
  ```

---

## 5. Step-by-Step Implementation Roadmap (For Developers / AI Agents)

This roadmap is sequenced so each phase produces a working, testable milestone:

### Phase 1: Environment & Project Scaffolding
- [ ] Initialize Python 3.11+ environment with `pyproject.toml` / `requirements.txt`.
- [ ] Set up directory structure (`configs/`, `data/`, `src/`, `tests/`).
- [ ] Create `configs/circuit_sectors.yaml` with GPS coordinates and names for key Nordschleife corners.
- [ ] Create `.env.example` with API key templates.

### Phase 2: Ingestion & Spatial-Temporal Alignment
- [ ] Build `exif_extractor.py`: Test on sample smartphone photos and confirm timestamp + GPS extraction.
- [ ] Build `time_synchronizer.py`: Test mapping of phone timestamps to official race hours (handling timezone offsets).
- [ ] Build `track_locator.py`: Verify that a sample coordinate near Brünnchen correctly resolves to `"Brünnchen"`.
- [ ] Build `timing_parser.py`: Ingest sample wige timing CSV/PDF data into `data/processed/timing_database.duckdb`.

### Phase 3: Embedding & Vector Storage
- [ ] Initialize LanceDB table with multimodal schema.
- [ ] Implement `multimodal_embedder.py` using `open_clip` (ViT-B-16 or SigLIP) to embed photos and video frames.
- [ ] Index commentary text chunks and official incident bulletins into vector collections.
- [ ] Write unit tests for vector similarity search.

### Phase 4: RAG Engine & Tool Orchestration
- [ ] Implement query classification in `router.py`.
- [ ] Write DuckDB query generator for tabular lap time lookups.
- [ ] Implement `context_assembler.py` to bundle timing + visual + text evidence.
- [ ] Connect LLM generator (Gemini 1.5 Flash / Claude 3.5 Sonnet) with structured source citations.

### Phase 5: User Interface & Visual Showcase
- [ ] Build Streamlit application (`src/ui/app.py`).
- [ ] Add interactive circuit map with pins representing user photos.
- [ ] Add media uploader: Drop a photo $\rightarrow$ displays metadata $\rightarrow$ triggers RAG explanation.
- [ ] Add 24-hour chronological scrubber bar.

### Phase 6: Evaluation, GitHub Polish & Documentation
- [ ] Create `evaluation/test_queries.json` with 25 benchmark motorsport questions.
- [ ] Run automated retrieval and answer quality evaluation.
- [ ] Record a 15-second animated GIF demo of uploading a track photo and getting the instant race breakdown.
- [ ] Write the public `README.md` with badges, architecture diagrams, and quickstart instructions.

---

## 6. What Data You Need to Add (Checklist for You)

To bring your project to life, you only need to drop files into the `data/raw/` folders:

1. **`data/raw/personal_media/`**
   * Put your personal smartphone photos (`.jpg`, `.heic`) and short video clips (`.mp4`, `.mov`) here.
2. **`data/raw/official_timing/`**
   * Download the official PDF or CSV results from the 24h Nürburgring official website (or wige-solutions.de) for the year you attended (e.g., *Official Final Classification*, *Hourly Results*, *Starting Grid*).
3. **`data/raw/bulletins/`**
   * Download any published *Stewards Decisions / Penalties* bulletins and *Balance of Performance (BoP)* tables.
4. **`data/raw/regulations/`**
   * The official *ADAC 24h Nürburgring Supplementary Regulations* PDF.
5. **`data/raw/transcripts/`** (Optional but great):
   * An audio or text transcript of the English or German YouTube live stream during the hours you attended.

---

## 7. Key Portfolio Selling Points (Why this lands job interviews)

When hiring managers or senior engineers look at your GitHub repository, this project demonstrates:
1. **Multimodal Mastery:** You didn't just embed text; you linked raw pixel data, EXIF metadata, tabular data, and legal rulebooks into one coherent query engine.
2. **Spatio-Temporal Grounding:** Demonstrates advanced engineering in mapping noisy real-world smartphone clocks and GPS coordinates to an official synchronized event timeline.
3. **Hybrid RAG Engineering:** Combining Vector search (LanceDB), Lexical search (BM25), and Structured Relational queries (DuckDB) avoids hallucinations on numerical lap deltas.
4. **Authentic Storytelling:** Having your own photos and videos makes your code review memorable, authentic, and fun to present during live interviews.

