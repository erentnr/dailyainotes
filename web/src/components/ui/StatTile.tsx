/** A label, a value in tabular figures, and a line of context or a sparkline. */
export function StatTile({
  label,
  value,
  context,
  series,
}: {
  label: string;
  value: string;
  context?: string;
  series?: number[];
}) {
  return (
    <div className="stat-tile">
      <div className="label">{label}</div>
      <div className="stat-value">{value}</div>
      {series ? <Sparkline values={series} /> : <div className="small muted">{context}</div>}
    </div>
  );
}

export function Sparkline({ values }: { values: number[] }) {
  const width = 120;
  const height = 28;
  const top = Math.max(1, ...values);
  const step = values.length > 1 ? width / (values.length - 1) : 0;
  const points = values
    .map((v, i) => `${(i * step).toFixed(1)},${(height - 2 - (v / top) * (height - 4)).toFixed(1)}`)
    .join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <polyline points={points} fill="none" stroke="var(--accent)" strokeWidth="1.5" />
    </svg>
  );
}
