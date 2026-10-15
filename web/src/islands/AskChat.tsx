import { type KeyboardEvent, type SubmitEvent, useEffect, useRef, useState } from "react";

import { CitedText } from "../components/ui/CitedText";
import { Check, Cross, EmptyPage, Forward } from "../components/ui/Icons";
import { Publishers } from "../components/ui/Publishers";
import { ChipContent } from "../components/ui/TopicChip";
import { TopicCover } from "../components/ui/TopicCover";
import type { NoteDetail, Topic } from "../lib/api/client";
import { api } from "../lib/api/client";
import { daysLabel, daysOf, RANGES, type Range, scopeLabel, shortfall, suggestedQuestions } from "../lib/ask";
import { motifOf, seedOf } from "../lib/covers";
import { formatDay, plural } from "../lib/format";
import { readEvents } from "../lib/sse";
import { addTopic, homeSlot, loadPicked, type Picked, savePicked, slotFor } from "../lib/topics";

/** A note an answer may cite, as the API's `sources` event names it. */
interface Source {
  marker: number;
  slug: string;
  topic: string;
  title: string;
  edition_date: string;
}

interface Exchange {
  question: string;
  scope: string;
  /** Why the notes fell short, when they do. */
  shortfall: string;
  /** What the question searched, to widen it when the notes fall short. */
  topics: string[];
  range: Range;
  answer: string;
  sources: Source[] | null;
  cited: number[];
  status: "streaming" | "done" | "error";
  insufficient: boolean;
  message?: string;
}

const NOT_ENOUGH = "Not enough in the notes to answer that.";

/** Ask the notes: answers come only from published notes, cite them, and say when they fall
 * short. The answer streams in. */
