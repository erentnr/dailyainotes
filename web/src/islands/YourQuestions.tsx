import { Fragment, useEffect, useState } from "react";

import type { AskedQuestion } from "../lib/api/client";
import { api } from "../lib/api/client";
import { formatDay } from "../lib/format";

/** The reader's questions to Ask from the last 30 days, newest first (ADR 0004 keeps them with
 * the account). Each links to asking it again, and to the notes its answer cited. */
export default function YourQuestions() {
  const [questions, setQuestions] = useState<AskedQuestion[] | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api()
      .GET("/api/v1/me/questions")
      .then(({ data }) => (data ? setQuestions(data) : setFailed(true)))
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <p className="small muted">Your questions did not load. Reload the page to try again.</p>;
  if (questions === null) return <p className="small muted">Loading your questions…</p>;
  if (questions.length === 0) {
    return (
      <p className="muted">
        No questions in the last 30 days. <a href="/ask">Ask the notes</a>.
      </p>
    );
  }
  return (
    <ul className="plain-list">
      {questions.map((q) => (
        <li key={`${q.asked_at}-${q.question}`}>
          <a href={`/ask?q=${encodeURIComponent(q.question)}`}>{q.question}</a>{" "}
          <span className="meta">{formatDay(q.asked_at.slice(0, 10))}</span>
          <div className="small muted">
            {!q.answered && "Not enough in the notes."}
            {q.answered &&
              (q.notes.length === 0 ? (
                "Answered from notes no longer published."
              ) : (
                <>
                  From{" "}
                  {q.notes.map((n, i) => (
                    <Fragment key={n.slug}>
                      {i > 0 && ", "}
                      <a href={`/notes/${n.slug}`}>{n.title}</a>
                    </Fragment>
                  ))}
                </>
              ))}
          </div>
        </li>
      ))}
    </ul>
  );
}
