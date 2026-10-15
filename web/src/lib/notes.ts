/** Reading a note: its text with citation markers, the day's order, and the times in its trail. */

/** "It rained [1][2]." → ["It rained ", 1, "", 2, "."]: text, then each marker's number. */
export function splitMarkers(text: string): (string | number)[] {
  const parts: (string | number)[] = [];
  let last = 0;
  for (const match of text.matchAll(/\[(\d+)\]/g)) {
    parts.push(text.slice(last, match.index), Number(match[1]));
    last = match.index + match[0].length;
  }
  parts.push(text.slice(last));
  return parts;
}

export function paragraphsOf(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

/** The day's order everywhere: the biggest story (most reports merged) first, then the rest as
 * the API lists them. */
export function orderDay<T extends { reports: number }>(notes: T[]): T[] {
  const lead = notes.reduce<T | undefined>((best, n) => (!best || n.reports > best.reports ? n : best), undefined);
  return lead ? [lead, ...notes.filter((n) => n !== lead)] : [];
}

/** Which citation is open, and in which paragraph its chip was pressed. */
export interface OpenCitation {
  marker: number;
  paragraph: number;
}

/** Pressing the open chip closes it; any other chip opens in its own place. */
export function toggleCitation(open: OpenCitation | null, pressed: OpenCitation): OpenCitation | null {
  return open && open.marker === pressed.marker && open.paragraph === pressed.paragraph ? null : pressed;
}

/** "01:42 UTC": the server does not know the reader's time zone, so the trail says UTC. */
export function timeUtc(iso: string): string {
  return `${new Date(iso).toISOString().slice(11, 16)} UTC`;
}

/** "14 min", "2 h 5 min", "3 days" between two times; null when the order is wrong. */
export function duration(fromIso: string, toIso: string): string | null {
  const minutes = Math.round((Date.parse(toIso) - Date.parse(fromIso)) / 60_000);
  if (Number.isNaN(minutes) || minutes < 0) return null;
  if (minutes < 60) return `${Math.max(1, minutes)} min`;
  if (minutes < 48 * 60) {
    const rest = minutes % 60;
    return `${Math.floor(minutes / 60)} h${rest ? ` ${rest} min` : ""}`;
  }
  return `${Math.round(minutes / 1440)} days`;
}
