export const base = import.meta.env.BASE_URL.endsWith('/') ? import.meta.env.BASE_URL : `${import.meta.env.BASE_URL}/`;
export const url = (p: string) => `${base}${p.replace(/^\//, '')}`;

export const SITE = {
  title: 'The State of Mechanistic Interpretability for AI Safety',
  short: 'Mechanistic Interpretability for AI Safety',
  notebooksRepo: 'https://github.com/TSGLAB/Interpretability_Survey_Safety',
  siteRepo: 'https://github.com/TSGLAB/mechinterp-safety',
  contact: 'fazl@robots.ox.ac.uk',
  paper: 'https://arxiv.org/abs/2611.08438',
  paperPdf: 'https://arxiv.org/pdf/2611.08438',
};

export const NAV = [
  { href: 'handbook/', label: 'Handbook', draft: true },
  { href: 'methods/', label: 'Methods', draft: true },
  { href: 'evaluation/', label: 'Evaluation', draft: true },
  { href: 'orientations/', label: 'Orientations', draft: true },
  { href: 'safety/', label: 'Safety & open problems', draft: true },
  { href: 'demos/', label: 'Demos', draft: false },
  { href: 'notebooks/', label: 'Notebooks', draft: false },
];
