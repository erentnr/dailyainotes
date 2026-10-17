import { describe, expect, it } from "vitest";

import { duration, orderDay, paragraphsOf, splitMarkers, timeUtc, toggleCitation } from "../src/lib/notes";

describe("a note's text", () => {
  it("turns markers into citation numbers between the words", () => {
    expect(splitMarkers("It rained [1][2]. Then it stopped [3].")).toEqual([
      "It rained ",
      1,
      "",
      2,
      ". Then it stopped ",
      3,
      ".",
    ]);
    expect(splitMarkers("No sources here.")).toEqual(["No sources here."]);
  });

  it("splits paragraphs on blank lines", () => {
    expect(paragraphsOf("One [1].\n\nTwo [2].\n \n\nThree.")).toEqual(["One [1].", "Two [2].", "Three."]);
  });
});

describe("citations", () => {
  it("opens a chip in its paragraph, moves to another, and closes the same one", () => {
    const first = toggleCitation(null, { marker: 1, paragraph: 0 });
    const other = toggleCitation(first, { marker: 3, paragraph: 0 });
    const sameSourceLater = toggleCitation(other, { marker: 3, paragraph: 2 });

    expect(first).toEqual({ marker: 1, paragraph: 0 });
    expect(other).toEqual({ marker: 3, paragraph: 0 });
    expect(sameSourceLater).toEqual({ marker: 3, paragraph: 2 });
    expect(toggleCitation(sameSourceLater, { marker: 3, paragraph: 2 })).toBeNull();
  });
});

describe("the day's order", () => {
  it("leads with the story that merged the most reports, the rest as listed", () => {
    const notes = [{ slug: "a", reports: 2 }, { slug: "b", reports: 9 }, { slug: "c", reports: 9 }];

    expect(orderDay(notes).map((n) => n.slug)).toEqual(["b", "a", "c"]);
    expect(orderDay([])).toEqual([]);
  });

  it("follows a reader's preferences when they have any, the biggest story aside", () => {
    const notes = [
      { slug: "big", reports: 9, preference: -0.2 },
      { slug: "liked", reports: 1, preference: 0.8 },
      { slug: "unscored", reports: 5, preference: null },
      { slug: "neutral", reports: 2, preference: 0.1 },
    ];

    expect(orderDay(notes).map((n) => n.slug)).toEqual(["liked", "neutral", "big", "unscored"]);
  });
});

describe("the trail's times", () => {
  it("says times in UTC and durations in words", () => {
    expect(timeUtc("2026-10-13T01:42:07.5+00:00")).toBe("01:42 UTC");
    expect(timeUtc("2026-10-13T04:42:07+03:00")).toBe("01:42 UTC");
    expect(duration("2026-10-13T01:30:00Z", "2026-10-13T01:44:30Z")).toBe("15 min");
    expect(duration("2026-10-13T01:30:00Z", "2026-10-13T03:35:00Z")).toBe("2 h 5 min");
    expect(duration("2026-10-13T01:30:00Z", "2026-10-16T01:30:00Z")).toBe("3 days");
    expect(duration("2026-10-13T02:00:00Z", "2026-10-13T01:00:00Z")).toBeNull();
  });
});
