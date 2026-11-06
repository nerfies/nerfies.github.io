// Checks the built site (run after `npm run build`): internal links and anchors
// resolve, assets exist, maths rendered, nothing private leaked.
import { describe, expect, test } from 'vitest';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { join } from 'node:path';

const DIST = 'dist';
const BASE = `${(process.env.SITE_BASE ?? '/mechinterp-safety').replace(/\/$/, '')}/`;
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
  test('withheld draft chapters leak nowhere in the deployable output', () => {
    // Scans every deployable file (HTML, JS, JSON, XML, the decompressed search index) for any
    // sentence, heading or element id of a withheld chapter, using the hashes the ingest step
    // writes (src/generated/withheld-fingerprints.json), so the check also runs in CI, where the
    // withheld text itself does not exist.
    const manifest = JSON.parse(readFileSync('src/generated/manifest.json', 'utf8'));
    if (manifest.provenance.status === 'final' || process.env.PUBLIC_SHOW_ALL === '1') return;
    const fp = JSON.parse(readFileSync('src/generated/withheld-fingerprints.json', 'utf8')).chapters as
      Record<string, { sentences: string[]; headings: string[]; ids: string[] }>;
    const withheld: string[] = JSON.parse(readFileSync('src/data/withheld.json', 'utf8')).chapters;
    expect(Object.keys(fp).sort()).toEqual([...withheld].sort());
    const h = (x: string) => createHash('sha256').update(x.replace(/\s+/g, ' ').trim().toLowerCase()).digest('hex').slice(0, 24);
    const ent = (x: string) => x.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
    const files = walk(DIST).filter((f) => /\.(html|js|mjs|json|xml|txt|css|pf_fragment|pf_meta|pf_index)$/.test(f));
    const seen = { sentences: new Set<string>(), headings: new Set<string>(), ids: new Set<string>() };
    for (const f of files) {
      let t = /\.pf_/.test(f) ? gunzipSync(readFileSync(f)).toString('utf8') : readFileSync(f, 'utf8');
      for (const m of t.matchAll(/\sid="([^"]+)"|#([A-Za-z][\w:.-]*)/g)) seen.ids.add(h(m[1] ?? m[2]));
      const plain = ent(t.replace(/<\/(p|li|h\d|tr|figcaption|caption|a|summary)>/g, '\n').replace(/<[^>]+>/g, ' ')).replace(/\\n/g, '\n');
      // every 10-word sequence, so text embedded in other content or cut mid-sentence is still found
      const words = plain.toLowerCase().match(/[a-z0-9]+/g) ?? [];
      for (let i = 0; i + 10 <= words.length; i++) seen.sentences.add(h(words.slice(i, i + 10).join(' ')));
      for (const x of plain.split(/(?<=[.!?])\s+|\n|"/)) {
        const n = x.replace(/\s+/g, ' ').trim();
        if (n.length >= 40) seen.sentences.add(h(n));
        if (n.length >= 4) { seen.headings.add(h(n.replace(/^[§\dA-Z.]+\s+/, ''))); seen.headings.add(h(n)); }
      }
    }
    const leaks: string[] = [];
    for (const [ch, p] of Object.entries(fp)) {
      for (const k of ['sentences', 'headings', 'ids'] as const) {
        const n = p[k].filter((x) => seen[k].has(x)).length;
        if (n) leaks.push(`${ch}: ${n} ${k}`);
      }
    }
    expect(leaks).toEqual([]);
  });
  test('draft pages follow the indexing policy; public pages stay indexable', () => {
    const manifest = JSON.parse(readFileSync('src/generated/manifest.json', 'utf8'));
    const policy = JSON.parse(readFileSync('src/data/publication.json', 'utf8'));
    const noindex = (x: string) => x.includes('<meta name="robots" content="noindex"');
    for (const [p, x] of read) {
      if (p.includes('pagefind')) continue;
      if (x.includes('class="draft-banner"') && manifest.provenance.status !== 'final' && !policy.indexDraftPages) expect(noindex(x), p).toBe(true);
    }
    for (const p of ['index.html', 'demos/index.html', 'demos/patching/index.html', 'notebooks/index.html']) {
      expect(noindex(read.get(join(DIST, p)) ?? ''), p).toBe(false);
    }
  });
  test('no raw TeX visible in page text', () => {
    const bad: string[] = [];
    for (const [p, x] of read) {
      if (p.includes('pagefind')) continue;
      const text = x.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>|<code[\s\S]*?<\/code>|<pre[\s\S]*?<\/pre>/g, '')
        .replace(/<span class="katex">[\s\S]*?<\/math><\/span>/g, '').replace(/<annotation[\s\S]*?<\/annotation>/g, '')
        .replace(/<[^>]+>/g, ' ');
      for (const m of text.matchAll(/\\(?:[a-zA-Z]{2,})(?:\{|\b)/g)) bad.push(`${p}: …${text.slice(Math.max(0, m.index! - 40), m.index! + 40).replace(/\s+/g, ' ')}…`);
    }
    expect(bad.slice(0, 20)).toEqual([]);
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
