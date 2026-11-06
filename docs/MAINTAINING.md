# Maintaining the handbook

## Layout

| Path | What it is | Edited by |
|---|---|---|
| `scripts/ingest/ingest.py` | LaTeX manuscript → HTML fragments, references, figures, manifest | code |
| `src/generated/` | Output of the ingest step. **Never edit by hand.** Withheld chapters go to `src/generated/withheld/`, which is gitignored | `npm run ingest` |
| `src/data/chapter-ids.json` | Stable chapter URL ids, and the LaTeX labels and titles that map to them | hand, when chapters change |
| `src/data/published-urls.json`, `src/data/redirects.json` | Every URL ever published; old → new URLs and anchors | `scripts/urls/snapshot_urls.py`, then hand |
| `src/data/publication.json`, `src/data/withheld.json` | Indexing policy; draft chapters held back | authors (see `docs/DECISIONS.md`) |
| `public/figures/` | Figures converted from the manuscript's `figs/` | `npm run ingest` |
| `src/data/methods.json`, `src/data/framework.json` | Curated, **verbatim** excerpts with section ids | `scripts/data/` + review |
| `src/data/links.json` | Editorial cross-links (notebook/demo ↔ method), navigation only | hand |
| `src/data/notebooks.json`, `public/notebook-previews/` | Notebook catalogue | `npm run catalogue` (CI regenerates it) |
| `src/data/experiments/patching_gpt2_ioi.json` | Measured patching results | `scripts/experiments/compute_patching.py` |
| `src/lib/sim/` | Numerics for the in-browser demos | code (pinned by `tests/sim.test.ts`) |
| `src/pages/`, `src/components/` | Site | code |

## Ingesting the final manuscript

The manuscript repository is private, so ingestion runs locally and its output is committed.

Requirements: Python 3.9 or later, `pandoc` 3.x and `poppler` (`pdftocairo`, `pdftotext`).

1. Compile the manuscript as usual, so that `main.aux`, `main.toc` and `main.pdf` sit next to `main.tex`. Numbering and PDF page links come from these files.
2. Run:
   ```bash
   python3 scripts/ingest/ingest.py --manuscript /path/to/manuscript --status final --publish-pdf
   ```
   - Leave out `--status final` for previews. Every page then shows a "Preview build" banner, and deployment is blocked.
   - Pass `--publish-pdf` only for a camera-ready PDF. Draft PDFs render the reviewer comments.
   - If the build's `main.bbl` is present (it is whenever the PDF was compiled with BibTeX), citations and the reference list are rendered from it, exactly as natbib prints them: same author labels, same `2024a`/`2024b` suffixes, same grouping. Without it, the converter falls back to citeproc and records a warning.
   - If the converter stops with "These chapters have no stable id", add the chapter's LaTeX label or title to the matching entry in `src/data/chapter-ids.json`, or add a new entry for a genuinely new chapter. See *Stable URLs* below.
3. Read the summary line. Check `src/generated/manifest.json → audit.warnings` for missing citations, unresolved cross-references and table-of-contents mismatches.
4. **Re-extract the curated data.** Section ids and wording change between versions, so the excerpt files must be rebuilt from the new text. Use `scripts/data/build_methods.py` and `scripts/data/build_framework.py` as the starting point: they hold the excerpts and their own verbatim check. Then run `npm test`. `tests/data.test.ts` fails on any excerpt that is no longer verbatim, or any section id that no longer exists.
5. If the orientations changed (the draft has five, the abstract six), update `PUBLIC` in `src/pages/orientations.astro`. The draft-only notice disappears automatically once `--status final` is set.
6. `npm run build && npm test`, then check a few chapters against the PDF (see the QA checklist below).

### Macros the converter knows about

`ingest.py` removes the reviewer-comment macros listed in `COMMENT_MACROS`, and maps the colour-citation macros (`\citeest`, `\citeem`, …) to natbib, recording each key's tier. If the manuscript gains a new reviewer macro, **add it to `COMMENT_MACROS`**. The test `no editorial comment markers leak` catches the common bracketed formats, but not every possible one.

`forest` and `tikzpicture` diagrams cannot be converted. They are replaced with a link to the PDF page and listed in `audit.dropped_environments`.

