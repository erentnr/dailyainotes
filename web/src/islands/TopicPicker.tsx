import { useEffect, useState } from "react";

import { Check } from "../components/ui/Icons";
import type { Topic } from "../lib/api/client";
import { plural } from "../lib/format";
import { addTopic, loadPicked, type Picked, removeTopic, SLOTS, savePicked } from "../lib/topics";

/** The catalog: pick up to eight topics; the choice stays in this browser. */
export default function TopicPicker({ topics }: { topics: Topic[] }) {
  const [picked, setPicked] = useState<Picked[]>([]);
  useEffect(() => setPicked(loadPicked()), []);

  const toggle = (slug: string) => {
    const next = picked.some((p) => p.slug === slug)
      ? removeTopic(picked, slug)
      : addTopic(picked, slug);
    savePicked(next);
    setPicked(next);
  };

  return (
    <>
      <p className="muted">
        {picked.length} of {SLOTS} picked. Your choice stays in this browser; there are no
        accounts.
      </p>
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
              onClick={() => toggle(topic.slug)}
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
