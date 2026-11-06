// Small, dependency-free numerics shared by the demos. Deterministic given a seed.

/** mulberry32: fast seeded PRNG with good statistical quality for demos. */
export function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Standard normal via Box–Muller. */
export function gauss(r: () => number) {
  const u = Math.max(r(), 1e-12), v = r();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/** Adam optimiser over a flat Float64Array of parameters. */
export class Adam {
  m: Float64Array; v: Float64Array; t = 0;
  constructor(n: number, public lr = 1e-2, public b1 = 0.9, public b2 = 0.999, public eps = 1e-8) {
    this.m = new Float64Array(n); this.v = new Float64Array(n);
  }
  step(p: Float64Array, g: Float64Array) {
    this.t++;
    const { b1, b2, lr, eps } = this;
    const c1 = 1 - b1 ** this.t, c2 = 1 - b2 ** this.t;
    for (let i = 0; i < p.length; i++) {
      this.m[i] = b1 * this.m[i] + (1 - b1) * g[i];
      this.v[i] = b2 * this.v[i] + (1 - b2) * g[i] * g[i];
      p[i] -= (lr * (this.m[i] / c1)) / (Math.sqrt(this.v[i] / c2) + eps);
    }
  }
}
