import type { AskResponse, Car, CarDetail, CircuitSegments, Lap, MediaItem, MomentRow, PhotoHit, TrackOutline } from "./types";

async function get<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return (await response.json()) as T;
}

export const api = {
  cars: () => get<Car[]>("/api/cars"),
  car: (n: number) => get<CarDetail>(`/api/cars/${n}`),
  laps: (n: number) => get<Lap[]>(`/api/cars/${n}/laps?limit=2000`),
  media: () => get<MediaItem[]>("/api/media"),
  track: () => get<TrackOutline>("/api/track"),
  circuit: () => get<CircuitSegments>("/api/track/circuit"),
  moment: (t: number) => get<MomentRow>(`/api/moment?t=${encodeURIComponent(t)}`),
  async searchPhotos(q: string, k = 8): Promise<PhotoHit[]> {
    const params = new URLSearchParams({ q, k: String(k) });
    const response = await fetch(`/api/search/photos?${params}`);
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new Error(body.detail ?? `search failed (${response.status})`);
    }
    return (await response.json()) as PhotoHit[];
  },
  async ask(body: { question: string; car_number?: number; file?: string }): Promise<AskResponse> {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`/api/ask: ${response.status}`);
    return (await response.json()) as AskResponse;
  },
};
