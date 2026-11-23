import { useEffect, useMemo, useState } from "react";
import { fmtRaceHour } from "../format";
import type { EventData, SlideItem } from "../types";

const INTERVAL_MS = 6500;
const WINDOW = 12;

interface Props {
  event: EventData | null;
  slides: SlideItem[];
  clock: number;
}

/**
 * Full-bleed slideshow of the author's photos behind the race headline. The photos shown are
 * the ones taken closest to the race clock, so moving the scrubber changes the background.
 */
export function Hero({ event, slides, clock }: Props) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const reduced = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  const near = useMemo(() => {
    const timed = slides.filter((s) => s.race_elapsed_s !== undefined);
    const pool = timed.length ? timed : slides;
    const byDistance = [...pool].sort(
      (a, b) => Math.abs((a.race_elapsed_s ?? 0) - clock) - Math.abs((b.race_elapsed_s ?? 0) - clock),
    );
    const chosen = byDistance.slice(0, WINDOW);
    // Play the chosen window in race order, starting from the photo closest to the clock.
    const closest = chosen[0];
    const inOrder = [...chosen].sort((a, b) => (a.race_elapsed_s ?? 0) - (b.race_elapsed_s ?? 0));
    const start = Math.max(0, inOrder.indexOf(closest));
    return { list: inOrder, start };
  }, [slides, clock]);

  const closestSrc = near.list[near.start]?.src;
  useEffect(() => {
    setIndex(near.start);
  }, [closestSrc, near.start]);

  useEffect(() => {
    if (paused || reduced || near.list.length < 2) return;
    const id = window.setInterval(() => setIndex((i) => (i + 1) % near.list.length), INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [paused, reduced, near.list.length]);

  const winner = event?.podium.find((p) => p.position === 1);
  const current = near.list.length ? near.list[index % near.list.length] : null;

  return (
    <header className="hero">
      <div className="hero-slides" aria-hidden>
        {near.list.map((s, i) => (
          <img
            key={s.src}
            src={s.src}
            alt=""
            loading="lazy"
            className={i === index % near.list.length ? "is-active" : ""}
          />
        ))}
        <div className="hero-shade" />
      </div>

      <div className="hero-copy">
        <p className="eyebrow">{event?.dates ?? "14–17 May 2026"} · Nürburgring Nordschleife</p>
        <h1>{event?.title ?? "54th ADAC RAVENOL 24h Nürburgring"}</h1>
        <p className="hero-lede">
          {winner
            ? `${winner.team}, car ${winner.car_number}, won the 24 hours. Trackside 24 follows the race through our own photos.`
            : "Trackside 24 follows the race through our own photos."}
        </p>
        <div className="hero-controls">
          <button type="button" className="ghost" onClick={() => setPaused((p) => !p)} aria-pressed={paused}>
            {paused ? "Play slideshow" : "Pause slideshow"}
          </button>
          <span className="caption">
            Photos near {fmtRaceHour(clock)} race time{current ? ` · ${current.caption}` : ""}
          </span>
        </div>
      </div>
    </header>
  );
}
