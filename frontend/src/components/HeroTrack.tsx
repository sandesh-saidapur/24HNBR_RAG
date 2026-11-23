import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { CircuitSegments } from "../types";

/** Equirectangular projection, scaled by cos(latitude) so the circuit keeps its shape. */
function projector(points: [number, number][]) {
  const lats = points.map((p) => p[0]);
  const lons = points.map((p) => p[1]);
  const minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const minLon = Math.min(...lons), maxLon = Math.max(...lons);
  const kx = Math.cos(((minLat + maxLat) / 2) * (Math.PI / 180));
  const width = (maxLon - minLon) * kx;
  const height = maxLat - minLat;
  const pad = 0.04;
  return (lat: number, lon: number): [number, number] => {
    const x = ((lon - minLon) * kx) / width;
    const y = (maxLat - lat) / height;
    return [pad + x * (1 - 2 * pad), pad + y * (1 - 2 * pad)];
  };
}

/** Bold outline of the Nordschleife and Grand Prix circuit, drawn from OpenStreetMap (ODbL). */
export function HeroTrack() {
  const [data, setData] = useState<CircuitSegments | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.circuit().then(setData).catch(() => setFailed(true));
  }, []);

  const path = useMemo(() => {
    if (!data || data.segments.length === 0) return "";
    const project = projector(data.segments.flat());
    return data.segments
      .map((segment) =>
        segment
          .map(([lat, lon], i) => {
            const [x, y] = project(lat, lon);
            return `${i === 0 ? "M" : "L"}${(x * 1000).toFixed(1)},${(y * 1000).toFixed(1)}`;
          })
          .join(" "),
      )
      .join(" ");
  }, [data]);

  return (
    <figure className="hero-track">
      <svg viewBox="0 0 1000 1000" role="img" aria-label="Nürburgring circuit outline">
        {path && <path d={path} className="circuit-edge" />}
        {path && <path d={path} className="circuit" />}
      </svg>
      <figcaption className="attribution">
        {data?.attribution ?? (failed ? "Track outline unavailable" : "")}
      </figcaption>
    </figure>
  );
}
