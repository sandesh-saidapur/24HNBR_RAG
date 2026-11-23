import { useState, type FormEvent } from "react";
import { api } from "../api";
import type { AskResponse } from "../types";

interface Props {
  carNumber: number | null;
}

export function AskPanel({ carNumber }: Props) {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (question.trim().length < 3) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.ask({ question, car_number: carNumber ?? undefined }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Ask the race</h2>
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
              <p>{result.answer}</p>
              <p className={result.verified ? "verified ok" : "verified warn"}>
                {result.verified ? "Every figure checked against the evidence" : `Needs review: ${result.problems.join("; ")}`}
              </p>
            </>
          ) : (
            <p className="muted">
              {result.status === "needs_question"
                ? "Name a car, split or photo, or ask about a document."
                : "The evidence is below. The answer needs a Groq key on the server."}
            </p>
          )}
          {result.notes.map((n) => <p key={n} className="muted">{n}</p>)}
          <ol className="evidence">
            {result.evidence.map((e) => (
              <li key={e.id}><span className="cite">[{e.id}]</span> {e.text} <span className="muted">· {e.source}</span></li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
