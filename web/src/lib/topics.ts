/** The visitor's topics, kept in the browser (no accounts in phase 1), each with one of the
 * eight color slots. A topic keeps its slot when another is removed (DESIGN.md, Colors). */

export interface Picked {
  slug: string;
  slot: number;
}

export const SLOTS = 8;
const KEY = "dan.topics";

export function addTopic(picked: Picked[], slug: string): Picked[] {
  if (picked.some((p) => p.slug === slug) || picked.length >= SLOTS) return picked;
  const taken = new Set(picked.map((p) => p.slot));
  const slot = Array.from({ length: SLOTS }, (_, i) => i + 1).find((s) => !taken.has(s));
  return slot === undefined ? picked : [...picked, { slug, slot }];
}

export function removeTopic(picked: Picked[], slug: string): Picked[] {
  return picked.filter((p) => p.slug !== slug);
}

export function slotOf(picked: Picked[], slug: string): number | undefined {
  return picked.find((p) => p.slug === slug)?.slot;
}

export function loadPicked(storage: Pick<Storage, "getItem"> = localStorage): Picked[] {
  try {
    const value: unknown = JSON.parse(storage.getItem(KEY) ?? "[]");
    if (!Array.isArray(value)) return [];
    return value.filter(
      (p): p is Picked => typeof p?.slug === "string" && Number.isInteger(p?.slot),
    );
  } catch {
    return [];
  }
}

export function savePicked(picked: Picked[], storage: Pick<Storage, "setItem"> = localStorage) {
  storage.setItem(KEY, JSON.stringify(picked));
}
