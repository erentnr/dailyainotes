/** The example Ask shows a visitor who is not signed in: a made-up question about a fictional
 * company from the eval corpus (evals/corpus.jsonl), answered the way Ask answers. Every frame
 * is a function of time, so the animation can be tested and shown still. */

export const DEMO = {
  question: "What did Brightwater Energy switch on?",
  answer:
    "Brightwater Energy switched on an iron-air battery in Oakridge that can discharge for up to " +
    "100 hours [1]. The 10-megawatt pilot runs for two years before the utility decides on a " +
    "larger order [1].",
  note: {
    topic: "Climate tech",
    date: "2026-09-02",
    title: "Brightwater Energy starts a 100-hour iron-air battery pilot",
  },
};

/** When each part starts, in seconds; the example loops after `end`. */
export const TIMES = { type: 0.6, send: 3.2, search: 3.6, found: 4.3, write: 5.0, done: 8.6, press: 9.4, end: 14 };

export type Status = "idle" | "searching" | "found" | "writing" | "done";

export interface Frame {
  /** The part of the question typed so far, before it is sent. */
  typed: string;
  sent: boolean;
  status: Status;
  /** The part of the answer streamed so far, whole words only. */
  answer: string;
  /** The citation chip is pressed and the cited note is open. */
  open: boolean;
  /** The last moment, as the example fades out to start again. */
  fading: boolean;
}

const WORDS = DEMO.answer.split(" ");

function share(at: number, from: number, to: number): number {
  return Math.min(1, Math.max(0, (at - from) / (to - from)));
}

export function frameAt(seconds: number): Frame {
  // One remainder only: adding and taking off `end` again would move 3.2 to 3.1999….
  const at = seconds % TIMES.end;
  const typed = DEMO.question.slice(0, Math.round(share(at, TIMES.type, TIMES.send - 0.2) * DEMO.question.length));
  const status: Status =
    at < TIMES.search ? "idle" : at < TIMES.found ? "searching" : at < TIMES.write ? "found" : at < TIMES.done ? "writing" : "done";
  const words = Math.round(share(at, TIMES.write, TIMES.done) * WORDS.length);
  return {
    typed: at < TIMES.send ? typed : "",
    sent: at >= TIMES.send,
    status,
    answer: WORDS.slice(0, words).join(" "),
    open: at >= TIMES.press,
    fading: at >= TIMES.end - 0.6,
  };
}

/** The frame to show still: everything done and the cited note open. */
export const STILL = TIMES.press + 1;
