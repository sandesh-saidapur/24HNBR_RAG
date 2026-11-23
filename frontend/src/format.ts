/** Race clock, matching the Python formatter: 86727.664 -> "24:05:27.664". */
export function fmtClock(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "—";
  const totalMs = Math.round(seconds * 1000);
  const hours = Math.floor(totalMs / 3_600_000);
  const minutes = Math.floor((totalMs % 3_600_000) / 60_000);
  const secs = Math.floor((totalMs % 60_000) / 1000);
  const ms = totalMs % 1000;
  const mm = String(minutes).padStart(2, "0");
  const ss = String(secs).padStart(2, "0");
  const sss = String(ms).padStart(3, "0");
  return hours > 0 ? `${hours}:${mm}:${ss}.${sss}` : `${minutes}:${ss}.${sss}`;
}

/** Penalty and gap values: 90 -> "90 s", 118.795 -> "118.8 s". */
export function fmtSeconds(seconds: number): string {
  return Number.isInteger(seconds) ? `${seconds} s` : `${seconds.toFixed(1)} s`;
}

/** Hour of the race clock, for scrubber labels: 13 -> "13:00" (race hour, not wall clock). */
export function fmtRaceHour(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}
