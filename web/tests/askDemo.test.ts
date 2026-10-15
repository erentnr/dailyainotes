import { describe, expect, it } from "vitest";

import { DEMO, frameAt, STILL, TIMES } from "../src/lib/askDemo";

describe("the Ask example", () => {
  it("starts empty and types the question before sending it", () => {
    expect(frameAt(0)).toMatchObject({ typed: "", sent: false, status: "idle", answer: "", open: false });
    const typing = frameAt((TIMES.type + TIMES.send) / 2).typed;
    expect(typing.length).toBeGreaterThan(0);
    expect(DEMO.question.startsWith(typing)).toBe(true);
    expect(frameAt(TIMES.send)).toMatchObject({ typed: "", sent: true });
  });

  it("searches, then streams the answer in whole words", () => {
    expect(frameAt(TIMES.search).status).toBe("searching");
    expect(frameAt(TIMES.found).status).toBe("found");
    const halfway = frameAt((TIMES.write + TIMES.done) / 2).answer;
    expect(halfway.length).toBeGreaterThan(0);
    expect(DEMO.answer.startsWith(halfway)).toBe(true);
    expect(DEMO.answer.split(" ")).toEqual(expect.arrayContaining(halfway.split(" ")));
    expect(frameAt(TIMES.done)).toMatchObject({ status: "done", answer: DEMO.answer, open: false });
  });

  it("opens the cited note, then fades and starts again", () => {
    expect(frameAt(TIMES.press).open).toBe(true);
    expect(frameAt(TIMES.end - 0.1).fading).toBe(true);
    expect(frameAt(TIMES.end + 1)).toEqual(frameAt(1));
  });

  it("shows everything, the note open, when it stands still", () => {
    expect(frameAt(STILL)).toMatchObject({ sent: true, status: "done", answer: DEMO.answer, open: true, fading: false });
  });
});
