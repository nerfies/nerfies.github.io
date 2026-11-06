// Every URL and anchor ever published (src/data/published-urls.json) must keep working:
// directly, through a static redirect page (src/data/redirects.json → pages), or through an
// anchor alias (→ anchors). Run after `npm run build`.
import { describe, expect, test } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const DIST = 'dist';
const built = existsSync(join(DIST, 'index.html'));
const registry = JSON.parse(readFileSync('src/data/published-urls.json', 'utf8')).pages as Record<string, string[]>;
const redirects = JSON.parse(readFileSync('src/data/redirects.json', 'utf8'));
const withheld: string[] = JSON.parse(readFileSync('src/data/withheld.json', 'utf8')).chapters;
const manifest = JSON.parse(readFileSync('src/generated/manifest.json', 'utf8'));
const html = (path: string) => readFileSync(join(DIST, path, 'index.html'), 'utf8');
const BASE = '/mi_survey/';

/** Follow redirect pages; returns the final site-relative path. */
function finalPath(path: string): string {
  for (let i = 0; i < 5; i++) {
    const h = html(path);
    const m = h.match(/<meta name="mi-survey:redirect" content="([^"]+)"/);
    if (!m) return path;
    expect(m[1].startsWith(BASE), m[1]).toBe(true);
    path = m[1].slice(BASE.length);
  }
  throw new Error(`redirect loop at ${path}`);
}

describe.skipIf(!built)('published URLs keep working', () => {
  test('every registered page resolves', () => {
    const broken = Object.keys(registry).filter((p) => !existsSync(join(DIST, p, 'index.html')));
    expect(broken).toEqual([]);
  });

  test('every registered anchor resolves at its final location', () => {
    const broken: string[] = [];
    for (const [path, ids] of Object.entries(registry)) {
      if (!existsSync(join(DIST, path, 'index.html'))) continue;
      const end = finalPath(path);
      const page = html(end);
      const isWithheldPage = manifest.provenance.status !== 'final' && withheld.some((w) => end === `handbook/${w}/`);
      for (const id of ids) {
        if (page.includes(` id="${id}"`)) continue;
        const alias = redirects.anchors[`${path}#${id}`] ?? redirects.anchors[`${end}#${id}`];
        if (alias) {
          const [p, a] = alias.split('#');
          if (existsSync(join(DIST, p, 'index.html')) && html(p).includes(` id="${a}"`)) continue;
        }
        if (isWithheldPage) continue; // the page loads; its anchors return with the final manuscript
        broken.push(`${path}#${id}`);
      }
    }
    expect(broken.slice(0, 30)).toEqual([]);
  });

  test('redirect pages forward, keep the anchor, and are not indexed', () => {
    for (const [from, to] of Object.entries(redirects.pages as Record<string, string>)) {
      const h = html(from);
      expect(h, from).toContain(`<meta name="mi-survey:redirect" content="${BASE}${to}"`);
      expect(h, from).toContain('<meta name="robots" content="noindex"');
      expect(h, from).toMatch(/location\.replace\(/);
      expect(h, from).toContain(`http-equiv="refresh"`);
      expect(existsSync(join(DIST, to, 'index.html')), `${from} → ${to}`).toBe(true);
    }
  });

  test('every current chapter, method and demo page is in the registry', () => {
    // Forces a registry update (scripts/urls/snapshot_urls.py --merge) when new pages are published,
    // so they are protected from then on.
    const current = [
      ...manifest.toc.map((c: any) => `handbook/${c.slug}/`),
      ...JSON.parse(readFileSync('src/data/methods.json', 'utf8')).methods.map((m: any) => `methods/${m.id}/`),
      'demos/superposition/', 'demos/sae/', 'demos/patching/',
    ];
    expect(current.filter((p) => !(p in registry))).toEqual([]);
  });
});
