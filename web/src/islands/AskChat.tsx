import { type SubmitEvent, useState } from "react";

import { TopicTag } from "../components/ui/TopicTag";
import { formatDay } from "../lib/format";
import { readEvents } from "../lib/sse";
import { addTopic, loadPicked, savePicked, slotOf } from "../lib/topics";

interface Source {
  marker: number;
  slug: string;
  topic: string;
  title: string;
  edition_date: string;
}

interface Exchange {
  question: string;
  answer: string;
  sources: Source[];
  cited: number[];
  status: "streaming" | "done" | "error";
  message?: string;
}

/** Ask the notes: the answer streams in, citing the notes it comes from. */
export default function AskChat() {
  const [question, setQuestion] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [picked, setPicked] = useState(loadPickedSafely);
  const busy = exchanges.at(-1)?.status === "streaming";

  const update = (change: Partial<Exchange> | ((e: Exchange) => Partial<Exchange>)) =>
    setExchanges((all) => {
      const last = all.at(-1);
      if (!last) return all;
      const next = typeof change === "function" ? change(last) : change;
      return [...all.slice(0, -1), { ...last, ...next }];
    });

  async function ask(event: SubmitEvent) {
    event.preventDefault();
    const asked = question.trim();
    if (asked.length < 3 || busy) return;
    setQuestion("");
    setExchanges((all) => [
      ...all,
      { question: asked, answer: "", sources: [], cited: [], status: "streaming" },
    ]);
    try {
      const response = await fetch("/api/v1/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: asked, topics: picked.map((p) => p.slug) }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
        const message = typeof body.detail === "string" ? body.detail : "Ask is unavailable.";
        update({ status: "error", message });
        return;
      }
      for await (const { event: kind, data } of readEvents(response)) {
        if (kind === "sources") update({ sources: data as Source[] });
        else if (kind === "text") update((e) => ({ answer: e.answer + (data as string) }));
        else if (kind === "done") update({ status: "done", cited: (data as { cited: number[] }).cited });
        else if (kind === "error") update({ status: "error", message: data as string });
      }
      update((e) => (e.status === "streaming" ? { status: "done" } : {}));
    } catch {
      update({ status: "error", message: "Ask could not be reached." });
    }
  }

  const follow = (slug: string) => {
    const next = addTopic(picked, slug);
    savePicked(next);
    setPicked(next);
  };

  return (
    <div className="measure">
      <div className="chat">
        {exchanges.map((e, i) => (
          <div key={i} className="chat">
            <div className="chat-question">{e.question}</div>
            <div className="chat-answer" aria-live="polite">
              {e.answer || (e.status === "streaming" ? "…" : "")}
              {e.status === "error" && <p className="state state-error">{e.message}</p>}
            </div>
            {e.cited.length > 0 && (
              <ul className="notes">
                {e.cited.map((marker) => {
                  const s = e.sources[marker - 1];
                  if (!s) return null;
                  const followed = slotOf(picked, s.topic) !== undefined;
                  return (
                    <li key={marker} className="note-card">
                      <div className="top">
                        <span className="citation">{marker}</span>
                        <TopicTag name={s.topic} slot={slotOf(picked, s.topic)} />
                        <span className="meta">{formatDay(s.edition_date)}</span>
                      </div>
                      <a href={`/notes/${s.slug}`}>{s.title}</a>
                      {!followed && (
                        <button
                          type="button"
                          className="button button-secondary"
                          style={{ marginLeft: "var(--space-3)" }}
                          onClick={() => follow(s.topic)}
                        >
                          Follow
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        ))}
      </div>
      <form className="ask-form" onSubmit={ask}>
        <label className="sr-only" htmlFor="question">
          Your question
        </label>
        <input
          id="question"
          className="input"
          value={question}
          maxLength={300}
          placeholder="Ask about your topics"
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button className="button button-primary" type="submit" disabled={busy}>
          Ask
        </button>
      </form>
      <p className="small muted">
        Answers come only from published notes, with their sources. Ten questions a day.
      </p>
    </div>
  );
}

function loadPickedSafely() {
  return typeof localStorage === "undefined" ? [] : loadPicked();
}
