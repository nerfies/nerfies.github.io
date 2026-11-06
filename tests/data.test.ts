// Scientific-integrity checks on the curated data: every quoted excerpt must
// appear verbatim in the ingested manuscript, and every link must resolve.
import { describe, expect, test } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import methods from '../src/data/methods.json';
import framework from '../src/data/framework.json';
import notebooks from '../src/data/notebooks.json';
import links from '../src/data/links.json';
import patching from '../src/data/experiments/patching_gpt2_ioi.json';
import manifest from '../src/generated/manifest.json';

const dir = 'src/generated/chapters/';
const html = readdirSync(dir).map((f) => readFileSync(dir + f, 'utf8')).join('\n');
const unescape = (s: string) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
const norm = (s: string) => s.replace(/\s+/g, ' ').trim();
// plain text built exactly as the extraction dumps were (tags stripped, maths kept as raw TeX)
const plain = norm(unescape(html
  .replace(/<\/(p|li|h\d|tr|figcaption|caption)>/g, '\n')
  .replace(/<[^>]+>/g, '')));
const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));

const NON_EXCERPT = new Set(['id', 'name', 'family', 'title', 'subtitle', 'heading', 'step', 'methods', 'methods_used', 'metrics_named', 'related_methods',
  'related_orientations', 'orientations', 'related', 'sections', 'mentioned_in', 'chapter_sections', 'formulas_tex', 'public_name', 'draft_name',
  'draft_sections', 'status', 'source', 'gaps', 'table_id', 'caption', 'columns', 'rows', 'table_row', 'section', 'source_chapter', 'motivation_section',
  'protocol_section', 'framework_limitations_section', 'decision_framework_section', 'tensions_section', 'comparison_table', 'method_guidance',
  'risk_taxonomy', 'evidence_key', 'items', 'groups']);
function* excerpts(o: any, key = ''): Generator<[string, string]> {
  if (NON_EXCERPT.has(key)) return;
  if (typeof o === 'string') { yield [key, o]; return; }
  if (Array.isArray(o)) { for (const x of o) yield* excerpts(x, key); return; }
  if (o && typeof o === 'object') for (const [k, v] of Object.entries(o)) yield* excerpts(v, k);
}
function* sectionRefs(o: any, key = ''): Generator<string> {
  if (Array.isArray(o)) { for (const x of o) yield* sectionRefs(x, key); return; }
  if (typeof o === 'string' && ['sections', 'mentioned_in', 'chapter_sections', 'section', 'protocol_section', 'framework_limitations_section',
    'decision_framework_section', 'tensions_section', 'motivation_section'].includes(key)) { yield o; return; }
  if (o && typeof o === 'object') for (const [k, v] of Object.entries(o)) yield* sectionRefs(v, k);
}
const stripCites = (s: string) => norm(s);

describe('curated excerpts are verbatim', () => {
  for (const [name, data] of [['methods.json', { m: (methods as any).methods, h: (methods as any).hypotheses }], ['framework.json', { ...(framework as any), gaps: undefined, source: undefined }]] as const) {
    test(name, () => {
      const missing = [...excerpts(data)].filter(([, t]) => t.length > 25 && !plain.includes(stripCites(t)));
      expect(missing.map(([k, t]) => `${k}: ${t.slice(0, 90)}`)).toEqual([]);
    });
  }
});

describe('section references resolve', () => {
  test('all section ids used by curated data exist', () => {
    const refs = [...sectionRefs(methods), ...sectionRefs({ ...(framework as any), gaps: undefined })].filter((s) => !s.includes(' ('));
    expect(refs.filter((r) => !ids.has(r))).toEqual([]);
  });
  test('method cross-links point at existing methods', () => {
    const all = new Set((methods as any).methods.map((m: any) => m.id));
    const bad = (methods as any).methods.flatMap((m: any) => (m.related ?? []).filter((r: string) => !all.has(r)).map((r: string) => `${m.id}→${r}`));
    expect(bad).toEqual([]);
  });
  test('editorial links reference real notebooks and methods', () => {
    const paths = new Set((notebooks as any).notebooks.map((n: any) => n.path));
    const ms = new Set((methods as any).methods.map((m: any) => m.id));
    const hs = new Set((methods as any).hypotheses.map((m: any) => m.id));
    for (const [p, l] of Object.entries((links as any).notebooks)) {
      expect(paths.has(p), p).toBe(true);
      for (const id of (l as any).methods ?? []) expect(ms.has(id), id).toBe(true);
      for (const id of (l as any).hypotheses ?? []) expect(hs.has(id), id).toBe(true);
    }
    for (const d of Object.values((links as any).demos) as any[]) if (d.notebook) expect(paths.has(d.notebook), d.notebook).toBe(true);
  });
});

describe('manuscript ingestion', () => {
  test('no editorial comment markers leak into the text', () => {
    expect(html).not.toMatch(/\[(Fazl|Hunar|Abir|Mike|Hassan|Stella|Riley|Naomi|Mor|Neel):/);
    expect(html).not.toMatch(/TODO:/);
  });
  test('every chapter in the manifest has a fragment', () => {
    const files = new Set(readdirSync(dir).map((f) => f.replace('.html', '')));
    expect((manifest as any).toc.filter((c: any) => !files.has(c.slug))).toEqual([]);
  });
  test('every numbered figure and table got its PDF number', () => {
    const labels = Object.entries((manifest as any).labels).filter(([k]) => /^(fig|tab):/.test(k) && ids.has(k));
    const missing = labels.filter(([k]) => !new RegExp(`id="${k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"[\\s\\S]{0,4000}?class="capnum"`).test(html));
    expect(missing.map(([k]) => k)).toEqual([]);
  });
  test('equation numbers are sequential', () => {
    const tags = [...html.matchAll(/\\tag\{(\d+)\}/g)].map((m) => +m[1]);
    expect(tags.sort((a, b) => a - b)).toEqual(tags.map((_, i) => i + 1));
  });
});

describe('patching experiment output', () => {
  test('stored correlation matches the stored matrices', () => {
    const a = patching.head_z_recovery.flat(), b = patching.head_attribution_patching.flat();
    const mean = (v: number[]) => v.reduce((x, y) => x + y, 0) / v.length;
    const ma = mean(a), mb = mean(b);
    const cov = a.reduce((s, x, i) => s + (x - ma) * (b[i] - mb), 0);
    const r = cov / Math.sqrt(a.reduce((s, x) => s + (x - ma) ** 2, 0) * b.reduce((s, x) => s + (x - mb) ** 2, 0));
    expect(r).toBeCloseTo(patching.pearson_activation_vs_attribution, 2);
  });
  test('sanity: patching the full residual stream at the last position in the last layer restores the clean run', () => {
    const last = patching.resid_pre_recovery[patching.resid_pre_recovery.length - 1];
    expect(last[last.length - 1]).toBeGreaterThan(0.95);
    expect(patching.clean_accuracy).toBe(1);
  });
});
