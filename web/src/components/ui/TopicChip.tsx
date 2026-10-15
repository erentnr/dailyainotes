import type { Motif } from "../../lib/covers";
import { TopicCover } from "./TopicCover";

/** What goes inside a topic pill: the cover circle, the name, and a count in mono. The caller
 * picks the element (a tab, a toggle or a link) and gives it the `chip` class. */
export function ChipContent({
  name,
  motif,
  slot,
  count,
}: {
  name: string;
  motif?: Motif | undefined;
  slot?: number | undefined;
  count?: number | undefined;
}) {
  return (
    <>
      {motif && <TopicCover motif={motif} slot={slot} variant="circle" />}
      {name}
      {count !== undefined && <span className="chip-count">{count}</span>}
    </>
  );
}
