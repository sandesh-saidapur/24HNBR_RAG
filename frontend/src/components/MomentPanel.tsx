import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { fmtClock } from "../format";
import type { MediaItem, MomentRow } from "../types";

type Kind = "all" | "photo" | "video";

const stem = (file: string) => file.replace(/\.[^.]+$/, "");

/** Pick any photo or video and see the race at its moment: stage, leader and running order. */
export function MomentPanel() {
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [kind, setKind] = useState<Kind>("all");
  const [selected, setSelected] = useState<MediaItem | null>(null);
  const [moment, setMoment] = useState<MomentRow | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.media().then(setMedia).catch(() => setError("The media list could not be loaded."));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setMoment(null);
    api.moment(selected.race_elapsed_s).then(setMoment).catch(() => setError("The race state could not be loaded."));
  }, [selected]);

  const shown = useMemo(
    () => media.filter((m) => kind === "all" || (kind === "photo" ? m.media_type === "photo" : m.media_type !== "photo")),
    [media, kind],
  );

  return (
    <div className="moments">
      <div className="moments-pick">
        <div className="chips">
          {(["all", "photo", "video"] as Kind[]).map((k) => (
            <button key={k} className={`chip ${kind === k ? "is-on" : ""}`} onClick={() => setKind(k)}>
              {k === "all" ? `All ${media.length}` : k === "photo" ? "Photos" : "Videos"}
            </button>
          ))}
        </div>
        <div className="thumb-grid">
          {shown.map((m) => (
            <button
              key={m.file}
              className={`thumb ${selected?.file === m.file ? "is-picked" : ""}`}
              onClick={() => setSelected(m)}
              title={`${m.file} at ${fmtClock(m.race_elapsed_s)}`}
            >
              <img src={`/thumbs/${stem(m.file)}.jpg`} alt="" loading="lazy" />
              <span>{fmtClock(m.race_elapsed_s)}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="moment-detail">
        {!selected && <p className="muted">Pick a photo or video to see the race at that moment.</p>}
        {selected && (
          <>
            {selected.media_type === "photo" ? (
              <img className="moment-photo" src={`/thumbs/${stem(selected.file)}.jpg`} alt={selected.file} />
            ) : (
              <video
                className="moment-photo"
                key={selected.file}
                src={`/videos/${stem(selected.file)}.mp4`}
                poster={`/thumbs/${stem(selected.file)}.jpg`}
                controls
                preload="metadata"
                playsInline
              />
            )}
            <dl className="moment-facts">
              <div><dt>File</dt><dd>{selected.file}</dd></div>
              <div><dt>Race time</dt><dd>{fmtClock(selected.race_elapsed_s)}</dd></div>
              <div><dt>Stage</dt><dd>{moment?.stage ?? "Loading"}</dd></div>
              <div>
                <dt>Leader at the last hourly split</dt>
                <dd>{selected.leader_team ? `${selected.leader_team}, car ${selected.leader_car}` : "Not known"}</dd>
              </div>
              {selected.nearest_section && <div><dt>Near</dt><dd>{selected.nearest_section}</dd></div>}
            </dl>
            {moment && moment.rows.length > 0 && (
              <table className="moment-order">
                <thead>
                  <tr><th>Position</th><th>Car</th><th>Team</th><th>Laps</th></tr>
                </thead>
                <tbody>
                  {moment.rows.slice(0, 10).map((r) => (
                    <tr key={r.car_number}>
                      <td>{r.position}</td>
                      <td>{r.car_number}</td>
                      <td>{r.team ?? ""}</td>
                      <td>{r.laps}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {moment && moment.rows.length === 0 && <p className="muted">No laps are recorded before the start.</p>}
            <p className="attribution">
              Order uses official lap times. Listed penalty time is added in full from the start, so positions near
              a penalty are approximate. Car 84 has a known gap in its lap records.
            </p>
          </>
        )}
        {error && <p className="banner">{error}</p>}
      </div>
    </div>
  );
}
