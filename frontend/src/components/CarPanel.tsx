import { useEffect, useState } from "react";
import { api } from "../api";
import { fmtClock, fmtSeconds } from "../format";
import type { CarDetail, Lap } from "../types";

interface Props {
  carNumber: number | null;
}

export function CarPanel({ carNumber }: Props) {
  const [car, setCar] = useState<CarDetail | null>(null);
  const [laps, setLaps] = useState<Lap[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (carNumber === null) return;
    let live = true;
    setError(null);
    Promise.all([api.car(carNumber), api.laps(carNumber)])
      .then(([c, l]) => {
        if (!live) return;
        setCar(c);
        setLaps(l);
      })
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [carNumber]);

  if (carNumber === null) return <div className="card muted">Select a car.</div>;
  if (error) return <div className="card banner">{error}</div>;
  if (!car) return <div className="card muted">Loading car {carNumber}…</div>;

  const times = laps.map((l) => l.lap_time_s).filter((t): t is number => t !== null);
  const best = times.length ? Math.min(...times) : null;
  const sparkline = sparkPath(times);

  return (
    <div className="card">
      <div className="card-head">
        <h2>Car {car.car_number}</h2>
        <span className={`badge badge-${car.status.toLowerCase()}`}>{car.status}</span>
      </div>
      <p className="muted">{car.team} · {car.class} · {car.drivers ?? "drivers n/a"}</p>
      <dl className="facts">
        <div><dt>Position</dt><dd>{car.position ?? "—"}</dd></div>
        <div><dt>Laps</dt><dd>{car.laps}</dd></div>
        <div><dt>Total</dt><dd>{fmtClock(car.total_time_s)}</dd></div>
        <div><dt>Best lap</dt><dd>{fmtClock(best)}</dd></div>
      </dl>
      <h3>Lap times</h3>
      <svg className="spark" viewBox="0 0 300 60" preserveAspectRatio="none" role="img" aria-label="Lap time trend">
        <path d={sparkline} />
      </svg>
      <h3>Penalties</h3>
      {car.penalties.length === 0 ? (
        <p className="muted">None on the official list.</p>
      ) : (
        <ul className="penalties">
          {car.penalties.map((p, i) => (
            <li key={i}>
              <strong>{fmtSeconds(p.penalty_seconds)}</strong>
              {p.steward_decision_no ? ` · decision ${p.steward_decision_no}` : ""}
              <span className="muted"> {p.offence_verbatim}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Lap times as a polyline; slower laps sit lower. Fixed-size viewBox, scaled by the browser. */
function sparkPath(values: number[]): string {
  if (values.length < 2) return "";
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;
  return values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * 300;
      const y = 6 + ((v - lo) / span) * 48;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}
