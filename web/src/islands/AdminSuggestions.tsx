import { useEffect, useState } from "react";

import { ErrorState } from "../components/ui/States";
import type { WaitingSuggestion } from "../lib/api/client";
import { api } from "../lib/api/client";
import { problem } from "../lib/admin";
import { formatDay } from "../lib/format";

/** Readers' topic suggestions. Accepting makes a draft topic and asks the worker to plan it;
 * its plan then waits under Topic plans. Who suggested a topic is not shown. */
export default function AdminSuggestions() {
  const [waiting, setWaiting] = useState<WaitingSuggestion[] | null>(null);
  const [error, setError] = useState("");
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [done, setDone] = useState<string[]>([]);

  useEffect(() => {
    api()
      .GET("/api/v1/admin/suggestions")
      .then(({ data, response }) => (data ? setWaiting(data) : setError(problem(response.status))))
      .catch(() => setError(problem(undefined)));
  }, []);

  async function decide(s: WaitingSuggestion, decision: "accept" | "decline") {
    try {
      const { data, error: failed } = await api().POST(
        "/api/v1/admin/suggestions/{suggestion_id}/decision",
        { params: { path: { suggestion_id: s.id } }, body: { decision, reason: reasons[s.id] ?? "" } },
      );
      if (failed || !data) return setError(`"${s.name}" could not be ${decision}ed.`);
      setWaiting((all) => (all ?? []).filter((w) => w.id !== s.id));
      setDone((all) => [
        ...all,
        decision === "accept"
          ? `Accepted "${s.name}" as ${data.topic}. The planner is running; its plan will wait under Topic plans.`
          : `Declined "${s.name}".`,
      ]);
    } catch {
      setError(problem(undefined));
    }
  }

  return (
    <div className="measure stack">
      {error && <ErrorState>{error}</ErrorState>}
      {done.map((line) => (
        <p key={line} className="muted" role="status">
          {line}
        </p>
      ))}
      {waiting?.length === 0 && <p className="muted">No suggestion waits for a decision.</p>}
      {waiting?.map((s) => (
        <article key={s.id} className="section stack">
          <div className="meta">
            suggestion-{s.id} · {formatDay(s.created_at.slice(0, 10))}
          </div>
          <h2 className="h2">{s.name}</h2>
          {s.note && <p>{s.note}</p>}
          <textarea
            className="input"
            aria-label={`Reason for declining ${s.name}`}
            placeholder="Reason, shown to the reader if you decline"
            maxLength={300}
            value={reasons[s.id] ?? ""}
            onChange={(e) => setReasons({ ...reasons, [s.id]: e.target.value })}
          />
          <div className="chips">
            <button className="button button-primary" type="button" onClick={() => decide(s, "accept")}>
              Accept and plan
            </button>
            <button className="button button-secondary" type="button" onClick={() => decide(s, "decline")}>
              Decline
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}
