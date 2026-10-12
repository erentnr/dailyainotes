/** A notebook square with three ruled lines and an ink-blue margin line (DESIGN.md). */
export function Logo() {
  return (
    <a className="logo" href="/">
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
        <rect x="1" y="1" width="20" height="20" rx="3" stroke="var(--ink)" strokeWidth="1.5" />
        <path d="M6 1v20" stroke="var(--accent)" strokeWidth="1.5" />
        <path d="M9 7h8M9 11h8M9 15h6" stroke="var(--ink)" strokeWidth="1.2" />
      </svg>
      Daily AI Notes
    </a>
  );
}
