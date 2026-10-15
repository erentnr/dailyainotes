import { type CSSProperties, useEffect, useRef, useState } from "react";

import { NIGHT_LENGTH, NIGHT_STILL, nightAt } from "../lib/night";

/** A step of the pipeline: its name, who does it, and what it does. */
export type Stage = [name: string, kind: string, text: string];

/** What each step does in the diagram, in a line under it. */
const CAPTIONS = [
  "Reports of one event merge into one story.",
  "The facts each report states, with its source.",
  "A short note: every sentence cites a source.",
  "Code checks every citation, number and quote.",
  "Another model checks each claim against its sources.",
  "Nothing is published until the editor approves it.",
  "Answers from published notes, citing them.",
];

// Where each report sits as it arrives, and in the story's stack once merged; the fourth is
// about another event and stays out of the story.
const ARRIVED = [
  [16, 16],
  [124, 16],
  [16, 98],
  [124, 98],
] as const;
const MERGED = [
  [40, 58],
  [47, 65],
  [54, 72],
  [124, 160],
] as const;
const LINES = [104, 134, 164];

/** One story's night, played: the steps of How it works as a diagram, with the list of steps
 * beside it marking the one playing. Screen readers get the diagram in one sentence and the list
 * in full. It can be paused, and before its script runs, or with reduced motion, it shows the
 * approved note and stays. */
