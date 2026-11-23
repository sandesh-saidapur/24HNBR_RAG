import { fmtClock, fmtRaceHour } from "../format";
import type { MediaItem } from "../types";

interface Props {
  min: number;
  max: number;
  value: number;
  onChange: (seconds: number) => void;
  media: MediaItem[];
}

export function Timeline({ min, max, value, onChange, media }: Props) {
  const span = Math.max(1, max - min);
  const hours: number[] = [];
  for (let h = Math.ceil(min / 3600); h * 3600 <= max; h += 1) hours.push(h);

  return (
    <div className="timeline">
      <div className="timeline-head">
        <h2>24-hour scrubber</h2>
        <span className="muted">{fmtRaceHour(value)} race time</span>
      </div>
      <div className="track-bar">
        <input
          type="range"
          aria-label="Race clock"
          min={min}
          max={max}
          step={30}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
        />
        <div className="ticks" aria-hidden>
          {hours.map((h) => (
            <span key={h} style={{ left: `${((h * 3600 - min) / span) * 100}%` }}>{h}h</span>
          ))}
        </div>
        <div className="marks" aria-hidden>
          {media.map((m) => (
            <i
              key={m.file}
              title={`${m.file} · ${fmtClock(m.race_elapsed_s)}`}
              className={m.on_course ? "mark on" : "mark"}
              style={{ left: `${((m.race_elapsed_s - min) / span) * 100}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
