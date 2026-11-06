// Checks the built site (run after `npm run build`): internal links and anchors
// resolve, assets exist, maths rendered, nothing private leaked.
import { describe, expect, test } from 'vitest';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const DIST = 'dist';
const BASE = '/mi_survey/';
const built = existsSync(DIST);
const walk = (d: string): string[] => readdirSync(d).flatMap((f) => { const p = join(d, f); return statSync(p).isDirectory() ? walk(p) : [p]; });
const pages = built ? walk(DIST).filter((f) => f.endsWith('.html')) : [];
const read = new Map(pages.map((p) => [p, readFileSync(p, 'utf8')]));
const idsOf = (h: string) => new Set([...h.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
const idCache = new Map<string, Set<string>>();

function resolve(href: string, from: string): { file: string; hash: string } | null {
  const [path, hash = ''] = href.split('#');
  if (!path) return { file: from, hash };
  if (!path.startsWith(BASE)) return null;
  let rel = decodeURIComponent(path.slice(BASE.length).split('?')[0]);
  let file = join(DIST, rel);
  if (rel === '' || rel.endsWith('/')) file = join(DIST, rel, 'index.html');
  return { file, hash };
}

describe.skipIf(!built)('built site', () => {
  test('every internal link and anchor resolves', () => {
    const broken: string[] = [];
    for (const [p, h] of read) {
      for (const m of h.matchAll(/\s(?:href|src)="([^"]+)"/g)) {
        const href = m[1].replace(/&amp;/g, '&');
        if (/^(https?:|mailto:|data:|javascript:)/.test(href)) continue;
        const r = resolve(href, p);
        if (!r) continue;
        if (!existsSync(r.file)) { broken.push(`${p} → ${href}`); continue; }
        if (r.hash && r.file.endsWith('.html') && !r.hash.startsWith('page=')) {
          if (!idCache.has(r.file)) idCache.set(r.file, idsOf(read.get(r.file) ?? readFileSync(r.file, 'utf8')));
          if (!idCache.get(r.file)!.has(decodeURIComponent(r.hash))) broken.push(`${p} → ${href} (missing anchor)`);
        }
      }
    }
    expect(broken.slice(0, 40)).toEqual([]);
  });
  test('all maths rendered', () => {
    const bad = [...read].filter(([, h]) => h.includes('class="math-error"')).map(([p]) => p);
    expect(bad).toEqual([]);
  });
  test('no reviewer comments or draft PDF published', () => {
    for (const [p, h] of read) expect(h, p).not.toMatch(/\[(Fazl|Hunar|Abir|Mike|Hassan|Stella|Riley):/);
    const manifest = JSON.parse(readFileSync('src/generated/manifest.json', 'utf8'));
    if (manifest.provenance.status !== 'final') expect(existsSync(join(DIST, 'survey.pdf'))).toBe(false);
  });
  test('public draft builds contain no manuscript text', () => {
    const manifest = JSON.parse(readFileSync('src/generated/manifest.json', 'utf8'));
    if (manifest.provenance.status === 'final' || process.env.PUBLIC_HIDE_DRAFT !== '1') return;
    const leaks = [...read].filter(([, h]) => /class="secnum"|data-cite=|class="csl-entry|blockquote class="excerpt"|Preview build\./.test(h)).map(([p]) => p);
    expect(leaks).toEqual([]);
    expect(existsSync(join(DIST, 'handbook', manifest.toc[0].slug))).toBe(false);
  });
  test('every page has a title, description and a single h1', () => {
    for (const [p, h] of read) {
      if (p.includes('pagefind')) continue;
      expect(h, p).toMatch(/<title>[^<]+<\/title>/);
      expect(h, p).toMatch(/<meta name="description" content="[^"]+"/);
      expect((h.match(/<h1[\s>]/g) ?? []).length, p).toBe(1);
    }
  });
  test('images have alt text', () => {
    const bad: string[] = [];
    for (const [p, h] of read) for (const m of h.matchAll(/<img\b[^>]*>/g)) if (!/\salt="[^"]*"/.test(m[0])) bad.push(`${p}: ${m[0].slice(0, 80)}`);
    expect(bad.slice(0, 20)).toEqual([]);
  });
});
