import methodsJson from '../data/methods.json';
import frameworkJson from '../data/framework.json';
import notebooksJson from '../data/notebooks.json';
import links from '../data/links.json';
import { sectionInfo, citationsInSections, referenceByKey, isWithheldText } from './manuscript';

// Drop any curated excerpt quoting a withheld chapter.
function scrub(o: any): any {
  if (Array.isArray(o)) return o.filter((x) => !(typeof x === 'string' && isWithheldText(x))).map(scrub);
  if (o && typeof o === 'object') return Object.fromEntries(Object.entries(o).map(([k, v]) => [k, typeof v === 'string' && isWithheldText(v) ? '' : scrub(v)]));
  return o;
}

export const methodsData = scrub(methodsJson) as any;
export const framework = scrub(frameworkJson) as any;
export const notebooks = (notebooksJson as any).notebooks as any[];
export const notebookMeta = notebooksJson as any;

export const families: any[] = methodsData.families;
export const methods: any[] = methodsData.methods;
export const hypotheses: any[] = methodsData.hypotheses;
export const methodById = new Map(methods.map((m) => [m.id, m]));
export const familyById = new Map(families.map((f) => [f.id, f]));

export const DEMOS = [
  { id: 'superposition', title: 'Superposition in a toy model', href: 'demos/superposition/' },
  { id: 'sae', title: 'Sparse autoencoders recover planted features', href: 'demos/sae/' },
  { id: 'patching', title: 'Activation patching on GPT-2 small', href: 'demos/patching/' },
];

export function sections(ids: string[] = []) {
  return ids.map((id) => ({ id, ...(sectionInfo(id) ?? { num: null, title: id, href: null }) }));
}

export function notebooksFor(kind: 'methods' | 'hypotheses' | 'applications', id: string) {
  return notebooks.filter((n) => ((links.notebooks as any)[n.path]?.[kind] ?? []).includes(id));
}
export function demosFor(kind: 'methods' | 'hypotheses', id: string) {
  return DEMOS.filter((d) => ((links.demos as any)[d.id]?.[kind] ?? []).includes(id));
}
export function linksForNotebook(path: string) { return (links.notebooks as any)[path] ?? {}; }
export function demoLinks(id: string) { return (links.demos as any)[id] ?? {}; }

/** Key papers = works cited in the method's primary sections (computed from the manuscript). */
export function keyPapers(m: any, limit = 12) {
  const keys = citationsInSections(m.sections?.slice(0, 1) ?? []);
  // Reference titles keep a few TeX symbols from the .bbl (e.g. "$\\infty$Bench"); show them as characters.
  const TEX: Record<string, string> = { '\\infty': '∞', '\\alpha': 'α', '\\beta': 'β', '\\lambda': 'λ', '\\ell': 'ℓ' };
  return keys.slice(0, limit).map((k) => referenceByKey.get(k)).filter(Boolean)
    .map((r: any) => ({ ...r, text: r.text.replace(/\\(infty|alpha|beta|lambda|ell)/g, (m: string) => TEX[m] ?? m) })) as { key: string; text: string; tier: string | null }[];
}

/** Find a method whose name appears in a free-text method mention from the framework data. */
export function resolveMethod(name: string) {
  const n = name.toLowerCase();
  return methods.find((m) => n.includes(m.name.toLowerCase()) || m.name.toLowerCase().includes(n));
}
