import { describe, expect, it } from "vitest";

import { formatDay, plural, verdictOf } from "../src/lib/format";
import { parseEvents } from "../src/lib/sse";
import { addTopic, loadPicked, removeTopic, SLOTS } from "../src/lib/topics";

describe("topics", () => {
  it("gives each topic the first free slot and keeps slots when one is removed", () => {
    let picked = ["f1", "tennis", "astronomy"].reduce(addTopic, []);
    picked = removeTopic(picked, "tennis");
    picked = addTopic(picked, "film");

    expect(picked).toEqual([
      { slug: "f1", slot: 1 },
      { slug: "astronomy", slot: 3 },
      { slug: "film", slot: 2 },
    ]);
  });

  it("allows eight topics and ignores a repeat", () => {
    const slugs = Array.from({ length: SLOTS + 1 }, (_, i) => `t${i}`);
    const picked = [...slugs, "t0"].reduce(addTopic, []);

    expect(picked).toHaveLength(SLOTS);
  });

  it("reads nothing from broken storage", () => {
    expect(loadPicked({ getItem: () => "{not json" })).toEqual([]);
    expect(loadPicked({ getItem: () => '[{"slug": 1}]' })).toEqual([]);
  });
});

describe("server-sent events", () => {
  it("parses complete events and keeps the unfinished rest", () => {
    const { events, rest } = parseEvents(
      'event: sources\ndata: []\n\nevent: text\ndata: "It rained [1]."\n\nevent: do',
    );

    expect(events).toEqual([
      { event: "sources", data: [] },
      { event: "text", data: "It rained [1]." },
    ]);
    expect(rest).toBe("event: do");
  });
});

describe("format", () => {
  it("writes absolute dates", () => {
    expect(formatDay("2026-10-12")).toBe("Mon 12 Oct 2026");
    expect(formatDay("2026-09-30T08:00:00Z")).toBe("Wed 30 Sep 2026");
  });

  it("turns fact-check counts into a verdict", () => {
    expect(verdictOf({ claims: 3, supported: 3, unsupported: 0 })).toBe("verified");
    expect(verdictOf({ claims: 3, supported: 2, unsupported: 0 })).toBe("partial");
    expect(verdictOf({ claims: 3, supported: 2, unsupported: 1 })).toBe("unsupported");
    expect(verdictOf({ claims: 0, supported: 0, unsupported: 0 })).toBe("unchecked");
  });

  it("counts in words", () => {
    expect(plural(1, "source")).toBe("1 source");
    expect(plural(4, "source")).toBe("4 sources");
  });
});
