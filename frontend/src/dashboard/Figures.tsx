import type { EventFigure } from "../types";

export function Figures({ figures }: { figures: EventFigure[] }) {
  return (
    <section className="block">
      <div className="block-head">
        <h2>The weekend in figures</h2>
        <span className="muted">From the organiser's published figures</span>
      </div>
      <ul className="figures">
        {figures.map((f) => (
          <li key={f.label}>
            <strong>{f.value}</strong>
            <span>{f.label}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
