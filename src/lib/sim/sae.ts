// Sparse autoencoder trained on synthetic data with KNOWN ground-truth features,
// so we can measure how well the dictionary recovers them.
//   data:  x = Σ_i a_i g_i,  g_i unit vectors in R^d (n_true > d: superposition),
//          a_i = 0 w.p. 1 − p, else Uniform[0,1]
//   SAE:   f = ReLU(W_e (x − b_d) + b_e),  x̂ = W_d f + b_d
//   loss:  ‖x − x̂‖² + λ ‖f‖₁  (decoder columns renormalised to unit norm), or TopK(k) activation
import { Adam, gauss, rng } from './core';

export interface SaeConfig {
  d: number; nTrue: number; dict: number; p: number; seed: number;
  mode: 'l1' | 'topk'; l1: number; k: number; lr?: number; batch?: number;
}

export function makeFeatures(d: number, n: number, seed: number) {
  const r = rng(seed * 7919 + 1);
  return Array.from({ length: n }, () => { const v = Array.from({ length: d }, () => gauss(r)); const s = Math.hypot(...v); return v.map((x) => x / s); });
}

export class Sae {
  G: number[][]; r: () => number; dataR: () => number;
  P: Float64Array; We: Float64Array; be: Float64Array; Wd: Float64Array; bd: Float64Array; opt: Adam; step = 0;
  last = { loss: NaN, mse: NaN, l0: NaN };
  constructor(public cfg: SaeConfig) {
    const { d, dict, nTrue, seed } = cfg;
    this.G = makeFeatures(d, nTrue, seed);
    this.r = rng(seed); this.dataR = rng(seed + 1);
    this.P = new Float64Array(dict * d * 2 + dict + d);
    let o = 0;
    this.We = this.P.subarray(o, (o += dict * d)); this.be = this.P.subarray(o, (o += dict));
    this.Wd = this.P.subarray(o, (o += dict * d)); this.bd = this.P.subarray(o, (o += d));
    // decoder: random unit columns; encoder initialised to decoder transpose (common practice)
    for (let j = 0; j < dict; j++) {
      const v = Array.from({ length: d }, () => gauss(this.r)); const s = Math.hypot(...v);
      for (let i = 0; i < d; i++) { this.Wd[i * dict + j] = v[i] / s; this.We[j * d + i] = v[i] / s; }
    }
    this.opt = new Adam(this.P.length, cfg.lr ?? 3e-3);
  }
  sample(x: Float64Array) {
    const { d, nTrue, p } = this.cfg; x.fill(0);
    for (let i = 0; i < nTrue; i++) if (this.dataR() < p) { const a = this.dataR(); for (let t = 0; t < d; t++) x[t] += a * this.G[i][t]; }
  }
  encode(x: Float64Array, pre: Float64Array, f: Float64Array) {
    const { d, dict, mode, k } = this.cfg;
    for (let j = 0; j < dict; j++) { let a = this.be[j]; for (let i = 0; i < d; i++) a += this.We[j * d + i] * (x[i] - this.bd[i]); pre[j] = a; f[j] = a > 0 ? a : 0; }
    if (mode === 'topk') {
      const thr = [...f].sort((a, b) => b - a)[Math.min(k, dict) - 1] ?? 0;
      let kept = 0;
      for (let j = 0; j < dict; j++) { if (f[j] >= thr && f[j] > 0 && kept < k) kept++; else f[j] = 0; }
    }
  }
  train(steps: number) {
    const { d, dict, mode, l1 } = this.cfg, B = this.cfg.batch ?? 256;
    const g = new Float64Array(this.P.length);
    let o = 0;
    const gWe = g.subarray(o, (o += dict * d)), gbe = g.subarray(o, (o += dict)), gWd = g.subarray(o, (o += dict * d)), gbd = g.subarray(o, (o += d));
    const x = new Float64Array(d), pre = new Float64Array(dict), f = new Float64Array(dict), xh = new Float64Array(d), e = new Float64Array(d), df = new Float64Array(dict);
    for (let s = 0; s < steps; s++) {
      g.fill(0); let loss = 0, mse = 0, l0 = 0;
      for (let b = 0; b < B; b++) {
        this.sample(x); this.encode(x, pre, f);
        for (let i = 0; i < d; i++) { let a = this.bd[i]; for (let j = 0; j < dict; j++) a += this.Wd[i * dict + j] * f[j]; xh[i] = a; e[i] = (2 * (a - x[i])) / B; mse += (a - x[i]) ** 2; }
        for (let j = 0; j < dict; j++) {
          if (f[j] > 0) l0++;
          let gf = 0; for (let i = 0; i < d; i++) { gf += this.Wd[i * dict + j] * e[i]; gWd[i * dict + j] += e[i] * f[j]; }
          if (mode === 'l1') { gf += f[j] > 0 ? l1 / B : 0; loss += l1 * f[j]; }
          df[j] = f[j] > 0 ? gf : 0;
          gbe[j] += df[j];
          for (let i = 0; i < d; i++) gWe[j * d + i] += df[j] * (x[i] - this.bd[i]);
        }
        for (let i = 0; i < d; i++) { gbd[i] += e[i]; let a = 0; for (let j = 0; j < dict; j++) a += this.We[j * d + i] * df[j]; gbd[i] -= a; }
      }
      this.opt.step(this.P, g);
      // keep decoder columns at unit norm so the L1 penalty can't be dodged by shrinking f
      for (let j = 0; j < dict; j++) { let s = 0; for (let i = 0; i < d; i++) s += this.Wd[i * dict + j] ** 2; s = Math.sqrt(s) || 1; for (let i = 0; i < d; i++) this.Wd[i * dict + j] /= s; }
      this.step++;
      this.last = { loss: (loss + mse) / B, mse: mse / B, l0: l0 / B };
    }
  }
  /** cos(true feature i, decoder column j) */
  cosines() {
    const { d, dict } = this.cfg;
    return this.G.map((gv) => Array.from({ length: dict }, (_, j) => { let s = 0; for (let i = 0; i < d; i++) s += gv[i] * this.Wd[i * dict + j]; return s; }));
  }
  /** Evaluate on fresh samples: fraction of variance unexplained, mean L0, dead latents. */
  evaluate(nSamples = 2000) {
    const { d, dict } = this.cfg, r0 = this.dataR;
    this.dataR = rng(this.cfg.seed + 999);
    const x = new Float64Array(d), pre = new Float64Array(dict), f = new Float64Array(dict);
    let se = 0, l0 = 0; const alive = new Uint8Array(dict); const xs: number[][] = [];
    for (let s = 0; s < nSamples; s++) {
      this.sample(x); this.encode(x, pre, f); xs.push([...x]);
      for (let i = 0; i < d; i++) { let a = this.bd[i]; for (let j = 0; j < dict; j++) a += this.Wd[i * dict + j] * f[j]; se += (a - x[i]) ** 2; }
      for (let j = 0; j < dict; j++) if (f[j] > 0) { l0++; alive[j] = 1; }
    }
    this.dataR = r0;
    const mean = Array.from({ length: d }, (_, i) => xs.reduce((a, v) => a + v[i], 0) / nSamples);
    const tv = xs.reduce((a, v) => a + v.reduce((b, xi, i) => b + (xi - mean[i]) ** 2, 0), 0);
    const C = this.cosines();
    const maxCos = C.map((row) => Math.max(...row));
    return {
      fvu: se / tv, l0: l0 / nSamples, dead: dict - alive.reduce((a, b) => a + b, 0),
      mmcs: maxCos.reduce((a, b) => a + b, 0) / maxCos.length,
      recovered: maxCos.filter((c) => c > 0.9).length, maxCos,
    };
  }
}
