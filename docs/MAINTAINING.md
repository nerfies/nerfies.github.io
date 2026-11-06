# Maintaining the handbook

## Layout

| Path | What it is | Edited by |
|---|---|---|
| `scripts/ingest/ingest.py` | LaTeX manuscript → HTML fragments, references, figures, manifest | code |
| `src/generated/` | Output of the ingest step. **Never edit by hand.** | `npm run ingest` |
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
3. Read the summary line. Check `src/generated/manifest.json → audit.warnings` for missing citations, unresolved cross-references and table-of-contents mismatches.
4. **Re-extract the curated data.** Section ids and wording change between versions, so the excerpt files must be rebuilt from the new text. Use `scripts/data/build_methods.py` and `scripts/data/build_framework.py` as the starting point: they hold the excerpts and their own verbatim check. Then run `npm test`. `tests/data.test.ts` fails on any excerpt that is no longer verbatim, or any section id that no longer exists.
5. If the orientations changed (the draft has five, the abstract six), update `PUBLIC` in `src/pages/orientations.astro`. The draft-only notice disappears automatically once `--status final` is set.
6. `npm run build && npm test`, then check a few chapters against the PDF (see the QA checklist below).

### Macros the converter knows about

`ingest.py` removes the reviewer-comment macros listed in `COMMENT_MACROS`, and maps the colour-citation macros (`\citeest`, `\citeem`, …) to natbib, recording each key's tier. If the manuscript gains a new reviewer macro, **add it to `COMMENT_MACROS`**. The test `no editorial comment markers leak` catches the common bracketed formats, but not every possible one.

`forest` and `tikzpicture` diagrams cannot be converted. They are replaced with a link to the PDF page and listed in `audit.dropped_environments`.

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

The workflow `.github/workflows/site.yml` runs on every PR and push. It produces two builds:

- **Full build.** Every page, tested.
- **Public build** (`PUBLIC_HIDE_DRAFT=1`). This is the one that deploys. While the ingested manuscript is a draft, it leaves out the reader, references, methods, evaluation, orientations and safety pages. Their URLs show a "coming with the paper" note, and every link to them is removed. `tests/site.test.ts` fails if any manuscript text gets into this build.

Deploys run from `main` and from `feature/interactive-handbook`. Pages is set to **GitHub Actions**, and the `github-pages` environment allows both branches.

Once the final manuscript is ingested with `--status final`, the public build includes every page automatically.

Preview the public build locally:

```bash
PUBLIC_HIDE_DRAFT=1 npm run build && npm run preview
```

## QA checklist for a new manuscript version

- [ ] `npm test` is green, including the built-site link and anchor checks.
- [ ] Compare three chapters at random against the PDF: section numbers, a figure caption, a table, an equation number, and a citation's year.
- [ ] `audit.warnings` is empty or every item is understood.
- [ ] The orientations page shows the right set.
- [ ] Spot-check on a phone, and in dark mode.
