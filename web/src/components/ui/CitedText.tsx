import type { NoteDetail } from "../../lib/api/client";
import { formatDay } from "../../lib/format";
import { External } from "./Icons";

type Citation = NoteDetail["citations"][number];

const MARKER = /\[(\d+)\]/g;

/** A paragraph whose [n] markers are citation chips; the open one's source follows it. */
export function CitedText({
  text,
  citations,
  open,
  onToggle,
}: {
  text: string;
  citations: Citation[];
  open: number | null;
  onToggle?: ((marker: number) => void) | undefined;
}) {
  const byMarker = new Map(citations.map((c) => [c.marker, c]));
  const parts: (string | number)[] = [];
  let last = 0;
  for (const match of text.matchAll(MARKER)) {
    parts.push(text.slice(last, match.index), Number(match[1]));
    last = (match.index ?? 0) + match[0].length;
  }
  parts.push(text.slice(last));
  const shown = open !== null && parts.includes(open) ? byMarker.get(open) : undefined;
  return (
    <>
      <p>
        {parts.map((part, i) =>
          typeof part === "string" ? (
            part
          ) : (
            <button
              key={i}
              type="button"
              className="citation"
              aria-expanded={open === part}
              aria-label={`Source ${part}`}
              onClick={() => onToggle?.(part)}
            >
              {part}
            </button>
          ),
        )}
      </p>
      {shown && <CitationPanel citation={shown} />}
    </>
  );
}

export function CitationPanel({ citation }: { citation: Citation }) {
  return (
    <div className="panel">
      <div className="meta">
        [{citation.marker}] {citation.publisher}
        {citation.published_at ? ` · ${formatDay(citation.published_at)}` : ""}
      </div>
      <div className="small" style={{ marginTop: 4 }}>
        {citation.title}
      </div>
      {citation.quote && (
        <p className="quote">
          <mark>{citation.quote}</mark>
        </p>
      )}
      <a href={citation.url} rel="noopener noreferrer" target="_blank">
        Open source <External />
      </a>
    </div>
  );
}
