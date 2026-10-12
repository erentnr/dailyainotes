import type { NoteCard as Note } from "../../lib/api/client";
import { formatDay, plural } from "../../lib/format";
import { Publishers } from "./Publishers";
import { TopicTag } from "./TopicTag";
import { VerdictBadge } from "./VerdictBadge";

export function NoteCard({ note, slot }: { note: Note; slot?: number | undefined }) {
  return (
    <li className="note-card">
      <div className="top">
        <TopicTag name={note.topic_name} slot={slot} />
        <span className="meta">{formatDay(note.edition_date)}</span>
      </div>
      <h3 className="title">
        <a href={`/notes/${note.slug}`}>{note.title}</a>
      </h3>
      <p className="summary">{note.summary}</p>
      <div className="footer">
        <Publishers names={note.publishers} />
        <span className="meta">{plural(note.sources, "source")}</span>
        <VerdictBadge {...note} />
      </div>
    </li>
  );
}
