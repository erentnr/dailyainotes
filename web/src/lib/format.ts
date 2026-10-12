/** Dates and verdicts as DESIGN.md writes them. */

// en-US for the names: en-GB writes September as "Sept".
const DAY = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const MONTH = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });

/** "2026-10-12" → "Mon 12 Oct 2026": absolute, never "yesterday". */
export function formatDay(isoDate: string): string {
  const parts = DAY.formatToParts(new Date(`${isoDate.slice(0, 10)}T00:00:00Z`));
  const part = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${part("weekday")} ${part("day")} ${part("month")} ${part("year")}`;
}

export function formatMonth(isoDate: string): string {
  return MONTH.format(new Date(`${isoDate.slice(0, 10)}T00:00:00Z`));
}

export type Verdict = "verified" | "partial" | "unsupported" | "unchecked";

export function verdictOf(counts: {
  claims: number;
  supported: number;
  unsupported: number;
}): Verdict {
  if (counts.claims === 0) return "unchecked";
  if (counts.unsupported > 0) return "unsupported";
  return counts.supported === counts.claims ? "verified" : "partial";
}

export function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}
