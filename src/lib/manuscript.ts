// Loads the ingested manuscript (src/generated, produced by scripts/ingest/ingest.py)
// and renders maths with KaTeX at build time, so pages ship no maths JavaScript.
import katex from 'katex';
import manifestJson from '../generated/manifest.json';
import { base, SITE } from './site';
import withheldJson from '../data/withheld.json';

export interface TocSection { id: string; num: string | null; title: string; level: number; page: string | null }
export interface Chapter {
  slug: string; num: string; title: string; appendix: boolean; page: string | null;
  sections: TocSection[]; words: number; withheld?: boolean;
}
export interface Reference { key: string; text: string; tier: string | null }
export interface Manifest {
  provenance: { status: string; source_commit: string | null; source_commit_date: string | null;
    main_tex_sha256: string; pdf_included: boolean; generated: string };
  toc: Chapter[];
  labels: Record<string, { num: string; page: string; kind: string; chapter: string | null }>;
  cite_tiers: Record<string, string>;
  references: Reference[];
  audit: Record<string, unknown>;
}

export const manifest = manifestJson as unknown as Manifest;
export const chapters = manifest.toc;
export const isDraft = manifest.provenance.status !== 'final';
/** Opt-in: PUBLIC_HIDE_DRAFT=1 hides every page built from a draft manuscript. */
export const draftHidden = isDraft && import.meta.env.PUBLIC_HIDE_DRAFT === '1';
/** Draft chapters never published (src/data/withheld.json). PUBLIC_SHOW_ALL=1 shows them for local review. */
export const withheld = new Set<string>(isDraft && import.meta.env.PUBLIC_SHOW_ALL !== '1' ? (withheldJson as any).chapters : []);

