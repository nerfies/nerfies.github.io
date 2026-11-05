import { useMemo, useState } from 'react';
import { Heatmap, Legend } from './viz';

interface Data {
  tokens_example: string[]; resid_pre_recovery: number[][]; head_z_recovery: number[][]; head_attribution_patching: number[][];
  pearson_activation_vs_attribution: number; logit_diff_clean: number; logit_diff_corrupt: number; n_prompts: number;
  example: { clean: string; corrupt: string; IO: string; S: string };
}

export default function PatchingDemo({ data }: { data: Data }) {
  const [view, setView] = useState<'resid' | 'heads'>('resid');
  const [method, setMethod] = useState<'act' | 'attr'>('act');
  const [sel, setSel] = useState<[number, number] | null>(null);
  const layers = data.resid_pre_recovery.length;
  const toks = data.tokens_example.map((t, i) => `${i}:${t.replace(/ /g, '·')}`);
  const heads = method === 'act' ? data.head_z_recovery : data.head_attribution_patching;
  const top = useMemo(() => data.head_z_recovery.flatMap((r, l) => r.map((v, h) => ({ l, h, v, a: data.head_attribution_patching[l][h] })))
    .sort((a, b) => Math.abs(b.v) - Math.abs(a.v)).slice(0, 8), [data]);

  const pts = data.head_z_recovery.flatMap((r, l) => r.map((v, h) => ({ l, h, x: v, y: data.head_attribution_patching[l][h] })));
  const ext = Math.max(...pts.flatMap((p) => [Math.abs(p.x), Math.abs(p.y)])) * 1.1;
  const S = 220, pad = 30, sx = (v: number) => pad + ((v + ext) / (2 * ext)) * S, sy = (v: number) => pad + S - ((v + ext) / (2 * ext)) * S;

  const detail = sel && (view === 'resid'
    ? `Patching the clean residual stream into the corrupted run at layer ${sel[0]}, token ${toks[sel[1]]} recovers ${(data.resid_pre_recovery[sel[0]][sel[1]] * 100).toFixed(1)}% of the clean logit difference.`
    : `Patching the output of head L${sel[0]}H${sel[1]}: activation patching ${(data.head_z_recovery[sel[0]][sel[1]] * 100).toFixed(1)}%, attribution patching estimate ${(data.head_attribution_patching[sel[0]][sel[1]] * 100).toFixed(1)}%.`);

  return (
    <div>
      <div className="card" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'grid', gap: '.3rem', fontFamily: 'var(--mono)', fontSize: '.88rem' }}>
          <div><span className="chip">clean</span> {data.example.clean} <b>→ {data.example.IO}</b></div>
          <div><span className="chip">corrupted</span> {data.example.corrupt} <b>→ {data.example.S}</b></div>
        </div>
        <div className="stat-row" style={{ marginTop: '.8rem' }}>
          <div className="stat"><b>{data.n_prompts}</b><span>prompt pairs</span></div>
          <div className="stat"><b>{data.logit_diff_clean.toFixed(2)}</b><span>clean logit diff</span></div>
          <div className="stat"><b>{data.logit_diff_corrupt.toFixed(2)}</b><span>corrupted logit diff</span></div>
          <div className="stat"><b>{data.pearson_activation_vs_attribution.toFixed(3)}</b><span>r(activation, attribution)</span></div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: '.4rem', flexWrap: 'wrap', marginBottom: '.8rem' }} role="tablist" aria-label="What to patch">
        <button role="tab" aria-selected={view === 'resid'} className={`chip ${view === 'resid' ? 'on' : ''}`} onClick={() => { setView('resid'); setSel(null); }}>Residual stream × position</button>
        <button role="tab" aria-selected={view === 'heads'} className={`chip ${view === 'heads' ? 'on' : ''}`} onClick={() => { setView('heads'); setSel(null); }}>Attention heads</button>
        {view === 'heads' && <>
          <span className="muted small" style={{ alignSelf: 'center', marginLeft: '.5rem' }}>Estimate:</span>
          <button className={`chip ${method === 'act' ? 'on' : ''}`} aria-pressed={method === 'act'} onClick={() => setMethod('act')}>activation patching (exact)</button>
          <button className={`chip ${method === 'attr' ? 'on' : ''}`} aria-pressed={method === 'attr'} onClick={() => setMethod('attr')}>attribution patching (gradient)</button>
        </>}
      </div>
      <div className="demo" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(14rem, 18rem)' }}>
        <div className="viz">
          <div className="scroll-x">
            {view === 'resid'
              ? <Heatmap data={data.resid_pre_recovery} rowLabels={[...Array(layers).keys()].map((l) => `L${l}`)} colLabels={toks} cell={30} colLabelRotate
                  title="Fraction of logit difference recovered by patching resid_pre at each layer and position" onSelect={(r, c) => setSel([r, c])} selected={sel}
                  format={(v) => `${(v * 100).toFixed(1)}%`} rowTitle="layer" />
              : <Heatmap data={heads} rowLabels={[...Array(layers).keys()].map((l) => `L${l}`)} colLabels={[...Array(heads[0].length).keys()].map((h) => `H${h}`)} cell={28}
                  scale={0.5} title={`Per-head recovery (${method === 'act' ? 'activation' : 'attribution'} patching)`} onSelect={(r, c) => setSel([r, c])} selected={sel}
                  format={(v) => `${(v * 100).toFixed(1)}%`} rowTitle="layer" colTitle="head" />}
          </div>
          <Legend min={view === 'resid' ? '−100%' : '−50%'} max={view === 'resid' ? '+100%' : '+50%'} label="share of clean–corrupted logit difference restored" />
          <p className="small" aria-live="polite" style={{ minHeight: '2.6em' }}>{detail ?? 'Click or tab to a cell for its value.'}</p>
        </div>
        <div className="card">
          {view === 'resid' ? (
            <p className="small">Information that separates clean from corrupted sits at the <b>second name</b> (position {data.tokens_example.findIndex((t, i) => i > 4 && t.trim() === data.example.S)}) in early layers, then moves to the <b>final token</b> in the later layers. Reading off where each row “lights up” shows where the circuit carries the signal.</p>
          ) : (<>
            <h3 style={{ fontSize: '.95rem', margin: '0 0 .4rem' }}>Largest effects</h3>
            <table className="data small"><thead><tr><th>Head</th><th>activation</th><th>attribution</th></tr></thead>
              <tbody>{top.map((t) => <tr key={`${t.l}-${t.h}`}><td>L{t.l}H{t.h}</td><td>{(t.v * 100).toFixed(1)}%</td><td>{(t.a * 100).toFixed(1)}%</td></tr>)}</tbody></table>
            <p className="small muted">Negative values are heads whose clean output pushes <em>against</em> the correct answer.</p>
            <svg viewBox={`0 0 ${S + pad * 2} ${S + pad * 2}`} role="img" aria-label={`Scatter of activation versus attribution patching across 144 heads, Pearson r = ${data.pearson_activation_vs_attribution.toFixed(3)}`}>
              <line x1={sx(-ext)} y1={sy(-ext)} x2={sx(ext)} y2={sy(ext)} stroke="var(--rule)" strokeDasharray="4 3" />
              <line x1={sx(0)} x2={sx(0)} y1={pad} y2={pad + S} stroke="var(--rule)" /><line y1={sy(0)} y2={sy(0)} x1={pad} x2={pad + S} stroke="var(--rule)" />
              {pts.map((p) => <circle key={`${p.l}-${p.h}`} cx={sx(p.x)} cy={sy(p.y)} r="2.6" fill="var(--accent)" opacity=".65"><title>{`L${p.l}H${p.h}: act ${p.x.toFixed(3)}, attr ${p.y.toFixed(3)}`}</title></circle>)}
              <text x={pad + S / 2} y={S + pad * 2 - 6} fontSize="10" textAnchor="middle">activation patching</text>
              <text x={10} y={pad + S / 2} fontSize="10" textAnchor="middle" transform={`rotate(-90 10 ${pad + S / 2})`}>attribution patching</text>
            </svg>
          </>)}
        </div>
      </div>
    </div>
  );
}
