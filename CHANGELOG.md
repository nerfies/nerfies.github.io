# Changelog

## Handbook now shows the arXiv version (2611.08438v1)
- Every tab is built from the arXiv LaTeX source, ingested with `--status final`: 15 chapters, Acknowledgements, 3 appendices, 517 references. Preview banners, the withheld chapter and draft `noindex` are gone.
- Chapter 10 is now *Learning Dynamics and Mechanistic Interpretability* at `/handbook/learning-dynamics/`. `/handbook/developmental-interpretability/` and the removed *SAE Architecture Details* appendix redirect.
- Every previously published section anchor still resolves: 318 anchor redirects (`scripts/urls/suggest_anchor_redirects.py`, same-chapter matches only, else the chapter top), and 47 references the arXiv version no longer cites point to the reference list.
- Methods, Evaluation and Safety & open problems quotes re-selected from the arXiv text, verbatim (`scripts/data/check_verbatim.py`).
- Page numbers link to that page of the arXiv PDF.
- Ingest fixes: `\ref` always prints LaTeX's number (pandoc's own figure numbering was off by one because the taxonomy figure sits in main.tex); unnumbered chapters keep their title; a `.bib` is optional when a `.bbl` is present.

## Paper on arXiv
- The paper is out as [arXiv:2611.08438](https://arxiv.org/abs/2611.08438). The homepage links the abstract page and PDF, and the citation section shows the arXiv BibTeX with a copy button. README gains a Citation section.


## Repository renamed to `mechinterp-safety`
- The site moves to https://tsglab.github.io/mechinterp-safety/. CI derives the base path from the repository name.
- The old address, tsglab.github.io/mi_survey/, forwards every published page, with its `#anchor`, through a generated redirect repository (`scripts/urls/build_legacy_site.py`).


## Phase 2, PR 1: stable URLs, publication safeguards, citation and maths fidelity

### Changed
- **Chapter URLs are stable and number-free** (`/handbook/circuits/`, not `/handbook/7-circuits-in-mechanistic-interpretability/`), with ids from `src/data/chapter-ids.json`. Every old URL redirects, and keeps its `#anchor`.
- **Citations render exactly as in the PDF**, from natbib's `main.bbl`. This removes the doubled parentheses ("((A 2023); (B 2024))") and fixes same-year suffixes and name particles. The bibliography also comes from `main.bbl`. 100 curated excerpts were updated mechanically to the corrected citation text. Each one was accepted only if it appears verbatim in the manuscript.
- **Inline maths in excerpts, method cards, the comparison table and framework tables** is rendered with KaTeX at build time.
- Pages built from the draft manuscript are `noindex` by default (`src/data/publication.json`; author decision pending).
- Preprint and flagged citations are marked by underline style and a text tag, not by colour alone.
- Homepage: author legend († core contributors, ‡ senior advisors, * correspondence). Copy no longer says the full survey is online.
- The masthead title wraps on narrow screens instead of overflowing.

### Security / publication
- **Withheld chapters are no longer committed.** The ingest step writes them to a gitignored folder. Their curated quotes, heading-derived anchors and section links were removed from the data, the build scripts and the docs. A hash-based leak test scans every deployable file, including the search index.

### Added
- `src/data/published-urls.json` (105 pages, 1,060 anchors) and `tests/urls.test.ts`: published URLs and anchors must keep resolving.
- `docs/DECISIONS.md`: author decision sheet and source inventory.
- Tests: 25 → 33.


## Unreleased: interactive handbook (`feature/interactive-handbook`)

### Added
- Astro static site replacing the single-page template, deployed at the same URL with the same base path.
- **Homepage** centred on "Does understanding how models work actually make them safer?". Title, authors, affiliations, abstract, overview figure, pillars and taxonomy are carried over verbatim, and the four pillars now link into the site.
- **Handbook reader**: 16 chapters and 4 appendices, generated from LaTeX. Section, figure, table and equation numbers match the PDF. Includes collapsible chapter navigation, a scroll-synced contents panel, permalinks on every heading, figure and table, citation previews coloured by publication status, printed-page references, previous/next navigation and mobile layouts.
- **References**: 298 entries, filterable by text and publication status.
- **Search**: Pagefind full-text search across the site.
- **Methods explorer**: 51 methods in 11 families plus 4 core hypotheses. Search, family filter, side-by-side comparison of up to three methods (shareable URL), and a page per method with its survey sections, key papers (computed from the survey's citations), related methods, safety applications, notebooks and demos.
- **Evaluation framework**: the five dimensions with definitions, metrics, formulas, the survey's summary table, a per-method guidance table, the step-by-step protocol and its limitations. Keyboard-accessible tabs.
- **Research orientations**: cards for the six public orientations, draft content where it exists, a comparison table with column toggles, a decision framework and tensions.
- **Safety applications and open problems**: a searchable directory of 5 applications and 11 open problems with linked methods and orientations, evidence separated from illustrative worked examples, a risk taxonomy and an interactive verification checklist.
- **Notebook catalogue**: 19 notebooks generated from the repo, with survey section (matched by title), prerequisites, estimated compute, models (gated ones flagged), dependencies (including ones missing from `requirements.txt`), learning outcomes where stated, output previews, source and Colab links, and Colab caveats.
- **Demos**:
  - A toy model of superposition, trained in the browser.
  - A sparse autoencoder against planted ground-truth features, with a λ sweep.
  - Activation and attribution patching on GPT-2 small (IOI, 32 prompt pairs, r = 0.985), measured by `scripts/experiments/compute_patching.py`.
- Tests (23): demo results, verbatim checks on all curated excerpts, section-id resolution, ingestion integrity, internal links and anchors across the built site, maths rendering, metadata and alt text.
- CI: build and test on every PR, a weekly notebook link check, and a Pages deploy from `main` guarded against publishing draft text.
- Dark mode, metadata for search engines and social sharing (Open Graph, Twitter card, schema.org ScholarlyArticle), a skip link, and visible focus styles.
- Docs: `README.md`, `docs/MAINTAINING.md`, `docs/AUDIT.md`.

### Changed
- `static/` moved to `public/static/`. Asset URLs are unchanged.
- README rewritten. The Nerfies README was template residue.

### Not changed
- Unused template videos and images (see `docs/AUDIT.md` §5).
- The live site: nothing is deployed until this merges, the Pages source is switched, and the final manuscript is ingested.
