import { useEffect, useRef, useState } from 'react';
import { Sae, type SaeConfig } from '../../lib/sim/sae';
import { divColor, Legend } from './viz';

const BASE = { d: 8, nTrue: 16, dict: 32, p: 0.1 };
const TOTAL = 2000, CHUNK = 40;

export default function SaeDemo() {
  const [mode, setMode] = useState<'l1' | 'topk'>('l1');
  const [l1, setL1] = useState(0.3);
  const [k, setK] = useState(3);
  const [seed, setSeed] = useState(1);
  const [, force] = useState(0);
  const sae = useRef<Sae | null>(null);
  const raf = useRef<number | null>(null);
  const [evalRes, setEval] = useState<ReturnType<Sae['evaluate']> | null>(null);
  const [sweep, setSweep] = useState<{ l1: number; fvu: number; l0: number; mmcs: number }[]>([]);
  const [sweeping, setSweeping] = useState(false);

  function start() {
    if (raf.current) cancelAnimationFrame(raf.current);
    const cfg: SaeConfig = { ...BASE, seed, mode, l1, k };
    sae.current = new Sae(cfg); setEval(null);
    const tick = () => {
      const s = sae.current!; s.train(CHUNK); force((x) => x + 1);
      if (s.step < TOTAL) raf.current = requestAnimationFrame(tick); else setEval(s.evaluate());
    };
    raf.current = requestAnimationFrame(tick);
  }
  useEffect(() => { start(); return () => { if (raf.current) cancelAnimationFrame(raf.current); }; }, [mode, l1, k, seed]);

  async function runSweep() {
    setSweeping(true); setSweep([]);
    const pts: typeof sweep = [];
    for (const lam of [0, 0.03, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2]) {
      await new Promise((r) => setTimeout(r, 0));
      const s = new Sae({ ...BASE, seed, mode: 'l1', l1: lam, k }); s.train(TOTAL); const e = s.evaluate();
      pts.push({ l1: lam, fvu: e.fvu, l0: e.l0, mmcs: e.mmcs }); setSweep([...pts]);
    }
    setSweeping(false);
  }

  const s = sae.current;
  const C = s ? s.cosines() : [];
  // order learned latents by their best-matching planted feature, strongest match first
  const best = C.length ? [...Array(BASE.dict).keys()].map((j) => { let bi = 0; C.forEach((row, i) => { if (row[j] > C[bi][j]) bi = i; }); return { j, i: bi, c: C[bi][j] }; }) : [];
  const order = best.sort((a, b) => a.i - b.i || b.c - a.c).map((x) => x.j);
  const cell = 12, left = 34, top = 18;
  const training = s && s.step < TOTAL;

  return (
    <div className="demo">
      <div className="controls card">
        <div role="radiogroup" aria-label="Sparsity mechanism" style={{ display: 'flex', gap: '.4rem' }}>
          <button className={`chip ${mode === 'l1' ? 'on' : ''}`} role="radio" aria-checked={mode === 'l1'} onClick={() => setMode('l1')}>ReLU + L1</button>
          <button className={`chip ${mode === 'topk' ? 'on' : ''}`} role="radio" aria-checked={mode === 'topk'} onClick={() => setMode('topk')}>TopK</button>
        </div>
        {mode === 'l1' ? (
          <label>L1 coefficient λ <output>{l1.toFixed(2)}</output>
            <input type="range" min="0" max="1.5" step="0.01" value={l1} onChange={(e) => setL1(+e.target.value)} /></label>
        ) : (
          <label>k (active latents per input) <output>{k}</output>
            <input type="range" min="1" max="10" step="1" value={k} onChange={(e) => setK(+e.target.value)} /></label>
        )}
        <div style={{ display: 'flex', gap: '.5rem', flexWrap: 'wrap' }}>
          <button className="btn ghost" onClick={() => setSeed((x) => x + 1)}>New seed ({seed})</button>
          <button className="btn ghost" onClick={runSweep} disabled={sweeping}>{sweeping ? 'Sweeping…' : 'Sweep λ'}</button>
        </div>
        <p className="small muted" style={{ margin: 0 }}>Data: {BASE.nTrue} planted features in {BASE.d} dimensions, each active with probability {BASE.p}. Dictionary: {BASE.dict} latents.</p>
        <div className="stat-row">
          <div className="stat"><b>{evalRes ? `${evalRes.recovered}/${BASE.nTrue}` : '…'}</b><span>features recovered (cos &gt; 0.9)</span></div>
          <div className="stat"><b>{evalRes ? evalRes.mmcs.toFixed(3) : '…'}</b><span>MMCS</span></div>
          <div className="stat"><b>{evalRes ? evalRes.fvu.toFixed(3) : s ? s.last.mse.toFixed(3) : '…'}</b><span>{evalRes ? 'variance unexplained' : 'train MSE'}</span></div>
          <div className="stat"><b>{evalRes ? evalRes.l0.toFixed(2) : s ? s.last.l0.toFixed(2) : '…'}</b><span>L0 (mean active)</span></div>
          <div className="stat"><b>{evalRes ? evalRes.dead : '…'}</b><span>dead latents</span></div>
        </div>
        <p className="small muted" style={{ margin: 0 }} aria-live="polite">{training ? `Training… step ${s!.step}/${TOTAL}` : 'Trained. Metrics come from 2,000 held-out samples.'}</p>
      </div>
      <div className="viz">
        <figure style={{ margin: 0 }}>
          <div className="scroll-x">
            <svg viewBox={`0 0 ${left + BASE.dict * cell + 4} ${top + BASE.nTrue * cell + 20}`} role="img" aria-label="Cosine similarity between each planted feature and each learned decoder direction" style={{ width: '100%', minWidth: 360 }}>
              {C.map((row, i) => (
                <g key={i}>
                  <text x={left - 4} y={top + i * cell + 9} fontSize="8" textAnchor="end">g{i + 1}</text>
                  {order.map((j, jj) => <rect key={j} x={left + jj * cell} y={top + i * cell} width={cell - 1} height={cell - 1} fill={divColor(row[j])}><title>{`g${i + 1} · latent ${j}: ${row[j].toFixed(2)}`}</title></rect>)}
                </g>
              ))}
              <text x={left} y={10} fontSize="9">learned latents (sorted by best-matching planted feature) →</text>
            </svg>
          </div>
          <Legend min="−1" max="+1" label="cosine(planted feature, decoder column)" />
          <figcaption className="small muted">With good recovery, each planted feature (row) has one bright cell. Rows smeared across many latents mean the SAE has mixed features together.</figcaption>
        </figure>
        {sweep.length > 0 && (
          <figure style={{ margin: '1.5rem 0 0' }}>
            <table className="data small">
              <caption className="small muted" style={{ captionSide: 'top', textAlign: 'left', paddingBottom: '.4rem' }}>λ sweep (ReLU + L1, seed {seed}, {TOTAL} steps each). Measured live in your browser.</caption>
              <thead><tr><th>λ</th><th>variance unexplained</th><th>L0</th><th>MMCS</th></tr></thead>
              <tbody>{sweep.map((p) => <tr key={p.l1}><td>{p.l1}</td><td>{p.fvu.toFixed(3)}</td><td>{p.l0.toFixed(2)}</td><td>{p.mmcs.toFixed(3)}</td></tr>)}</tbody>
            </table>
          </figure>
        )}
      </div>
    </div>
  );
}
