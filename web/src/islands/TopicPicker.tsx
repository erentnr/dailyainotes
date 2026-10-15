import { type SubmitEvent, useEffect, useState } from "react";

import { Check, Cross, Search } from "../components/ui/Icons";
import { ChipContent } from "../components/ui/TopicChip";
import { TopicCover } from "../components/ui/TopicCover";
import { TopicTag } from "../components/ui/TopicTag";
import { VerdictBadge } from "../components/ui/VerdictBadge";
import type { NoteCard, Topic } from "../lib/api/client";
import { api } from "../lib/api/client";
import { motifOf, seedOf } from "../lib/covers";
import { plural } from "../lib/format";
import {
  addTopic,
  GROUPS,
  homeSlot,
  loadPicked,
  type Picked,
  pickStatus,
  removeTopic,
  SLOTS,
  savePicked,
  slotFor,
} from "../lib/topics";

interface Props {
  topics: Topic[];
  signedIn: boolean;
  /** Signed out with sign-in open: signing in is the second step. */
  twoSteps: boolean;
}

/** Onboarding and the topic picker in one: pick topics from the catalog, see a recent note on
 * the last one picked, and continue once there are 3 to 7. Picks are kept in the browser as they
 * are made, and in the account for a signed-in reader (ADR 0003). */
