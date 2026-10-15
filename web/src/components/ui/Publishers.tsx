/** Publishers as initials in overlapping circles. No favicons are fetched: that would send each
 * visit to other sites (DESIGN.md, Components). */
export function Publishers({ names }: { names: string[] }) {
  if (names.length === 0) return null;
  return (
    <span className="publishers" role="img" aria-label={`From ${names.join(", ")}`}>
      {names.slice(0, 4).map((name) => (
        <span className="publisher" key={name} title={name}>
          {initial(name)}
        </span>
      ))}
    </span>
  );
}

/** "The Race" → "R": the first letter of the name without a leading "The". */
export function initial(name: string): string {
  return name.replace(/^the\s+/i, "").trim().slice(0, 1).toUpperCase();
}
