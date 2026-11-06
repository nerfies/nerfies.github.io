# The State of Mechanistic Interpretability for AI Safety: interactive handbook

Source for <https://tsglab.github.io/mechinterp-safety/>, the companion site to the survey *The State of Mechanistic Interpretability for AI Safety* ([arXiv:2611.08438](https://arxiv.org/abs/2611.08438)).

The site has:

- **Handbook.** The survey as an online book, with numbering that matches the PDF, stable deep links, citation previews and searchable references. While the manuscript is a draft, pages say so, and chapters listed in `src/data/withheld.json` are held back.
- **Methods explorer.** Filter and compare methods side by side. All text is verbatim from the survey.
- **Evaluation framework, research orientations, safety applications and open problems.** Interactive pages built from the survey text.
- **Notebook catalogue.** Generated automatically from [TSGLAB/Interpretability_Survey_Safety](https://github.com/TSGLAB/Interpretability_Survey_Safety).
- **Three demos.** Superposition and sparse autoencoders train live in the browser. Activation patching shows measurements on GPT-2 small.
- **Full-text search.** Pagefind, built statically.

The site is static (Astro + MDX, React islands, KaTeX rendered at build time) and deploys to GitHub Pages. It has no backend and no paid APIs.

## Quick start

```bash
npm ci
npm run dev        # http://localhost:4321/mechinterp-safety/ (same pages as the live site; search needs a build)
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

## Citation

```bibtex
@misc{barez2026understandingaiinsidestate,
      title={Understanding AI from the Inside: The State of Mechanistic Interpretability for AI Safety}, 
      author={Fazl Barez and Tung-Yu Wu and Hunar Batra and Gabriele Dominici and Florent Draye and Yanai Elazar and Damiano Fornasiere and Antía García and Abir Harrasse and Riley Harris and Sara Hooker and Michael Lan and Belinda Z. Li and Aaron Maiwald and Narmeen Fatimah Oozeer and Naomi Saphra and Or David Shafran and Adi Simhi and Robert Trager and Shriyash Kaustubh Upadhyay and Ziyu Yao and Yu Zhao and Shay B. Cohen and Mor Geva and Yoshua Bengio and Stella Biderman and Hassan Sajjad},
      year={2026},
      eprint={2611.08438},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2611.08438}, 
}
```

## Website licence

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>. The original project page was built with the [Academic Project Page Template](https://github.com/eliahuhorwitz/Academic-project-page-template), adopted from [Nerfies](https://nerfies.github.io).
