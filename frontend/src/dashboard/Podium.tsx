import { fmtClock } from "../format";
import type { EventData, PodiumRow } from "../types";

interface Props {
  event: EventData;
  onSelect: (car: number) => void;
}

const LABELS: Record<number, string> = { 1: "Winner", 2: "Second", 3: "Third" };

export function Podium({ event, onSelect }: Props) {
  const dsq = event.podium.filter((p) => p.position === null);
  const top = event.podium.filter((p) => p.position !== null);
  return (
    <section className="block">
      <div className="block-head">
        <h2>Podium &amp; words from the drivers</h2>
        <span className="muted">Official result. Select a card to open that car below.</span>
      </div>
      <div className="podium">
        {top.map((row) => (
          <PodiumCard key={row.car_number} row={row} event={event} onSelect={onSelect} />
        ))}
      </div>
      {dsq.length > 0 && (
        <>
          <h3 className="sub">Disqualified after the race</h3>
          <div className="podium podium-dsq">
            {dsq.map((row) => (
              <PodiumCard key={row.car_number} row={row} event={event} onSelect={onSelect} />
            ))}
          </div>
          <p className="muted small">{event.note}</p>
        </>
      )}
    </section>
  );
}

function PodiumCard({ row, event, onSelect }: { row: PodiumRow; event: EventData; onSelect: (car: number) => void }) {
  const people = event.statements.find((s) => s.car_number === row.car_number)?.people ?? [];
  const label = row.position ? LABELS[row.position] ?? `P${row.position}` : "Disqualified";
  const open = () => {
    onSelect(row.car_number);
    document.getElementById("explore")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  return (
    <article
      role="button"
      tabIndex={0}
      aria-label={`Open car ${row.car_number}, ${row.team ?? ""}`}
      className={`podium-card ${row.position === 1 ? "is-winner" : ""}`}
      onClick={open}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open();
        }
      }}
    >
      <div className="podium-head">
        <span className="rank">{row.position ?? "DSQ"}</span>
        <div>
          <h3>{row.team}</h3>
          <p className="muted small">
            Car {row.car_number} · {label}{row.total_time_s ? ` · ${fmtClock(row.total_time_s)}` : ""}
          </p>
        </div>
      </div>
      <p className="drivers">{row.drivers?.split(";").join(" · ")}</p>
      <ul className="statements">
        {people.map((p) => (
          <li key={p.name}>
            <strong>{p.name}</strong> <span className="muted">· {p.role}</span>
            <p>{p.summary}</p>
          </li>
        ))}
      </ul>
    </article>
  );
}