export default function TopicPicker({ topics, signedIn, twoSteps }: Props) {
  const [picked, setPicked] = useState<Picked[]>([]);
  const [last, setLast] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [unsaved, setUnsaved] = useState(false);
  useEffect(() => setPicked(loadPicked()), []);

  const bySlug = new Map(topics.map((t) => [t.slug, t]));
  const look = (slug: string) => {
    const category = bySlug.get(slug)?.category;
    return { motif: motifOf(category), slot: slotFor(picked, slug, category) };
  };
  const chosen = picked.filter((p) => bySlug.has(p.slug));
  const status = pickStatus(chosen.length, topics.length);
  const next = twoSteps ? "/sign-in?next=/&step=2" : "/";

  const save = async (next: Picked[]) => {
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
  const follow = (slugs: string[]) => {
    const next = slugs.reduce((all, slug) => addTopic(all, slug, homeSlot(bySlug.get(slug)?.category)), picked);
    setLast(slugs.at(-1) ?? null);
    void save(next);
  };
  const unfollow = (slug: string) => void save(removeTopic(picked, slug));
  const toggle = (slug: string) => (picked.some((p) => p.slug === slug) ? unfollow(slug) : follow([slug]));

  const words = query.trim().toLowerCase();
  const matches = topics.filter((t) => `${t.name} ${t.description}`.toLowerCase().includes(words));
  const starters = [...topics].sort((a, b) => b.notes - a.notes || a.name.localeCompare(b.name)).slice(0, 3);
  const previewSlug = last && picked.some((p) => p.slug === last) ? last : chosen.at(-1)?.slug;

  return (
    <div className="onboarding">
      <div className="onboarding-main">
        <header className="onboarding-head">
          {twoSteps && (
            <div className="steps">
              <span className="meta">STEP 1 OF 2</span>
              <span className="steps-bar" aria-hidden="true">
                <span className="is-done" />
                <span />
              </span>
            </div>
          )}
          <h1 className="h1 onboarding-title">What should we take notes on?</h1>
          <p className="lede">
            Pick 3 to 7 topics. Each day you get short notes on what happened in them, every sentence with
            its source.
          </p>
          <div className="search-box">
            <Search />
            <label className="sr-only" htmlFor="topic-search">
              Search topics
            </label>
            <input
              id="topic-search"
              type="search"
              value={query}
              placeholder="Search topics: space, security, film…"
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </header>

        {unsaved && (
          <p className="form-error" role="alert">
            Your account could not save that change; it is kept in this browser. Try again in a moment.
          </p>
        )}

        {!words && starters.length > 1 && (
          <section className="starter" aria-labelledby="starter-title">
            <div className="starter-head">
              <h2 id="starter-title" className="starter-title">
                A good place to start
              </h2>
              <button type="button" className="text-button" onClick={() => follow(starters.map((t) => t.slug))}>
                Add all {starters.length}
              </button>
            </div>
            <div className="chips">
              {starters.map((t) => {
                const on = picked.some((p) => p.slug === t.slug);
                return (
                  <button key={t.slug} type="button" className="starter-chip" aria-pressed={on} onClick={() => toggle(t.slug)}>
                    <ChipContent name={t.name} {...look(t.slug)} />
                    {on && <Check />}
                  </button>
                );
              })}
            </div>
          </section>
        )}

        {GROUPS.map((group) => {
          const items = matches.filter((t) => group.categories.includes(t.category));
          if (!items.length) return null;
          return (
            <section key={group.name} className="topic-group" aria-labelledby={`group-${group.name}`}>
              <h2 className="section-title" id={`group-${group.name}`}>
                {group.name}
              </h2>
              <div className="tiles">
                {items.map((t) => {
                  const on = picked.some((p) => p.slug === t.slug);
                  return (
                    <button
                      key={t.slug}
                      type="button"
                      className="tile"
                      aria-pressed={on}
                      disabled={!on && picked.length >= SLOTS}
                      onClick={() => toggle(t.slug)}
                    >
                      <span className="tile-cover">
                        <TopicCover {...look(t.slug)} seed={seedOf(t.slug)} name={t.name} />
                      </span>
                      {on && (
                        <span className="tile-check" aria-hidden="true">
                          <Check />
                        </span>
                      )}
                      <span className="tile-body">
                        <span className="tile-name">{t.name}</span>
                        <span className="tile-desc">{t.description}</span>
                        <span className="meta">{plural(t.notes, "note")} so far</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>
          );
        })}
        {words && matches.length === 0 && (
          <p className="lede">No topic matches “{query.trim()}”. Suggest it below, and the editor will read it.</p>
        )}

        <div className="only-phone">
          <Suggest signedIn={signedIn} initialName={matches.length === 0 ? query.trim() : ""} />
        </div>
        {previewSlug && (
          <div className="only-phone">
            <Preview slug={previewSlug} topic={bySlug.get(previewSlug)!} {...look(previewSlug)} />
          </div>
        )}
      </div>

      <aside className="onboarding-side only-wide" aria-label="Your topics">
        <section className="card your-topics">
          <div className="card-head">
            <h2 className="section-title">Your topics</h2>
            <span className={`pick-status pick-${status.tone}`} aria-live="polite">
              {status.text}
            </span>
          </div>
          {chosen.length ? (
            <ul className="chosen-list">
              {chosen.map((p) => (
                <li key={p.slug}>
                  <span className="chosen-name">
                    <ChipContent name={bySlug.get(p.slug)!.name} {...look(p.slug)} />
                  </span>
                  <button type="button" className="close-button" aria-label={`Remove ${bySlug.get(p.slug)!.name}`} onClick={() => unfollow(p.slug)}>
                    <Cross />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="small muted">Nothing yet. Pick topics on the left.</p>
          )}
          <Suggest signedIn={signedIn} initialName="" compact />
          <Continue href={next} ready={status.ready} twoSteps={twoSteps} />
        </section>
        {previewSlug && <Preview slug={previewSlug} topic={bySlug.get(previewSlug)!} {...look(previewSlug)} />}
      </aside>

      <div className="tray only-phone">
        {chosen.length > 0 && (
          <div className="tray-chips">
            {chosen.map((p) => (
              <button key={p.slug} type="button" className="tray-chip" aria-label={`Remove ${bySlug.get(p.slug)!.name}`} onClick={() => unfollow(p.slug)}>
                <ChipContent name={bySlug.get(p.slug)!.name} {...look(p.slug)} />
                <Cross size={11} />
              </button>
            ))}
          </div>
        )}
        <div className="tray-foot">
          <span className={`pick-status pick-${status.tone}`} aria-live="polite">
            {status.text}
          </span>
          <Continue href={next} ready={status.ready} twoSteps={twoSteps} />
        </div>
      </div>
    </div>
  );
}

/** Not a link until there are enough topics; it stays focusable so the count can be heard. */
function Continue({ href, ready, twoSteps }: { href: string; ready: boolean; twoSteps: boolean }) {
  return (
    <a
      className="button button-primary continue"
      href={href}
      aria-disabled={!ready}
      onClick={(e) => {
        if (!ready) e.preventDefault();
      }}
    >
      {twoSteps ? "Continue" : "Read your page"}
    </a>
  );
}

/** A recent note on a topic, to show what its notes look like. */
function Preview({ slug, topic, motif, slot }: { slug: string; topic: Topic; motif: ReturnType<typeof motifOf>; slot: number }) {
  const [note, setNote] = useState<NoteCard | null | undefined>(undefined);
  useEffect(() => {
    setNote(undefined);
    api()
      .GET("/api/v1/topics/{slug}/notes", { params: { path: { slug }, query: { limit: 1 } } })
      .then(({ data }) => setNote(data?.notes[0] ?? null))
      .catch(() => setNote(null));
  }, [slug]);
  return (
    <section className="preview" aria-live="polite">
      <span className="label">Preview · a note on {topic.name}</span>
      <article className="card preview-card">
        <span className="preview-cover">
          <TopicCover motif={motif} slot={slot} seed={seedOf(note?.slug ?? slug)} name={topic.name} />
        </span>
        <div className="preview-body">
          <TopicTag name={topic.name} slot={slot} />
          {note ? (
            <>
              <b className="preview-title">{note.title}</b>
              <span className="note-summary small">{note.summary}</span>
              <span className="note-foot">
                <span className="meta">{plural(note.sources, "source")}</span>
                <VerdictBadge counts={note} />
              </span>
            </>
          ) : (
            note === null && (
              <b className="preview-title">Your first note on {topic.name} arrives once the editor approves one.</b>
            )
          )}
        </div>
      </article>
      {note && <span className="small muted">The latest note on this topic, as it was published.</span>}
    </section>
  );
}

/** "Something more specific?": a suggestion the editor reads (ADR 0003), not a topic of its own. */
function Suggest({ signedIn, initialName, compact = false }: { signedIn: boolean; initialName: string; compact?: boolean }) {
  const [name, setName] = useState(initialName);
  const [state, setState] = useState<"idle" | "busy" | "sent" | "failed">("idle");
  const [message, setMessage] = useState("");
  useEffect(() => setName(initialName), [initialName]);
  const id = compact ? "suggest-side" : "suggest-main";

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    setState("busy");
    try {
      const { data, error } = await api().POST("/api/v1/me/suggestions", { body: { name: name.trim(), note: "" } });
      if (data) {
        setState("sent");
        setName("");
        return;
      }
      const detail = (error as { detail?: unknown } | undefined)?.detail;
      setMessage(typeof detail === "string" ? detail : "That did not work. Try again.");
      setState("failed");
    } catch {
      setMessage("That did not work. Try again.");
      setState("failed");
    }
  }

  return (
    <section className={compact ? "suggest suggest-compact" : "card suggest"}>
      <label className="suggest-title" htmlFor={id}>
        Something more specific?
      </label>
      <span className="small muted">Describe a topic in a few words. The editor reads every suggestion.</span>
      {signedIn ? (
        <form className="suggest-form" onSubmit={submit}>
          <input
            id={id}
            className="input"
            value={name}
            minLength={3}
            maxLength={80}
            required
            placeholder="e.g. Electric ferries in Norway"
            onChange={(e) => {
              setName(e.target.value);
              setState("idle");
            }}
          />
          <button className="button button-primary" type="submit" disabled={state === "busy" || name.trim().length < 3}>
            Suggest
          </button>
        </form>
      ) : (
        <a className="source-link" id={id} href="/sign-in?next=/account%23suggest">
          Sign in to suggest a topic →
        </a>
      )}
      <span role="status" className="small">
        {state === "sent" && "Sent to the editor. Its status is on your account page."}
        {state === "failed" && <span className="form-error">{message}</span>}
      </span>
    </section>
  );
}
