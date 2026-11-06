// Loads the ingested manuscript (src/generated, produced by scripts/ingest/ingest.py)
// and renders maths with KaTeX at build time, so pages ship no maths JavaScript.
import katex from 'katex';
import manifestJson from '../generated/manifest.json';
import { base } from './site';

export interface TocSection { id: string; num: string | null; title: string; level: number; page: string | null }
export interface Chapter {
  slug: string; num: string; title: string; appendix: boolean; page: string | null;
  sections: TocSection[]; words: number;
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
/** Public builds made while the manuscript is still a draft hide every page built from it. */
export const draftHidden = isDraft && import.meta.env.PUBLIC_HIDE_DRAFT === '1';

const raw = import.meta.glob('../generated/chapters/*.html', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;
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
  const key = Object.keys(raw).find((k) => k.endsWith(`/${slug}.html`));
  if (!key) throw new Error(`chapter ${slug} not found`);
  return withBase(renderMath(raw[key]));
}

export function referencesHtml(): string {
  const v = Object.values(refsRaw)[0] ?? '';
  return withBase(renderMath(v));
}

export function pdfHref(page: string | null | undefined): string | null {
  if (!manifest.provenance.pdf_included || !page) return null;
  // Roman-numbered front matter pages are not addressable by number; skip them
  if (!/^\d+$/.test(page)) return null;
  // PDF viewers use physical page indices; the offset accounts for front matter.
  return `${base}survey.pdf#page=${Number(page) + pdfOffset}`;
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
  return null;
}

/** Citation keys cited inside the given section ids (computed from the manuscript, not curated). */
export function citationsInSections(ids: string[]): string[] {
  const keys = new Set<string>();
  for (const c of chapters) {
    const html = raw[Object.keys(raw).find((k) => k.endsWith(`/${c.slug}.html`))!];
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
