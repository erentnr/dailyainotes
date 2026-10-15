import type { Topic } from "../../lib/api/client";
import { motifOf } from "../../lib/covers";
import { TopicCover } from "./TopicCover";

/** A topic's cover as a wide banner. Astro pages use this, since they cannot pass a `slot`
 * prop: Astro keeps that attribute for its own slots. */
export function CoverBanner({ topic, tone }: { topic: Topic; tone: number }) {
  return (
    <div className="card cover-banner" aria-hidden="true">
      <TopicCover motif={motifOf(topic.category)} slot={tone} variant="hero" name={topic.name} />
    </div>
  );
}
