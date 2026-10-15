import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { TopicCover } from "../src/components/ui/TopicCover";
import { coverColor, HOME_SLOT, motifOf, NIGHT, nudge, PALETTES, seedOf } from "../src/lib/covers";

describe("covers", () => {
  it("draws each category's motif, and the plain cover without one", () => {
    expect(motifOf("motorsport")).toBe("moto");
    expect(motifOf("science")).toBe("space");
    expect(motifOf("culture")).toBe("rings");
    expect(motifOf(null)).toBe("custom");
  });

  it("moves the main shape by a stable amount within 40 units across and 20 up or down", () => {
    const seeds = ["a", "b", "2026-10-12-norris", ""].map(seedOf);
    const moves = seeds.map(nudge);

    expect(seedOf("2026-10-12-norris")).toBe(seeds[2]);
    expect(new Set(moves.map((m) => `${m.dx},${m.dy}`)).size).toBe(moves.length);
    for (const { dx, dy } of Array.from({ length: 500 }, (_, i) => nudge(seedOf(`note-${i}`)))) {
      expect(Math.abs(dx)).toBeLessThanOrEqual(40);
      expect(Math.abs(dy)).toBeLessThanOrEqual(20);
    }
  });

  it("paints a circle in the slot's base color, and space always on deep night", () => {
    expect(coverColor("dots", 5)).toBe(PALETTES[5]!.base);
    expect(coverColor("dots", undefined)).toBe(PALETTES[HOME_SLOT.dots]!.base);
    expect(coverColor("space", 2)).toBe(NIGHT);
  });

  it("gives every cover on a page its own pattern id", () => {
    const html = renderToString(
      <>
        <TopicCover motif="moto" slot={1} />
        <TopicCover motif="moto" slot={1} />
        <TopicCover motif="dots" slot={4} />
      </>,
    );
    const ids = [...html.matchAll(/<pattern id="([^"]+)"/g)].map((m) => m[1]);

    expect(ids).toHaveLength(3);
    expect(new Set(ids).size).toBe(3);
    for (const id of ids) expect(html).toContain(`url(#${id})`);
  });

  it("is hidden from screen readers and shows a plain cover's initial", () => {
    const html = renderToString(<TopicCover motif="custom" name="electric ferries" />);

    expect(html).toContain('aria-hidden="true"');
    expect(html).toContain(">E</text>");
  });
});
