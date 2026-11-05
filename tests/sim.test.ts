// The demo pages state these results. If a code change alters them, these fail
// and the page text must be updated with it.
import { describe, expect, test } from 'vitest';
import { ToyModel } from '../src/lib/sim/toy';
import { Sae } from '../src/lib/sim/sae';

const toy = (S: number) => { const t = new ToyModel({ n: 5, m: 2, sparsity: S, importanceDecay: 0.9, seed: 1, lr: 1e-2, batch: 512 }); t.train(1500); return t; };
const sae = (l1: number) => { const s = new Sae({ d: 8, nTrue: 16, dict: 32, p: 0.1, seed: 1, mode: 'l1', l1, k: 3 }); s.train(2000); return s.evaluate(); };

describe('toy model of superposition (demos/superposition)', () => {
  test('dense features: only 2 of 5 represented', () => expect(toy(0).represented()).toBe(2));
  test('S = 0.7: 4 of 5 represented', () => expect(toy(0.7).represented()).toBe(4));
  test('S = 0.9: all 5 represented (superposition)', () => expect(toy(0.9).represented()).toBe(5));
  test('deterministic for a fixed seed', () => expect(toy(0.9).norms()).toEqual(toy(0.9).norms()));
}, 60000);

describe('sparse autoencoder (demos/sae)', () => {
  test('λ = 0: near-perfect reconstruction, no planted features recovered', () => {
    const e = sae(0); expect(e.fvu).toBeLessThan(0.01); expect(e.recovered).toBe(0); expect(e.mmcs).toBeCloseTo(0.69, 1);
  });
  test('λ = 0.3: all 16 recovered, ~13% variance unexplained', () => {
    const e = sae(0.3); expect(e.recovered).toBe(16); expect(e.mmcs).toBeGreaterThan(0.96); expect(e.fvu).toBeCloseTo(0.13, 1);
  });
  test('λ = 1: reconstruction degrades to ~60% variance unexplained', () => {
    const e = sae(1); expect(e.fvu).toBeGreaterThan(0.5); expect(e.fvu).toBeLessThan(0.7);
  });
}, 120000);
