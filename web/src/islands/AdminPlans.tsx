import { useEffect, useState } from "react";

import { ErrorState } from "../components/ui/States";
import type { Plan } from "../lib/api/client";
import { api } from "../lib/api/client";
import { percent, problem } from "../lib/admin";
import { formatDay } from "../lib/format";

/** Topic plans waiting for review: approving adds the sources and makes the topic active. */
export default function AdminPlans() {
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [error, setError] = useState("");
  const [comments, setComments] = useState<Record<number, string>>({});

  useEffect(() => {
    api()
      .GET("/api/v1/admin/plans")
      .then(({ data, response }) => (data ? setPlans(data) : setError(problem(response.status))))
      .catch(() => setError(problem(undefined)));
  }, []);

  async function decide(id: number, decision: "approve" | "reject") {
    try {
      const { error: failed } = await api().POST("/api/v1/admin/plans/{plan_id}/decision", {
        params: { path: { plan_id: id } },
        body: { decision, comment: comments[id] ?? "" },
      });
      if (failed) return setError(`plan-${id} could not be ${decision}d.`);
      setPlans((all) => (all ?? []).filter((p) => p.id !== id));
    } catch {
      setError(problem(undefined));
    }
  }

  return (
    <div className="measure stack">
      {error && <ErrorState>{error}</ErrorState>}
      {plans?.length === 0 && <p className="muted">No topic plan waits for review.</p>}
      {plans?.map((p) => (
        <article key={p.id} className="section stack">
          <div className="meta">
            plan-{p.id} · {p.topic} · version {p.version} · {formatDay(p.created_at.slice(0, 10))}
          </div>
          <h2 className="h2">{p.name}</h2>
          <p>
            <span className="label">Keywords</span>
            <br />
            {p.keywords.join(", ")}
          </p>
          {p.entities.length > 0 && (
            <p>
              <span className="label">Entities</span>
              <br />
              {p.entities.join(", ")}
            </p>
          )}
          {p.negative_keywords.length > 0 && (
            <p className="muted">Not about: {p.negative_keywords.join(", ")}</p>
          )}
          <div className="label">Sources ({p.sources.length})</div>
          {p.sources.length === 0 ? (
            <p className="muted">The planner found no usable source. Reject it, or plan it again later.</p>
          ) : (
            <div className="table-wrap">
              <table className="table small">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th className="num">Recent</th>
                    <th className="num">On topic</th>
                    <th className="num">Readable</th>
                  </tr>
                </thead>
                <tbody>
                  {p.sources.map((s) => (
                    <tr key={s.locator}>
                      <td>
                        <span className="meta">{s.type}</span>
                        <br />
                        {s.type === "rss" ? (
                          <a href={s.locator} rel="noopener noreferrer" target="_blank">
                            {s.locator}
                          </a>
                        ) : (
                          s.locator
                        )}
                      </td>
                      <td className="num">{s.recent_items}</td>
                      <td className="num">{percent(s.match_share)}</td>
                      <td className="num">{percent(s.readable_share)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {p.dropped.length > 0 && (
            <details>
              <summary className="label">Tried and not used ({p.dropped.length})</summary>
              <ul className="small">
                {p.dropped.map((d) => (
                  <li key={d.locator}>
                    <span className="meta">{d.locator}</span>
                    <br />
                    {d.reason}
                  </li>
                ))}
              </ul>
            </details>
          )}
          <textarea
            className="input"
            aria-label={`Comment on plan-${p.id}`}
            placeholder="Comment (kept with the decision)"
            value={comments[p.id] ?? ""}
            onChange={(e) => setComments({ ...comments, [p.id]: e.target.value })}
          />
          <div className="chips">
            <button
              className="button button-primary"
              type="button"
              disabled={p.sources.length === 0}
              onClick={() => decide(p.id, "approve")}
            >
              Approve and activate
            </button>
            <button className="button button-secondary" type="button" onClick={() => decide(p.id, "reject")}>
              Reject
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}
