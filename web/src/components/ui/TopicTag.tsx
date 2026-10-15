/** A topic's slot dot beside its name; never the color alone (DESIGN.md, Colors). */
export function TopicTag({ name, slot }: { name: string; slot?: number | undefined }) {
  return (
    <span className="tag">
      <span
        className="dot"
        style={{ background: slot ? `var(--s${slot})` : "var(--line2)" }}
        aria-hidden="true"
      />
      {name}
    </span>
  );
}
