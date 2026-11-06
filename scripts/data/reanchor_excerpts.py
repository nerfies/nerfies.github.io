#!/usr/bin/env python3
"""Re-anchor curated excerpts to a newly ingested manuscript.

Every quote in src/data/methods.json and src/data/framework.json must appear verbatim in the
ingested manuscript (tests/data.test.ts). When a new version is ingested, most quotes differ only
by copy-editing (spelling, citation format, small rewordings). For each quote that is no longer
verbatim, this finds the passage of the new text with the same number of sentences that is most
similar, and:
  - similarity >= ACCEPT: replaces the quote with the new passage, verbatim;
  - otherwise: drops the quote (the site never shows text the paper does not contain).
Section ids that no longer exist are remapped through src/data/redirects.json (anchors), else dropped.
The same replacements are applied to the string literals in build_methods.py / build_framework.py
where they can be found, so the build scripts stay in step.

  python3 scripts/data/reanchor_excerpts.py [--write] [--report out.tsv]
"""
import argparse, difflib, glob, html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCEPT = 0.85
FILES = {"src/data/methods.json": "scripts/data/build_methods.py", "src/data/framework.json": "scripts/data/build_framework.py"}
NON_EXCERPT = {'id', 'name', 'family', 'title', 'subtitle', 'heading', 'step', 'methods', 'methods_used', 'metrics_named', 'related_methods',
  'related_orientations', 'orientations', 'related', 'sections', 'mentioned_in', 'chapter_sections', 'formulas_tex', 'public_name', 'draft_name',
  'draft_sections', 'status', 'source', 'gaps', 'table_id', 'caption', 'columns', 'rows', 'table_row', 'section', 'source_chapter', 'motivation_section',
  'protocol_section', 'framework_limitations_section', 'decision_framework_section', 'tensions_section', 'comparison_table', 'method_guidance',
  'risk_taxonomy', 'evidence_key', 'items', 'groups'}
SECTION_KEYS = {'sections', 'mentioned_in', 'chapter_sections', 'section', 'protocol_section', 'framework_limitations_section',
                'decision_framework_section', 'tensions_section', 'motivation_section', 'draft_sections'}
SENT = re.compile(r"(?<=[.!?:])\s+(?=[A-Z(“\"])")
WORD = re.compile(r"[a-z]{4,}")


def plain_blocks():
    h = "\n".join(open(f).read() for f in sorted(glob.glob(str(ROOT / "src/generated/chapters/*.html"))))
    h = re.sub(r"</(p|li|h\d|tr|figcaption|caption|td|th)>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", "", h))
    return [re.sub(r"\s+", " ", b).strip() for b in t.split("\n") if b.strip()], h


def build_index(blocks):
    sents = []  # (block_no, sentence)
    for i, b in enumerate(blocks):
        for s in SENT.split(b):
            if s.strip():
                sents.append((i, s.strip()))
    inv = {}
    for j, (_, s) in enumerate(sents):
        for w in set(WORD.findall(s.lower())):
            inv.setdefault(w, []).append(j)
    return sents, inv


def best_match(text, sents, inv, plain):
    k = max(1, len([s for s in SENT.split(text) if s.strip()]))
    words = set(WORD.findall(text.lower()))
    if not words:
        return None, 0.0
    votes = {}
    for w in words:
        lst = inv.get(w, [])
        if len(lst) > 400:  # too common to discriminate
            continue
        for j in lst:
            votes[j] = votes.get(j, 0) + 1
    starts = set()
    for j, _ in sorted(votes.items(), key=lambda x: -x[1])[:60]:
        for d in range(k):
            starts.add(j - d)
    best, score = None, 0.0
    for st in starts:
        if st < 0 or st + k > len(sents):
            continue
        win = sents[st:st + k]
        if len({b for b, _ in win}) > 1 and k > 1 and win[0][0] != win[-1][0]:
            pass  # windows may cross paragraph breaks; still verbatim in the joined text check below
        cand = " ".join(s for _, s in win)
        sm = difflib.SequenceMatcher(None, text, cand, autojunk=False)
        if sm.real_quick_ratio() < score or sm.quick_ratio() < score:
            continue
        r = sm.ratio()
        if r > score and cand in plain:
            best, score = cand, r
    return best, score


def walk(o, key, fn):
    if key in NON_EXCERPT and key not in SECTION_KEYS:
        return o
    if key in SECTION_KEYS:
        return fn(o, key, section=True)
    if isinstance(o, str):
        return fn(o, key, section=False)
    if isinstance(o, list):
        return [x for x in (walk(x, key, fn) for x in o) if x is not None]
    if isinstance(o, dict):
        return {k: v for k, v in ((k, walk(v, k, fn)) for k, v in o.items()) if v is not None}
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    blocks, h = plain_blocks()
    plain = " ".join(blocks)
    ids = set(re.findall(r'\sid="([^"]+)"', h))
    sents, inv = build_index(blocks)
    red = json.loads((ROOT / "src/data/redirects.json").read_text())["anchors"]
    id_map = {}
    for k, v in red.items():
        if v.startswith("handbook/"):
            id_map.setdefault(k.split("#", 1)[1], v.split("#", 1)[1])
    rows = []
    for jf, pyf in FILES.items():
        data = json.loads((ROOT / jf).read_text())
        py = (ROOT / pyf).read_text()
        repl = {}

        def fn(o, key, section):
            if section:
                if isinstance(o, list):
                    out = []
                    for x in o:
                        y = fn(x, key, True)
                        if y is not None and y not in out:
                            out.append(y)
                    return out
                if not isinstance(o, str) or " (" in o or o in ids:
                    return o
                new = id_map.get(o)
                rows.append((jf, key, "section", "remap" if new in ids else "drop", o, new or ""))
                return new if new in ids else None
            if len(o) <= 25 or re.sub(r"\s+", " ", o).strip() in plain:
                return o
            best, score = best_match(o, sents, inv, plain)
            if best and score >= ACCEPT:
                repl[o] = best
                rows.append((jf, key, f"{score:.2f}", "replace", o, best))
                return best
            rows.append((jf, key, f"{score:.2f}", "drop", o, best or ""))
            return None

        # top-level "methods"/"hypotheses" are containers here, not the excerpt-free key of the same name
        new = {k: (v if k in ("source", "gaps") else walk(v, "" if k in ("methods", "hypotheses") else k, fn)) for k, v in data.items()}
        if a.write:
            (ROOT / jf).write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n")
            hits = 0
            for o, n in repl.items():
                for q in (json.dumps(o, ensure_ascii=False), '"' + o.replace('"', '\\"') + '"'):
                    if q in py:
                        py = py.replace(q, json.dumps(n, ensure_ascii=False)); hits += 1; break
            (ROOT / pyf).write_text(py)
            print(f"{pyf}: {hits}/{len(repl)} replacements applied to source literals")
    acts = {}
    for r in rows:
        acts[(r[0], r[3])] = acts.get((r[0], r[3]), 0) + 1
    for k, v in sorted(acts.items()):
        print(*k, v)
    if a.report:
        with open(a.report, "w") as f:
            for r in rows:
                f.write("\t".join(r) + "\n")


if __name__ == "__main__":
    main()
