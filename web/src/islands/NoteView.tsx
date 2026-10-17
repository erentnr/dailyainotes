import { Fragment, useEffect, useRef, useState } from "react";

import { CitationCard, CitedText, SourceBody } from "../components/ui/CitedText";
import { Back, Check, Cross, Half } from "../components/ui/Icons";
import { initial } from "../components/ui/Publishers";
import { ShareButton } from "../components/ui/ShareButton";
import { ChipContent } from "../components/ui/TopicChip";
import { TopicCover } from "../components/ui/TopicCover";
import { VerdictBadge } from "../components/ui/VerdictBadge";
import type { NoteCard, NoteDetail, Topic } from "../lib/api/client";
import { api } from "../lib/api/client";
import { type Motif, motifOf, seedOf } from "../lib/covers";
import { formatDay, formatLongDay, plural, readingMinutes } from "../lib/format";
import { duration, type OpenCitation, orderDay, paragraphsOf, timeUtc, toggleCitation } from "../lib/notes";
import { loadPicked, type Picked, slotFor } from "../lib/topics";
import ThemeToggle from "./ThemeToggle";

interface Props {
  note: NoteDetail;
  topics: Topic[];
  /** Earlier notes on the topic. */
  context: NoteCard[];
  /** The notes of the note's day, for "2 of 8" and the next one. */
  day: NoteCard[];
  /** A signed-in reader's topics, known on the server; others come from the browser. */
  readerTopics: Picked[] | null;
}

/** A note: its cover, its text with citations, its sources and how it was made. On a phone a
 * citation opens under its paragraph; on a wide screen it opens in the Sources panel beside. */
