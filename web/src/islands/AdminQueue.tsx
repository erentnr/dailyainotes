import { type SubmitEvent, useEffect, useState } from "react";

import { ErrorState } from "../components/ui/States";
import { VerdictBadge } from "../components/ui/VerdictBadge";
import type { Review } from "../lib/api/client";
import { api } from "../lib/api/client";
import { formatDay } from "../lib/format";

const KEY = "dan.admin";
const VERDICT = { supported: "verdict-ok", weak: "verdict-warn" } as Record<string, string>;

/** The minimal approval page: the token stays in this tab's session storage. */
export default function AdminQueue() {
  const [token, setToken] = useState(() => sessionStorage.getItem(KEY) ?? "");
  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [error, setError] = useState("");
  const [comments, setComments] = useState<Record<number, string>>({});
  const headers = { Authorization: `Bearer ${token}` };

  async function load() {
    setError("");
    const { data, response } = await api().GET("/api/v1/admin/notes", { headers });
    if (!data) {
      setReviews(null);
      setError(response.status === 401 ? "That token is not right." : "Admin is unavailable.");
      return;
    }
    sessionStorage.setItem(KEY, token);
    setReviews(data);
  }

  // Once, with a token saved earlier in this tab.
  useEffect(() => {
    if (token) void load();
  }, []);

  async function decide(id: number, decision: "approve" | "reject") {
    const { error: failed } = await api().POST("/api/v1/admin/notes/{note_id}/decision", {
      params: { path: { note_id: id } },
      body: { decision, comment: comments[id] ?? "" },
      headers,
    });
    if (failed) setError(`note-${id} could not be ${decision}d.`);
    else setReviews((all) => (all ?? []).filter((r) => r.id !== id));
  }

  const signIn = (event: SubmitEvent) => {
    event.preventDefault();
    void load();
  };

  return (
    <div className="measure stack">
      <form className="ask-form" onSubmit={signIn}>
        <label className="sr-only" htmlFor="token">
          Admin token
        </label>
        <input
          id="token"
          className="input"
          type="password"
          autoComplete="off"
          value={token}
          placeholder="Admin token"
          onChange={(e) => setToken(e.target.value)}
        />
        <button className="button button-secondary" type="submit">
          Load
        </button>
      </form>
      {error && <ErrorState>{error}</ErrorState>}
      {reviews?.length === 0 && <p className="muted">Nothing waits for approval.</p>}
      {reviews?.map((r) => {
        const supported = r.claims.filter((c) => c.verdict === "supported").length;
        const unsupported = r.claims.filter((c) => c.verdict !== "supported" && c.verdict !== "weak").length;
        return (
          <article key={r.id} className="section">
            <div className="meta">
              note-{r.id} · {r.topic} · {formatDay(r.edition_date)} · version {r.version}
            </div>
            <h2 className="h2" style={{ marginTop: "var(--space-2)" }}>
              {r.title}
            </h2>
            <p className="reading">{r.body}</p>
            <p className="muted">Why it matters: {r.why_it_matters}</p>
            <div className="label">Sources</div>
            <ol className="small">
              {r.citations.map((c) => (
                <li key={c.marker}>
                  [{c.marker}] {c.publisher}:{" "}
                  <a href={c.url} rel="noopener noreferrer" target="_blank">
                    {c.title}
                  </a>
                </li>
              ))}
            </ol>
            <div className="label">
              Claims <VerdictBadge claims={r.claims.length} supported={supported} unsupported={unsupported} />
            </div>
            <table className="table small">
              <tbody>
                {r.claims.map((c, i) => (
                  <tr key={i}>
                    <td>
                      <span className={`verdict ${VERDICT[c.verdict] ?? "verdict-bad"}`}>{c.verdict}</span>
                    </td>
                    <td>
                      {c.text} <span className="meta">{c.markers.map((m) => `[${m}]`).join("")}</span>
                      {c.verdict !== "supported" && <div className="muted">{c.rationale}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <textarea
              className="input"
              aria-label={`Comment on note-${r.id}`}
              placeholder="Comment (kept with the decision)"
              value={comments[r.id] ?? ""}
              onChange={(e) => setComments({ ...comments, [r.id]: e.target.value })}
            />
            <div className="chips" style={{ marginTop: "var(--space-3)" }}>
              <button className="button button-primary" type="button" onClick={() => decide(r.id, "approve")}>
                Approve and publish
              </button>
              <button className="button button-secondary" type="button" onClick={() => decide(r.id, "reject")}>
                Reject
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}
