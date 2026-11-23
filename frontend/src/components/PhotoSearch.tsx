import { FormEvent, useState } from "react";
import { api } from "../api";
import { fmtRaceHour } from "../format";
import type { PhotoHit } from "../types";

interface Props {
  onPick: (raceSeconds: number) => void;
}

/** Find photos by describing them. Picking a result moves the race clock to that moment. */
export function PhotoSearch({ onPick }: Props) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<PhotoHit[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const q = query.trim();
    if (q.length < 2) return;
    setBusy(true);
    setStatus(null);
    try {
      const results = await api.searchPhotos(q, 8);
      setHits(results);
      if (results.length === 0) setStatus("No photos matched that.");
    } catch (e) {
      setHits([]);
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card photo-search">
      <div className="card-head">
        <h2>Find a moment</h2>
        <span className="muted small">Search our photos by what they show</span>
      </div>
      <form onSubmit={submit} className="search-row">
        <input
          aria-label="Describe a photo"
          placeholder="e.g. pit lane in rain, Brünnchen at night"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" disabled={busy || query.trim().length < 2}>
          {busy ? "Searching…" : "Search"}
        </button>
      </form>
      {status && <p className="muted small">{status}</p>}
      {hits.length > 0 && (
        <ul className="hits">
          {hits.map((h) => (
            <li key={h.key}>
              <button type="button" onClick={() => onPick(h.race_elapsed_s)}>
                <span className="hit-file">{h.file}</span>
                <span className="muted small">
                  {h.caption} · {fmtRaceHour(h.race_elapsed_s)} · match {Math.round(h.score * 100)}%
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
