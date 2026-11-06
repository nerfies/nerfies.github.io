# Audit, implementation plan and open gaps

Audit date: 5 Nov 2026. Branch: `feature/interactive-handbook`.

## Status on 6 Nov 2026 (phase 2, PR 1)

Re-checked against the deployed site and the 5 Nov PDF. Author decisions are in `docs/DECISIONS.md`.

- **Fixed in this PR.**
  - Doubled parentheses around citations (72): the converter now renders citations from the build's `main.bbl`. 411 of 412 citation strings match the PDF text; the one exception sits in a table that PDF text extraction breaks. 296 of 298 reference entries match, and the other two differ only in accent encoding.
  - Same-year suffixes in the bibliography ("2018a"), and URLs capitalised by citeproc ("Https://…").
  - Raw TeX in method cards and tables.
  - Colour as the only cue for evidence tiers.
  - Links and heading anchors that exposed the withheld chapter.
  - Copy claiming the full manuscript is online.
  - The phone masthead overflow.
  - Chapter URLs no longer depend on numbers or titles.
- **Still valid.** §3 (website and manuscript inconsistencies) and §4 (manuscript issues) still describe the *13 Jul draft*. The 5 Nov PDF already resolves §3.1 (six orientations), §3.3 (one framework, §7.5) and the title. These close when the new source is ingested (PR 2).
- **New.** Chapter 11's text was committed to this public repo on 5 Nov (see DECISIONS D4). Neither repo has a licence file (D5).

## 1. What existed

**Website (`TSGLAB/mi_survey`)**
- Fork of the Nerfies / Academic Project Page Template. One `index.html` with Bulma and Font Awesome, served by GitHub Pages ("legacy" mode, `main` branch root). No build step and no CI.
- Content: title, 27 authors, 17 affiliations, abstract, overview figure, four-pillar summary, taxonomy figure. "Paper (coming soon)", BibTeX "will be available with the release".
- About 180 MB of unused template assets (`static/videos/*.mp4`, `static/interpolation/`). Left untouched (moved with `static/` to `public/static/`) per "do not remove existing assets unnecessarily". Deleting them would shrink the deployed site considerably and is worth doing as a separate commit.
- The README is still the Nerfies README.

**Notebooks (`TSGLAB/Interpretability_Survey_Safety`)**: 19 notebooks in 6 folders. CPU/GPU estimates by largest model loaded:

| Tier | Count | Notebooks |
|---|---|---|
| CPU | 13 | linear representation, superposition, SAE basics, transcoders, crosscoders, circuit discovery, logit lens, tuned lens, patchscopes, probing, knowledge localisation, concept erasure, steering vectors |
| GPU | 3 | privileged access (Llama-3.1-8B, gated), natural-language autoencoders (Qwen2.5-7B), model diffing (Gemma-2-2B, gated) |
| Large GPU | 3 | Jacobian lens (Qwen3.6-27B), activation oracles (up to Llama-3.3-70B), representation engineering (Llama-2-13B, gated) |

- Needs external services: Hugging Face token (Jacobian lens, model diffing, representation engineering); runtime downloads (Jacobian lens, probing, NLAs).
- Imports **missing from `requirements.txt`**: tqdm, pyyaml, sae-lens, tuned-lens, peft, httpx, huggingface-hub, python-dotenv.
- Repository-local or unpublished modules (Colab needs a clone first): `model` (privileged access), `jlens` (Jacobian lens), `nla_inference` (NLAs).
- No notebook has a Colab badge. 7 notebooks state learning objectives.
- `README.md` clone URL points to `fbarez/Interpretability_Survey_Safety`, not `TSGLAB/…`. The citation is `[incoming]`. `docs/` holds a stale copy of the template site.
- `06_safety_applications/01_concept_erasure.ipynb` has no "Survey Reference" line. `07_natural_language_autoencoders` says "dedicated handbook section coming soon".

**Manuscript.** No manuscript source is in either public repo. The only source available was the private Overleaf-synced repo `fbarez/The-Handbook-on-Interpretability` (last commit `cd5bc3c`, 13 Jul 2026, titled *The Handbook on Interpretability*). **It is older than the public site and differs from it structurally**, so this build treats it as a *preview* source only (see §3).

## 2. What was built (implementation plan as executed)

1. Static Astro site (TypeScript, MDX-capable, React islands only where interactive). KaTeX is rendered at build time, Pagefind gives static search, and GitHub Actions builds, tests and deploys. No backend.
2. A reproducible LaTeX → HTML pipeline (`scripts/ingest/ingest.py`, pandoc + citeproc). Numbering, figure/table/equation numbers and PDF page numbers come from the LaTeX build's `.aux` and `.toc`, so they match the PDF exactly. It removes reviewer comments (94 removed from this draft) and keeps the manuscript's peer-reviewed / emerging citation colouring.
3. Curated data for the methods explorer, evaluation framework, orientations, safety applications and open problems. Every text field is a **verbatim** excerpt with its section id, and tests enforce this (623 excerpts).
4. A notebook catalogue generated from the notebooks, with links verified in CI.
5. Three demos with genuine computation, results pinned by tests.

