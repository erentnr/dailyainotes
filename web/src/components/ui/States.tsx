import type { ReactNode } from "react";

/** Empty and "not enough" states sit on graph paper; errors reassure. */
export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="state graph-paper">{children}</div>;
}

export function ErrorState({ children }: { children: ReactNode }) {
  return (
    <div className="state state-error" role="alert">
      {children} Your notes are safe; try again in a moment.
    </div>
  );
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading">
      {Array.from({ length: lines }, (_, i) => (
        <div className="skeleton" key={i} style={{ width: `${90 - i * 15}%` }} />
      ))}
    </div>
  );
}
