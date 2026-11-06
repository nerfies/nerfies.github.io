import { useEffect, useRef, useState } from 'react';
import { ToyModel } from '../../lib/sim/toy';
import { Bars, Heatmap, Legend } from './viz';

const N = 5, M = 2, TOTAL = 1500, CHUNK = 50;

export default function SuperpositionDemo() {
  const [sparsity, setSparsity] = useState(0.9);
  const [decay, setDecay] = useState(0.9);
  const [seed, setSeed] = useState(1);
  const [, force] = useState(0);
  const model = useRef<ToyModel | null>(null);
  const raf = useRef<number | null>(null);
  const [running, setRunning] = useState(false);

  function start() {
    if (raf.current) cancelAnimationFrame(raf.current);
    model.current = new ToyModel({ n: N, m: M, sparsity, importanceDecay: decay, seed, lr: 1e-2, batch: 512 });
    setRunning(true);
    const tick = () => {
      const m = model.current!;
      m.train(CHUNK); force((x) => x + 1);
      if (m.step < TOTAL) raf.current = requestAnimationFrame(tick); else setRunning(false);
    };
    raf.current = requestAnimationFrame(tick);
  }
  useEffect(() => { start(); return () => { if (raf.current) cancelAnimationFrame(raf.current); }; }, [sparsity, decay, seed]);

  const m = model.current;
  const norms = m?.norms() ?? Array(N).fill(0);
  const interf = m?.interference() ?? Array(N).fill(0);
  const gram = m?.gram() ?? [];
  const rep = m?.represented() ?? 0;
  const labels = Array.from({ length: N }, (_, i) => `f${i + 1}`);
  const R = 120, cx = 150, cy = 150, scale = R / 1.3;

  return (
    <div className="demo">
      <div className="controls card">
        <label><span>Sparsity S (probability a feature is zero)</span> <output>{sparsity.toFixed(2)}</output>
          <input type="range" min="0" max="0.99" step="0.01" value={sparsity} onChange={(e) => setSparsity(+e.target.value)} /></label>
        <label><span>Importance decay (I<sub>i</sub> = r<sup>i</sup>)</span> <output>{decay.toFixed(2)}</output>
          <input type="range" min="0.5" max="1" step="0.01" value={decay} onChange={(e) => setDecay(+e.target.value)} /></label>
        <div style={{ display: 'flex', gap: '.5rem', flexWrap: 'wrap' }}>
          <button className="btn" onClick={() => start()} disabled={running}>{running ? 'Training…' : 'Retrain'}</button>
          <button className="btn ghost" onClick={() => setSeed((s) => s + 1)}>New seed ({seed})</button>
        </div>
        <div className="small muted">Presets:{' '}
          <button className="chip" onClick={() => setSparsity(0)}>dense (S = 0)</button>{' '}
          <button className="chip" onClick={() => setSparsity(0.7)}>S = 0.7</button>{' '}
          <button className="chip" onClick={() => setSparsity(0.97)}>very sparse</button>
        </div>
        <div className="stat-row">
          <div className="stat"><b>{rep} / {N}</b><span>features represented</span></div>
          <div className="stat"><b>{M}</b><span>hidden dimensions</span></div>
          <div className="stat"><b>{m ? m.lastLoss.toFixed(4) : '–'}</b><span>loss</span></div>
          <div className="stat"><b>{m?.step ?? 0}</b><span>steps</span></div>
        </div>
        <p className="small muted" style={{ margin: 0 }}>{rep > M ? `${rep} features share ${M} dimensions. That is superposition.` : `With ${M} dimensions the model keeps only the ${rep} most important features.`}</p>
      </div>
      <div className="viz" aria-live="polite">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))', gap: '1rem' }}>
          <figure style={{ margin: 0 }}>
            <svg viewBox="0 0 300 300" role="img" aria-label={`Feature directions W_i in the 2-D hidden space. ${rep} of ${N} have norm above 0.5.`}>
              <circle cx={cx} cy={cy} r={scale} fill="none" stroke="var(--rule)" />
              <line x1={cx - R - 10} x2={cx + R + 10} y1={cy} y2={cy} stroke="var(--rule)" />
              <line y1={cy - R - 10} y2={cy + R + 10} x1={cx} x2={cx} stroke="var(--rule)" />
              {m && labels.map((l, i) => {
                const x = m.w(0, i), y = m.w(1, i);
                const op = Math.min(1, 0.25 + norms[i]);
                return (
                  <g key={l} opacity={op}>
                    <line x1={cx} y1={cy} x2={cx + x * scale} y2={cy - y * scale} stroke={`color-mix(in srgb, var(--pos) ${Math.round(100 * decay ** i)}%, var(--ink-3))`} strokeWidth="2.5" markerEnd="url(#arr)" />
                    <text x={cx + x * scale * 1.12} y={cy - y * scale * 1.12 + 4} fontSize="11" textAnchor="middle">{l}</text>
                  </g>
                );
              })}
              <defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-2)" /></marker></defs>
            </svg>
            <figcaption className="small muted">Columns W<sub>i</sub> of the 2 × {N} weight matrix: how each feature is embedded in the hidden space. Darker means more important. The unit circle is shown for reference.</figcaption>
          </figure>
          <figure style={{ margin: 0 }}>
            {gram.length > 0 && <Heatmap data={gram} rowLabels={labels} colLabels={labels} scale={1.2} cell={30} title="Gram matrix W transpose W" />}
            <Legend min="−1" max="+1" label="WᵀW" />
            <figcaption className="small muted">W<sup>T</sup>W. Off-diagonal entries are interference between features.</figcaption>
          </figure>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))', gap: '1rem', marginTop: '1rem' }}>
          <figure style={{ margin: 0 }}><Bars values={norms} labels={labels} max={1.5} title="Norm of each feature's embedding" threshold={0.5} />
            <figcaption className="small muted">‖W<sub>i</sub>‖. Above the dashed line (0.5) a feature counts as represented.</figcaption></figure>
          <figure style={{ margin: 0 }}><Bars values={interf} labels={labels} max={Math.max(1, ...interf)} title="Superposition per feature" color="var(--gold)" />
            <figcaption className="small muted">Σ<sub>j≠i</sub>(Ŵ<sub>i</sub>·W<sub>j</sub>)²: how much feature i shares its direction with the others.</figcaption></figure>
        </div>
      </div>
    </div>
  );
}
