interface Props {
  values: number[];
  width?: number;
  height?: number;
  label: string;
}

/**
 * Lap-time sparkline. Faster laps sit higher. The scale stops at 1.4 x the median, so pit
 * laps and outliers are pinned to the floor instead of flattening the rest of the line.
 */
export function Spark({ values, width = 120, height = 22, label }: Props) {
  if (values.length < 2) return <span className="muted small">—</span>;
  const sorted = [...values].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)];
  const lo = sorted[0];
  const hi = Math.min(sorted[sorted.length - 1], median * 1.4);
  const span = hi - lo || 1;
  const path = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const clipped = Math.min(Math.max(v, lo), hi);
      const y = 2 + (1 - (clipped - lo) / span) * (height - 4);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg className="spark-inline" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label}>
      <title>{label}</title>
      <path d={path} />
    </svg>
  );
}
