import type { ReactNode } from "react";
import type { EventData } from "../types";

interface Props {
  event: EventData | null;
  map?: ReactNode;
  children?: ReactNode;
}

/** Title block for the top of the page. The map sits above the title; children (the photo window) sit in the right column. */
export function Hero({ event, map, children }: Props) {
  const winner = event?.podium.find((p) => p.position === 1);
  return (
    <header className="hero">
      <div className="hero-copy">
        {map}
        <p className="eyebrow">{event?.dates ?? "14–17 May 2026"} · Nürburgring Nordschleife</p>
        <h1>{event?.title ?? "54th ADAC RAVENOL 24h Nürburgring"}</h1>
        <p className="hero-lede">
          {winner
            ? `${winner.team}, car ${winner.car_number}, won the 24 hours. Trackside 24 follows the race through our own photos.`
            : "Trackside 24 follows the race through our own photos."}
        </p>
        <div className="hero-actions">
          <a className="btn" href="#podium">See the podium</a>
          <a className="btn ghost" href="#explore">Explore the race</a>
        </div>
      </div>
      <div className="hero-media">{children}</div>
    </header>
  );
}
