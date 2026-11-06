#!/usr/bin/env python3
"""Build src/data/orientations-arxiv.json from the arXiv LaTeX source of the paper.

The orientations page quotes §12 "Six Research Orientations" of the paper as
published on arXiv, while the rest of the handbook still shows the ingested
13 Jul draft. Everything written here is verbatim manuscript text: LaTeX markup
is removed, natbib citations are rendered from the build's .bbl exactly as
natbib prints author labels and years, and cross-references are resolved from
REF_NUMBERS (read off the arXiv PDF).

Usage:
  curl -L -o src.tar.gz https://arxiv.org/e-print/2611.08438 && mkdir src && tar -xzf src.tar.gz -C src
  python3 scripts/data/build_orientations_arxiv.py --source src
"""
import argparse, json, re, sys
from pathlib import Path

ARXIV = {"id": "2611.08438", "version": "v1", "abs": "https://arxiv.org/abs/2611.08438v1",
         "pdf": "https://arxiv.org/pdf/2611.08438v1"}
CHAPTER_FILE = "chapters/12_six_research_orientations.tex"
CHAPTER_NUM = "12"

# \label -> printed number, from the arXiv v1 PDF.
REF_NUMBERS = {
    "sec:architectural-interventions": "6.10",
    "sec:ld-localization": "10.2.1",
    "sec:training_phase_why": "10.3.4",
    "subsec: iat": "12.4",
    "subsec:privileged-access": "5.3",
    "subsec:valproce model self-reports": "12.5.2",
    "subsec:choosing orientation": "12.8",
    "fig:sixresearchorientation": "17",
    "tab:orientations": "13",
    "tab:human-automated-workflow": "12",
}

# Card order and URL ids. The four ids that already existed keep their anchors.
ORDER = [
    ("pragmatic", "Pragmatic Interpretability", "Proxy-Task-Oriented Safety Interventions"),
    ("ambitious", "Ambitious Interpretability", "Towards Complete Mechanistic Understanding"),
    ("developmental", "Developmental Interpretability", "Characterising How Models Learn"),
    ("interpretability-across-time", "Interpretability Across Time", "Understanding the Causes of Model Behaviours"),
    ("introspective-interpretability", "Introspective Interpretability", "Models Interpreting Themselves"),
    ("automated", "Automated Interpretability", "Scaling Discovery via Automation"),
]


