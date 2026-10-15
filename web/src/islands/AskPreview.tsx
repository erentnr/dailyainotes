import { useEffect, useRef, useState } from "react";

import { Forward } from "../components/ui/Icons";
import { TopicCover } from "../components/ui/TopicCover";
import { DEMO, frameAt, STILL } from "../lib/askDemo";
import { formatDay } from "../lib/format";
import { splitMarkers } from "../lib/notes";

/** What a reader gets from Ask once signed in, played as a short example. It is decoration with
 * a caption: the moving parts are hidden from screen readers, and it can be paused. Before its
 * script runs, and for a reader who prefers less motion, it shows its last frame and stays. */
export default function AskPreview() {
  const [seconds, setSeconds] = useState(STILL);
  const [playing, setPlaying] = useState(false);
  const started = useRef(0);

  useEffect(() => {
    if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
      started.current = performance.now();
      setSeconds(0);
      setPlaying(true);
    }
  }, []);

  useEffect(() => {
    if (!playing) return;
    started.current = performance.now() - seconds * 1000;
    const timer = setInterval(() => setSeconds((performance.now() - started.current) / 1000), 80);
    return () => clearInterval(timer);
    // Resume from where it was paused; `seconds` changes every tick and must not restart it.
  }, [playing]);

  const frame = frameAt(seconds);
  const shown = (on: boolean) => (on ? "demo-part" : "demo-part is-hidden");

  return (
    <figure className="card ask-demo">
      <figcaption className="ask-demo-head">
        <span>
          <span className="meta caps">Example</span>
          <span className="small muted"> A made-up question about a fictional company, to show what Ask does.</span>
        </span>
        <button type="button" className="button button-secondary small-button" onClick={() => setPlaying(!playing)}>
          {playing ? "Pause" : "Play"}
        </button>
      </figcaption>
      <div className={frame.fading ? "ask-demo-stage is-fading" : "ask-demo-stage"} aria-hidden="true">
        <p className={`ask-question ${shown(frame.sent)}`}>{DEMO.question}</p>
        <div className={`demo-answer ${shown(frame.status !== "idle")}`}>
          <span className="meta caps">From the notes · All topics · All time</span>
          <p className="demo-text">
            {/* The whole answer, invisible, holds the space the streamed words fill. */}
            <span className="demo-ghost">
              <Cited text={DEMO.answer} open={false} />
            </span>
            <span className="demo-live">
              {frame.status === "searching" && <span className="meta">Searching the notes…</span>}
              {frame.status === "found" && <span className="meta">✓ Found 1 note › Writing an answer with citations…</span>}
              <Cited text={frame.answer} open={frame.open} />
            </span>
          </p>
          <div className={`cited-note ${shown(frame.open)}`}>
            <span className="cited-note-cover">
              <TopicCover motif="waves" slot={2} seed={7} variant="tile" />
            </span>
            <span className="cited-note-body">
              <span className="meta caps">
                {DEMO.note.topic} · Note of {formatDay(DEMO.note.date)}
              </span>
              <span className="cited-note-title">{DEMO.note.title}</span>
              <span className="source-link">Open note →</span>
            </span>
          </div>
        </div>
        <div className="demo-composer">
          <span className={frame.typed ? "demo-typed" : "demo-placeholder"}>
            {frame.typed || "Ask about anything in the notes…"}
            {frame.typed && <span className="demo-caret" />}
          </span>
          <span className="demo-send">
            <Forward size={18} />
          </span>
        </div>
      </div>
    </figure>
  );
}

/** Citation markers drawn as chips, not buttons: nothing in the example can be pressed. */
function Cited({ text, open }: { text: string; open: boolean }) {
  return (
    <>
      {splitMarkers(text).map((part, i) =>
        typeof part === "string" ? (
          part
        ) : (
          <span key={i} className={open ? "citation is-active" : "citation"}>
            {part}
          </span>
        ),
      )}
    </>
  );
}
