/** Topic covers (DESIGN.md, Covers): the motif comes from the topic's category, the colors from
 * its slot, and a seed from the note moves the main shape so no two covers match. */
import type { Topic } from "./api/client";

export type Category = NonNullable<Topic["category"]>;
export type Motif = "moto" | "pitch" | "space" | "waves" | "bars" | "dots" | "rings" | "custom";

const MOTIF: Record<Category, Motif> = {
  motorsport: "moto",
  sport: "pitch",
  science: "space",
  climate: "waves",
  business: "bars",
  technology: "dots",
  culture: "rings",
};

/** The slot a motif's art was drawn in; a topic takes it when it is free. */
export const HOME_SLOT: Record<Motif, number> = {
  moto: 1,
  waves: 2,
  bars: 3,
  dots: 4,
  pitch: 5,
  space: 6,
  custom: 7,
  rings: 8,
};

export function motifOf(category: Category | null | undefined): Motif {
  return category ? MOTIF[category] : "custom";
}

export interface Palette {
  base: string;
  light: string;
  lighter: string;
  dark: string;
  deep: string;
  /** The sun and the trend line: pale yellow, except where the base is yellow itself. */
  glow: string;
}

/** Cover tones per slot (Ember, Fern, Iris, Saffron, Rose, Night, Lagoon, Signal). A motif in its
 * home slot uses the canvas's own colors; the other tones follow the same steps. Covers keep
 * these in both themes. */
export const PALETTES: Record<number, Palette> = {
  1: { base: "#FF5A1F", light: "#FF7E4D", lighter: "#FFA27E", dark: "#F2471A", deep: "#E63E12", glow: "#FFE08A" },
  2: { base: "#17A673", light: "#33C08A", lighter: "#5FD4A6", dark: "#0E8A5C", deep: "#0A6F49", glow: "#F6E7A1" },
  3: { base: "#5B4BE0", light: "#8577FF", lighter: "#A49AFF", dark: "#4A3BC8", deep: "#3B2FA6", glow: "#FFD84D" },
  4: { base: "#F4B400", light: "#FFC83D", lighter: "#FFDB75", dark: "#DB9F00", deep: "#B98600", glow: "#FFFFFF" },
  5: { base: "#F06BA0", light: "#F58DB6", lighter: "#F9B0CD", dark: "#E0548C", deep: "#C93F76", glow: "#FFE08A" },
  6: { base: "#3A4CC0", light: "#5B6BD6", lighter: "#8592E6", dark: "#2E3DA3", deep: "#232F85", glow: "#FFD84D" },
  7: { base: "#0FA3A3", light: "#3DBDBD", lighter: "#74D3D3", dark: "#0B8C8C", deep: "#087272", glow: "#FFE08A" },
  8: { base: "#D93A3A", light: "#F27272", lighter: "#F7A0A0", dark: "#C02E2E", deep: "#A12424", glow: "#FFD84D" },
};

/** The space motif always sits on deep night, whatever the slot. */
export const NIGHT = "#121A40";

export function paletteOf(motif: Motif, slot: number | undefined): Palette {
  return PALETTES[slot ?? HOME_SLOT[motif]] ?? PALETTES[HOME_SLOT[motif]]!;
}

/** The color of a topic's cover circle in chips and tabs. */
export function coverColor(motif: Motif, slot: number | undefined): string {
  return motif === "space" ? NIGHT : paletteOf(motif, slot).base;
}

/** A stable number from a note's slug (FNV-1a). */
export function seedOf(text: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

/** How far the seed moves the main shape: up to 40 units sideways and 20 up or down. */
export function nudge(seed: number): { dx: number; dy: number } {
  return { dx: (seed % 81) - 40, dy: (Math.floor(seed / 81) % 41) - 20 };
}
