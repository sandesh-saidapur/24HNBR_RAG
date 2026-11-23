export interface Car {
  position: number | null;
  status: string;
  car_number: number;
  class: string | null;
  team: string | null;
  car_model: string | null;
  laps: number;
  total_time_s: number | null;
  best_lap_s: number | null;
  gap_or_interval: string | null;
  drivers: string | null;
  penalty_seconds_listed: number | null;
  lap_sum_minus_total_s: number | null;
  sector_sum_mismatch_laps: number | null;
}

export interface Penalty {
  car_number: number;
  penalty_seconds: number;
  kind: string;
  steward_decision_no: number | null;
  offence_verbatim: string;
  source_file: string;
}

export interface CarDetail extends Car {
  penalties: Penalty[];
}

export interface Lap {
  lap: number;
  lap_time_s: number | null;
}

export interface MediaItem {
  file: string;
  media_type: string;
  capture_utc: string;
  latitude: number | null;
  longitude: number | null;
  phase: string;
  race_elapsed_s: number;
  split_hour: number | null;
  leader_car: number | null;
  leader_team: string | null;
  nearest_section: string | null;
  distance_m: number | null;
  on_course: boolean | null;
}

export interface TrackOutline {
  attribution: string;
  points: [number, number][];
}

export interface EvidenceItem {
  id: string;
  kind: string;
  source: string;
  text: string;
}

export interface AskResponse {
  status: "answered" | "evidence_only" | "needs_question";
  intent: string;
  evidence: EvidenceItem[];
  answer: string | null;
  verified: boolean | null;
  problems: string[];
  notes: string[];
}

export interface EventFigure {
  value: string;
  label: string;
}

export interface PodiumRow {
  position: number | null;
  car_number: number;
  status: string;
  team: string | null;
  drivers: string | null;
  total_time_s: number | null;
}

export interface Statement {
  name: string;
  role: string;
  summary: string;
}

export interface EventData {
  title: string;
  dates: string;
  figures: EventFigure[];
  podium: PodiumRow[];
  statements: { car_number: number; people: Statement[] }[];
  sources: string[];
  note: string;
}

export interface SlideItem {
  src: string;
  caption: string;
  kind: "photo" | "video";
  file?: string;
  race_elapsed_s?: number;
  width?: number;
  height?: number;
}

/** Lap times in seconds per car number (string key), in lap order. */
export type PaceMap = Record<string, number[]>;

/** Identified photos and video frames per car number (string key). */
export type CarPhotoMap = Record<string, SlideItem[]>;

export interface PhotoHit {
  key: string;
  file: string;
  race_elapsed_s: number;
  caption: string;
  score: number;
}

export interface CircuitSegments {
  attribution: string;
  segments: [number, number][][];
}
