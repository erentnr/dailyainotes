import type { NoteDetail } from "../../lib/api/client";
import { formatDay } from "../../lib/format";
import { splitMarkers } from "../../lib/notes";
import { Cross, External } from "./Icons";
import { initial } from "./Publishers";

type Citation = NoteDetail["citations"][number];

/** Text whose [n] markers are citation chips. */
export function CitedText({
  text,
  isOpen,
  onToggle,
}: {
  text: string;
  isOpen: (marker: number) => boolean;
  onToggle: (marker: number) => void;
}) {
  return (
    <>
      {splitMarkers(text).map((part, i) =>
        typeof part === "string" ? (
          part
        ) : (
          <button
            key={i}
            type="button"
            className="citation"
            aria-expanded={isOpen(part)}
            aria-label={`Source ${part}`}
            onClick={() => onToggle(part)}
          >
            {part}
          </button>
        ),
      )}
    </>
  );
}

/** A cited source: who and when, its title, the quote the sentence rests on (at most 25 words,
 * the only text shown from a source), and a link to the original. */
export function CitationCard({ citation, onClose }: { citation: Citation; onClose?: () => void }) {
  return (
    <div className="citation-card" role="note" aria-label={`Source ${citation.marker}`}>
      <div className="citation-card-top">
        <span className="citation-card-who">
          <span className="publisher">{initial(citation.publisher)}</span>
          <span className="meta">
            {citation.publisher}
            {citation.published_at ? ` · ${formatDay(citation.published_at)}` : ""}
          </span>
        </span>
        {onClose && (
          <button type="button" className="close-button" onClick={onClose} aria-label="Close source">
            <Cross />
          </button>
        )}
      </div>
      <SourceBody citation={citation} />
    </div>
  );
}

export function SourceBody({ citation, withTitle = true }: { citation: Citation; withTitle?: boolean }) {
  return (
    <>
      {withTitle && <b className="citation-card-title">{citation.title}</b>}
      {citation.quote && (
        <q className="quote">
          <mark>{citation.quote}</mark>
        </q>
      )}
      <a className="source-link" href={citation.url} rel="noopener noreferrer" target="_blank">
        Open source <External />
      </a>
    </>
  );
}
