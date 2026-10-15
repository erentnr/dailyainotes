/** Ask's filters as the API takes them, and how an answer names what it searched. */
import { addDays } from "./format";

export type Range = "7d" | "30d" | "all" | "custom";

export const RANGES: { id: Range; label: string }[] = [
  { id: "7d", label: "Last 7 days" },
  { id: "30d", label: "Last 30 days" },
  { id: "all", label: "All time" },
  { id: "custom", label: "Pick dates…" },
];

/** The days to search, both included. Notes are dated by the UTC day of their run. */
export function daysOf(
  range: Range,
  today: string,
  picked: { from: string; to: string },
): { since?: string; until?: string } {
  if (range === "7d") return { since: addDays(today, -6) };
  if (range === "30d") return { since: addDays(today, -29) };
  if (range === "custom") {
    const [from, to] = [picked.from, picked.to].sort();
    return { ...(from ? { since: from } : {}), ...(to ? { until: to } : {}) };
  }
  return {};
}

const DAY = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

function day(iso: string): string {
  return DAY.format(new Date(`${iso}T00:00:00Z`));
}

/** "6 Oct 2026 – 12 Oct 2026", "From 6 Oct 2026", "Any day". */
export function daysLabel({ since, until }: { since?: string; until?: string }): string {
  if (since && until) return since === until ? day(since) : `${day(since)} – ${day(until)}`;
  if (since) return `From ${day(since)}`;
  if (until) return `Until ${day(until)}`;
  return "Any day";
}

/** What an answer searched: "FORMULA 1, CLIMATE TECH · LAST 7 DAYS" (set in capitals by CSS). */
export function scopeLabel(topicNames: string[], range: Range, days: { since?: string; until?: string }): string {
  const topics = topicNames.length ? topicNames.join(", ") : "All topics";
  const when = range === "custom" ? daysLabel(days) : (RANGES.find((r) => r.id === range)?.label ?? "");
  return `${topics} · ${when}`;
}

/** Why the notes fell short, in a sentence: "None of the notes on Formula 1 from the last 7
 * days cover it." Only what was searched; never a guess at the reason. */
export function shortfall(topicNames: string[], range: Range, days: { since?: string; until?: string }): string {
  const on = topicNames.length ? ` on ${topicNames.join(", ")}` : "";
  let when = "";
  if (range === "7d") when = " from the last 7 days";
  else if (range === "30d") when = " from the last 30 days";
  else if (days.since && days.until) when = ` from ${day(days.since)} to ${day(days.until)}`;
  else if (days.since) when = ` from ${day(days.since)} on`;
  else if (days.until) when = ` up to ${day(days.until)}`;
  return on || when
    ? `None of the notes${on}${when} cover it.`
    : "No published note covers it.";
}

/** Questions to start with, one per topic, worded in turn. */
export function suggestedQuestions(topicNames: string[]): string[] {
  const forms = [
    (t: string) => `What's new in ${t} this week?`,
    (t: string) => `What happened in ${t} this month?`,
    (t: string) => `What are the open questions in ${t} right now?`,
    (t: string) => `Summarise the latest on ${t}`,
  ];
  return topicNames.slice(0, 4).map((name, i) => forms[i % forms.length]!(name));
}