## Stable URLs

Chapter URLs are `/handbook/<id>/`, where `<id>` comes from `src/data/chapter-ids.json` and never contains a chapter number. Section, figure and table anchors are the LaTeX `\label`s where the manuscript has them.

- `src/data/published-urls.json` records every page and anchor the site has published. `tests/urls.test.ts` fails if any of them stops resolving.
- When a new manuscript renames or moves an anchor, the test lists it. Add `"handbook/<old>/#<old-anchor>": "handbook/<new>/#<new-anchor>"` to `anchors` in `src/data/redirects.json`. Chapter pages forward moved anchors in the browser.
- When a page moves, add `"old/path/": "new/path/"` to `pages`. Each entry becomes a static redirect page that keeps the `#anchor`. GitHub Pages has no server-side redirects.
- After each release, record the newly published pages: `npm run build && python3 scripts/urls/snapshot_urls.py --merge --note "…"`.

## Withheld chapters

Chapters listed in `src/data/withheld.json` (by stable id) are written only to `src/generated/withheld/`, which is gitignored. Their text is never committed, built or deployed. The ingest step also writes `src/generated/withheld-fingerprints.json`, which holds hashes of their sentences, 10-word sequences, headings and ids. `tests/site.test.ts` scans every deployable file for them, including JavaScript, JSON and the decompressed search index, so the check also runs in CI, where the withheld text does not exist. `npm run dev:all` / `build:all` show withheld chapters locally if you have run the ingest step.

## Notebooks

```bash
python3 scripts/catalogue_notebooks.py --repo ../Interpretability_Survey_Safety --verify-links
```

Everything shown comes from the notebooks themselves: the title, the `**Survey Reference:**` line, the overview, any "Learning objectives" section, and the imports and models used. Compute tiers are estimated from the largest model loaded. Add sizes for new models to `MODEL_SIZES`. To link a notebook to the methods explorer, add it to `src/data/links.json`.

CI regenerates the catalogue on every build and every Monday, and fails if any notebook link stops resolving. Colab links open the notebook. Nothing executes notebooks automatically, so check that a notebook actually runs in Colab by hand.

## Demos

- Superposition and SAE: the code is in `src/lib/sim/` and the UI in `src/components/demos/`. If you change defaults or numerics, update the "Checked results" paragraph on the page **and** `tests/sim.test.ts` together.
- Patching: `pip install torch transformer-lens && python3 scripts/experiments/compute_patching.py`. It takes about a minute on a CPU and is deterministic. Commit the JSON. The page reads its numbers from the JSON.

## Deploying

The workflow `.github/workflows/site.yml` runs on every PR and push to `main` and deploys `main` to GitHub Pages (Settings → Pages → Source = GitHub Actions). It produces two builds:

- **`npm run build:all`** (`PUBLIC_SHOW_ALL=1`). Every page, including withheld draft chapters. Tested, never deployed.
- **`npm run build`**. The live site. It includes the reader and every page built from the manuscript, each marked "Preview build" while the manuscript is a draft. Chapters listed in `src/data/withheld.json` show a "published with the final manuscript" note instead of their text. Quotes from them are dropped from the methods and framework pages, and `tests/site.test.ts` fails if any of their sentences appear anywhere on the site.

Locally, `npm run dev` and `npm run build && npm run preview` show exactly the live site. `npm run dev:all` also shows the withheld chapters.

`PUBLIC_HIDE_DRAFT=1` still exists as an emergency switch: it hides every manuscript-derived page.

Once the manuscript is ingested with `--status final`, the withheld list and the preview banners are ignored automatically.

Indexing: while the manuscript is a draft, pages built from it carry `noindex` unless `indexDraftPages` is `true` in `src/data/publication.json`. That is an author decision (`docs/DECISIONS.md`, D4). `noindex` keeps pages out of search engines but does not hide them.

## QA checklist for a new manuscript version

- [ ] `npm test` is green, including the built-site link and anchor checks.
- [ ] Compare three chapters at random against the PDF: section numbers, a figure caption, a table, an equation number, and a citation's year.
- [ ] `audit.warnings` is empty or every item is understood.
- [ ] The orientations page shows the right set.
- [ ] Spot-check on a phone, and in dark mode.