export default function AskChat({
  topics,
  signedIn,
  initialQuestion,
  initialTopic,
}: {
  topics: Topic[];
  signedIn: boolean;
  initialQuestion: string;
  initialTopic: string | null;
}) {
  const [picked, setPicked] = useState<Picked[]>([]);
  const [chosen, setChosen] = useState<string[]>(initialTopic ? [initialTopic] : []);
  const [range, setRange] = useState<Range>("all");
  const [dates, setDates] = useState({ from: "", to: "" });
  const [question, setQuestion] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const asked = useRef(false);
  const busy = exchanges.at(-1)?.status === "streaming";

  const bySlug = new Map(topics.map((t) => [t.slug, t]));
  const look = (slug: string) => {
    const category = bySlug.get(slug)?.category;
    return { motif: motifOf(category), slot: slotFor(picked, slug, category) };
  };
  // The reader's topics to filter by, or every topic when none are followed.
  const filterSlugs = (picked.length ? picked.map((p) => p.slug) : topics.map((t) => t.slug)).filter((s) =>
    bySlug.has(s),
  );
  const today = new Date().toISOString().slice(0, 10);
  const days = daysOf(range, today, dates);

  useEffect(() => {
    setPicked(loadPicked());
    if (initialQuestion && !asked.current) {
      asked.current = true;
      void send(initialQuestion, chosen, "all");
    }
    // Ask the question from the URL once, on arrival.
  }, []);

  const update = (change: (e: Exchange) => Partial<Exchange>) =>
    setExchanges((all) => {
      const last = all.at(-1);
      return last ? [...all.slice(0, -1), { ...last, ...change(last) }] : all;
    });

  async function send(text: string, topicSlugs: string[], when: Range) {
    const words = text.trim();
    if (words.length < 3 || busy) return;
    const span = daysOf(when, today, dates);
    const names = topicSlugs.map((s) => bySlug.get(s)?.name ?? s);
    setExchanges((all) => [
      ...all,
      {
        question: words,
        scope: scopeLabel(names, when, span),
        shortfall: shortfall(names, when, span),
        topics: topicSlugs,
        range: when,
        answer: "",
        sources: null,
        cited: [],
        status: "streaming",
        insufficient: false,
      },
    ]);
    try {
      const response = await fetch("/api/v1/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: words, topics: topicSlugs, ...span }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
        const message = typeof body.detail === "string" ? body.detail : "Ask is unavailable right now.";
        update(() => ({ status: "error", message }));
        return;
      }
      for await (const { event, data } of readEvents(response)) {
        if (event === "sources") update(() => ({ sources: data as Source[] }));
        else if (event === "text") update((e) => ({ answer: e.answer + (data as string) }));
        else if (event === "done") {
          const done = data as { cited: number[]; insufficient: boolean };
          update(() => ({ status: "done", cited: done.cited, insufficient: done.insufficient }));
        } else if (event === "error") update(() => ({ status: "error", message: data as string }));
      }
      update((e) => (e.status === "streaming" ? { status: "done" } : {}));
    } catch {
      update(() => ({ status: "error", message: "Ask could not be reached. Try again in a moment." }));
    }
  }

  const submit = (event?: SubmitEvent) => {
    event?.preventDefault();
    const text = question;
    setQuestion("");
    void send(text, chosen, range);
  };
  const onKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };
  const toggleTopic = (slug: string) =>
    setChosen((all) => (all.includes(slug) ? all.filter((s) => s !== slug) : [...all, slug]));
  const follow = (slug: string) => {
    const next = addTopic(picked, slug, homeSlot(bySlug.get(slug)?.category));
    savePicked(next);
    setPicked(next);
    if (signedIn) void api().PUT("/api/v1/me/topics", { body: { topics: next } }).catch(() => undefined);
  };

  const suggestions = suggestedQuestions(filterSlugs.map((s) => bySlug.get(s)!.name));

  return (
    <div className="ask">
      <aside className="ask-side">
        <header className="ask-head">
          <h1 className="h1">Ask your notes</h1>
          <p className="lede">
            Answers come only from published notes, and every sentence is cited. If the notes don't cover
            it, we say so. Ten questions a day.
          </p>
        </header>

        <div className="ask-filters only-phone">
          <div className="chip-row" role="group" aria-label="Topics to search">
            <button type="button" className="chip" aria-pressed={chosen.length === 0} onClick={() => setChosen([])}>
              All topics
            </button>
            {filterSlugs.map((slug) => (
              <button key={slug} type="button" className="chip" aria-pressed={chosen.includes(slug)} onClick={() => toggleTopic(slug)}>
                <ChipContent name={bySlug.get(slug)!.name} {...look(slug)} />
              </button>
            ))}
          </div>
          <div className="chip-row" role="group" aria-label="Days to search">
            {RANGES.map((r) => (
              <button key={r.id} type="button" className="range-chip" aria-pressed={range === r.id} onClick={() => setRange(r.id)}>
                {r.label}
              </button>
            ))}
          </div>
        </div>

        <section className="card ask-panel only-wide" aria-labelledby="ask-topics">
          <h2 className="panel-title" id="ask-topics">
            Topics
          </h2>
          <button type="button" className="check-row" aria-pressed={chosen.length === 0} onClick={() => setChosen([])}>
            <span>All topics</span>
            <span className="check-box" aria-hidden="true">
              {chosen.length === 0 && <Check size={11} />}
            </span>
          </button>
          {filterSlugs.map((slug) => (
            <button key={slug} type="button" className="check-row" aria-pressed={chosen.includes(slug)} onClick={() => toggleTopic(slug)}>
              <span className="check-row-name">
                <ChipContent name={bySlug.get(slug)!.name} {...look(slug)} />
              </span>
              <span className="check-box" aria-hidden="true">
                {chosen.includes(slug) && <Check size={11} />}
              </span>
            </button>
          ))}
        </section>

        <section className="card ask-panel only-wide" aria-labelledby="ask-days">
          <h2 className="panel-title" id="ask-days">
            Date range
          </h2>
          <div className="range-grid">
            {RANGES.map((r) => (
              <button key={r.id} type="button" className="range-chip" aria-pressed={range === r.id} onClick={() => setRange(r.id)}>
                {r.label}
              </button>
            ))}
          </div>
          <span className="meta">{daysLabel(days)}</span>
        </section>

        {range === "custom" && (
          <div className="card ask-panel date-pick">
            <label className="field">
              <span className="small">From</span>
              <input className="input" type="date" max={today} value={dates.from} onChange={(e) => setDates({ ...dates, from: e.target.value })} />
            </label>
            <label className="field">
              <span className="small">To</span>
              <input className="input" type="date" max={today} value={dates.to} onChange={(e) => setDates({ ...dates, to: e.target.value })} />
            </label>
          </div>
        )}
      </aside>

      <section className="ask-main" aria-label="Conversation">
        {exchanges.map((e, i) => (
          <ExchangeView
            key={i}
            exchange={e}
            look={look}
            followed={(slug) => picked.some((p) => p.slug === slug)}
            onFollow={follow}
            onWiden={(topicSlugs, when) => void send(e.question, topicSlugs, when)}
          />
        ))}

        {exchanges.length === 0 && suggestions.length > 0 && (
          <section className="suggestions" aria-labelledby="try-asking">
            <h2 className="suggestions-title" id="try-asking">
              Try asking{picked.length ? " · based on your topics" : ""}
            </h2>
            <div className="suggestion-grid">
              {suggestions.map((q, i) => (
                <button key={q} type="button" className="card suggestion" onClick={() => void send(q, chosen, range)}>
                  <TopicCover {...look(filterSlugs[i]!)} variant="circle" />
                  {q}
                </button>
              ))}
            </div>
          </section>
        )}

        <form className="composer" onSubmit={submit}>
          <label className="sr-only" htmlFor="question">
            Your question
          </label>
          <textarea
            id="question"
            rows={2}
            value={question}
            maxLength={300}
            placeholder="Ask about anything in the notes…"
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={onKey}
          />
          <button className="button button-primary" type="submit" disabled={busy || question.trim().length < 3} aria-label="Ask">
            <span className="only-wide">Ask</span>
            <span className="only-phone">
              <Forward size={18} />
            </span>
          </button>
        </form>
      </section>
    </div>
  );
}