const raw = import.meta.glob('../generated/chapters/*.html', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;
// Withheld draft chapters live in a gitignored folder. It exists only on a machine that ran the ingest
// step, and is read only for PUBLIC_SHOW_ALL=1 previews or to scrub curated data.
const privateRaw = import.meta.glob('../generated/withheld/*.html', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;
const findRaw = (slug: string) => {
  const k = Object.keys(raw).find((x) => x.endsWith(`/${slug}.html`));
  if (k) return raw[k];
  const pk = withheld.has(slug) ? undefined : Object.keys(privateRaw).find((x) => x.endsWith(`/${slug}.html`));
  return pk ? privateRaw[pk] : undefined;
};
/** True when this build can show the chapter's text. */
export const hasChapterText = (slug: string) => !withheld.has(slug) && findRaw(slug) !== undefined;
const refsRaw = import.meta.glob('../generated/references.html', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;

const unescape = (s: string) =>
  s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');

export function renderMath(html: string): string {
  return html.replace(/<span class="math (inline|display)">([\s\S]*?)<\/span>/g, (_m, mode: string, tex: string) => {
    let src = unescape(tex).trim();
    // pandoc may keep delimiters; strip them
    src = src.replace(/^\\\(|\\\)$/g, '').replace(/^\\\[|\\\]$/g, '');
    try {
      const out = katex.renderToString(src, {
        displayMode: mode === 'display', throwOnError: true, strict: 'ignore', trust: false,
        macros: { '\\R': '\\mathbb{R}', '\\E': '\\mathbb{E}', '\\mathbbm': '\\mathbb' },
      });
      return mode === 'display' ? `<div class="math-display">${out}</div>` : out;
    } catch (e) {
      // Keep the source visible rather than silently dropping maths; tests flag these.
      return `<code class="math-error" title="${String((e as Error).message).replace(/"/g, '&quot;')}">${tex}</code>`;
    }
  });
}

export function withBase(html: string): string {
  return html.replaceAll('@@BASE@@', base);
}

export function chapterHtml(slug: string): string {
  const h = findRaw(slug);
  if (h === undefined) throw new Error(`chapter ${slug} not found`);
  return withBase(renderMath(h));
}

// Inline maths as written in the manuscript. Curated excerpts are plain text (the extraction drops the
// maths markup), so any of these TeX strings found in an excerpt is rendered with KaTeX at build time.
const MATH_TEX = [...new Set(Object.values(raw).flatMap((h) =>
  [...h.matchAll(/<span class="math inline">([\s\S]*?)<\/span>/g)].map((m) => unescape(m[1]).replace(/^\\\(|\\\)$/g, '').replace(/\s+/g, ' ').trim())))]
  .filter((t) => /[\\^_{}]/.test(t) && t.length > 1)
  .sort((a, b) => b.length - a.length);
const MATH_RE = MATH_TEX.length
  ? new RegExp(MATH_TEX.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'g') : null;
const escHtml = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const inlineMath = (tex: string) => renderMath(`<span class="math inline">${escHtml(tex)}</span>`);
const reEsc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// Citations as natbib prints them in the chapters ("Rajamanoharan et al., 2024b", "Koh et al. (2020)"),
// mapped to their reference key. Excerpts are plain text, so a label found in one is linked like the
// chapter's own citation. Year-only anchors ("2019" in "Bau et al. (2019, 2020)") are ambiguous and
// skipped, as is any label that points at two different references.
const CITE_KEY = new Map<string, string | null>();
for (const h of Object.values(raw)) {
  for (const m of h.matchAll(/<a href="@@BASE@@references\/#ref-([^"]+)" class="cite[^"]*"[^>]*>([\s\S]*?)<\/a>/g)) {
    const label = unescape(m[2].replace(/<[^>]+>/g, '')).replace(/\s+/g, ' ').trim();
    if (!/\p{L}{2}/u.test(label)) continue;
    for (const l of new Set([label, label.replace(/’/g, "'")])) {  // some curated text uses straight apostrophes
      const prev = CITE_KEY.get(l);
      CITE_KEY.set(l, prev === undefined || prev === m[1] ? m[1] : null);
    }
  }
}
const CITE_LABELS = [...CITE_KEY].filter(([, k]) => k).map(([l]) => escHtml(l)).sort((a, b) => b.length - a.length);
// Cross-references to numbered figures, tables and sections, resolved through the LaTeX labels.
const XREF = new Map<string, string>();
for (const [id, l] of Object.entries(manifest.labels)) {
  const kinds = l.kind === 'figure' ? ['Figure'] : l.kind === 'table' ? ['Table']
    : /^(sub)*section$|^appendix$/.test(l.kind) ? (/^[A-Z]/.test(l.num) ? ['Appendix', 'Section'] : ['Section']) : [];
  const href = l.chapter ? (withheld.has(l.chapter) ? null : `${base}handbook/${l.chapter}/#${id}`)
    : id === 'fig:simplified-taxonomy' ? `${base}#taxonomy` : null;  // the taxonomy sits on the homepage
  for (const kind of kinds) if (href && !XREF.has(`${kind} ${l.num}`)) XREF.set(`${kind} ${l.num}`, href);
}
const LINK_RE = new RegExp(
  `(?<![\\p{L}\\p{N}])(?:(${CITE_LABELS.map(reEsc).join('|') || '(?!)'})|(Figure|Table|Section|Appendix)\\s+([A-Z]?\\d*(?:\\.\\d+)*))(?![\\p{L}\\p{N}]|\\.\\d)`, 'gu');
/** Link citations and cross-references in already-escaped excerpt text. */
const linkRefs = (s: string) => s.replace(LINK_RE, (m, cite: string | undefined, kind: string, num: string) => {
  if (cite) {
    const key = CITE_KEY.get(unescape(cite))!;
    const tier = manifest.cite_tiers[key];
    return `<a href="${base}references/#ref-${key}" class="cite${tier ? ` cite-${tier}` : ''}" data-cite="${key}">${m}</a>`;
  }
  const href = XREF.get(`${kind} ${num}`);
  return href ? `<a href="${href}">${m}</a>` : m;
});

/** HTML for a verbatim excerpt: text escaped, the manuscript's inline maths rendered. */
export function excerptHtml(text: string): string {
  const out: string[] = [];
  let last = 0;
  const src = text.replace(/\\\((.+?)\\\)/g, '$1');
  if (MATH_RE) for (const m of src.matchAll(MATH_RE)) {
    out.push(linkRefs(escHtml(src.slice(last, m.index))), inlineMath(m[0]));
    last = m.index! + m[0].length;
  }
  out.push(linkRefs(escHtml(src.slice(last))));
  return out.join('');
}

export function referencesHtml(): string {
  const v = Object.values(refsRaw)[0] ?? '';
  return withBase(renderMath(v));
}

export function pdfHref(page: string | null | undefined): string | null {
  if (!page) return null;
  // Roman-numbered front matter pages are not addressable by number; skip them
  if (!/^\d+$/.test(page)) return null;
  // PDF viewers use physical page indices; the offset accounts for front matter.
  // Without a local copy, link the published arXiv PDF (the ingested source is that build).
  const pdf = manifest.provenance.pdf_included ? `${base}survey.pdf` : manifest.provenance.status === 'final' ? SITE.paperPdf : null;
  return pdf ? `${pdf}#page=${Number(page) + pdfOffset}` : null;
}

// Physical index of printed page 1. Set by the ingest step from the PDF if known.
const pdfOffset: number = (manifestJson as any).provenance?.pdf_page_offset ?? 0;

export function sectionLink(id: string): string | null {
  const lab = manifest.labels[id];
  const ch = lab?.chapter ?? chapters.find((c) => c.sections.some((s) => s.id === id) || c.slug === id)?.slug;
  if (!ch) {
    // fall back: search section ids across chapters
    for (const c of chapters) if (c.sections.some((s) => s.id === id)) return `${base}handbook/${c.slug}/#${id}`;
    return null;
  }
  return `${base}handbook/${ch}/#${id}`;
}

export function sectionInfo(id: string): { num: string | null; title: string; href: string | null } | null {
  for (const c of chapters) {
    if (c.slug === id) return { num: c.num, title: c.title, href: `${base}handbook/${c.slug}/` };
    const s = c.sections.find((x) => x.id === id);
    if (s) return { num: s.num, title: s.title, href: `${base}handbook/${c.slug}/#${id}` };
  }
  const lab = manifest.labels[id];
  if (lab?.chapter) {
    const ch = chapters.find((c) => c.slug === lab.chapter);
    const title = ch && ch.num === lab.num ? ch.title : (ch?.sections.find((s) => s.num === lab.num)?.title ?? id);
    return { num: lab.num, title, href: `${base}handbook/${lab.chapter}/#${id}` };
  }
  // Unnumbered paragraph headings ("Per-Token Learning Curves."): number of the enclosing numbered section,
  // title of the paragraph heading itself.
  for (const c of chapters) {
    if (withheld.has(c.slug)) continue;
    const h = findRaw(c.slug);
    const at = h?.indexOf(` id="${id}"`) ?? -1;
    if (!h || at < 0) continue;
    let num = c.num;
    for (const s of c.sections) { const p = h.indexOf(` id="${s.id}"`); if (p >= 0 && p < at && s.num) num = s.num; }
    const head = h.slice(at).match(/<h\d[^>]*>([\s\S]*?)<\/h\d>/);
    const title = head ? unescape(head[1].replace(/<a class="anchor"[\s\S]*?<\/a>/, '').replace(/<[^>]+>/g, '')).trim().replace(/\.$/, '') : id;
    return { num, title, href: `${base}handbook/${c.slug}/#${id}` };
  }
  return null;
}

/** Citation keys cited inside the given section ids (computed from the manuscript, not curated). */
export function citationsInSections(ids: string[]): string[] {
  const keys = new Set<string>();
  for (const c of chapters) {
    const html = findRaw(c.slug);
    if (!html || withheld.has(c.slug)) continue;
    for (const id of ids) {
      const start = html.indexOf(`<section id="${id}"`);
      if (start < 0) continue;
      // section ends at the matching </section>: walk nesting
      let depth = 0, i = start, end = html.length;
      const re = /<section\b|<\/section>/g;
      re.lastIndex = start;
      let m: RegExpExecArray | null;
      while ((m = re.exec(html))) {
        depth += m[0] === '</section>' ? -1 : 1;
        if (depth === 0) { end = m.index; break; }
      }
      for (const mm of html.slice(i, end).matchAll(/data-cite="([^"]+)"/g)) keys.add(mm[1]);
    }
  }
  return [...keys];
}

export const referenceByKey = new Map(manifest.references.map((r) => [r.key, r]));

const normText = (x: string) => x.replace(/\s+/g, ' ').trim();
const withheldPlain = [...withheld].map((slug) => {
  const key = Object.keys(privateRaw).find((k) => k.endsWith(`/${slug}.html`));
  return key ? normText(unescape(privateRaw[key].replace(/<\/(p|li|h\d|tr|figcaption|caption)>/g, '\n').replace(/<[^>]+>/g, ''))) : '';
}).join('\n');
/** True if a curated excerpt is text from a withheld chapter. */
export function isWithheldText(s: string): boolean {
  return withheldPlain.length > 0 && s.length > 25 && withheldPlain.includes(normText(s));
}
