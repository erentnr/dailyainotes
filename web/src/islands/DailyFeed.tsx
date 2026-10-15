import { type KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";

import { Back, Forward, Search } from "../components/ui/Icons";
import { NoteCardItem, NoteCardLead } from "../components/ui/NoteCard";
import { EmptyState, ErrorState, SkeletonCard } from "../components/ui/States";
import { ChipContent } from "../components/ui/TopicChip";
import type { NoteCard as Note, Topic } from "../lib/api/client";
import { api } from "../lib/api/client";
import { motifOf } from "../lib/covers";
import {
  addDays,
  formatLongDay,
  formatShortDay,
  greeting,
  plural,
  readingMinutes,
} from "../lib/format";
import { loadPicked, type Picked, slotFor } from "../lib/topics";

type Loaded = { day: string | null; notes: Note[]; topics: Topic[]; picked: Picked[] };

/** The daily page: one day's notes on the topics this browser follows, the latest day by
 * default. Topics live in the browser, so everything here loads after the page does. */
export default function DailyFeed({ date }: { date?: string | undefined }) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [failed, setFailed] = useState(false);
  const [tab, setTab] = useState<string | null>(null);

  const load = useCallback(() => {
    setFailed(false);
    const picked = loadPicked();
    const client = api();
    const query = { topic: picked.map((p) => p.slug), ...(date ? { date } : {}) };
    Promise.all([client.GET("/api/v1/topics"), client.GET("/api/v1/notes", { params: { query } })])
      .then(([topics, day]) => {
        if (!topics.data || !day.data) throw new Error("API error");
        setLoaded({ day: day.data.date, notes: day.data.notes, topics: topics.data, picked });
      })
      .catch(() => setFailed(true));
  }, [date]);

  useEffect(() => {
    setTab(new URLSearchParams(location.search).get("topic"));
    load();
  }, [load]);

  const pick = (slug: string | null) => {
    setTab(slug);
    const url = new URL(location.href);
    if (slug) url.searchParams.set("topic", slug);
    else url.searchParams.delete("topic");
    history.replaceState(null, "", url);
  };

  if (failed) {
    return (
      <div className="feed" style={{ marginTop: "var(--space-3)" }}>
        <ErrorState onRetry={load}>Couldn't load today.</ErrorState>
      </div>
    );
  }
  if (!loaded) return <Loading />;

  const { day, notes, topics, picked } = loaded;
  const bySlug = new Map(topics.map((t) => [t.slug, t]));
  const look = (slug: string) => {
    const category = bySlug.get(slug)?.category;
    return { motif: motifOf(category), slot: slotFor(picked, slug, category) };
  };
  const counts = new Map<string, number>();
  for (const n of notes) counts.set(n.topic, (counts.get(n.topic) ?? 0) + 1);
  // Tabs for the followed topics; with none followed, for the topics this day covers.
  const tabSlugs = picked.length ? picked.map((p) => p.slug) : [...counts.keys()];
  const shown = tab && tabSlugs.includes(tab) ? notes.filter((n) => n.topic === tab) : notes;
  // The biggest story of the day leads.
  const lead = shown.reduce<Note | undefined>((best, n) => (!best || n.reports > best.reports ? n : best), undefined);
  const rest = shown.filter((n) => n !== lead);
  const quiet = picked.filter((p) => !counts.has(p.slug));
  const today = new Date().toISOString().slice(0, 10);

  return (
    <>
      <DayHead
        day={day}
        today={today}
        line={
          notes.length
            ? `${plural(notes.length, "story", "stories")}, ${plural(readingMinutes(notes.map((n) => n.summary)), "minute")}.`
            : null
        }
      />
      {tabSlugs.length > 0 && (
        <TopicTabs
          tabs={[
            { slug: null, name: picked.length ? "For you" : "All", count: notes.length },
            ...tabSlugs.map((slug) => ({
              slug,
              name: bySlug.get(slug)?.name ?? slug,
              count: counts.get(slug) ?? 0,
              ...look(slug),
            })),
          ]}
          selected={tab && tabSlugs.includes(tab) ? tab : null}
          onSelect={pick}
        />
      )}
      <div className="feed" id="feed">
        {picked.length === 0 && (
          <div className="card callout">
            <p className="callout-title">Make this page yours.</p>
            <p className="muted">You're seeing every topic. Pick the ones you follow, and this page shows only those.</p>
            <a className="button button-primary" href="/topics">
              Pick your topics
            </a>
          </div>
        )}
        {lead ? (
          <NoteCardLead note={lead} {...look(lead.topic)} />
        ) : (
          <EmptyState>
            <p className="state-title">{day ? "Nothing on your topics that day." : "No notes on your topics yet."}</p>
            <p className="muted">
              Notes are written overnight and appear once the editor approves them. We don't pad your page.
            </p>
          </EmptyState>
        )}
        {rest.length > 0 && (
          <div className="feed-grid">
            {rest.map((note) => (
              <NoteCardItem key={note.slug} note={note} {...look(note.topic)} />
            ))}
          </div>
        )}
        {quiet.length > 0 && day && !tab && (
          <TopicStatus
            rows={picked.map((p) => ({
              name: bySlug.get(p.slug)?.name ?? p.slug,
              count: counts.get(p.slug) ?? 0,
              ...look(p.slug),
            }))}
          />
        )}
        {day && <CaughtUp day={day} hasNotes={notes.length > 0} />}
      </div>
    </>
  );
}

