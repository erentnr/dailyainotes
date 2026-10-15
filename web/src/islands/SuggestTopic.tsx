import { type SubmitEvent, useState } from "react";

import type { Suggestion } from "../lib/api/client";
import { api } from "../lib/api/client";
import { formatDay } from "../lib/format";

/** What a suggestion's reader sees about it. */
function outcome(s: Suggestion): string {
  if (s.status === "open") return "Waiting for the editor.";
  if (s.status === "declined") return s.reason ? `Declined: ${s.reason}` : "Declined.";
  return s.topic_status === "active"
    ? "Accepted, and live: follow it on Topics."
    : "Accepted. We are finding sources for it; it goes live once the editor approves them.";
}

/** Suggest a topic for the catalog; the editor accepts or declines it (ADR 0003). */
export default function SuggestTopic({ initial }: { initial: Suggestion[] }) {
  const [suggestions, setSuggestions] = useState(initial);
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { data, error: failed } = await api().POST("/api/v1/me/suggestions", {
        body: { name, note },
      });
      if (!data) {
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
        Missing a topic? Suggest it. The editor reads every suggestion; an accepted one gets its own
        sources, checked before they are used.
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
        <div>
          <button className="button button-primary" type="submit" disabled={busy || name.trim().length < 3}>
            Suggest
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
