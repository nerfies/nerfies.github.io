# Author decisions and source inventory

Prepared 6 Nov 2026 for the corresponding author. Phase 2, step 0.

Each item below is the authors' call. The site keeps its current behaviour until a decision is recorded here. Record the decision and the date under each item.

## Source inventory

| Source | What it is | Status |
|---|---|---|
| Private repo `fbarez/The-Handbook-on-Interpretability`, commit `cd5bc3c` (13 Jul 2026) | LaTeX source, `tmlr.bib`, and compiled `main.aux`, `main.toc`, `main.bbl` and `main.pdf`. Titled *The Handbook on Interpretability*. | **This is what the site shows now.** The repo was last synced from Overleaf on 13 Jul. |
| PDF compiled 5 Nov 2026 (TMLR submission build, 181 pp.) | *Understanding AI from the Inside: The State of Mechanistic Interpretability for AI Safety*. Newer structure: ten method and analysis chapters, then §12 Six Research Orientations, §13 Safety applications and §14 Open problems. | **PDF only.** No LaTeX source for this version exists on GitHub or locally. It is probably on Overleaf. |
| Older PDFs (Jan and Feb 2026) | *Mechanistic Interpretability: A Survey…* and *The State of Interpretability for Safety…* | Superseded. Not used. |
| Title and authors shown on the site since PR #2 | From the title-page screenshot supplied on 6 Nov | **Differs from the 5 Nov PDF** (see D1). |

**6 Nov 2026 09:00 build (182 pp.)**: the version to publish. Chapters: 1 Introduction … 7 Circuits, 8 Understanding Intermediate Representations, 9 Representation Analysis, 10 Learning Dynamics, 11 Training Data Attribution, 12 Six Research Orientations, 13 Safety Applications, 14 Open Problems, 15 Conclusion; appendices A Notation, B Colour Key, C Mathematical Foundations. Its titles are registered in `src/data/chapter-ids.json`. To decide at ingest: the 13 Jul chapters *Developmental Interpretability and Training Dynamics* and *Appendix C, SAE Architecture Details* have no counterpart, so their old URLs need a redirect target. The new chapter 10 shares its title with the withheld chapter, but a text search finds none of the authoring notes, so it can probably be published (remove it from `withheld.json`).

**Needed to re-ingest (PR 2).** The approved LaTeX source for the version to publish, in a form the ingest script can read: `main.tex`, the chapter files, `.bib`, `figs/`, and the compiled `main.aux`, `main.toc`, `main.bbl` and `main.pdf` from the same build. The simplest route is to sync Overleaf to the GitHub repo again, or to export the Overleaf project as a zip after compiling. The ingest step must not be run with `--status final` until D4 says so.

## Decisions

### D1. Official title and author metadata
**Decided 6 Nov 2026:** the title, authors, affiliations and abstract stay as they are on the site. Only the body of the paper is updated. The authoritative body is the TMLR submission build compiled 6 Nov 2026 09:00 (182 pp.), whose author list matches the site.

<details><summary>Earlier comparison with the 5 Nov build (superseded)</summary>

The site and the 5 Nov PDF differ:

| | Site now | 5 Nov PDF |
|---|---|---|
| Title | The State of Mechanistic Interpretability for AI Safety | *Understanding AI from the Inside:* The State of Mechanistic Interpretability for AI Safety |
| Shay B. Cohen | Senior advisor (‡), affiliation 14 (Edinburgh) | Alphabetical group, affiliation 3 (Edinburgh) |
| Naomi Saphra | Alphabetical group, affiliation 10 | Senior advisor (‡), affiliation 13 (Boston University) |
| Belinda Z. Li | Affiliations 8 (MIT) and 9 (Anthropic) | Affiliation 9, "MIT & Anthropic" |
| Number of affiliations | 17 | 16 |
| Legend | (none until this PR) | "† Core contributors. ‡ Senior advisors. Remaining authors listed alphabetically by surname. * Correspondence" |

</details>

### D2. Research orientations
The 5 Nov PDF has six orientations, §12.1 to §12.6: Pragmatic, Ambitious, Developmental, Interpretability Across Time, Introspective, Automated. "Agentic" no longer appears. The site currently shows the 13 Jul draft, which has five, including Agentic. **Decide:** confirm the six and their definitions from the approved source. The site will quote the definitions verbatim. It will not map Agentic onto Introspective.

### D3. Evaluation framework
The 5 Nov PDF defines one framework in §7.5 with five dimensions: attribution faithfulness, completeness, stability, causal validity and human interpretability. §14.2 refers back to §7.5. A text search found no second framework. The 13 Jul draft also had a four-dimension framework in §15.2.1. **Decide:** confirm that §7.5 is the only framework in the approved source.

### D4. Publication status of draft text
Now: the live site publishes the 13 Jul draft text, with "Preview build" banners, for every chapter except chapter 11.

**This PR.** Pages built from draft text now carry `<meta name="robots" content="noindex">`. They stay reachable by link and in the site's own search. The switch is `indexDraftPages` in `src/data/publication.json`. `noindex` is not access control: anything deployed is public.

**Decide:**
1. Keep the draft text public, unindexed (the current default).
2. Keep it public and indexed.
3. Hide all draft pages (`PUBLIC_HIDE_DRAFT=1`), so only the homepage, demos and notebooks remain.
4. When the new source arrives, publish the new draft instead.

Separately, decide when `--status final` applies (after acceptance? camera-ready?).

**Also decide (urgent): chapter 11 in the repository history.** The site never showed chapter 11. However, its converted text, including the authoring notes, was committed to this **public** repository on 5 Nov (commit `c80c20f`, merged to `main`). It is still readable in the history and at the old raw-file URL until removed. This PR stops that going forward: withheld chapters are now written only to a gitignored folder. Removing it from history requires rewriting `main` and force-pushing, plus asking GitHub support to purge cached views. Forks and clones made since 5 Nov keep a copy. Whether to do this is your call. I have not done it.

### D5. Licensing
Neither `TSGLAB/mi_survey` nor `TSGLAB/Interpretability_Survey_Safety` has a licence file. The README's CC BY-SA 4.0 line was inherited from the original page template. **Decide**, separately for each:
- the website code
- the survey text and figures shown on the site (this follows the paper's licence, e.g. the TMLR/arXiv choice)
- the notebook code, which with no licence is legally "all rights reserved"
- the generated data (excerpts, patching results)

## Work that does not need a decision

- PR 1 (this one): stable URLs and redirects, safeguards for withheld content, natbib-exact citations, maths in cards and tables, non-colour evidence cues, copy that no longer claims the full manuscript is online.
- PR 3: repair and pin the notebook environments, and execute the CPU notebooks in clean environments.
- PR 4: the patching statistics (more prompt pairs, bootstrap intervals, random baselines) and SAE seed stability. These are website demos and do not depend on the manuscript.
- PR 5: remove the unused template videos, and do the performance and social-preview checks.
- Blocked on the source (D1–D3): PR 2, re-ingesting and re-extracting the curated excerpts.
