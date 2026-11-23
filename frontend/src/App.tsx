import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { AskPanel } from "./components/AskPanel";
import { CarPanel } from "./components/CarPanel";
import { CarPhotos } from "./components/CarPhotos";
import { ClassificationTable } from "./components/ClassificationTable";
import { Timeline } from "./components/Timeline";
import { TrackMap } from "./components/TrackMap";
import { Figures } from "./dashboard/Figures";
import { Hero } from "./dashboard/Hero";
import { Podium } from "./dashboard/Podium";
import type { Car, CarPhotoMap, EventData, MediaItem, PaceMap, SlideItem, TrackOutline } from "./types";

export default function App() {
  const [cars, setCars] = useState<Car[]>([]);
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [track, setTrack] = useState<TrackOutline | null>(null);
  const [event, setEvent] = useState<EventData | null>(null);
  const [slides, setSlides] = useState<SlideItem[]>([]);
  const [pace, setPace] = useState<PaceMap>({});
  const [photos, setPhotos] = useState<CarPhotoMap>({});
  const [selectedCar, setSelectedCar] = useState<number | null>(80);
  const [clock, setClock] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Static assets come from /public; live data comes from the API.
    fetch("/data/event.json").then((r) => r.json()).then((e: EventData) => setEvent(e)).catch(() => undefined);
    fetch("/data/pace.json").then((r) => r.json()).then((p: PaceMap) => setPace(p)).catch(() => undefined);
    fetch("/data/car_photos.json").then((r) => r.json()).then((p: CarPhotoMap) => setPhotos(p)).catch(() => undefined);
    fetch("/data/slideshow.json").then((r) => r.json()).then((s: SlideItem[]) => setSlides(s)).catch(() => undefined);
    Promise.all([api.cars(), api.media(), api.track()])
      .then(([c, m, t]) => {
        setCars(c);
        setMedia(m);
        setTrack(t);
        const first = m.length ? Math.min(...m.map((x) => x.race_elapsed_s)) : 0;
        setClock(Math.max(0, first));
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const range = useMemo(() => {
    if (!media.length) return { min: 0, max: 86_400 };
    const times = media.map((m) => m.race_elapsed_s);
    return { min: Math.min(0, ...times), max: Math.max(...times) };
  }, [media]);

  return (
    <div className="dashboard">
      <Hero event={event} slides={slides} clock={clock} />

      <main className="content">
        {error && <p className="banner">Could not load the race data: {error}. Is the API running on port 8000?</p>}

        {event && <Figures figures={event.figures} />}
        {event && <Podium event={event} onSelect={setSelectedCar} />}

        <section className="block" id="explore">
          <div className="block-head">
            <h2>Explore the race</h2>
            <span className="muted">Classification, circuit, clock and questions. Everything here is live from the database.</span>
          </div>
          <div className="grid">
            <section className="panel panel-table">
              <ClassificationTable cars={cars} selected={selectedCar} onSelect={setSelectedCar} pace={pace} />
            </section>
            <section className="panel panel-map">
              <TrackMap track={track} media={media} clock={clock} />
              <Timeline min={range.min} max={range.max} value={clock} onChange={setClock} media={media} />
            </section>
            <section className="panel panel-side">
              <CarPanel carNumber={selectedCar} />
              <CarPhotos carNumber={selectedCar} photos={photos} />
              <AskPanel carNumber={selectedCar} />
            </section>
          </div>
        </section>

        {event && (
          <footer className="sources">
            <h3>Sources</h3>
            <ul>{event.sources.map((s) => <li key={s}>{s}</li>)}</ul>
          </footer>
        )}
      </main>
    </div>
  );
}
