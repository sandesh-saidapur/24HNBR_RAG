import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { fmtClock } from "../format";
import type { CircuitSegments, MediaItem, TrackOutline } from "../types";

const WINDOW_S = 900; // photos within 15 minutes of the scrubber are highlighted

interface Props {
  track: TrackOutline | null;
  media: MediaItem[];
  clock: number;
}

/** Equirectangular projection, scaled by cos(latitude) so the circuit keeps its shape. */
function projector(points: [number, number][]) {
  const lats = points.map((p) => p[0]);
  const lons = points.map((p) => p[1]);
  const minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const minLon = Math.min(...lons), maxLon = Math.max(...lons);
  const kx = Math.cos(((minLat + maxLat) / 2) * (Math.PI / 180));
  const width = (maxLon - minLon) * kx;
  const height = maxLat - minLat;
  const pad = 0.06;
  return (lat: number, lon: number): [number, number] => {
    const x = ((lon - minLon) * kx) / width;
    const y = (maxLat - lat) / height;
    return [pad + x * (1 - 2 * pad), pad + y * (1 - 2 * pad)];
  };
}

export function TrackMap({ track, media, clock }: Props) {
  const [picked, setPicked] = useState<string | null>(null);
  const [circuit, setCircuit] = useState<CircuitSegments | null>(null);

  useEffect(() => {
    api.circuit().then(setCircuit).catch(() => setCircuit(null));
  }, []);

  // Project with the circuit's own extent so pins and sections share one frame.
  const project = useMemo(() => {
    const points = circuit?.segments.flat() ?? track?.points ?? [];
    return points.length ? projector(points) : null;
  }, [circuit, track]);

  // One subpath per circuit section, so sections are never joined by straight jumps.
  const path = useMemo(() => {
    if (!project) return "";
    const segments = circuit?.segments ?? (track ? [track.points] : []);
    return segments
      .map((segment) =>
        segment
          .map(([lat, lon], i) => {
            const [x, y] = project(lat, lon);
            return `${i === 0 ? "M" : "L"}${(x * 1000).toFixed(1)},${(y * 1000).toFixed(1)}`;
          })
          .join(" "),
      )
      .join(" ");
  }, [project, circuit, track]);

  const pins = media.filter((m) => m.latitude !== null && m.longitude !== null && project);
  const current = pins.find((m) => m.file === picked) ?? null;

  return (
    <div className="map">
      <div className="map-head">
        <h2>Where your photos were taken</h2>
        <span className="muted">Race clock {fmtClock(clock)}</span>
      </div>
      <svg viewBox="0 0 1000 1000" role="img" aria-label="Nürburgring outline with photo locations">
        {path && <path d={path} className="track" />}
        {project &&
          pins.map((m) => {
            const [x, y] = project(m.latitude!, m.longitude!);
            const near = Math.abs(m.race_elapsed_s - clock) <= WINDOW_S;
            return (
              <circle
                key={m.file}
                cx={x * 1000}
                cy={y * 1000}
                r={near ? 9 : 5}
                className={`pin ${near ? "pin-near" : ""} ${m.file === picked ? "pin-picked" : ""}`}
                onClick={() => setPicked(m.file)}
              >
                <title>{m.file}</title>
              </circle>
            );
          })}
      </svg>
      <p className="attribution">{track?.attribution ?? ""}</p>
      {current ? (
        <p className="pin-info">
          <strong>{current.file}</strong> · {fmtClock(current.race_elapsed_s)} race time ·{" "}
          {current.nearest_section ?? "section n/a"}
          {current.distance_m !== null ? ` (${current.distance_m.toFixed(0)} m)` : ""}
        </p>
      ) : (
        <p className="pin-info muted">Click a dot to see that photo. Bright dots were taken within 15 minutes of the time shown.</p>
      )}
    </div>
  );
}
