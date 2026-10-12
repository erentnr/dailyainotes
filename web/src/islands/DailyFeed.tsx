import { useEffect, useState } from "react";

import { NoteCard } from "../components/ui/NoteCard";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/States";
import { TopicTag } from "../components/ui/TopicTag";
import type { NoteCard as Note, Topic } from "../lib/api/client";
import { api } from "../lib/api/client";
import { formatDay } from "../lib/format";
import { loadPicked, type Picked, slotOf } from "../lib/topics";

type Loaded = { day: string | null; notes: Note[]; topics: Topic[]; picked: Picked[] };

/** The daily page: the latest day's notes on the topics this browser follows. */
export default function DailyFeed() {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [failed, setFailed] = useState(false);
  const [tab, setTab] = useState<string | null>(null);

  useEffect(() => {
    const picked = loadPicked();
    const client = api();
    Promise.all([
      client.GET("/api/v1/topics"),
      client.GET("/api/v1/notes", { params: { query: { topic: picked.map((p) => p.slug) } } }),
    ])
      .then(([topics, day]) => {
        if (!topics.data || !day.data) throw new Error("API error");
        setLoaded({ day: day.data.date, notes: day.data.notes, topics: topics.data, picked });
      })
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <ErrorState>The notes could not be loaded.</ErrorState>;
  if (!loaded) return <Skeleton lines={6} />;

  const { day, notes, picked } = loaded;
  const names = new Map(loaded.topics.map((t) => [t.slug, t.name]));
  const shown = tab ? notes.filter((n) => n.topic === tab) : notes;
  const counts = new Map<string, number>();
  for (const n of notes) counts.set(n.topic, (counts.get(n.topic) ?? 0) + 1);

  return (
    <>
      <header className="page-head graph-paper">
        <div className="label">{day ? "Notes for" : "Today"}</div>
        <h1 className="display">{day ? formatDay(day) : "No notes yet"}</h1>
        <p className="muted">
          {picked.length === 0 ? (
            <>
              Showing every topic. <a href="/topics">Pick your topics</a> to make this page yours.
            </>
          ) : (
            <>
              {notes.length} notes on your {picked.length} topics. <a href="/topics">Edit topics</a>
            </>
          )}
        </p>
      </header>
      {picked.length > 0 && (
        <div className="chips" role="group" aria-label="Filter by topic">
          <button
            type="button"
            className="topic-tab"
            aria-pressed={tab === null}
            onClick={() => setTab(null)}
          >
            All <span className="count">{notes.length}</span>
          </button>
          {picked.map((p) => (
            <button
              key={p.slug}
              type="button"
              className="topic-tab"
              aria-pressed={tab === p.slug}
              style={{ ["--tab-color" as string]: `var(--t${p.slot})` }}
              onClick={() => setTab(p.slug)}
            >
              <TopicTag name={names.get(p.slug) ?? p.slug} slot={p.slot} />
              <span className="count">{counts.get(p.slug) ?? 0}</span>
            </button>
          ))}
        </div>
      )}
      {shown.length === 0 ? (
        <EmptyState>
          <p className="title">Nothing new</p>
          <p className="muted">
            "Nothing new" means no source published on these topics, or no note was approved yet.
            We don't pad your page.
          </p>
        </EmptyState>
      ) : (
        <ul className="notes" style={{ marginTop: "var(--space-5)" }}>
          {shown.map((note) => (
            <NoteCard key={note.slug} note={note} slot={slotOf(picked, note.topic)} />
          ))}
        </ul>
      )}
    </>
  );
}