function ExchangeView({
  exchange: e,
  look,
  followed,
  onFollow,
  onWiden,
}: {
  exchange: Exchange;
  look: (slug: string) => { motif: ReturnType<typeof motifOf>; slot: number };
  followed: (slug: string) => boolean;
  onFollow: (slug: string) => void;
  onWiden: (topics: string[], range: Range) => void;
}) {
  const [open, setOpen] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const notEnough = e.status === "done" && e.insufficient && e.cited.length === 0;
  const cited = (e.sources ?? []).filter((s) => e.cited.includes(s.marker));
  const source = open === null ? undefined : e.sources?.find((s) => s.marker === open);

  const copy = async () => {
    const links = cited.map((s) => `[${s.marker}] ${s.title}: ${location.origin}/notes/${s.slug}`).join("\n");
    await navigator.clipboard.writeText(`${e.answer.trim()}\n\n${links}`);
    setCopied(true);
  };

  return (
    <>
      <p className="ask-question">{e.question}</p>
      {e.status === "error" ? (
        <div className="card state state-error" role="alert">
          <p>{e.message}</p>
        </div>
      ) : notEnough ? (
        <NotEnough exchange={e} onWiden={onWiden} />
      ) : (
        <article className="card answer" aria-busy={e.status === "streaming"}>
          <span className="meta caps">From the notes · {e.scope}</span>
          {e.status === "streaming" && !e.answer && <Progress sources={e.sources} />}
          <p className="answer-text" aria-live="polite">
            <CitedText
              text={e.answer.replace(NOT_ENOUGH, "").trim()}
              isOpen={(m) => open === m}
              onToggle={(m) => setOpen(open === m ? null : m)}
            />
          </p>
          {source && (
            <CitedNote
              source={source}
              look={look(source.topic)}
              followed={followed(source.topic)}
              onFollow={() => onFollow(source.topic)}
              onClose={() => setOpen(null)}
            />
          )}
          {e.status === "done" && (
            <div className="answer-foot">
              <span className="meta">{plural(cited.length, "note")} cited</span>
              <span className="answer-actions">
                <button type="button" className="button button-secondary small-button" onClick={() => void copy()}>
                  {copied ? "Copied" : "Copy"}
                </button>
              </span>
            </div>
          )}
        </article>
      )}
    </>
  );
}

