import { useState, type FormEvent } from "react";
import { api } from "../api";
import type { AskResponse, EvidenceItem } from "../types";

interface Props {
  carNumber: number | null;
}

const SOURCE_LABEL: Record<string, string> = {
  car: "Official timing",
  penalty: "Penalty list",
  standing: "Hourly standing",
  media: "Photo timeline",
  document: "Press documents",
};

const CITATION = /\[(E\d+)\]/g;

/** Turns verifier messages into plain English for the reader. */
export function explain(problem: string): string {
  if (problem === "no citations") return "The answer does not point to any evidence.";
  const cited = problem.match(/^citation (E\d+) is not in the evidence$/);
  if (cited) return `The answer cites ${cited[1]}, which is not in the evidence.`;
  const figure = problem.match(/^figure not in evidence: (.+)$/);
  if (figure) return `The figure ${figure[1]} does not appear in the evidence.`;
  return problem;
}

/** Answer text with each [E#] shown as a button that highlights its evidence. */
export function AnswerText({ text, onCite }: { text: string; onCite: (id: string) => void }) {
  const parts = text.split(CITATION);
  return (
    <p className="answer-text">
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <button key={i} type="button" className="cite-chip" onClick={() => onCite(part)}>
            {part}
          </button>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </p>
  );
}

export function EvidenceList({ items, active }: { items: EvidenceItem[]; active: string | null }) {
  return (
    <ol className="evidence">
      {items.map((e) => (
        <li key={e.id} id={`ev-${e.id}`} className={e.id === active ? "is-active" : undefined}>
          <span className="cite">[{e.id}]</span> {e.text}{" "}
          <span className="muted small">
            · {SOURCE_LABEL[e.kind] ?? e.kind} · {e.source}
          </span>
        </li>
      ))}
    </ol>
  );
}

export function AskPanel({ carNumber }: Props) {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (question.trim().length < 3) return;
    setBusy(true);
    setError(null);
    setActive(null);
    try {
      setResult(await api.ask({ question, car_number: carNumber ?? undefined }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function cite(id: string) {
    setActive(id);
    document.getElementById(`ev-${id}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  return (
    <div className="card">
      <h2>Ask a question</h2>
      <form onSubmit={submit} className="ask">
        <textarea
          aria-label="Question"
          placeholder={carNumber ? `Ask about car ${carNumber} or the race` : "Ask about the race"}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
        />
        <button type="submit" disabled={busy || question.trim().length < 3}>
          {busy ? "Checking the evidence…" : "Ask"}
        </button>
      </form>
      {error && <p className="banner">{error}</p>}
      {result && (
        <div className="answer">
          {result.answer ? (
            <>
              <AnswerText text={result.answer} onCite={cite} />
              {result.verified ? (
                <p className="verified ok">Every claim cites evidence, and every figure is in it.</p>
              ) : (
                <div className="verified warn">
                  <strong>Needs review</strong>
                  <ul>
                    {result.problems.map((p) => (
                      <li key={p}>{explain(p)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <p className="muted">
              {result.status === "needs_question"
                ? "Name a car, split or photo, or ask about a document."
                : "The evidence is below. The answer needs a Groq key on the server."}
            </p>
          )}
          {result.notes.map((n) => (
            <p key={n} className="muted small">{n}</p>
          ))}
          <EvidenceList items={result.evidence} active={active} />
        </div>
      )}
    </div>
  );
}
