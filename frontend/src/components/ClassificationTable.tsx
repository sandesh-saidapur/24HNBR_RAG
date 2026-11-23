import { useMemo, useState } from "react";
import { fmtClock } from "../format";
import type { Car, PaceMap } from "../types";
import { Spark } from "../sparkline";

interface Props {
  cars: Car[];
  selected: number | null;
  onSelect: (car: number) => void;
  pace: PaceMap;
}

export function ClassificationTable({ cars, selected, onSelect, pace }: Props) {
  const [query, setQuery] = useState("");
  const [classFilter, setClassFilter] = useState("all");
  const classes = useMemo(
    () => ["all", ...Array.from(new Set(cars.map((c) => c.class ?? "—"))).sort()],
    [cars],
  );
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return cars.filter((c) => {
      if (classFilter !== "all" && (c.class ?? "—") !== classFilter) return false;
      if (!q) return true;
      return (
        String(c.car_number).includes(q) ||
        (c.team ?? "").toLowerCase().includes(q) ||
        (c.drivers ?? "").toLowerCase().includes(q)
      );
    });
  }, [cars, query, classFilter]);

  return (
    <div className="table-wrap">
      <div className="toolbar">
        <input
          aria-label="Search cars"
          placeholder="Car, team or driver"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select aria-label="Class" value={classFilter} onChange={(e) => setClassFilter(e.target.value)}>
          {classes.map((c) => (
            <option key={c} value={c}>{c === "all" ? "All classes" : c}</option>
          ))}
        </select>
      </div>
      <div className="scroll">
        <table>
          <thead>
            <tr><th>Pos</th><th>No.</th><th>Team</th><th>Class</th><th>Laps</th><th>Total</th><th>Status</th><th>Pace</th></tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr
                key={c.car_number}
                className={c.car_number === selected ? "is-selected" : undefined}
                onClick={() => onSelect(c.car_number)}
              >
                <td>{c.position ?? "—"}</td>
                <td className="num">{c.car_number}</td>
                <td>{c.team ?? "—"}</td>
                <td>{c.class ?? "—"}</td>
                <td className="num">{c.laps}</td>
                <td className="num">{fmtClock(c.total_time_s)}</td>
                <td><span className={`badge badge-${c.status.toLowerCase()}`}>{c.status}</span></td>
                <td>
                  <Spark
                    values={pace[String(c.car_number)] ?? []}
                    label={`Lap times for car ${c.car_number}, faster laps higher`}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
