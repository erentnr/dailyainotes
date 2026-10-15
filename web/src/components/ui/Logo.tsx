/** An ink square with three ruled lines, beside the name (DESIGN.md, Iconography). */
export function Logo() {
  return (
    <a className="logo" href="/">
      <span className="logo-mark" aria-hidden="true">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <path d="M2 3h8M2 6h8M2 9h5" stroke="var(--card)" strokeWidth="1.6" />
        </svg>
      </span>
      Daily AI Notes
    </a>
  );
}
