import type { NoteCard as Note } from "../../lib/api/client";
import { type Motif, seedOf } from "../../lib/covers";
import { plural } from "../../lib/format";
import { Publishers } from "./Publishers";
import { TopicCover } from "./TopicCover";
import { TopicTag } from "./TopicTag";
import { VerdictBadge } from "./VerdictBadge";

interface Props {
  note: Note;
  motif: Motif;
  slot: number | undefined;
}

/** The day's first story: a wide cover, then the story; a split card on desktop. */
export function NoteCardLead({ note, motif, slot }: Props) {
  const href = `/notes/${note.slug}`;
  return (
    <article className="card note-lead">
      <a className="note-lead-cover" href={href} tabIndex={-1} aria-hidden="true">
        <TopicCover motif={motif} slot={slot} seed={seedOf(note.slug)} name={note.topic_name} />
      </a>
      <div className="note-lead-body">
        <div className="note-top">
          <TopicTag name={note.topic_name} slot={slot} />
          <Merged reports={note.reports} />
        </div>
        <h2 className="lead-title">
          <a href={href}>{note.title}</a>
        </h2>
        <p className="note-summary">{note.summary}</p>
        <Footer note={note} />
      </div>
    </article>
  );
}

/** Every other story: a cover tile beside the story on a phone, a cover on top in a grid. */
export function NoteCardItem({ note, motif, slot }: Props) {
  const href = `/notes/${note.slug}`;
  const cover = { motif, slot, seed: seedOf(note.slug), name: note.topic_name };
  return (
    <article className="card note-item">
      <a className="note-item-cover" href={href} tabIndex={-1} aria-hidden="true">
        <span className="only-phone">
          <TopicCover {...cover} variant="tile" />
        </span>
        <span className="only-wide">
          <TopicCover {...cover} />
        </span>
      </a>
      <div className="note-item-body">
        <TopicTag name={note.topic_name} slot={slot} />
        <h3 className="title">
          <a href={href}>{note.title}</a>
        </h3>
        <p className="note-summary">{note.summary}</p>
      </div>
      <Footer note={note} />
    </article>
  );
}

function Merged({ reports }: { reports: number }) {
  if (reports < 2) return null;
  return <span className="meta">{reports} reports → 1</span>;
}

function Footer({ note }: { note: Note }) {
  return (
    <div className="note-foot">
      <Publishers names={note.publishers} />
      <span className="meta">{plural(note.sources, "source")}</span>
      <VerdictBadge counts={note} />
    </div>
  );
}
