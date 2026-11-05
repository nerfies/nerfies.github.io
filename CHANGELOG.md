# Changelog

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
