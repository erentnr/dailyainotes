/** Publishers as initials in overlapping circles; no favicons are fetched from anyone. */
export function Publishers({ names }: { names: string[] }) {
  return (
    <span className="publishers" aria-label={names.join(", ")}>
      {names.slice(0, 5).map((name) => (
        <span className="publisher" key={name} title={name} aria-hidden="true">
          {name.slice(0, 1).toUpperCase()}
        </span>
      ))}
    </span>
  );
}
