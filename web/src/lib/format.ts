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
const LONG = new Intl.DateTimeFormat("en-US", {
  weekday: "long",
  day: "numeric",
  month: "long",
  timeZone: "UTC",
});
const SHORT = new Intl.DateTimeFormat("en-US", { weekday: "short", day: "numeric", timeZone: "UTC" });

function utc(isoDate: string): Date {
  return new Date(`${isoDate.slice(0, 10)}T00:00:00Z`);
}

function parts(format: Intl.DateTimeFormat, isoDate: string) {
  const all = format.formatToParts(utc(isoDate));
  return (type: string) => all.find((p) => p.type === type)?.value ?? "";
}

/** "2026-10-12" → "Mon 12 Oct 2026": absolute, never "yesterday". */
export function formatDay(isoDate: string): string {
  const part = parts(DAY, isoDate);
  return `${part("weekday")} ${part("day")} ${part("month")} ${part("year")}`;
}

/** "2026-10-15" → "Thursday 15 October", for the top of a day. */
export function formatLongDay(isoDate: string): string {
  const part = parts(LONG, isoDate);
  return `${part("weekday")} ${part("day")} ${part("month")}`;
}

/** "2026-10-14" → "Wed 14", for a row of days. */
export function formatShortDay(isoDate: string): string {
  const part = parts(SHORT, isoDate);
  return `${part("weekday")} ${part("day")}`;
}

/** The ISO date `days` after (or before) another. */
export function addDays(isoDate: string, days: number): string {
  const date = utc(isoDate);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/** Minutes to read some texts at 200 words a minute, at least one. */
export function readingMinutes(texts: string[]): number {
  const words = texts.reduce((sum, text) => sum + text.split(/\s+/).filter(Boolean).length, 0);
  return Math.max(1, Math.round(words / 200));
}

/** By the reader's own clock. */
export function greeting(hour: number): string {
  if (hour >= 5 && hour < 12) return "Good morning.";
  if (hour >= 12 && hour < 18) return "Good afternoon.";
  return "Good evening.";
}

export function formatMonth(isoDate: string): string {
  return MONTH.format(utc(isoDate));
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

export function plural(count: number, word: string, many = `${word}s`): string {
  return `${count} ${count === 1 ? word : many}`;
}
