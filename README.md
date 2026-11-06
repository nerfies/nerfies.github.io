# The State of Mechanistic Interpretability for AI Safety: interactive handbook

Source for <https://tsglab.github.io/mi_survey/>, the companion site to the survey *The State of Mechanistic Interpretability for AI Safety*.

The site has:

- **Handbook.** The full manuscript as an online book, with numbering that matches the PDF, deep links, citation previews and searchable references.
- **Methods explorer.** Filter and compare methods side by side. All text is verbatim from the survey.
- **Evaluation framework, research orientations, safety applications and open problems.** Interactive pages built from the survey text.
- **Notebook catalogue.** Generated automatically from [TSGLAB/Interpretability_Survey_Safety](https://github.com/TSGLAB/Interpretability_Survey_Safety).
- **Three demos.** Superposition and sparse autoencoders train live in the browser. Activation patching shows measurements on GPT-2 small.
- **Full-text search.** Pagefind, built statically.

The site is static (Astro + MDX, React islands, KaTeX rendered at build time) and deploys to GitHub Pages. It has no backend and no paid APIs.

## Quick start

```bash
npm ci
npm run dev        # http://localhost:4321/mi_survey/ (same pages as the live site; search needs a build)
npm run build      # static site in dist/ + search index, identical to what deploys
npm run build:all  # also includes draft chapters withheld from the live site (src/data/withheld.json)
npm test           # unit, data-integrity and built-site tests (run after build)
```

To update content, see [docs/MAINTAINING.md](docs/MAINTAINING.md). For what changed and what is still open, see [CHANGELOG.md](CHANGELOG.md) and [docs/AUDIT.md](docs/AUDIT.md).

## Scientific-integrity rules the build enforces

- Text attributed to the survey is verbatim. `tests/data.test.ts` checks every curated excerpt against the ingested manuscript.
- Demo results quoted on the pages are pinned by `tests/sim.test.ts`. The patching numbers come only from `scripts/experiments/compute_patching.py`.
- Reviewer comment macros are stripped during ingestion, and a test fails if any reach the output.
- While the ingested manuscript is a draft, every page built from it says so, the draft PDF is never copied into the site, and chapters listed in `src/data/withheld.json` are not published (a test checks their text appears nowhere).

## Website licence

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>. The original project page was built with the [Academic Project Page Template](https://github.com/eliahuhorwitz/Academic-project-page-template), adopted from [Nerfies](https://nerfies.github.io).
