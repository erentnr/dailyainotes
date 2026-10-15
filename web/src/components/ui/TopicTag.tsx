/** A topic's color square beside its name; never the color alone (DESIGN.md, Colors). */
export function TopicTag({ name, slot }: { name: string; slot?: number | undefined }) {
  return (
    <span className="tag">
      <span
        className="tag-square"
        style={{ background: slot ? `var(--s${slot})` : "var(--line2)" }}
        aria-hidden="true"
      />
      {name}
    </span>
  );
}
