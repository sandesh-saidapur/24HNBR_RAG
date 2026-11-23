import type { CarPhotoMap } from "../types";

interface Props {
  carNumber: number | null;
  photos: CarPhotoMap;
}

/** Photos and video frames where the photo pass identified this car. */
export function CarPhotos({ carNumber, photos }: Props) {
  if (carNumber === null) return null;
  const list = photos[String(carNumber)] ?? [];
  return (
    <div className="card">
      <div className="card-head">
        <h2>In our photos</h2>
        <span className="muted small">{list.length} identified</span>
      </div>
      {list.length === 0 ? (
        <p className="muted small">No photos of car {carNumber} have been identified yet.</p>
      ) : (
        <ul className="car-photos">
          {list.map((s) => (
            <li key={s.src}>
              <img src={s.src} alt={s.caption} loading="lazy" />
              <span className="caption">{s.caption}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
