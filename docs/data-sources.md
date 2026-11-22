# Data sources

Each fact is marked with how well it was checked. Anything marked "re-check" must be confirmed against the original before it appears in a public answer.

## Race timing and schedule

| Item | Value | Status |
|---|---|---|
| Race start | Saturday 16 May 2026, 15:00 CEST | Confirmed in several published sources during research. Re-check the organiser's page before publishing. |
| Race finish | Sunday 17 May 2026, 15:00 CEST | Same as start plus 24 hours. |
| Formation lap | 14:40 CEST | Taken from the published schedule. Re-check. |
| Warm-up | 10:00–11:00 | Taken from the published schedule. Re-check. |
| Track length | 25.378 km | Taken from the organiser's material. Re-check. |
| Final classification | 159 started, 110 classified, 49 not classified | Extracted from the organiser's final result PDF (timing by wige SOLUTIONS GmbH & Co. KG). Transcription checked for internal consistency only. Verify against the PDF. |
| Winner | #80 Winward Racing, 156 laps, 24:05:27.664 | From the same extraction. Verify against the PDF. |

The organiser publishes results at 24h-rennen.de. The exact PDF file names were read from search results, not verified by opening them in this build.

## Files in this repository

- `data/raw/official_timing/race_classification_2026.csv`: the final classification (110 classified rows, positions 1–110 contiguous; 4 DNC, 44 DNF, 1 DSQ). Gitignored because it is third-party data. Verify against the PDF.
- Hourly split results are **not yet ingested**.
- Lap-by-lap timing has **not** been obtained.

## Track geometry

- No checked coordinates yet. OpenStreetMap, Overpass and GitHub were blocked in the build environment.
- Earlier lookups suggested Breidscheid village near 50.3739 N, 6.9519 E and Brünnchen at about kilometre 16. **Re-check both** before use. They are not verified in this repository.
- Corner coordinates in `configs/circuit_sectors.yaml` are unverified (see the note at the top of that file).
- Media-based clustering (see the project notes) gives candidate locations from the author's own GPS data. Those are candidates until the author names them.

## Personal media

The `media/` folder holds the author's own photos and videos. It is git-ignored and must not be committed.
