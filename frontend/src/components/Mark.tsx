/** Original Trackside 24 mark: a track loop with "24". It is not the organiser's logo. */
export function Mark({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true" className="mark">
      <circle cx="20" cy="20" r="18.5" className="mark-ring" />
      <path d="M7 25 C10 11, 30 11, 33 25 C35 31, 24 33, 20 27 C16 21, 5 31, 7 25 Z" className="mark-loop" />
      <text x="20" y="23.5" textAnchor="middle" className="mark-text">24</text>
    </svg>
  );
}
