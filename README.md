# Trackside 24: Multimodal Spatio-Temporal Race Companion (2026 Edition) 🏎️
### *An AI-powered multimodal RAG that synchronizes personal trackside fan media from the 2026 24h Nürburgring with official race telemetry, steward bulletins, and live commentary.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LanceDB](https://img.shields.io/badge/Vector_DB-LanceDB-black.svg)](https://lancedb.com/)
[![DuckDB](https://img.shields.io/badge/SQL_Store-DuckDB-yellow.svg)](https://duckdb.org/)
[![Event: 2026 24h NBR](https://img.shields.io/badge/Event-2026_24h_NBR-red.svg)](https://www.24h-rennen.de)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🏁 The Vision: Completing the Circle

The **2026 ADAC RAVENOL 24 Hours of Nürburgring** (held May 14–17, 2026) is the ultimate endurance race: 130+ race cars, 25.378 km of the legendary *Green Hell*, unpredictable Eifel weather, and over 200,000 fans camping in the forest.

While attending the 2026 event trackside, I captured photos and 4K clips: glowing brake discs at Pflanzgarten, high-speed flybys at Flugplatz, and dramatic overtakes at the Karussell in the dead of night.

**Trackside 24** brings those memories to life by using **Multimodal Spatio-Temporal RAG**:
- Drop in any smartphone photo or video clip taken at the track.
- The system automatically extracts EXIF timestamps and GPS, calculates the exact race hour, maps your location to the Nordschleife corner, identifies the car livery, and queries official timing, steward bulletins, and live transcripts.
- It returns the exact story of what was happening on track at that exact second.

---

## 🛠️ Architecture & Tech Stack

```
[ Smartphone Photos & Videos ]    [ Official Lap Timing (PDF/CSV) ]    [ Steward Decisions & Audio ]
              │                                   │                                  │
              └─────────────────────────┬─────────┴──────────────────────────────────┘
                                        ▼
                      [ Ingestion & Alignment Engine ]
                      - EXIF Time -> Official Race Clock Sync
                      - GPS -> Track Sector Geofencing (170+ corners)
                      - Vision Model (Car #, Livery, Make recognition)
                                        │
                                        ▼
                      [ Hybrid Storage & Retrieval ]
                      - LanceDB (Multimodal SigLIP Vectors)
                      - DuckDB (Sub-second Lap Timing & Speed Traps)
                      - BM25 (Regulations & Incident Bulletins)
                                        │
                                        ▼
                      [ Context Assembler & LLM Engine ]
                      (Gemini 1.5 Flash / Claude 3.5 Sonnet)
                                        │
                                        ▼
                      [ Interactive Web UI ]
                      (Leaflet Map + 24h Scrubber + Multimodal Chat)
```

---

## 🚀 Quickstart Guide

### 1. Clone & Set Up
```bash
git clone https://github.com/yourusername/24HNBR_RAG.git
cd 24HNBR_RAG
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Add Your Event Data
* Drop your personal photos & videos into `data/raw/personal_media/`.
* Place official timing results and bulletins into `data/raw/official_timing/` and `data/raw/bulletins/`.

### 3. Run Ingestion & Alignment
```bash
python scripts/ingest_all.py
```

### 4. Launch the Interactive Companion
```bash
streamlit run src/ui/app.py
```

---

## 📖 Complete Documentation
For full architectural specifications, mathematical alignment details, and step-by-step developer instructions, see [PROJECT_SPEC_AND_GUIDE.md](file:///Users/sandeshsaidapur/Documents/24HNBR_RAG/PROJECT_SPEC_AND_GUIDE.md).

