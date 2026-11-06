// Toy model of superposition (Elhage et al., 2022, "Toy Models of Superposition"):
//   h = W x,   x' = ReLU(Wᵀ h + b),   L = E[ Σ_i I_i (x_i − x'_i)² ]
// x_i = 0 with probability S (sparsity), else Uniform[0, 1]. W is m×n (m < n).
import { Adam, gauss, rng } from './core';

export interface ToyConfig { n: number; m: number; sparsity: number; importanceDecay: number; seed: number; lr?: number; batch?: number }

export class ToyModel {
  W: Float64Array; b: Float64Array; params: Float64Array; opt: Adam; r: () => number; I: Float64Array;
  step = 0; lastLoss = NaN;
  constructor(public cfg: ToyConfig) {
    const { n, m, seed } = cfg;
    this.r = rng(seed);
    this.params = new Float64Array(m * n + n);
    this.W = this.params.subarray(0, m * n); this.b = this.params.subarray(m * n);
    const s = Math.sqrt(2 / (m + n));
    for (let i = 0; i < m * n; i++) this.W[i] = gauss(this.r) * s; // Xavier normal
    this.opt = new Adam(this.params.length, cfg.lr ?? 1e-3);
    this.I = Float64Array.from({ length: n }, (_, i) => cfg.importanceDecay ** i);
  }
  /** W[k, i] = weight from feature i to hidden k */
  w(k: number, i: number) { return this.W[k * this.cfg.n + i]; }

  train(steps: number) {
    const { n, m, sparsity } = this.cfg, B = this.cfg.batch ?? 1024;
    const g = new Float64Array(this.params.length);
    const gW = g.subarray(0, m * n), gb = g.subarray(m * n);
    const x = new Float64Array(n), h = new Float64Array(m), d = new Float64Array(n);
    for (let s = 0; s < steps; s++) {
      g.fill(0);
      let loss = 0;
      for (let bi = 0; bi < B; bi++) {
        for (let i = 0; i < n; i++) x[i] = this.r() < sparsity ? 0 : this.r();
        for (let k = 0; k < m; k++) { let a = 0; for (let i = 0; i < n; i++) a += this.W[k * n + i] * x[i]; h[k] = a; }
        for (let i = 0; i < n; i++) {
          let pre = this.b[i]; for (let k = 0; k < m; k++) pre += this.W[k * n + i] * h[k];
          const out = pre > 0 ? pre : 0, err = out - x[i];
          loss += this.I[i] * err * err;
          d[i] = pre > 0 ? (2 * this.I[i] * err) / B : 0; // dL/dpre_i
        }
        // pre_i = b_i + Σ_k W[k,i] h_k,  h_k = Σ_j W[k,j] x_j
        for (let i = 0; i < n; i++) gb[i] += d[i];
        for (let k = 0; k < m; k++) {
          let dh = 0; for (let i = 0; i < n; i++) { dh += this.W[k * n + i] * d[i]; gW[k * n + i] += d[i] * h[k]; }
          for (let j = 0; j < n; j++) gW[k * n + j] += dh * x[j];
        }
      }
      this.opt.step(this.params, g);
      this.lastLoss = loss / B; this.step++;
    }
  }

  /** ‖W_i‖ for each feature: how strongly feature i is represented. */
  norms() { const { n, m } = this.cfg; return Array.from({ length: n }, (_, i) => { let s = 0; for (let k = 0; k < m; k++) s += this.w(k, i) ** 2; return Math.sqrt(s); }); }
  /** Superposition per feature: Σ_{j≠i} (Ŵ_i · W_j)²  (Elhage et al. 2022). */
  interference() {
    const { n, m } = this.cfg, nr = this.norms();
    return Array.from({ length: n }, (_, i) => {
      if (nr[i] < 1e-9) return 0;
      let s = 0;
      for (let j = 0; j < n; j++) { if (j === i) continue; let dot = 0; for (let k = 0; k < m; k++) dot += (this.w(k, i) / nr[i]) * this.w(k, j); s += dot * dot; }
      return s;
    });
  }
  gram() { const { n, m } = this.cfg; return Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => { let s = 0; for (let k = 0; k < m; k++) s += this.w(k, i) * this.w(k, j); return s; })); }
  /** Features with ‖W_i‖ > threshold count as represented. */
  represented(threshold = 0.5) { return this.norms().filter((x) => x > threshold).length; }
}