export default function StoryNight({ stages }: { stages: Stage[] }) {
  const [seconds, setSeconds] = useState(NIGHT_STILL);
  const [playing, setPlaying] = useState(false);
  const [moving, setMoving] = useState(false);
  const started = useRef(0);

  useEffect(() => {
    if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setSeconds(0);
      setPlaying(true);
      setMoving(true);
    }
  }, []);

  useEffect(() => {
    if (!playing) return;
    started.current = performance.now() - seconds * 1000;
    const timer = setInterval(() => setSeconds((performance.now() - started.current) / 1000), 100);
    return () => clearInterval(timer);
    // Resume from where it was paused; `seconds` changes every tick and must not restart it.
  }, [playing]);

  const f = nightAt(seconds);
  const at = (x: number, y: number, shown = true): CSSProperties => ({
    transform: `translate(${x}px, ${y}px)`,
    opacity: shown ? 1 : 0,
  });

  return (
    <div className="night">
      <figure className="card night-stage" data-step={moving ? f.step : undefined}>
        <figcaption className="night-head">
          <span className="meta caps">One story's night</span>
          <button
            type="button"
            className="button button-secondary small-button"
            onClick={() => {
              setPlaying(!playing);
              setMoving(true);
            }}
          >
            {playing ? "Pause" : "Play"}
          </button>
        </figcaption>
        {/* On a phone the view is closer and pans from the reports to the note. */}
        <div className="night-view" style={{ "--pan": f.step < 2 ? "0%" : "-37.5%" } as CSSProperties}>
          <svg
            className={f.fading ? "night-svg is-fading" : "night-svg"}
            viewBox="0 0 600 240"
            role="img"
            aria-label="Reports merge into a story, a note is written from it, checked and approved, and Ask cites it."
          >
            {ARRIVED.map((arrived, i) => {
              // The reports land one after another, then three of them stack into the story.
              const landed = f.reports !== "arriving" || seconds % NIGHT_LENGTH > 0.3 * i;
              const [x, y] = f.reports === "merged" ? MERGED[i]! : arrived;
              const opacity = !landed ? 0 : i === 3 ? (f.asked ? 0 : f.reports === "merged" ? 0.25 : 1) : f.asked ? 0.35 : 1;
              return (
                <g key={i} className="night-part" style={{ transform: `translate(${x}px, ${landed ? y : y - 30}px)`, opacity }}>
                  <rect width="100" height="64" rx="10" className="night-report" />
                  <circle cx="20" cy="20" r="10" className="night-ink" />
                  <text x="20" y="24" className="night-initial">
                    {"ABCD"[i]}
                  </text>
                  <rect x="38" y="15" width="48" height="6" rx="3" className="night-line" />
                  <rect x="12" y="40" width="74" height="6" rx="3" className="night-line" />
                </g>
              );
            })}

            {[0, 1, 2].map((i) => (
              <g key={i} className="night-part" style={at(f.facts > i ? 252 : 236, 40 + i * 52, f.facts > i && !f.asked)}>
                <rect width="116" height="32" rx="16" className="night-report" />
                <rect x="12" y="13" width="56" height="6" rx="3" className="night-line" />
                <rect x="80" y="7" width="26" height="18" rx="6" className="night-chip" />
                <text x="93" y="20" className="night-chip-text">
                  {i + 1}
                </text>
              </g>
            ))}

            <g className="night-part" style={at(388, 8, f.step >= 2 || f.lines > 0)}>
              <rect width="204" height="224" rx="16" className="night-report" />
              <clipPath id="night-cover">
                <rect width="204" height="60" rx="16" />
              </clipPath>
              <g clipPath="url(#night-cover)">
                <rect width="204" height="76" fill="#17A673" />
                <circle cx="150" cy="24" r="12" fill="#F6E7A1" />
                <path d="M0 44 Q25 34 50 44 T100 44 T150 44 T204 44 V76 H0Z" fill="#33C08A" />
                <path d="M0 54 Q25 46 50 54 T100 54 T150 54 T204 54 V76 H0Z" fill="#0E8A5C" />
              </g>
              <rect x="14" y="74" width="132" height="10" rx="5" className="night-ink" />
              {LINES.map((y, i) => (
                <g key={y}>
                  <rect
                    x="14"
                    y={y}
                    width="120"
                    height="7"
                    rx="3.5"
                    className="night-line night-grow"
                    style={{ transform: `scaleX(${f.lines > i ? 1 : 0})` }}
                  />
                  <g className="night-part" style={{ opacity: f.lines > i ? 1 : 0 }}>
                    <rect x="140" y={y - 6} width="24" height="18" rx="6" className={f.cited > i ? "night-chip is-checked" : "night-chip"} />
                    <text x="152" y={y + 7} className={f.cited > i ? "night-chip-text is-checked" : "night-chip-text"}>
                      {i + 1}
                    </text>
                  </g>
                  <g className="night-part" style={{ opacity: f.supported > i ? 1 : 0 }}>
                    <circle cx="182" cy={y + 3} r="9" className="night-ok" />
                    <path d={`M177.5 ${y + 3} l3 3 l5.5 -6`} className="night-ok-mark" />
                  </g>
                </g>
              ))}
              <g className="night-part" style={{ opacity: f.step >= 5 || f.approved ? 1 : 0 }}>
                <rect x="14" y="188" width="128" height="26" rx="13" className={f.approved ? "night-approve is-approved" : "night-approve"} />
                <text x="78" y="205" className={f.approved ? "night-approve-text is-approved" : "night-approve-text"}>
                  {f.approved ? "✓ Approved" : "Approve"}
                </text>
              </g>
            </g>

            {/* Ask's question, where the facts were: beside the note it cites. */}
            <g className="night-part" style={at(236, 176, f.asked)}>
              <rect width="140" height="44" rx="20" className="night-ink" />
              <rect x="18" y="14" width="96" height="6" rx="3" className="night-on-ink" />
              <rect x="18" y="26" width="64" height="6" rx="3" className="night-on-ink" />
            </g>
            <path
              d="M376 198 C450 198 470 140 528 140"
              className="night-part night-link"
              style={{ opacity: f.asked ? 1 : 0 }}
            />
          </svg>
        </div>
        <p className="night-caption" aria-hidden="true">
          <b>{stages[f.step]?.[0]}</b> {moving ? CAPTIONS[f.step] : "A note, written, checked and approved."}
        </p>
      </figure>

      <ol className="card pipeline">
        {stages.map(([name, kind, text], i) => (
          <li key={name} className={moving && i === f.step ? "is-active" : undefined}>
            <div>
              <strong>{name}</strong> <span className="agent">{kind}</span>
              <div className="muted">{text}</div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
