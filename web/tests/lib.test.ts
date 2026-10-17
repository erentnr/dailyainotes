import { describe, expect, it } from "vitest";

import { formatDay, plural, verdictOf } from "../src/lib/format";
import { parseEvents } from "../src/lib/sse";
import { safeNext } from "../src/lib/account";
import {
  addTopic,
  coveredBy,
  GROUPS,
  homeSlot,
  loadPicked,
  mergePicked,
  type Picked,
  removeTopic,
  SLOTS,
  pickStatus,
  samePicked,
  slotFor,
} from "../src/lib/topics";

describe("topics", () => {
  it("gives a topic its home slot when free, else the next free one, and keeps slots", () => {
    let picked = addTopic([], "f1", homeSlot("motorsport"));
    picked = addTopic(picked, "ai-models", homeSlot("technology"));
    picked = addTopic(picked, "security", homeSlot("technology"));
    picked = removeTopic(picked, "ai-models");
    picked = addTopic(picked, "suggested", homeSlot(null));

    expect(picked).toEqual([
      { slug: "f1", slot: 1 },
      { slug: "security", slot: 5 },
      { slug: "suggested", slot: 7 },
    ]);
  });

  it("wraps around to the first free slot after the last one", () => {
    let picked = addTopic([], "film", homeSlot("culture"));
    picked = addTopic(picked, "games", homeSlot("culture"));

    expect(picked).toEqual([
      { slug: "film", slot: 8 },
      { slug: "games", slot: 1 },
    ]);
  });

  it("shows a topic not followed in the slot it would take", () => {
    const picked = [{ slug: "f1", slot: 1 }];

    expect(slotFor(picked, "f1", "motorsport")).toBe(1);
    expect(slotFor(picked, "motogp", "motorsport")).toBe(2);
    expect(slotFor(picked, "climate", "climate")).toBe(2);
  });

  it("allows eight topics and ignores a repeat", () => {
    const slugs = Array.from({ length: SLOTS + 1 }, (_, i) => `t${i}`);
    const picked = [...slugs, "t0"].reduce<Picked[]>((all, slug) => addTopic(all, slug), []);

    expect(picked).toHaveLength(SLOTS);
  });

  it("merges the browser's picks into the account's at sign-in, account slots first", () => {
    const account = [
      { slug: "f1", slot: 1 },
      { slug: "film", slot: 3 },
    ];
    const local = [
      { slug: "film", slot: 1 },
      { slug: "tennis", slot: 2 },
      { slug: "astronomy", slot: 3 },
    ];

    expect(mergePicked(account, local)).toEqual([
      { slug: "f1", slot: 1 },
      { slug: "film", slot: 3 },
      { slug: "tennis", slot: 2 },
      { slug: "astronomy", slot: 4 },
    ]);
    expect(mergePicked([], local)).toEqual([
      { slug: "film", slot: 1 },
      { slug: "tennis", slot: 2 },
      { slug: "astronomy", slot: 3 },
    ]);
    expect(samePicked(mergePicked(account, []), account)).toBe(true);
  });

  it("reads nothing from broken storage", () => {
    expect(loadPicked({ getItem: () => "{not json" })).toEqual([]);
    expect(loadPicked({ getItem: () => '[{"slug": 1}]' })).toEqual([]);
  });
});

describe("the topic picker", () => {
  it("lets a reader continue with 3 to 7 topics, and says what is missing", () => {
    expect(pickStatus(0, 12)).toEqual({ ready: false, tone: "short", text: "0 picked · 3 more to go" });
    expect(pickStatus(2, 12).ready).toBe(false);
    expect(pickStatus(3, 12)).toEqual({ ready: true, tone: "ok", text: "3 picked · good to go" });
    expect(pickStatus(7, 12).ready).toBe(true);
    expect(pickStatus(8, 12)).toEqual({ ready: false, tone: "over", text: "8 picked · remove 1" });
  });

  it("asks for fewer when the catalog has fewer than 3 topics", () => {
    expect(pickStatus(2, 2).ready).toBe(true);
    expect(pickStatus(1, 2).text).toBe("1 picked · 1 more to go");
  });

  it("puts every category in exactly one group, and topics without one last", () => {
    const categories = GROUPS.flatMap((g) => g.categories);

    expect(new Set(categories).size).toBe(categories.length);
    expect(categories).toHaveLength(8);
    expect(GROUPS.at(-1)?.categories).toEqual([null]);
  });
});

describe("accounts", () => {
  it("sends a reader back only to a path on this site after signing in", () => {
    expect(safeNext("/topics")).toBe("/topics");
    expect(safeNext("/notes/a?x=1")).toBe("/notes/a?x=1");
    for (const bad of [null, "", "https://evil.example", "//evil.example", "/\\evil.example", "topics"]) {
      expect(safeNext(bad)).toBe("/");
    }
    // Browsers drop tabs and line breaks from URLs, so these become //evil.example.
    for (const bad of ["/\t/evil.example", "/\n/evil.example", "/\r/evil.example", "/\u0000/x"]) {
      expect(safeNext(bad)).toBe("/");
    }
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
    expect(plural(5, "story", "stories")).toBe("5 stories");
  });
});

describe("coveredBy", () => {
  it("reads the topic that already covers an added one", () => {
    const error = { detail: { message: "Tennis already covers it.", slug: "tennis", name: "Tennis" } };
    expect(coveredBy(error)).toEqual({ slug: "tennis", name: "Tennis", message: "Tennis already covers it." });
  });

  it("is null for any other error", () => {
    expect(coveredBy({ detail: "You have 3 topics being planned." })).toBeNull();
    expect(coveredBy(undefined)).toBeNull();
    expect(coveredBy({ detail: { slug: 1 } })).toBeNull();
  });
});
