import { useEffect, useState } from "react";

import { Check } from "../components/ui/Icons";
import type { Topic } from "../lib/api/client";
import { api } from "../lib/api/client";
import { plural } from "../lib/format";
import { addTopic, loadPicked, type Picked, removeTopic, SLOTS, savePicked } from "../lib/topics";

/** The catalog: pick up to eight topics. The choice stays in this browser, and a signed-in
 * reader's account keeps it for every device (ADR 0003). */
export default function TopicPicker({ topics, signedIn }: { topics: Topic[]; signedIn: boolean }) {
  const [picked, setPicked] = useState<Picked[]>([]);
  const [unsaved, setUnsaved] = useState(false);
  useEffect(() => setPicked(loadPicked()), []);

  const toggle = async (slug: string) => {
    const next = picked.some((p) => p.slug === slug)
      ? removeTopic(picked, slug)
      : addTopic(picked, slug);
    savePicked(next);
    setPicked(next);
    if (!signedIn) return;
    try {
      const { error } = await api().PUT("/api/v1/me/topics", { body: { topics: next } });
      setUnsaved(error !== undefined);
    } catch {
      setUnsaved(true);
    }
  };

  return (
    <>
      <p className="muted">
        {picked.length} of {SLOTS} picked.{" "}
        {signedIn ? (
          "Your account keeps them for every device you sign in on."
        ) : (
          <>
            Your choice stays in this browser. <a href="/sign-in?next=/topics">Sign in</a> to keep
            it on every device.
          </>
        )}
      </p>
      {unsaved && (
        <p className="form-error" role="alert">
          Your account could not save that change; it is kept in this browser. Try again in a moment.
        </p>
      )}
      <div className="tiles">
        {topics.map((topic) => {
          const on = picked.some((p) => p.slug === topic.slug);
          return (
            <button
              key={topic.slug}
              type="button"
              className="tile"
              aria-pressed={on}
              disabled={!on && picked.length >= SLOTS}
              onClick={() => void toggle(topic.slug)}
            >
              <span className="tile-name">
                {topic.name}
                {on && <Check />}
              </span>
              <span className="small muted">{topic.description}</span>
              <span className="meta">{plural(topic.notes, "note")} so far</span>
            </button>
          );
        })}
      </div>
      <p style={{ marginTop: "var(--space-6)" }}>
        <a className="button button-primary" href="/">
          Read today's notes
        </a>
      </p>
    </>
  );
}