def brace_arg(s, i):
    """Return (content, end) of the {...} group starting at s[i] == '{'."""
    assert s[i] == "{", s[i:i + 30]
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{": depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0: return s[i + 1:j], j + 1
    raise ValueError("unbalanced braces")


def load_bbl(path):
    txt = path.read_text()
    out = {}
    for m in re.finditer(r"\\bibitem\[", txt):
        i, depth = m.end(), 1
        j = i
        while depth:
            if txt[j] == "[": depth += 1
            elif txt[j] == "]": depth -= 1
            j += 1
        label = txt[i:j - 1]
        key, _ = brace_arg(txt, txt.index("{", j - 1))
        lm = re.match(r"(.*?)\((.*?)\)", label, re.S)
        authors = latex_to_text(lm.group(1)).strip()
        year = re.sub(r"\{?\\natexlab\{(\w+)\}\}?", r"\1", lm.group(2)).strip()
        out[key.strip()] = (authors, latex_to_text(year))
    return out


def latex_to_text(s):
    s = s.replace("~", " ").replace("\\&", "&").replace("{\\'e}", "é").replace("{\\'a}", "á")
    s = re.sub(r"\{\\(['`\"^~])\{?(\w)\}?\}", lambda m: ACCENTS.get(m.group(1) + m.group(2), m.group(2)), s)
    s = re.sub(r"\\(['`\"^~])\{?(\w)\}?", lambda m: ACCENTS.get(m.group(1) + m.group(2), m.group(2)), s)
    return re.sub(r"[{}]", "", s)


ACCENTS = {"'e": "é", "'a": "á", "'i": "í", "'o": "ó", "'u": "ú", '"o': "ö", '"u': "ü", '"a': "ä", "`e": "è", "`a": "à", "~n": "ñ", "^o": "ô", "'c": "ć", "'s": "ś"}


class Converter:
    def __init__(self, bbl):
        self.bbl = bbl
        self.missing = set()
        self.unresolved = set()

    def cite(self, keys, form):
        parts, prev = [], None
        for k in [k.strip() for k in keys.split(",") if k.strip()]:
            if k not in self.bbl:
                self.missing.add(k); parts.append(f"[{k}]"); continue
            a, y = self.bbl[k]
            if a == prev and form != "t":  # natbib compresses repeated authors: "Biderman et al., 2023b; 2026"
                parts.append(y); continue
            prev = a
            parts.append(f"{a} ({y})" if form == "t" else f"{a}, {y}")
        if form == "t": return ", ".join(parts)
        if form == "alp": return "; ".join(parts)
        return "(" + "; ".join(parts) + ")"

    def convert(self, s):
        s = re.sub(r"(?<!\\)%.*", "", s)
        # citations
        def repl(m):
            name = m.group(1)
            arg, end = brace_arg(s_ref[0], m.end() - 1)
            form = "t" if name.startswith("citet") else "alp" if name.endswith("alp") else "p"
            return self.cite(arg, form), end
        s_ref = [s]
        out, i = [], 0
        for m in re.finditer(r"\\(citeestalp|citeemalp|citeflagalp|citetest|citetem|citetflag|citeest|citeem|citeflag|citep|citet)\{", s):
            if m.start() < i: continue
            text, end = repl(m)
            out.append(s[i:m.start()]); out.append(text); i = end
        out.append(s[i:]); s = "".join(out)
        s = re.sub(r"\\ref\{([^}]*)\}", lambda m: self.ref(m.group(1)), s)
        s = re.sub(r"\\paragraph\{(.*?)\}", r"\1 ", s)
        for cmd in ("emph", "textbf", "textit", "text"):
            while f"\\{cmd}{{" in s:
                k = s.index(f"\\{cmd}{{")
                arg, end = brace_arg(s, k + len(cmd) + 1)
                s = s[:k] + arg + s[end:]
        s = s.replace("\\\\", " ").replace("~", " ").replace("\\%", "%").replace("\\&", "&")
        s = s.replace("``", "“").replace("''", "”").replace("---", "—").replace("--", "–")
        s = re.sub(r"\s+", " ", s).strip()
        s = s.replace("( ", "(").replace(" )", ")")
        if "\\" in s: raise ValueError(f"unconverted LaTeX: {s[:200]}")
        return s

    def ref(self, label):
        if label not in REF_NUMBERS:
            self.unresolved.add(label); return f"??{label}??"
        return REF_NUMBERS[label]


def split_blocks(body):
    """Paragraphs and itemize lists of a LaTeX chunk, in order."""
    blocks = []
    pos = 0
    for m in re.finditer(r"\\begin\{itemize\}(.*?)\\end\{itemize\}", body, re.S):
        blocks += [("p", p) for p in re.split(r"\n\s*\n", body[pos:m.start()]) if p.strip()]
        items = [it.strip() for it in re.split(r"\\item\s", m.group(1)) if it.strip()]
        blocks.append(("ul", items)); pos = m.end()
    blocks += [("p", p) for p in re.split(r"\n\s*\n", body[pos:]) if p.strip()]
    return blocks


def sections(tex):
    """Map subsection title -> body, and the chapter intro."""
    tex = re.sub(r"\\begin\{(figure|table|warningbox|practicebox)\}.*?\\end\{\1\}", "", tex, flags=re.S)
    tex = re.sub(r"\\label\{[^}]*\}", "", tex)
    parts = re.split(r"\\subsection\{(.*?)\}\n", tex)
    intro = parts[0].split("\n", 1)[1]
    subs = {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}
    return intro, subs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2] / "src/data/orientations-arxiv.json")
    args = ap.parse_args()
    bbl = load_bbl(next(args.source.glob("*.bbl")))
    cv = Converter(bbl)
    tex = (args.source / CHAPTER_FILE).read_text()
    intro, subs = sections(tex)
    titles = list(subs)

    def num(i): return f"{CHAPTER_NUM}.{i + 1}"

    orientations = []
    for (oid, name, sub), title in zip(ORDER, titles[:6]):
        assert title.startswith(name), (title, name)
        i = titles.index(title)
        body = subs[title]
        # Main text only: the subsubsections are failure modes, guardrails and checklists.
        main_part, *subsubs = re.split(r"\\subsubsection\{(.*?)\}\n", body)
        blocks = split_blocks(main_part)
        body = []
        for k, b in blocks:
            if k == "p":
                body.append({"p": cv.convert(b)})
            else:
                items = []
                for it in b:
                    tm = re.match(r"\\textbf\{(.*?)\}", it)
                    items.append({"term": cv.convert(tm.group(1)).rstrip(",:") if tm else None, "text": cv.convert(it)})
                body.append({"ul": items})
        for j in range(0, len(subsubs), 2):
            st, sb = subsubs[j], subsubs[j + 1]
            if st.startswith("When to Use"):
                body.append({"h": cv.convert(st), "section": f"{num(i)}.{j // 2 + 1}"})
                body += [{"p": cv.convert(b)} for k, b in split_blocks(sb) if k == "p"]
        # Definition = the first two sentences; the rest of that paragraph stays in the body.
        first = re.split(r"(?<=[.!?])\s+(?=[A-Z])", body[0]["p"])
        body = ([{"p": " ".join(first[2:])}] if len(first) > 2 else []) + body[1:]
        terms = [it["term"] for blk in body if "ul" in blk for it in blk["ul"] if it["term"]]
        lead = next((body[k - 1].get("p", "") for k, blk in enumerate(body) if "ul" in blk and k), "")
        list_label = "Example metrics" if "metrics" in lead else "Methods"
        orientations.append({
            "id": oid, "name": name, "subtitle": sub, "section": num(i), "section_title": title,
            "definition": " ".join(first[:2]), "list_label": list_label, "list_terms": terms, "body": body,
        })

    def sec_text(prefix):
        t = next(t for t in titles if t.startswith(prefix))
        return titles.index(t), [cv.convert(b) for k, b in split_blocks(subs[t]) if k == "p"]

    ci, comparison_intro = sec_text("Comparative Analysis")
    di, decision = sec_text("Choosing an Orientation")
    ti, tensions = sec_text("Critical Concerns")

    # Comparison table (tab:orientations), cell by cell.
    tab = re.search(r"\\label\{tab:orientations\}.*?\\midrule(.*?)\\bottomrule", tex, re.S).group(1)
    cap = re.search(r"\\caption\{((?:(?!\\caption).)*?)\}\s*\\label\{tab:orientations\}", tex, re.S).group(1)
    cols = ["Dimension", "Pragmatic", "Ambitious", "Developmental", "Across Time", "Introspective", "Automated"]
    rows = []
    for r in re.split(r"\\\\", tab):
        r = re.sub(r"\\rowcolor\{[^}]*\}", "", r).strip()
        if not r: continue
        cells = [cv.convert(c) for c in r.split("&")]
        assert len(cells) == 7, cells
        rows.append(dict(zip(cols, cells)))

    if cv.missing or cv.unresolved:
        sys.exit(f"missing citations: {sorted(cv.missing)}; unresolved refs: {sorted(cv.unresolved)}")

    data = {
        "about": "Generated by scripts/data/build_orientations_arxiv.py from the arXiv v1 LaTeX source. Verbatim; do not edit by hand.",
        "source": {**ARXIV, "chapter": CHAPTER_NUM, "chapter_title": "Six Research Orientations"},
        "intro": [cv.convert(b) for k, b in split_blocks(intro) if k == "p"],
        "orientations": orientations,
        "comparison": {"section": num(ci), "intro": comparison_intro, "caption": f"Table {REF_NUMBERS['tab:orientations']}: " + cv.convert(cap), "columns": cols, "rows": rows},
        "decision": {"section": num(di), "paragraphs": decision},
        "tensions": {"section": num(ti), "paragraphs": tensions},
    }
    args.out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {args.out}: {len(orientations)} orientations, {len(rows)} table rows")


if __name__ == "__main__":
    main()
