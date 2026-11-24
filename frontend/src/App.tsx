import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { AskPanel } from "./components/AskPanel";
import { CarPanel } from "./components/CarPanel";
import { CarPhotos } from "./components/CarPhotos";
import { ClassificationTable } from "./components/ClassificationTable";
import { Mark } from "./components/Mark";
import { PhotoSearch } from "./components/PhotoSearch";
import { PhotoWindow } from "./components/PhotoWindow";
import { MomentPanel } from "./components/MomentPanel";
import { HeroTrack } from "./components/HeroTrack";
import { Timeline } from "./components/Timeline";
import { TrackMap } from "./components/TrackMap";
import { Figures } from "./dashboard/Figures";
import { Hero } from "./dashboard/Hero";
import { Podium } from "./dashboard/Podium";
import type { Car, CarPhotoMap, EventData, MediaItem, PaceMap, SlideItem, TrackOutline } from "./types";

const SECTIONS = [
  { id: "weekend", label: "Weekend" },
  { id: "podium", label: "Podium" },
  { id: "explore", label: "Explore" },
  { id: "moments", label: "Moments" },
];

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
  const [active, setActive] = useState<string>("weekend");

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

  // Highlight the section in view in the top bar.
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-40% 0px -55% 0px" },
    );
    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [event]);

  const range = useMemo(() => {
    if (!media.length) return { min: 0, max: 86_400 };
    const times = media.map((m) => m.race_elapsed_s);
    return { min: Math.min(0, ...times), max: Math.max(...times) };
  }, [media]);

  return (
    <div className="dashboard">
      <nav className="topbar">
        <a className="brand" href="#top">
          <Mark />
          <span>Trackside 24</span>
        </a>
        <ul className="navlinks">
          {SECTIONS.map((s) => (
            <li key={s.id}>
              <a href={`#${s.id}`} className={active === s.id ? "is-active" : undefined}>{s.label}</a>
            </li>
          ))}
        </ul>
      </nav>

      <div id="top" />
      <Hero event={event} map={<HeroTrack />}>
        <PhotoWindow slides={slides} clock={clock} />
      </Hero>

      <main className="content">
        {error && <p className="banner">Could not load the race data: {error}. Is the API running on port 8000?</p>}

        <section className="block section" id="weekend">
          <div className="section-title"><h2>The weekend in figures</h2></div>
          {event && <Figures figures={event.figures} />}
        </section>

        <section className="block section" id="podium">
          <div className="section-title"><h2>Podium and words from the drivers</h2></div>
          {event && <Podium event={event} onSelect={setSelectedCar} />}
        </section>

        <section className="block section" id="explore">
          <div className="section-title">
            <h2>Explore the race</h2>
            <span className="muted small">Classification, circuit, clock and questions. Live from the database.</span>
          </div>
          <PhotoSearch onPick={(s) => setClock(s)} />
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


        <section className="block section" id="moments">
          <div className="section-title">
            <h2>Moments</h2>
            <span className="muted small">Pick a photo or video to see the race at that moment.</span>
          </div>
          <MomentPanel />
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
