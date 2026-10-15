/** One story's night, as How it works plays it: reports arrive and merge into a story, facts
 * are gathered, a note is written, its citations and claims are checked, the editor approves it,
 * and Ask cites it. Every frame is a function of time, so it can be tested and shown still. */

/** When each step starts, in seconds, in the order How it works lists them. */
export const STEPS = [0, 3, 5, 7.5, 9, 11, 13] as const;
export const NIGHT_LENGTH = 16;

export interface NightFrame {
  /** Which step is playing: an index into How it works' list. */
  step: number;
  /** Reports drop in, then three of them merge into one story. */
  reports: "arriving" | "arrived" | "merged";
  /** How many facts, written lines, checked citations and supported claims show (0 to 3). */
  facts: number;
  lines: number;
  cited: number;
  supported: number;
  approved: boolean;
  asked: boolean;
  fading: boolean;
}

/** How many of three things show over a step that runs from `from` to `to`. */
function three(at: number, from: number, to: number): number {
  if (at < from) return 0;
  return Math.min(3, 1 + Math.floor(((at - from) / (to - from)) * 3));
}

export function nightAt(seconds: number): NightFrame {
  // One remainder only, so a step's own start never falls a hair before it.
  const at = seconds % NIGHT_LENGTH;
  const step = STEPS.findLastIndex((start) => at >= start);
  return {
    step,
    reports: at < 1.2 ? "arriving" : at < 2 ? "arrived" : "merged",
    facts: three(at, STEPS[1], STEPS[2]),
    lines: three(at, STEPS[2], STEPS[3]),
    cited: three(at, STEPS[3], STEPS[4]),
    supported: three(at, STEPS[4], STEPS[5]),
    approved: at >= STEPS[5] + 0.8,
    asked: at >= STEPS[6],
    fading: at >= NIGHT_LENGTH - 0.6,
  };
}

/** The frame to show still: the note written, checked and approved. */
export const NIGHT_STILL = STEPS[6] - 0.5;