## 3. Inconsistencies between manuscript, website and notebooks

**These block a public launch of the reader, explorer and framework pages. They resolve once the final manuscript is ingested.**

| # | Website / abstract | Draft manuscript (13 Jul) | Notebooks |
|---|---|---|---|
| 1 | **Six** orientations: Pragmatic, Ambitious, Developmental, *Interpretability Across Time*, *Introspective*, Automated | **Five**: Pragmatic, Ambitious, Developmental, *Agentic*, Automated. "Across time" appears nowhere. | — |
| 2 | Orientations §12, Safety & Open Problems §13–14, Methods §6–11 | Orientations §13, Safety §14, Open problems §15, Methods §6–12 | Model diffing "11.1", steering "13.3" (match the website's numbering, not the draft's) |
| 3 | Evaluation dimension "Attribution faithfulness" | "Faithfulness" (ch. 7). Ch. 15.2.1 proposes a *different four-dimension* framework | — |
| 4 | Title *The State of Mechanistic Interpretability for AI Safety* (earlier: *The State of Interpretability for AI Safety*) | *The Handbook on Interpretability* | Survey title |

The site handles each of these honestly. It shows the public six orientations with a clear "not in this draft" state for the two missing ones, and does not assume Agentic = Introspective. It shows both names for faithfulness. It resolves notebook sections by title, not number, and flags numbering differences.

## 4. Manuscript issues found (for the authors)

These are reproduced faithfully in the reader. Flagged, not fixed:

- **Chapter 11 contains authoring notes as body text** (first-person notes about what to write or move). These are not macros, so the converter cannot strip them. They must be removed in the source.
- Unresolved citation keys `binder`, `song` in §5.3. The bibliography lacks them, and the reader shows unlinked placeholders.
- Cross-references off by one: §5.1 "Figure 2" → Figure 3; §5.2 "Figure 3" → Figure 4; §6.1 "Figure 4" → Figure 5; §13.2 "Figure 16" → Figure 18; "Appendix 19" should be Appendix C; §6.3.4 cites Table 5 for Table 4.
- Contradictions: SPARTAN L1 (text) vs L0 (Table 7). Gated SAE hard gate (§6.2) vs sigmoid (App. C.3). Top-k k = 50–100 (Table 4) vs 50–200 (App. C.4). Causal scrubbing as a necessity test (§7.4) vs a protocol covering sufficiency (§7.6.6). The "necessity > 0.5" threshold is cited but never proposed.
- Duplicated coverage: induction heads ×3 (6.6, 7.5, 10.6), grokking ×3, SLT ×2. Chapters 10 and 11 overlap. §12 has no introduction.
- Probable missing word, §13.3: "a valuable source of feedback, but required" (likely "but not required").
- Citations to check: Ouyang et al. 2022 for sleeper-agent detectability (§15.1); Bai, Jones et al. 2022 for "value learning" (§15.4).
- Typos in headings and ids: "Hnadbook Scope", "bild on", "Bethods", "Principle Component", "artificailly", "Bascially", "two many".
- Two section ids contain spaces. ACDC is never expanded.
- One `\mathbbm{1}` is rendered as `\mathbb{1}` (KaTeX has no `bbm`).

## 5. Remaining gaps in the site

- **Final manuscript.** Not yet supplied. Every manuscript-derived page carries a preview banner, and the deploy job refuses to publish until it is ingested with `--status final`.
- **Figure fidelity** checked visually on chapters 1, 5 and 6 against the draft PDF, with numbering verified by tests. The full chapter-by-chapter PDF comparison must be repeated on the final manuscript (see the QA checklist in `MAINTAINING.md`).
- **PDF page links** show printed page numbers. They become links once a camera-ready PDF is ingested with `--publish-pdf`. The draft PDF renders reviewer comments, so it is deliberately not published.
- **Paper link and BibTeX**: still "coming soon", as on the current site.
- **Colab execution** is not verified. The links resolve (checked in CI), but no notebook has been run end to end in Colab. 6 notebooks need GPUs, gated models or local modules (flagged on each card).
- **Equation deep links** exist (`#eq-N`), but the manuscript labels no equations, so the text never cross-references them.
- **Template assets** (~180 MB of unused Nerfies videos) remain. Removing them is recommended in a follow-up.
- Excerpt fields in the explorer occasionally contain raw TeX (for example the ACDC definition), because the source sentence has no maths-free form.
- The Pages source must be switched to **GitHub Actions** before merging (see `MAINTAINING.md`).
