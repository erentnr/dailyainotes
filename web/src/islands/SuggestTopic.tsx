import { type SubmitEvent, useState } from "react";

import type { Suggestion } from "../lib/api/client";
import { api } from "../lib/api/client";
import { formatDay } from "../lib/format";
import { coveredBy } from "../lib/topics";

/** What the reader who added a topic sees about it. */
function outcome(s: Suggestion): string {
  if (s.topic_status === "active") return "Live for everyone, and in your topics.";
  if (s.status === "declined") return s.reason ? `Not added: ${s.reason}` : "Not added.";
  if (s.status === "open") return "Waiting for the editor.";
  return "We are finding sources for it; it goes live once the editor approves them.";
}

/** Add a topic (ADR 0006): planned at once, unless an existing topic covers it. */
export default function SuggestTopic({ initial }: { initial: Suggestion[] }) {
  const [suggestions, setSuggestions] = useState(initial);
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [covered, setCovered] = useState<{ slug: string; message: string } | null>(null);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setCovered(null);
    try {
      const { data, error: failed } = await api().POST("/api/v1/me/suggestions", {
        body: { name, note },
      });
      if (!data) {
        const covering = coveredBy(failed);
        if (covering) return setCovered(covering);
        const text = (failed as { detail?: unknown } | undefined)?.detail;
        return setError(typeof text === "string" ? text : "That did not work. Try again.");
      }
      setSuggestions(data.suggestions);
      setName("");
      setNote("");
    } catch {
      setError("That did not work. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <p className="muted">
        Missing a topic? Add it. If a topic already covers it, we point you there; otherwise we look
        for sources, and it goes live for everyone once the editor approves them.
      </p>
      <form className="stack" onSubmit={submit}>
        <div className="field">
          <label className="label" htmlFor="suggest-name">
            Topic
          </label>
          <input
            id="suggest-name"
            className="input"
            required
            minLength={3}
            maxLength={80}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="suggest-note">
            What it should follow (optional)
          </label>
          <textarea
            id="suggest-note"
            className="input"
            maxLength={300}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {covered && (
          <p role="status">
            {covered.message} <a href="/topics">Pick it on Topics</a>.
          </p>
        )}
        <div>
          <button className="button button-primary" type="submit" disabled={busy || name.trim().length < 3}>
            Add topic
          </button>
        </div>
      </form>
      {suggestions.length > 0 && (
        <ul className="plain-list">
          {suggestions.map((s) => (
            <li key={s.id}>
              <strong>{s.name}</strong> <span className="meta">{formatDay(s.created_at.slice(0, 10))}</span>
              <div className="small muted">{outcome(s)}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
