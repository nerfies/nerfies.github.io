export const base = import.meta.env.BASE_URL.endsWith('/') ? import.meta.env.BASE_URL : `${import.meta.env.BASE_URL}/`;
export const url = (p: string) => `${base}${p.replace(/^\//, '')}`;

export const SITE = {
  title: 'The State of Interpretability for AI Safety',
  subtitle: 'A Survey of Foundations, Methods, and Research Directions',
  short: 'Interpretability for AI Safety',
  notebooksRepo: 'https://github.com/TSGLAB/Interpretability_Survey_Safety',
  siteRepo: 'https://github.com/TSGLAB/mi_survey',
  contact: 'fazl@robots.ox.ac.uk',
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
