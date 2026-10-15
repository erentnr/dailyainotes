/** The visitor's topics, each with one of the eight color slots. A topic takes its category's
 * home slot when it is free, otherwise the next free one, and keeps it when another topic is
 * removed (DESIGN.md, Covers). They live in the browser; for a signed-in reader the account
 * holds them and the page copies them here before anything reads them (ADR 0003). */
import { type Category, HOME_SLOT, motifOf } from "./covers";


export interface Picked {
  slug: string;
  slot: number;
}

export const SLOTS = 8;
const KEY = "dan.topics";

/** Follow a topic in `preferred`, or in the next free slot after it. */
export function addTopic(picked: Picked[], slug: string, preferred = 1): Picked[] {
  if (picked.some((p) => p.slug === slug) || picked.length >= SLOTS) return picked;
  return [...picked, { slug, slot: freeSlot(picked, preferred) }];
}

export function homeSlot(category: Category | null | undefined): number {
  return HOME_SLOT[motifOf(category)];
}

/** A followed topic's slot, or the one it would take if followed now. */
export function slotFor(picked: Picked[], slug: string, category: Category | null | undefined) {
  return slotOf(picked, slug) ?? freeSlot(picked, homeSlot(category));
}

function freeSlot(picked: Picked[], preferred: number): number {
  const taken = new Set(picked.map((p) => p.slot));
  const order = Array.from({ length: SLOTS }, (_, i) => ((preferred - 1 + i) % SLOTS) + 1);
  return order.find((s) => !taken.has(s)) ?? preferred;
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

/** At sign-in: the account's topics keep their slots, and the browser's other picks join them,
 * in their own slot when it is free, up to eight. */
export function mergePicked(account: Picked[], local: Picked[]): Picked[] {
  return local.reduce((merged, p) => addTopic(merged, p.slug, p.slot), account);
}

export function samePicked(a: Picked[], b: Picked[]): boolean {
  const key = (picked: Picked[]) => JSON.stringify([...picked].sort((x, y) => x.slot - y.slot));
  return key(a) === key(b);
}

export function savePicked(picked: Picked[], storage: Pick<Storage, "setItem"> = localStorage) {
  storage.setItem(KEY, JSON.stringify(picked));
}

/** The topic picker's groups, by category; topics without one come last. */
export const GROUPS: { name: string; categories: (Category | null)[] }[] = [
  { name: "Sport", categories: ["motorsport", "sport"] },
  { name: "Science & space", categories: ["science"] },
  { name: "Climate & energy", categories: ["climate"] },
  { name: "Business", categories: ["business"] },
  { name: "Technology", categories: ["technology"] },
  { name: "Culture", categories: ["culture"] },
  { name: "More topics", categories: [null] },
];

/** A page works best with 3 to 7 topics: enough for a day to have something, few enough to
 * read. With fewer than 3 in the catalog, all of them will do. */
export const MOST_PICKS = 7;

export function pickStatus(count: number, available: number) {
  const least = Math.min(3, available);
  if (count > MOST_PICKS) {
    return { ready: false, tone: "over", text: `${count} picked · remove ${count - MOST_PICKS}` } as const;
  }
  if (count < least) {
    return { ready: false, tone: "short", text: `${count} picked · ${least - count} more to go` } as const;
  }
  return { ready: true, tone: "ok", text: `${count} picked · good to go` } as const;
}
