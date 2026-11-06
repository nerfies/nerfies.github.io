// Shared SVG chart primitives for the demos. Colours come from CSS tokens so
// charts follow the light/dark theme.

/** Diverging colour for v in [-1, 1]: --neg … --zero … --pos */
export function divColor(v: number) {
  const t = Math.max(-1, Math.min(1, v));
  const pct = Math.round(Math.abs(t) * 100);
  return `color-mix(in srgb, var(${t >= 0 ? '--pos' : '--neg'}) ${pct}%, var(--zero))`;
}

interface HeatProps {
  data: number[][]; rowLabels: string[]; colLabels: string[]; scale?: number; cell?: number;
  title: string; onSelect?: (r: number, c: number) => void; selected?: [number, number] | null;
  format?: (v: number) => string; colLabelRotate?: boolean; rowTitle?: string; colTitle?: string;
}
export function Heatmap({ data, rowLabels, colLabels, scale = 1, cell = 26, title, onSelect, selected, format = (v) => v.toFixed(2), colLabelRotate, rowTitle, colTitle }: HeatProps) {
  const left = 64, top = colLabelRotate ? 76 : 30;
  const W = left + colLabels.length * cell + 8, H = top + rowLabels.length * cell + (colTitle ? 26 : 8);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} style={{ width: '100%', maxWidth: W * 1.6 }}>
      <title>{title}</title>
      {colLabels.map((c, j) => (
        <text key={j} x={left + j * cell + cell / 2} y={top - 6} fontSize="10" textAnchor={colLabelRotate ? 'start' : 'middle'}
          transform={colLabelRotate ? `rotate(-55 ${left + j * cell + cell / 2} ${top - 6})` : undefined}>{c}</text>
      ))}
      {rowLabels.map((r, i) => <text key={i} x={left - 6} y={top + i * cell + cell / 2 + 3.5} fontSize="10" textAnchor="end">{r}</text>)}
      {data.map((row, i) => row.map((v, j) => {
        const sel = selected && selected[0] === i && selected[1] === j;
        return (
          <rect key={`${i}-${j}`} x={left + j * cell + 1} y={top + i * cell + 1} width={cell - 2} height={cell - 2} rx="2"
            fill={divColor(v / scale)} stroke={sel ? 'var(--ink)' : 'none'} strokeWidth={sel ? 2 : 0}
            tabIndex={onSelect ? 0 : undefined} role={onSelect ? 'button' : undefined}
            aria-label={`${rowLabels[i]}, ${colLabels[j]}: ${format(v)}`}
            onClick={onSelect ? () => onSelect(i, j) : undefined}
            onKeyDown={onSelect ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(i, j); } } : undefined}
            style={{ cursor: onSelect ? 'pointer' : undefined }}>
            <title>{`${rowLabels[i]}, ${colLabels[j]}: ${format(v)}`}</title>
          </rect>
        );
      }))}
      {rowTitle && <text x={10} y={top + (rowLabels.length * cell) / 2} fontSize="10" transform={`rotate(-90 10 ${top + (rowLabels.length * cell) / 2})`} textAnchor="middle">{rowTitle}</text>}
      {colTitle && <text x={left + (colLabels.length * cell) / 2} y={H - 6} fontSize="10" textAnchor="middle">{colTitle}</text>}
    </svg>
  );
}

export function Legend({ min, max, label }: { min: string; max: string; label: string }) {
  return (
    <div className="small muted" style={{ display: 'flex', alignItems: 'center', gap: '.5rem', marginTop: '.4rem' }} aria-hidden="true">
      <span>{min}</span>
      <span style={{ width: 140, height: 10, borderRadius: 3, background: 'linear-gradient(90deg, var(--neg), var(--zero), var(--pos))' }} />
      <span>{max}</span><span>· {label}</span>
    </div>
  );
}

export function Bars({ values, labels, max, title, color = 'var(--accent)', threshold }: { values: number[]; labels: string[]; max: number; title: string; color?: string; threshold?: number }) {
  const w = 260, rowH = 18, left = 34;
  return (
    <svg viewBox={`0 0 ${w + left + 40} ${values.length * rowH + 6}`} role="img" aria-label={title} style={{ width: '100%', maxWidth: 420 }}>
      <title>{title}</title>
      {values.map((v, i) => (
        <g key={i}>
          <text x={left - 6} y={i * rowH + 13} fontSize="10" textAnchor="end">{labels[i]}</text>
          <rect x={left} y={i * rowH + 3} width={Math.max(0, Math.min(1, v / max)) * w} height={rowH - 6} rx="2" fill={color} />
          <text x={left + Math.max(0, Math.min(1, v / max)) * w + 4} y={i * rowH + 13} fontSize="10">{v.toFixed(2)}</text>
        </g>
      ))}
      {threshold !== undefined && <line x1={left + (threshold / max) * w} x2={left + (threshold / max) * w} y1={0} y2={values.length * rowH + 6} stroke="var(--ink-3)" strokeDasharray="3 3" />}
    </svg>
  );
}
