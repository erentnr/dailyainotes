import { describe, expect, it } from "vitest";

import { NIGHT_LENGTH, NIGHT_STILL, nightAt, STEPS } from "../src/lib/night";

describe("one story's night", () => {
  it("plays the steps in the list's order, each from its own start", () => {
    expect(STEPS.map((start) => nightAt(start).step)).toEqual([0, 1, 2, 3, 4, 5, 6]);
    expect(nightAt(STEPS[1] - 0.01).step).toBe(0);
  });

  it("merges the reports, then gathers facts and writes three lines", () => {
    expect(nightAt(0).reports).toBe("arriving");
    expect(nightAt(2.5)).toMatchObject({ reports: "merged", facts: 0, lines: 0 });
    expect(nightAt(STEPS[1]).facts).toBe(1);
    expect(nightAt(STEPS[2] - 0.01).facts).toBe(3);
    expect(nightAt(STEPS[3] - 0.01).lines).toBe(3);
  });

  it("checks citations, then claims, before the note is published and Ask cites it", () => {
    const beforePublishing = nightAt(STEPS[5]);
    expect(beforePublishing).toMatchObject({ cited: 3, supported: 3, published: false, asked: false });
    expect(nightAt(STEPS[5] + 1).published).toBe(true);
    expect(nightAt(STEPS[6]).asked).toBe(true);
  });

  it("fades at the end and starts again", () => {
    expect(nightAt(NIGHT_LENGTH - 0.1).fading).toBe(true);
    expect(nightAt(NIGHT_LENGTH + 2)).toEqual(nightAt(2));
  });

  it("stands still on the published note", () => {
    expect(nightAt(NIGHT_STILL)).toMatchObject({ lines: 3, cited: 3, supported: 3, published: true, asked: false });
  });
});
