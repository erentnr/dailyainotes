import { useEffect, useState } from "react";

import { ErrorState } from "../components/ui/States";
import { VerdictBadge } from "../components/ui/VerdictBadge";
import type { Review } from "../lib/api/client";
import { api } from "../lib/api/client";
import { formatDay } from "../lib/format";

const VERDICT = { supported: "verdict-ok", weak: "verdict-warn" } as Record<string, string>;
// Cloudflare Access signs the editor in before this page loads (ADR 0003); this ends that session.
const SIGN_OUT = "/cdn-cgi/access/logout";

/** Why the queue could not load, from the API's status; a failed request most often means
 * Access sent it to its sign-in page because the session ended. */
function problem(status: number | undefined): string {
  if (status === 503) return "Admin is off: Cloudflare Access is not set up. Approve with dan review on the server.";
  if (status === 401) return "Sign in through Cloudflare Access: reload this page.";
  if (status === undefined) return "Your sign-in has ended. Reload this page to sign in again.";
  return "Admin is unavailable.";
}

/** The approval page. Cloudflare Access has signed the editor in; the API checks its token. */
export default function AdminQueue() {
  const [email, setEmail] = useState("");
  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [error, setError] = useState("");
  const [comments, setComments] = useState<Record<number, string>>({});

  useEffect(() => {
    void (async () => {
      try {
        const me = await api().GET("/api/v1/admin/me");
        if (!me.data) return setError(problem(me.response.status));
        setEmail(me.data.email);
        const { data, response } = await api().GET("/api/v1/admin/notes");
        if (!data) return setError(problem(response.status));
        setReviews(data);
      } catch {
        setError(problem(undefined));
      }
    })();
  }, []);

  async function decide(id: number, decision: "approve" | "reject") {
    try {
      const { error: failed } = await api().POST("/api/v1/admin/notes/{note_id}/decision", {
        params: { path: { note_id: id } },
        body: { decision, comment: comments[id] ?? "" },
      });
      if (failed) return setError(`note-${id} could not be ${decision}d.`);
      setReviews((all) => (all ?? []).filter((r) => r.id !== id));
    } catch {
      setError(problem(undefined));
    }
  }

  return (
    <div className="measure stack">
      {email && (
        <p className="meta">
          Signed in as {email} · <a href={SIGN_OUT}>Sign out</a>
        </p>
      )}
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
