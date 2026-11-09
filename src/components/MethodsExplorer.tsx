import { useEffect, useMemo, useState } from 'react';

export interface MethodRow {
  id: string; name: string; family: string; familyName: string; section: string | null; sectionHref: string | null;
  definition: string; assumptions: string[]; evaluation: string[]; applications: string[]; limitations: string[];
  related: { id: string; name: string }[]; notebooks: number; demos: number; href: string;
  /** Build-time HTML of each text field (maths rendered with KaTeX). */
  html: Record<string, string[]>;
}
interface Props { rows: MethodRow[]; families: { id: string; name: string; count: number }[] }

const FIELDS: [keyof MethodRow, string][] = [
  ['definition', 'Definition'], ['assumptions', 'Assumptions & requirements'], ['evaluation', 'Evaluation considerations'],
  ['applications', 'Intended applications'], ['limitations', 'Limitations'],
];
const norm = (s: string) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

export default function MethodsExplorer({ rows, families }: Props) {
  const [q, setQ] = useState('');
  const [fam, setFam] = useState<string | null>(null);
  const [onlyRunnable, setOnlyRunnable] = useState(false);
  const [compare, setCompare] = useState<string[]>([]);

  useEffect(() => {
    const p = new URLSearchParams(location.search);
    const c = p.get('compare'); if (c) setCompare(c.split(',').filter((id) => rows.some((r) => r.id === id)).slice(0, 3));
    const f = p.get('family'); if (f) setFam(f);
    const qq = p.get('q'); if (qq) setQ(qq);
  }, []);
  useEffect(() => {
    const p = new URLSearchParams();
    if (compare.length) p.set('compare', compare.join(','));
    if (fam) p.set('family', fam);
    if (q) p.set('q', q);
    const s = p.toString();
    history.replaceState(null, '', s ? `?${s}` : location.pathname);
  }, [compare, fam, q]);

  const shown = useMemo(() => {
    const terms = norm(q).split(/\s+/).filter(Boolean);
    return rows.filter((r) => (!fam || r.family === fam) && (!onlyRunnable || r.notebooks + r.demos > 0) &&
      terms.every((t) => norm([r.name, r.familyName, r.definition, ...r.assumptions, ...r.applications, ...r.limitations, ...r.evaluation].join(' ')).includes(t)));
  }, [rows, q, fam, onlyRunnable]);

  const toggle = (id: string) => setCompare((c) => c.includes(id) ? c.filter((x) => x !== id) : c.length >= 3 ? [...c.slice(1), id] : [...c, id]);
  const cmp = compare.map((id) => rows.find((r) => r.id === id)!).filter(Boolean);

  return (
    <div>
      <div style={{ display: 'grid', gap: '.6rem', margin: '1rem 0 1.25rem' }}>
        <label className="visually-hidden" htmlFor="mq">Search methods</label>
        <span className="search-field">
          <input id="mq" className="input" type="search" value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search names and survey text, e.g. “causal”, “sparsity”, “unlearning”" />
        </span>
        <div role="group" aria-label="Filter by family" style={{ display: 'flex', flexWrap: 'wrap', gap: '.35rem' }}>
          <button className={`chip ${!fam ? 'on' : ''}`} aria-pressed={!fam} onClick={() => setFam(null)}>All families ({rows.length})</button>
          {families.map((f) => (
            <button key={f.id} className={`chip ${fam === f.id ? 'on' : ''}`} aria-pressed={fam === f.id} onClick={() => setFam(fam === f.id ? null : f.id)}>
              {f.name} ({f.count})
            </button>
          ))}
        </div>
        <label className="small" style={{ display: 'flex', gap: '.4rem', alignItems: 'center' }}>
          <input type="checkbox" checked={onlyRunnable} onChange={(e) => setOnlyRunnable(e.target.checked)} /> Only methods with a notebook or demo
        </label>
        <p className="small muted" aria-live="polite" style={{ margin: 0 }}>
          {shown.length} of {rows.length} methods. Select up to three to compare.
        </p>
      </div>

      {cmp.length > 0 && (
        <section aria-labelledby="cmp-h" className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '1rem', flexWrap: 'wrap' }}>
            <h2 id="cmp-h" style={{ margin: 0, fontSize: '1.15rem' }}>Comparison</h2>
            <span className="small muted"><button className="chip" onClick={() => setCompare([])}>Clear</button></span>
          </div>
          <div className="scroll-x">
            <table className="data" style={{ marginTop: '.8rem', minWidth: `${12 + cmp.length * 16}rem` }}>
              <thead><tr><th style={{ width: '11rem' }}></th>{cmp.map((m) => <th key={m.id}><a href={m.href}>{m.name}</a><div className="small muted">{m.familyName}</div></th>)}</tr></thead>
              <tbody>
                {FIELDS.map(([k, label]) => (
                  <tr key={k}>
                    <th scope="row">{label}</th>
                    {cmp.map((m) => {
                      const list = m.html[k as string] ?? [];
                      return <td key={m.id} style={{ fontFamily: 'var(--serif)', fontSize: '.92rem' }}>
                        {list.length ? list.map((t, i) => <p key={i} style={{ margin: '0 0 .5rem' }} dangerouslySetInnerHTML={{ __html: `“${t}”` }} />) : <span className="muted small">Not stated</span>}
                      </td>;
                    })}
                  </tr>
                ))}
                <tr><th scope="row">Survey section</th>{cmp.map((m) => <td key={m.id}>{m.sectionHref ? <a href={m.sectionHref}>§{m.section}</a> : '—'}</td>)}</tr>
              </tbody>
            </table>
          </div>
        </section>
      )}

      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '.6rem' }}>
        {shown.map((r) => (
          <li key={r.id} className="card" style={{ display: 'grid', gridTemplateColumns: 'auto minmax(0, 1fr)', gap: '.8rem', alignItems: 'start' }}>
            <input type="checkbox" aria-label={`Compare ${r.name}`} checked={compare.includes(r.id)} onChange={() => toggle(r.id)} style={{ marginTop: '.35rem', width: '1.05rem', height: '1.05rem' }} />
            <div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.5rem', alignItems: 'baseline' }}>
                <a href={r.href} style={{ fontWeight: 650, fontSize: '1.02rem' }}>{r.name}</a>
                <span className="chip">{r.familyName}</span>
                {r.section && <span className="small muted">§{r.section}</span>}
                {r.notebooks > 0 && <span className="chip">notebook</span>}
                {r.demos > 0 && <span className="chip">demo</span>}
              </div>
              {r.definition
                ? <p className="small clamp-3" style={{ margin: '.35rem 0 0', color: 'var(--ink-2)', fontFamily: 'var(--serif)', fontSize: '.95rem' }}
                    dangerouslySetInnerHTML={{ __html: `“${r.html.definition[0]}”` }} />
                : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
