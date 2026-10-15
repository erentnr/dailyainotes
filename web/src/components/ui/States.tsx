import type { ReactNode } from "react";

/** Nothing to show, said plainly. */
export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="card state">{children}</div>;
}

/** An error that reassures, with a way to try again when there is one. */
export function ErrorState({ children, onRetry }: { children: ReactNode; onRetry?: () => void }) {
  return (
    <div className="card state state-error" role="alert">
      <p>
        {children} Your notes are safe.
      </p>
      {onRetry && (
        <button type="button" className="button button-primary" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

/** Bars that pulse while something loads, unless reduced motion is set. */
export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading">
      {Array.from({ length: lines }, (_, i) => (
        <div className="skeleton" key={i} style={{ width: `${90 - i * 15}%` }} />
      ))}
    </div>
  );
}

/** A note card still loading: a cover block and three bars. */
export function SkeletonCard() {
  return (
    <div className="card note-item skeleton-card" aria-hidden="true">
      <span className="note-item-cover skeleton-block" />
      <span className="note-item-body">
        <span className="skeleton" style={{ width: "40%" }} />
        <span className="skeleton skeleton-tall" style={{ width: "95%" }} />
        <span className="skeleton" style={{ width: "75%" }} />
      </span>
    </div>
  );
}