function DayHead({ day, today, line }: { day: string | null; today: string; line: string | null }) {
  const [hour, setHour] = useState<number | null>(null);
  useEffect(() => setHour(new Date().getHours()), []);
  const next = day ? addDays(day, 1) : null;
  return (
    <section className="day-head">
      <div className="day-head-main">
        <div className="day-head-top">
          <span className="meta day-date">{day ? formatLongDay(day) : "Your notes"}</span>
          {day && (
            <nav className="day-arrows only-phone" aria-label="Days">
              <a className="round-button" href={`/day/${addDays(day, -1)}`} aria-label={`Previous day, ${formatLongDay(addDays(day, -1))}`}>
                <Back size={14} />
              </a>
              {next && next <= today ? (
                <a className="round-button" href={`/day/${next}`} aria-label={`Next day, ${formatLongDay(next)}`}>
                  <Forward size={14} />
                </a>
              ) : (
                <span className="round-button" aria-disabled="true" aria-label="Next day: not written yet">
                  <Forward size={14} />
                </span>
              )}
            </nav>
          )}
        </div>
        <h1 className="display">
          {hour === null ? "Hello." : greeting(hour)}
          {line && (
            <>
              <br />
              <span className="soft">{line}</span>
            </>
          )}
        </h1>
      </div>
      <div className="day-head-side">
        <AskBox />
        {day && (
          <nav className="day-pills only-wide" aria-label="Previous days">
            {[0, -1, -2, -3].map((offset) => {
              const d = addDays(day, offset);
              return offset === 0 ? (
                <span key={d} className="day-pill" aria-current="date">
                  {formatShortDay(d)}
                </span>
              ) : (
                <a key={d} className="day-pill" href={`/day/${d}`}>
                  {formatShortDay(d)}
                </a>
              );
            })}
          </nav>
        )}
      </div>
    </section>
  );
}

/** A plain form: it works before the page's scripts load. */
function AskBox() {
  return (
    <form className="ask-box" action="/ask" method="get" role="search">
      <label className="sr-only" htmlFor="ask-box">
        Ask your notes
      </label>
      <Search />
      <input id="ask-box" name="q" type="text" minLength={3} maxLength={300} placeholder="Ask your notes…" />
      <button className="button button-primary" type="submit">
        Ask
      </button>
    </form>
  );
}

interface Tab {
  slug: string | null;
  name: string;
  count: number;
  motif?: ReturnType<typeof motifOf>;
  slot?: number;
}

/** A tab list: arrow keys move between tabs, Tab moves on to the notes. */
function TopicTabs({ tabs, selected, onSelect }: { tabs: Tab[]; selected: string | null; onSelect: (slug: string | null) => void }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (event: KeyboardEvent, index: number) => {
    const moves: Record<string, number> = { ArrowRight: 1, ArrowLeft: -1, Home: -index, End: tabs.length - 1 - index };
    const move = moves[event.key];
    if (move === undefined) return;
    event.preventDefault();
    const target = (index + move + tabs.length) % tabs.length;
    refs.current[target]?.focus();
    onSelect(tabs[target]!.slug);
  };
  return (
    <div className="chip-row" role="tablist" aria-label="Filter by topic">
      {tabs.map((t, i) => (
        <button
          key={t.slug ?? "all"}
          ref={(el) => {
            refs.current[i] = el;
          }}
          type="button"
          role="tab"
          className="chip"
          aria-selected={t.slug === selected}
          aria-controls="feed"
          tabIndex={t.slug === selected ? 0 : -1}
          onClick={() => onSelect(t.slug)}
          onKeyDown={(e) => onKey(e, i)}
        >
          <ChipContent name={t.name} motif={t.motif} slot={t.slot} count={t.count} />
        </button>
      ))}
    </div>
  );
}

function TopicStatus({ rows }: { rows: { name: string; count: number; motif: ReturnType<typeof motifOf>; slot: number }[] }) {
  return (
    <section className="card status-list" aria-label="Your topics on this day">
      <ul>
        {rows.map((r) => (
          <li key={r.name}>
            <span className="status-name">
              <ChipContent name={r.name} motif={r.motif} slot={r.slot} />
            </span>
            {r.count ? <span className="status-ok">✓ {plural(r.count, "note")}</span> : <span className="muted small">Nothing new</span>}
          </li>
        ))}
      </ul>
      <p className="small muted">
        "Nothing new" means no note on that topic was approved for this day. We don't pad your page.
      </p>
    </section>
  );
}

function CaughtUp({ day, hasNotes }: { day: string; hasNotes: boolean }) {
  const previous = addDays(day, -1);
  return (
    <div className="caught-up">
      {hasNotes && <p className="caught-up-title">You're all caught up.</p>}
      <p className="caught-up-text">
        New notes are written overnight and appear once the editor approves them. Every claim links back to its source.
      </p>
      <a className="button button-light" href={`/day/${previous}`}>
        ← {formatLongDay(previous)}
      </a>
    </div>
  );
}

function Loading() {
  return (
    <>
      <section className="day-head" aria-busy="true" aria-label="Loading today's notes">
        <div className="day-head-main">
          <span className="skeleton" style={{ width: "40%" }} />
          <span className="skeleton skeleton-display" style={{ width: "80%" }} />
        </div>
        <div className="day-head-side">
          <AskBox />
        </div>
      </section>
      <div className="feed">
        <div className="card note-lead skeleton-card" aria-hidden="true">
          <span className="note-lead-cover skeleton-block" />
        </div>
        <div className="feed-grid">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    </>
  );
}