export default function NoteView({ note, topics, context, day, readerTopics }: Props) {
  const [picked, setPicked] = useState<Picked[]>(readerTopics ?? []);
  const [open, setOpen] = useState<OpenCitation | null>(null);
  const rows = useRef(new Map<number, HTMLLIElement>());
  useEffect(() => setPicked(loadPicked()), []);

  const look = (slug: string) => {
    const category = topics.find((t) => t.slug === slug)?.category;
    return { motif: motifOf(category), slot: slotFor(picked, slug, category) };
  };
  const { motif, slot } = look(note.topic);
  const followed = picked.some((p) => p.slug === note.topic);
  const order = orderDay(followed ? day.filter((n) => picked.some((p) => p.slug === n.topic)) : day);
  const index = order.findIndex((n) => n.slug === note.slug);
  const next = index >= 0 ? order[index + 1] : undefined;
  const paragraphs = paragraphsOf(note.body);
  const dayHref = `/day/${note.edition_date}`;
  const minutes = readingMinutes([note.body, note.why_it_matters]);

  const press = (marker: number, paragraph: number) => {
    const next = toggleCitation(open, { marker, paragraph });
    setOpen(next);
    // Beside the text, the Sources panel shows it; bring its row into view.
    if (next && matchMedia("(min-width: 960px)").matches) {
      rows.current.get(marker)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  };
  const isOpen = (marker: number) => open?.marker === marker;
  const cited = (paragraph: number) =>
    open?.paragraph === paragraph ? note.citations.find((c) => c.marker === open.marker) : undefined;
  const text = (body: string, paragraph: number) => (
    <CitedText text={body} isOpen={isOpen} onToggle={(m) => press(m, paragraph)} />
  );
  const inline = (paragraph: number) => {
    const citation = cited(paragraph);
    return (
      citation && (
        <div className="citation-inline">
          <CitationCard citation={citation} onClose={() => setOpen(null)} />
        </div>
      )
    );
  };

  return (
    <>
      <div className="note-cover">
        <span className="cover-box only-phone">
          <TopicCover motif={motif} slot={slot} seed={seedOf(note.slug)} name={note.topic_name} />
        </span>
        <span className="cover-box only-wide">
          <TopicCover motif={motif} slot={slot} seed={seedOf(note.slug)} variant="hero" name={note.topic_name} />
        </span>
        <div className="note-cover-bar only-phone">
          <a className="float-button" href={dayHref} aria-label={`Back to ${formatLongDay(note.edition_date)}`}>
            <Back />
          </a>
          <span className="float-group">
            <ThemeToggle className="float-button" />
            <ShareButton title={note.title} className="float-button" />
          </span>
        </div>
        <div className="note-cover-bar only-wide">
          <a className="float-pill" href={dayHref}>
            ← {formatLongDay(note.edition_date)}
          </a>
          {index >= 0 && (
            <span className="float-tag">
              note {index + 1} of {order.length}
            </span>
          )}
        </div>
      </div>

      <div className="note-sheet">
        <div className="note-layout">
          <article className="note-article">
            <header className="note-head">
              <div className="note-head-top">
                <a className="chip chip-small" href={`/topics/${note.topic}`}>
                  <ChipContent name={note.topic_name} motif={motif} slot={slot} />
                </a>
                <span className="meta caps">
                  {formatDay(note.edition_date)}
                  {index >= 0 && ` · ${index + 1} of ${order.length}`}
                </span>
              </div>
              <h1 className="h1">{note.title}</h1>
              <div className="note-badges">
                <VerdictBadge counts={note} detail />
                <span className="meta">
                  {note.reports > 1 && `${note.reports} reports merged · `}
                  {note.sources} cited · {minutes} min read
                </span>
              </div>
            </header>
            <div className="note-text">
              {paragraphs.map((body, i) => (
                <Fragment key={i}>
                  <p>{text(body, i)}</p>
                  {inline(i)}
                </Fragment>
              ))}
              {note.why_it_matters && (
                <>
                  <p>
                    <b>Why it matters.</b> {text(note.why_it_matters, paragraphs.length)}
                  </p>
                  {inline(paragraphs.length)}
                </>
              )}
            </div>
            {note.disagreements.length > 0 && <Disagreements items={note.disagreements} />}
          </article>

          <aside className="note-rail" aria-label="About this note">
            <Sources note={note} open={open} rows={rows.current} onPress={(m) => press(m, -1)} />
            <HowMade note={note} />
            <section className="card follow-up">
              {readerTopics !== null && <MoreLikeThis slug={note.slug} />}
              <a href={`/ask?topic=${encodeURIComponent(note.topic)}`}>Ask a follow-up →</a>
              <p className="small muted">
                Our own summary, with quotes of at most 25 words from each source. Follow the links for the
                full reporting. Approved by the editor.
              </p>
            </section>
          </aside>

          {context.length > 0 && (
            <section className="note-context" aria-labelledby="context-title">
              <h2 className="section-title" id="context-title">
                Earlier on {note.topic_name}
              </h2>
              <div className="context-row">
                {context.map((c) => (
                  <ContextCard key={c.slug} note={c} motif={motif} slot={slot} />
                ))}
              </div>
            </section>
          )}
        </div>

        {next && <NextCard note={next} {...look(next.topic)} />}
      </div>
    </>
  );
}

function Sources({
  note,
  open,
  rows,
  onPress,
}: {
  note: NoteDetail;
  open: OpenCitation | null;
  rows: Map<number, HTMLLIElement>;
  onPress: (marker: number) => void;
}) {
  const [others, setOthers] = useState(false);
  const merged = note.citations.length + note.other_reports.length;
  return (
    <section className="card sources" aria-labelledby="sources-title">
      <div className="card-head">
        <h2 className="section-title" id="sources-title">
          Sources
        </h2>
        <span className="meta">
          {note.citations.length} cited of {merged} merged
        </span>
      </div>
      <ul className="source-rows">
        {note.citations.map((c) => {
          const expanded = open?.marker === c.marker;
          return (
            <li
              key={c.marker}
              className={expanded ? "source-row is-open" : "source-row"}
              ref={(el) => {
                if (el) rows.set(c.marker, el);
              }}
            >
              <button type="button" aria-expanded={expanded} onClick={() => onPress(c.marker)}>
                <span className="publisher">{initial(c.publisher)}</span>
                <span className="source-row-text">
                  <span className="source-title">{c.title}</span>
                  <span className="meta">
                    {c.publisher}
                    {c.published_at && ` · ${formatDay(c.published_at)}`}
                  </span>
                </span>
                <span className="source-number">{c.marker}</span>
              </button>
              {expanded && (
                <div className="source-detail">
                  <SourceBody citation={c} withTitle={false} />
                </div>
              )}
            </li>
          );
        })}
      </ul>
      {note.other_reports.length > 0 && (
        <>
          <button type="button" className="link-button" aria-expanded={others} onClick={() => setOthers(!others)}>
            {others
              ? "Hide the other reports"
              : `Show the ${plural(note.other_reports.length, "other report")} we merged`}
          </button>
          {others && (
            <ul className="other-reports">
              {note.other_reports.map((r) => (
                <li key={r.url}>
                  <a href={r.url} rel="noopener noreferrer" target="_blank">
                    {r.title}
                  </a>
                  <span className="meta">
                    {r.publisher || hostOf(r.url)}
                    {r.published_at && ` · ${formatDay(r.published_at)}`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

function HowMade({ note }: { note: NoteDetail }) {
  const [open, setOpen] = useState(true);
  const { trail } = note;
  const steps = [
    {
      agent: "Scout",
      at: trail.collected_at,
      what:
        note.reports > 0
          ? `Collected the day's coverage and merged ${plural(note.reports, "report")} from ${plural(note.independent_publishers, "publisher")} into this story.`
          : "Collected the day's coverage and picked this story.",
    },
    { agent: "Researcher", at: trail.researched_at, what: "Gathered the facts from the reports, each with its source." },
    {
      agent: "Writer",
      at: trail.drafted_at,
      what:
        trail.drafts > 1
          ? `Wrote the note, then rewrote it ${plural(trail.drafts - 1, "time")} after the fact-check.`
          : "Wrote the note, every sentence citing its source.",
    },
    {
      agent: "Fact-checker",
      at: null,
      what: note.claims
        ? `Checked ${plural(note.claims, "claim")} against the sources they cite.`
        : "Found no claims to check.",
    },
    { agent: "Editor", at: trail.approved_at, what: "Read it and approved it for publishing." },
  ];
  const drafted = trail.drafted_at ? duration(trail.collected_at, trail.drafted_at) : null;
  const tone = note.unsupported ? "bad" : note.weak ? "warn" : "ok";
  return (
    <section className="card how-made">
      <button type="button" className="disclosure" aria-expanded={open} aria-controls="how-made" onClick={() => setOpen(!open)}>
        <span className="disclosure-text">
          <span className="disclosure-title">How this note was made</span>
          <span className="meta">
            {steps.length} steps{drafted && ` · first draft in ${drafted}`} · approved by the editor
          </span>
        </span>
        <span className="disclosure-glyph" aria-hidden="true">
          {open ? "−" : "+"}
        </span>
      </button>
      <div id="how-made" hidden={!open}>
        <ol className="stepper">
          {steps.map((s, i) => (
            <li key={s.agent}>
              <span className="step-number">{i + 1}</span>
              <span className="step-body">
                <span className="step-top">
                  <b>{s.agent}</b>
                  {s.at && <span className="meta">{timeUtc(s.at)}</span>}
                </span>
                <span className="step-what">{s.what}</span>
              </span>
            </li>
          ))}
        </ol>
        {note.claims > 0 && (
          <p className={`result-bar result-${tone}`}>
            {tone === "ok" ? <Check /> : tone === "warn" ? <Half /> : <Cross />}
            {note.supported} supported · {note.weak} weak · {note.unsupported} unsupported
          </p>
        )}
      </div>
    </section>
  );
}

function ContextCard({ note, motif, slot }: { note: NoteCard; motif: Motif; slot: number }) {
  return (
    <a className="card context-card" href={`/notes/${note.slug}`}>
      <span className="context-cover">
        <TopicCover motif={motif} slot={slot} seed={seedOf(note.slug)} name={note.topic_name} />
      </span>
      <span className="context-body">
        <span className="meta caps">{formatDay(note.edition_date)}</span>
        <b className="context-title">{note.title}</b>
        <span className="note-summary small">{note.summary}</span>
      </span>
    </a>
  );
}

function NextCard({ note, motif, slot }: { note: NoteCard; motif: Motif; slot: number }) {
  return (
    <a className="next-card" href={`/notes/${note.slug}`}>
      <span className="next-cover">
        <TopicCover motif={motif} slot={slot} seed={seedOf(note.slug)} variant="tile" name={note.topic_name} />
      </span>
      <span className="next-body">
        <span className="meta caps">Next · {note.topic_name}</span>
        <b className="next-title">{note.title} →</b>
      </span>
    </a>
  );
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** "More like this" and "Less like this" for a signed-in reader (ADR 0007): they order the
 * reader's daily page. Pressing the pressed one clears it. */
function MoreLikeThis({ slug }: { slug: string }) {
  const [value, setValue] = useState<-1 | 0 | 1>(0);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api()
      .GET("/api/v1/me/notes/{slug}/feedback", { params: { path: { slug } } })
      .then(({ data }) => data && setValue(data.value))
      .catch(() => undefined);
  }, [slug]);

  async function choose(pressed: -1 | 1) {
    const before = value;
    const next = value === pressed ? 0 : pressed;
    setValue(next);
    setFailed(false);
    try {
      const { data } = await api().PUT("/api/v1/me/notes/{slug}/feedback", {
        params: { path: { slug } },
        body: { value: next },
      });
      if (!data) throw new Error("not saved");
    } catch {
      setValue(before);
      setFailed(true);
    }
  }

  return (
    <div className="stack">
      <div className="chips" role="group" aria-label="Notes like this one on your daily page">
        <button className="chip" type="button" aria-pressed={value === 1} onClick={() => choose(1)}>
          More like this
        </button>
        <button className="chip" type="button" aria-pressed={value === -1} onClick={() => choose(-1)}>
          Less like this
        </button>
      </div>
      <span className="small muted" role="status">
        {failed ? "That did not save. Try again." : "Orders your daily page."}
      </span>
    </div>
  );
}

/** Where publishers with no owner in common disagree: each point, and each position in our own
 * words with the publishers that state it. */
function Disagreements({ items }: { items: NoteDetail["disagreements"] }) {
  return (
    <section className="card disagreements" aria-labelledby="disagreements-title">
      <h2 className="label" id="disagreements-title">
        Sources disagree
      </h2>
      {items.map((d) => (
        <div key={d.point} className="stack">
          <p className="disagreement-point">{d.point}</p>
          <ul className="plain-list">
            {d.positions.map((p) => (
              <li key={p.says}>
                {p.says}
                <span className="small muted">
                  {" — "}
                  {p.sources.map((s, i) => (
                    <Fragment key={s.marker}>
                      {i > 0 && ", "}
                      <a href={s.url} rel="noopener noreferrer" target="_blank">
                        {s.publisher}
                      </a>
                    </Fragment>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