/** While the answer is on its way: what has been found, then lines that fill in. */
function Progress({ sources }: { sources: Source[] | null }) {
  return (
    <div className="progress" aria-live="polite">
      <span className="meta">
        {sources === null ? "Searching the notes…" : `✓ Found ${plural(sources.length, "note")} › Writing an answer with citations…`}
      </span>
      <span className="skeleton" style={{ width: "92%" }} />
      <span className="skeleton" style={{ width: "78%" }} />
      <span className="skeleton" style={{ width: "60%" }} />
    </div>
  );
}

/** The note a citation points at: its cover, topic, day and title, and its opening lines. */
function CitedNote({
  source,
  look,
  followed,
  onFollow,
  onClose,
}: {
  source: Source;
  look: { motif: ReturnType<typeof motifOf>; slot: number };
  followed: boolean;
  onFollow: () => void;
  onClose: () => void;
}) {
  const [note, setNote] = useState<NoteDetail | null>(null);
  useEffect(() => {
    setNote(null);
    api()
      .GET("/api/v1/notes/{slug}", { params: { path: { slug: source.slug } } })
      .then(({ data }) => setNote(data ?? null))
      .catch(() => setNote(null));
  }, [source.slug]);
  return (
    <div className="cited-note" role="note" aria-label={`Note ${source.marker}`}>
      <span className="cited-note-cover">
        <TopicCover {...look} seed={seedOf(source.slug)} variant="tile" name={note?.topic_name ?? ""} />
      </span>
      <span className="cited-note-body">
        <span className="cited-note-top">
          <span className="meta caps">
            {note?.topic_name ?? source.topic} · Note of {formatDay(source.edition_date)}
          </span>
          <button type="button" className="close-button" onClick={onClose} aria-label="Close note">
            <Cross />
          </button>
        </span>
        <a className="cited-note-title" href={`/notes/${source.slug}`}>
          {source.title}
        </a>
        {note && <span className="note-summary small">{note.summary}</span>}
        <span className="cited-note-foot">
          {note && <Publishers names={note.publishers} />}
          <a className="source-link" href={`/notes/${source.slug}`}>
            Open note →
          </a>
          {!followed && (
            <button type="button" className="text-link" onClick={onFollow}>
              + Follow {note?.topic_name ?? "this topic"}
            </button>
          )}
        </span>
      </span>
    </div>
  );
}

/** The notes fall short: say so, say what was searched, and offer to search wider. */
function NotEnough({ exchange: e, onWiden }: { exchange: Exchange; onWiden: (topics: string[], range: Range) => void }) {
  const narrowTopics = e.topics.length > 0;
  const narrowDays = e.range !== "all";
  return (
    <div className="card not-enough">
      <span className="empty-icon" aria-hidden="true">
        <EmptyPage />
      </span>
      <div className="not-enough-body">
        <p className="state-title">{NOT_ENOUGH}</p>
        <p className="muted">{e.shortfall} We only answer from published notes, never from guesses.</p>
        <div className="not-enough-actions">
          {narrowTopics && (
            <button type="button" className="button button-primary" onClick={() => onWiden([], e.range)}>
              Search all topics
            </button>
          )}
          {narrowDays && (
            <button type="button" className="button button-secondary" onClick={() => onWiden(e.topics, "all")}>
              Search all time
            </button>
          )}
          {!narrowTopics && !narrowDays && (
            <a className="button button-secondary" href="/topics">
              See the topics we follow
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
