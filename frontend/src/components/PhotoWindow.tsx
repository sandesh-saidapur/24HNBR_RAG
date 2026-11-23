import { useEffect, useMemo, useState } from "react";
import { fmtRaceHour } from "../format";
import type { SlideItem } from "../types";

const INTERVAL_MS = 6500;
const WINDOW = 14;

interface Props {
  slides: SlideItem[];
  clock: number;
}

/**
 * Photo window. Each frame takes the photo's own aspect ratio, so nothing is cropped or zoomed
 * out. The edges fade into the page. The photos shown are those nearest the race clock.
 */
export function PhotoWindow({ slides, clock }: Props) {
  const { list, start } = useMemo(() => {
    const timed = slides.filter((s) => s.race_elapsed_s !== undefined);
    const pool = timed.length ? timed : slides;
    const byDistance = [...pool].sort(
      (a, b) => Math.abs((a.race_elapsed_s ?? 0) - clock) - Math.abs((b.race_elapsed_s ?? 0) - clock),
    );
    const chosen = byDistance.slice(0, WINDOW);
    const inOrder = [...chosen].sort((a, b) => (a.race_elapsed_s ?? 0) - (b.race_elapsed_s ?? 0));
    return { list: inOrder, start: Math.max(0, inOrder.indexOf(chosen[0])) };
  }, [slides, clock]);

  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [zoomed, setZoomed] = useState(false);
  const reduced = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  const closestSrc = list[start]?.src;
  useEffect(() => {
    setIndex(start);
  }, [closestSrc, start]);

  const step = (delta: number) => setIndex((i) => (i + delta + list.length) % list.length);

  useEffect(() => {
    if (paused || reduced || zoomed || list.length < 2) return;
    const id = window.setInterval(() => setIndex((i) => (i + 1) % list.length), INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [paused, reduced, zoomed, list.length]);

  useEffect(() => {
    if (!zoomed) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setZoomed(false);
      if (e.key === "ArrowRight") setIndex((i) => (i + 1) % list.length);
      if (e.key === "ArrowLeft") setIndex((i) => (i - 1 + list.length) % list.length);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoomed, list.length]);

  const current = list.length ? list[index % list.length] : null;
  if (!current) return <div className="photo-window photo-empty">Photos will appear here.</div>;

  const ratio = current.width && current.height ? current.width / current.height : 4 / 3;

  return (
    <figure className="photo-window">
      <div
        className="photo-frame"
        style={{ aspectRatio: `${ratio}`, width: `min(100%, calc(64vh * ${ratio}))` }}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") step(1);
          if (e.key === "ArrowLeft") step(-1);
          if (e.key === " ") {
            e.preventDefault();
            setPaused((p) => !p);
          }
        }}
      >
        <img key={current.src} src={current.src} alt={current.caption} className="photo-main" />
        <div className="photo-glow" aria-hidden="true" />
        <button type="button" className="photo-zoom" onClick={() => setZoomed(true)}>
          Full size
        </button>
      </div>
      <figcaption className="photo-meta">
        <div className="photo-controls">
          <button type="button" className="icon-btn" onClick={() => step(-1)} aria-label="Previous photo">‹</button>
          <button type="button" className="icon-btn" onClick={() => setPaused((p) => !p)} aria-pressed={paused}>
            {paused ? "Play" : "Pause"}
          </button>
          <button type="button" className="icon-btn" onClick={() => step(1)} aria-label="Next photo">›</button>
          <span className="muted small">{index % list.length + 1} / {list.length}</span>
        </div>
        <span className="small">
          {current.caption} · {fmtRaceHour(current.race_elapsed_s ?? 0)}
        </span>
        <div className="dots" aria-hidden="true">
          {list.map((s, i) => (
            <button
              key={s.src}
              type="button"
              tabIndex={-1}
              className={i === index % list.length ? "dot is-on" : "dot"}
              onClick={() => setIndex(i)}
            />
          ))}
        </div>
      </figcaption>

      {zoomed && (
        <div className="lightbox" role="dialog" aria-modal="true" aria-label="Photo" onClick={() => setZoomed(false)}>
          <img src={current.src} alt={current.caption} />
          <p className="small muted">{current.caption} · press Esc to close, arrows to move</p>
          <button type="button" className="ghost" onClick={() => setZoomed(false)}>Close</button>
        </div>
      )}
    </figure>
  );
}
