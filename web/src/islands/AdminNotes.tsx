import { useEffect, useState } from "react";

import { ErrorState } from "../components/ui/States";
import type { AdminNote } from "../lib/api/client";
import { api } from "../lib/api/client";
import { problem } from "../lib/admin";
import { formatDay } from "../lib/format";

/** The latest published notes, each with Withdraw: notes publish without a review (ADR 0008).
 * Cloudflare Access has signed the editor in; the API checks its token. */
export default function AdminNotes() {
  const [email, setEmail] = useState("");
  const [notes, setNotes] = useState<AdminNote[] | null>(null);
  const [error, setError] = useState("");
  // Withdrawing asks first, on the page itself.
  const [confirming, setConfirming] = useState<number | null>(null);
  const [comment, setComment] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        const me = await api().GET("/api/v1/admin/me");
        if (!me.data) return setError(problem(me.response.status));
        setEmail(me.data.email);
        const { data, response } = await api().GET("/api/v1/admin/notes");
        if (!data) return setError(problem(response.status));
        setNotes(data);
      } catch {
        setError(problem(undefined));
      }
    })();
  }, []);

  function ask(id: number | null) {
    setConfirming(id);
    setComment("");
  }

  async function withdraw(id: number) {
    try {
      const { error: failed } = await api().POST("/api/v1/admin/notes/{note_id}/withdraw", {
        params: { path: { note_id: id } },
        body: { comment },
      });
      if (failed) return setError(`note-${id} could not be withdrawn.`);
      setNotes((all) => (all ?? []).filter((n) => n.id !== id));
      ask(null);
    } catch {
      setError(problem(undefined));
    }
  }

  return (
    <div className="measure stack">
      {email && <p className="meta">Signed in as {email}</p>}
      {error && <ErrorState>{error}</ErrorState>}
      {notes?.length === 0 && <p className="muted">No notes are published yet.</p>}
      {notes?.map((n) => (
        <article key={n.id} className="section">
          <div className="meta">
            note-{n.id} · {n.topic} · {formatDay(n.edition_date)} · {n.supported}/{n.claims} claims supported
          </div>
          <h2 className="h2" style={{ marginTop: "var(--space-2)" }}>
            <a href={`/notes/${n.slug}`}>{n.title}</a>
          </h2>
          {confirming === n.id ? (
            <div className="stack" style={{ marginTop: "var(--space-3)" }}>
              <p>Withdraw note-{n.id}? It leaves the site, Ask and the MCP server.</p>
              <textarea
                className="input"
                aria-label={`Why note-${n.id} is withdrawn`}
                placeholder="Why (kept with the decision)"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
              <div className="chips">
                <button className="button button-primary" type="button" onClick={() => withdraw(n.id)}>
                  Withdraw
                </button>
                <button className="button button-secondary" type="button" onClick={() => ask(null)}>
                  Keep it
                </button>
              </div>
            </div>
          ) : (
            <div className="chips" style={{ marginTop: "var(--space-3)" }}>
              <button className="button button-secondary" type="button" onClick={() => ask(n.id)}>
                Withdraw…
              </button>
            </div>
          )}
        </article>
      ))}
    </div>
  );
}
