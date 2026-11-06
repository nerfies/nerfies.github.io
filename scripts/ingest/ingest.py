#!/usr/bin/env python3
"""Convert the survey's LaTeX manuscript into HTML fragments for the online reader.

Usage:
    python3 scripts/ingest/ingest.py --manuscript /path/to/manuscript [--pdf-url URL]

The manuscript directory must contain main.tex, the chapter files it \\input{}s,
the .bib file, the figs/ directory and -- for exact numbering and PDF page links --
the compiled main.aux, main.toc and main.pdf from the same build.

Outputs (all regenerated on every run, never hand-edited):
    src/generated/chapters/<id>.html     one fragment per top-level section; <id> is the
                                         stable chapter id from src/data/chapter-ids.json
    src/generated/withheld/<id>.html     withheld draft chapters (gitignored, never committed)
    src/generated/withheld-fingerprints.json  hashes used to test that withheld text never leaks
    src/generated/references.html        bibliography
    src/generated/manifest.json          TOC, label map, cite tiers, provenance, audit
    public/figures/*                     converted figures
    public/survey.pdf                    copy of the compiled PDF (for page links)

The scientific text is never rewritten. The only transformations are mechanical:
editorial comment macros are removed, citation-colour macros are mapped to natbib,
numbering is taken from the LaTeX build so it matches the PDF. When the build's
main.bbl is present, citations and the bibliography are rendered from it, so author
labels and same-year suffixes (2024a, 2024b) are exactly natbib's.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "src" / "generated"
FIG_OUT = ROOT / "public" / "figures"
BASE_PLACEHOLDER = "@@BASE@@"  # replaced with the site base path at render time
CHAPTER_IDS = ROOT / "src" / "data" / "chapter-ids.json"
WITHHELD = ROOT / "src" / "data" / "withheld.json"
PRIVATE_OUT = OUT / "withheld"  # gitignored

# Editorial/reviewer comment macros defined in the manuscript preamble. Their
# arguments are internal discussion and must never reach the public site.
COMMENT_MACROS = [
    "narmeen", "aaron", "yuzhao", "hassan", "johnhew", "aaronm", "tony", "gab",
    "stella", "kyle", "naomi", "neel", "florent", "ziyu", "mor", "ye", "bzl",
    "lga", "riley", "fazl", "hunar", "abir", "mike", "todo",
]
ZERO_ARG_DROP = ["fix", "new"]

# Labels defined in main.tex, outside any chapter, mapped to where the site shows them.
EXTERNAL_TARGETS = {"fig:simplified-taxonomy": "#taxonomy"}  # homepage taxonomy figure

# Citation-colour macros -> (natbib command, evidence tier)
CITE_MACROS = {
    "citeest": ("citep", "established"), "citeem": ("citep", "emerging"),
    "citeflag": ("citep", "flagged"), "citetest": ("citet", "established"),
    "citetem": ("citet", "emerging"), "citetflag": ("citet", "flagged"),
    "citeestalp": ("citealp", "established"), "citeemalp": ("citealp", "emerging"),
    "citeflagalp": ("citealp", "flagged"), "cites": ("cite", None),
}


# ----------------------------------------------------------------- TeX helpers
def strip_comments(tex: str) -> str:
    out = []
    for line in tex.splitlines():
        i, cut = 0, None
        while i < len(line):
            if line[i] == "\\":
                i += 2
                continue
            if line[i] == "%":
                cut = i
                break
            i += 1
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


def braced(tex: str, start: int) -> tuple[str, int]:
    """Return (content, index after closing brace) for the group opening at tex[start]."""
    assert tex[start] == "{", tex[start:start + 30]
    depth, i = 0, start
    while i < len(tex):
        c = tex[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return tex[start + 1:i], i + 1
        i += 1
    raise ValueError("unbalanced braces near: " + tex[start:start + 80])


def remove_macro_calls(tex: str, name: str) -> tuple[str, int]:
    pat = re.compile(r"\\" + name + r"(?![A-Za-z])\s*\{")
    n = 0
    while True:
        m = pat.search(tex)
        if not m:
            return tex, n
        _, end = braced(tex, m.end() - 1)
        tex = tex[:m.start()] + tex[end:]
        n += 1


def map_cites(tex: str, tiers: dict[str, str]) -> str:
    for macro, (natbib, tier) in sorted(CITE_MACROS.items(), key=lambda kv: -len(kv[0])):
        pat = re.compile(r"\\" + macro + r"(?![A-Za-z])\s*\{")
        while True:
            m = pat.search(tex)
            if not m:
                break
            keys, end = braced(tex, m.end() - 1)
            if tier:
                for k in keys.split(","):
                    k = k.strip()
                    # strongest caution wins if a key is used with several tiers
                    rank = {"established": 0, "emerging": 1, "flagged": 2}
                    if k and rank[tier] >= rank.get(tiers.get(k, "established"), 0):
                        tiers[k] = tier
            tex = tex[:m.start()] + "\\" + natbib + "{" + keys + "}" + tex[end:]
    return tex


# ------------------------------------------------------- natbib citations (.bbl)
NATBIB_RE = re.compile(r"\\(citep|citet|citealp|citealt|cite|citeauthor|citeyear|citeyearpar)(\*?)\s*"
                       r"(?:\[([^\]]*)\])?\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}")


def tokenise_cites(tex: str, store: list[dict]) -> str:
    """Replace natbib commands with XCITE<n>X tokens; rendered after pandoc from main.bbl."""
    def f(m):
        cmd, _star, o1, o2, keys = m.groups()
        pre, post = ("", o1 or "") if o2 is None else (o1 or "", o2 or "")
        store.append({"cmd": cmd, "pre": pre, "post": post,
                      "keys": [k.strip() for k in keys.split(",") if k.strip()]})
        return f"XCITE{len(store) - 1}X"
    return NATBIB_RE.sub(f, tex)


def parse_bbl(path: Path) -> dict[str, dict]:
    """natbib .bbl -> {key: {short, year, body}} in bibliography order (TeX source strings)."""
    t = path.read_text(errors="replace")
    items: dict[str, dict] = {}
    for m in re.finditer(r"\\bibitem\[", t):
        i, depth = m.end(), 0
        while i < len(t):
            c = t[i]
            if c == "\\":
                i += 2
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == "]" and depth == 0:
                break
            i += 1
        label = t[m.end():i].strip()
        km = re.match(r"\s*\{([^}]*)\}", t[i + 1:])
        key = km.group(1).strip()
        start = i + 1 + km.end()
        nxt = re.search(r"\\bibitem\[|\\end\{thebibliography\}", t[start:])
        body = t[start:start + (nxt.start() if nxt else len(t) - start)]
        if label.startswith("{"):
            inner, end = braced(label, 0)
            if end == len(label):
                label = inner
        # natbib label: Short(Year)Long
        depth, j, open_at, close_at = 0, 0, None, None
        while j < len(label):
            c = label[j]
            if c == "\\":
                j += 2
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif depth == 0 and c == "(" and open_at is None:
                open_at = j
            elif depth == 0 and c == ")" and open_at is not None:
                close_at = j
                break
            j += 1
        if open_at is None or close_at is None:
            continue
        year = label[open_at + 1:close_at]
        year = re.sub(r"\{\\natexlab\{([^}]*)\}\}", r"\1", year)
        year = re.sub(r"\\natexlab\{([^}]*)\}", r"\1", year)
        body = re.sub(r"\{\\natexlab\{([^}]*)\}\}", r"\1", body)
        body = re.sub(r"\\natexlab\{([^}]*)\}", r"\1", body)
        items[key] = {"short": label[:open_at].strip(), "year": year.strip(),
                      "body": re.sub(r"\\newblock\s*", " ", body).strip()}
    return items


def tex_snippets_to_html(snips: list[str]) -> list[str]:
    """Convert many small TeX strings to inline HTML with one pandoc call."""
    doc = "\\begin{document}\n" + "\n\n".join(f"SNIPSTART{i}X {s}" for i, s in enumerate(snips)) + "\n\\end{document}\n"
    r = subprocess.run(["pandoc", "-f", "latex", "-t", "html5", "--wrap=none", "--katex"],
                       input="\\documentclass{article}\n" + doc, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("pandoc failed on bibliography snippets: " + r.stderr[:500])
    out = [""] * len(snips)
    for m in re.finditer(r"<p>SNIPSTART(\d+)X\s*(.*?)</p>", r.stdout, re.S):
        out[int(m.group(1))] = m.group(2).strip()
    return out


def tex_note(s: str) -> str:
    s = s.replace("~", "\u00a0").replace("\\S", "§").replace("---", "—").replace("--", "–").replace("\\,", "\u2009")
    s = re.sub(r"\\(?:emph|textit|textbf|text)\{([^}]*)\}", r"\1", s)
    return html.escape(s.replace("{", "").replace("}", "").strip(), quote=False)


def render_citation(c: dict, lab: dict[str, tuple[str, str]]) -> str:
    """natbib authoryear,round with citesep ';', aysep ',', yysep ';' (the manuscript's \\setcitestyle)."""
    cmd, keys = c["cmd"], c["keys"]
    pre, post = tex_note(c["pre"]), tex_note(c["post"])
    a = lambda k, text: f'<a href="#ref-{k}" role="doc-biblioref">{text}</a>'
    groups: list[list] = []  # [short or None, [(key, year)]]
    for k in keys:
        if k not in lab:
            groups.append([None, [(k, None)]])
        elif groups and groups[-1][0] == lab[k][0]:
            groups[-1][1].append((k, lab[k][1]))
        else:
            groups.append([lab[k][0], [(k, lab[k][1])]])
    parts = []
    if cmd in ("citet", "cite"):
        for gi, (short, ys) in enumerate(groups):
            note = f", {post}" if post and gi == len(groups) - 1 else ""
            if short is None:
                parts.append(a(ys[0][0], f"{ys[0][0]}?"))
            elif len(ys) == 1:
                k, y = ys[0]
                parts.append(a(k, f"{short} ({y})") if not note else a(k, f"{short} ({y}") + f"{note})")
            else:
                parts.append(f"{short} (" + "; ".join(a(k, y) for k, y in ys) + f"{note})")
        body = "; ".join(parts)
        return f'<span class="citation" data-cites="{" ".join(keys)}">{pre + " " if pre else ""}{body}</span>'
    if cmd == "citeauthor":
        body = ", ".join(a(ys[0][0], short or ys[0][0]) for short, ys in groups)
    elif cmd in ("citeyear", "citeyearpar"):
        body = "; ".join(a(k, y or k) for _s, ys in groups for k, y in ys)
        if cmd == "citeyearpar":
            body = f"({body})"
    else:  # citep, citealp, citealt
        sep = " " if cmd == "citealt" else ", "
        for short, ys in groups:
            if short is None:
                parts.append(a(ys[0][0], f"{ys[0][0]}?"))
            else:
                parts.append(a(ys[0][0], f"{short}{sep}{ys[0][1]}") + "".join(f"; {a(k, y)}" for k, y in ys[1:]))
        body = (pre + " " if pre else "") + "; ".join(parts) + (f", {post}" if post else "")
        if cmd == "citep":
            body = f"({body})"
    return f'<span class="citation" data-cites="{" ".join(keys)}">{body}</span>'


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def fingerprint(s: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", s).strip().lower().encode()).hexdigest()[:24]


def unwrap_macro(tex: str, name: str) -> str:
    pat = re.compile(r"\\" + name + r"(?![A-Za-z])\s*\{")
    while True:
        m = pat.search(tex)
        if not m:
            return tex
        inner, end = braced(tex, m.end() - 1)
        tex = tex[:m.start()] + inner + tex[end:]


# ------------------------------------------------------------- aux / toc parse
def parse_aux(aux: Path) -> dict[str, dict]:
    labels = {}
    if not aux.exists():
        return labels
    text = aux.read_text(errors="replace")
    for m in re.finditer(r"\\newlabel\{([^}]*)\}\{", text):
        name = m.group(1)
        if name.endswith("@cref"):
            continue
        try:
            body, _ = braced(text, m.end() - 1)
            parts, j = [], 0
            while j < len(body) and len(parts) < 4:
                if body[j] == "{":
                    p, j = braced(body, j)
                    parts.append(p)
                else:
                    j += 1
        except Exception:
            continue
        if len(parts) >= 2:
            anchor = parts[3] if len(parts) > 3 else ""
            labels[name] = {"num": parts[0], "page": parts[1], "kind": anchor.split(".")[0]}
    return labels


def parse_toc(toc: Path) -> list[dict]:
    entries = []
    if not toc.exists():
        return entries
    for line in toc.read_text(errors="replace").splitlines():
        m = re.match(r"\\contentsline \{(section|subsection|subsubsection)\}\{(.*)\}\{([^{}]*)\}\{([^{}]*)\}%?$", line)
        if not m:
            continue
        level, body, page, anchor = m.groups()
        nm = re.match(r"\\numberline \{([^}]*)\}(.*)", body)
        if not nm:
            continue  # unnumbered (preface etc.)
        entries.append({"level": ["section", "subsection", "subsubsection"].index(level) + 1,
                        "num": nm.group(1), "page": page})
    return entries


# ------------------------------------------------------------------- figures
def convert_figure(src: Path) -> str:
    FIG_OUT.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", src.stem).strip("-").lower()
    if src.suffix.lower() == ".pdf":
        dest = FIG_OUT / f"{stem}.svg"
        if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
            subprocess.run(["pdftocairo", "-svg", "-f", "1", "-l", "1", str(src), str(dest)], check=True)
        # SVGs from complex PDFs can be huge; fall back to a high-dpi PNG if so
        if dest.stat().st_size > 2_500_000:
            dest.unlink()
            png = FIG_OUT / f"{stem}.png"
            subprocess.run(["pdftocairo", "-png", "-r", "200", "-singlefile", str(src), str(png.with_suffix(""))], check=True)
            return png.name
        return dest.name
    dest = FIG_OUT / f"{stem}{src.suffix.lower()}"
    shutil.copyfile(src, dest)
    return dest.name


# ------------------------------------------------------------------ main flow
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manuscript", required=True, type=Path)
    ap.add_argument("--main", default="main.tex")
    ap.add_argument("--publish-pdf", action="store_true",
                    help="copy the compiled PDF into public/ for page links. Only use with a "
                         "camera-ready PDF: draft builds render reviewer comments.")
    ap.add_argument("--status", default="draft",
                    help="'draft' shows a provisional banner on every chapter; 'final' removes it")
    args = ap.parse_args()
    ms: Path = args.manuscript.resolve()
    main_tex = (ms / args.main).read_text()
    stem = Path(args.main).stem

    body_start = main_tex.index("\\begin{document}")
    doc = strip_comments(main_tex[body_start:])
    inputs = re.findall(r"\\input\{(chapters/[^}]+)\}|(\\appendix)", doc)
    order, appendix = [], False
    for path, app in inputs:
        if app:
            appendix = True
            continue
        order.append((path, appendix))

    audit = {"removed_comment_macros": 0, "dropped_environments": [], "warnings": []}
    bbl = ms / f"{stem}.bbl"
    bbl_items = parse_bbl(bbl) if bbl.exists() else None
    cite_store: list[dict] = []
    tiers: dict[str, str] = {}
    pieces = []
    figures = {}
    eq_counter, eq_labels = [0], {}
    for path, is_app in order:
        f = ms / (path if path.endswith(".tex") else path + ".tex")
        tex = strip_comments(f.read_text())
        for name in COMMENT_MACROS:
            tex, n = remove_macro_calls(tex, name)
            audit["removed_comment_macros"] += n
        for name in ZERO_ARG_DROP:
            tex = re.sub(r"\\" + name + r"(?![A-Za-z])", "", tex)
        tex = map_cites(tex, tiers)
        tex = unwrap_macro(tex, "citeleaf")
        if bbl_items is not None:
            tex = tokenise_cites(tex, cite_store)
        tex = tex.replace("\\cmark", "✓").replace("\\xmark", "✗")
        tex = re.sub(r"\\rowcolor(\[[^\]]*\])?\{[^}]*\}", "", tex)
        tex = re.sub(r"\\(?:hspace|vspace)\*?\{[^}]*\}", "", tex)
        # tcolorbox environments (warningbox, practicebox, …) take their title as an optional argument;
        # pandoc drops it, so emit it as the box's first line.
        tex = re.sub(r"\\begin\{(definitionbox|examplebox|insightbox|practicebox|theorybox|warningbox)\}\[([^\]]*)\]",
                     lambda m: f"\\begin{{{m.group(1)}}}\n\\noindent\\textbf{{{m.group(2)}}}\n\n", tex)
        tex = tex.replace("\\begin{wrapfigure}", "\\begin{figure}").replace("\\end{wrapfigure}", "\\end{figure}")
        tex = re.sub(r"(\\begin\{figure\})\{[^}]*\}\{[^}]*\}", r"\1", tex)
        # equations: anchor + exact number from the LaTeX build
        # The manuscript numbers `equation` globally (no \numberwithin), so the
        # n-th unstarred equation in reading order is (n) in the PDF.
        def eq_anchor(m):
            env_body = m.group(0)
            if m.group(2) == "*" or "\\nonumber" in env_body or "\\notag" in env_body:
                return env_body
            eq_counter[0] += 1
            n = eq_counter[0]
            lab = re.search(r"\\label\{([^}]*)\}", env_body)
            inner = m.group(3)
            if lab:
                inner = inner.replace(lab.group(0), "")
                eq_labels[lab.group(1)] = str(n)
            anchor = f"\\hypertarget{{eq-{n}}}{{}}" + (f"\\hypertarget{{{lab.group(1)}}}{{}}" if lab else "")
            return f"{anchor}\n\\begin{{equation*}}{inner}\\tag{{{n}}}\\end{{equation*}}"
        tex = re.sub(r"\\begin\{(equation)(\*?)\}(.*?)\\end\{equation\*?\}", eq_anchor, tex, flags=re.S)

        def fig_path(m):
            opts, p = m.group(1) or "", m.group(2)
            src = ms / p
            if not src.exists():
                cands = list((ms / Path(p).parent).glob(Path(p).name + ".*"))
                src = cands[0] if cands else src
            if not src.exists():
                audit["warnings"].append(f"missing figure file {p}")
                return m.group(0)
            name = convert_figure(src)
            figures[p] = name
            return f"\\includegraphics{{{BASE_PLACEHOLDER}figures/{name}}}"
        tex = re.sub(r"\\includegraphics(\[[^\]]*\])?\{([^}]*)\}", fig_path, tex)
        for env in ("forest", "tikzpicture"):
            for _ in re.finditer(r"\\begin\{" + env + r"\}", tex):
                audit["dropped_environments"].append({"file": f.name, "env": env})
            tex = re.sub(r"\\begin\{" + env + r"\}.*?\\end\{" + env + r"\}",
                         "\\\\textbf{@@UNRENDERED:" + env + "@@}", tex, flags=re.S)
        if is_app and not any(p[1] for p in pieces):
            tex = "\\appendix\n" + tex
        pieces.append((tex, is_app))

    audit["numbered_equations"] = eq_counter[0]
    combined = "\\documentclass{article}\n\\begin{document}\n" + "\n\n".join(p for p, _ in pieces) + "\n\\end{document}\n"
    work = ROOT / ".ingest-tmp"
    work.mkdir(exist_ok=True)
    (work / "combined.tex").write_text(combined)
    bib = next(iter(ms.glob("*.bib")), None)  # only needed without a .bbl (e.g. the arXiv source ships none)
    cmd = ["pandoc", str(work / "combined.tex"), "-f", "latex", "-t", "html5",
           "--katex", "--section-divs", "--wrap=none", "--reference-location=section",
           "-o", str(work / "combined.html")]
    if bbl_items is None:  # no compiled bibliography: fall back to citeproc
        if bib is None:
            sys.exit("no .bbl and no .bib in the manuscript directory")
        cmd[5:5] = ["--citeproc", "--bibliography", str(bib), "--metadata", "link-citations=true",
                    "--metadata", "reference-section-title=References"]
        audit["warnings"].append("no .bbl found: citations rendered by citeproc, which may differ from the PDF")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr)
    for line in r.stderr.splitlines():
        if "Citeproc: citation" in line and "not found" in line:
            audit["warnings"].append(line.strip())
    out_html = (work / "combined.html").read_text()
    refs_override = None
    if bbl_items is not None:
        cited = [k for c in cite_store for k in c["keys"]]
        order = [k for k in bbl_items if k in set(cited)]
        conv = tex_snippets_to_html([bbl_items[k]["short"] for k in order] + [bbl_items[k]["year"] for k in order]
                                    + [bbl_items[k]["body"] for k in order])
        n = len(order)
        lab = {k: (conv[i], conv[n + i]) for i, k in enumerate(order)}
        out_html = re.sub(r"XCITE(\d+)X", lambda m: render_citation(cite_store[int(m.group(1))], lab), out_html)
        if "XCITE" in out_html:
            sys.exit("a citation token survived conversion; check the cite commands near: "
                     + out_html[out_html.index("XCITE") - 80:out_html.index("XCITE") + 40])
        refs_override = ('<div id="refs" class="references csl-bib-body hanging-indent" role="list">\n'
                         + "\n".join(f'<div id="ref-{k}" class="csl-entry" role="listitem">{conv[2 * n + i]}</div>'
                                      for i, k in enumerate(order)) + "\n</div>")
        audit["citations_rendered_from_bbl"] = len(cite_store)

    labels = parse_aux(ms / f"{stem}.aux")
    toc_nums = parse_toc(ms / f"{stem}.toc")
    build_chapters(out_html, labels, toc_nums, tiers, audit, figures, ms, stem, args.status, args.publish_pdf,
                   refs_override, bbl_items is not None)
    shutil.rmtree(work)


def build_chapters(doc, labels, toc_nums, tiers, audit, figures, ms, stem, status, publish_pdf=False,
                   refs_override=None, from_bbl=False):
    # references
    refs_m = re.search(r'<div id="refs".*?</div>\s*(?=</section>|$)', doc, re.S)
    refs_html = ""
    ref_sec = re.search(r'<section id="bibliography"[^>]*>.*?</section>\s*$', doc, re.S) or \
              re.search(r'<section[^>]*class="[^"]*level1[^"]*"[^>]*>\s*<h1[^>]*>References</h1>.*', doc, re.S)
    if ref_sec:
        refs_html = ref_sec.group(0)
        doc = doc[:ref_sec.start()]
    elif refs_m:
        refs_html = refs_m.group(0)
        doc = doc[:refs_m.start()] + doc[refs_m.end():]
    refs_html = re.sub(r"^<section[^>]*>\s*<h1[^>]*>.*?</h1>", "", refs_html, flags=re.S)
    refs_html = re.sub(r"</section>\s*$", "", refs_html)
    if refs_override is not None:
        refs_html = refs_override

    body = re.search(r"<body[^>]*>(.*)</body>", doc, re.S)
    doc = body.group(1) if body else doc

    # top-level sections
    tops = list(re.finditer(r'<section id="([^"]+)" class="level1[^"]*">', doc))
    if not tops:
        sys.exit("pandoc produced no top-level sections")

    # assign numbers to every numbered heading in order, matching the LaTeX toc
    head_re = re.compile(r'<section id="([^"]+)" class="level([1-3])([^"]*)">\s*<h([1-3])([^>]*)>(.*?)</h\4>', re.S)
    toc_iter = iter(toc_nums)
    heading_meta = {}
    appendix_seen = False
    for m in head_re.finditer(doc):
        sid, lvl, cls = m.group(1), int(m.group(2)), m.group(3)
        if "unnumbered" in cls:
            if lvl == 1:
                heading_meta[sid] = {"num": "", "page": None, "level": lvl, "title": strip_tags(m.group(6)).strip()}
            continue
        nxt = next(toc_iter, None)
        if nxt is None or nxt["level"] != lvl:
            audit["warnings"].append(f"toc mismatch at heading '{strip_tags(m.group(6))[:60]}'")
            num, page = None, None
        else:
            num, page = nxt["num"], nxt["page"]
        heading_meta[sid] = {"num": num, "page": page, "level": lvl,
                             "title": strip_tags(m.group(6)).strip()}

    # stable chapter ids: matched by LaTeX \label, else by title, from the committed registry
    registry = json.loads(CHAPTER_IDS.read_text())["chapters"]
    def chapter_id(top_id: str, title: str):
        for e in registry:
            if top_id in e.get("labels", []) or norm_title(title) in {norm_title(t) for t in e.get("titles", [])}:
                return e["id"]
        return None

    # label -> page & number lookup for anchors pandoc created
    id_to_chapter = {}
    chapters = []
    unmatched = []
    for i, m in enumerate(tops):
        end = tops[i + 1].start() if i + 1 < len(tops) else len(doc)
        frag = doc[m.start():end]
        meta = heading_meta.get(m.group(1), {})
        num = meta["num"] if meta.get("num") is not None else str(i + 1)
        slug = chapter_id(m.group(1), meta.get("title", ""))
        if slug is None:
            unmatched.append(f"  {num}. {meta.get('title', '')}  (label: {m.group(1)})")
            continue
        appendix = bool(re.match(r"^[A-Z]$", num))
        for idm in re.finditer(r'\sid="([^"]+)"', frag):
            id_to_chapter[idm.group(1)] = slug
        chapters.append({"slug": slug, "num": num, "title": meta.get("title", ""), "html": frag,
                         "appendix": appendix, "page": meta.get("page")})

    if unmatched:
        sys.exit("These chapters have no stable id in src/data/chapter-ids.json. Add an entry for each "
                 "(new id, or the LaTeX label / title of an existing chapter it replaces):\n" + "\n".join(unmatched))
    if len({c["slug"] for c in chapters}) != len(chapters):
        sys.exit("two chapters matched the same stable id in src/data/chapter-ids.json")
    withheld = set(json.loads(WITHHELD.read_text())["chapters"]) if status != "final" else set()
    unknown = withheld - {c["slug"] for c in chapters}
    if unknown:
        sys.exit(f"src/data/withheld.json lists chapters that do not exist: {sorted(unknown)}")
    withheld_ids = {i for c in chapters if c["slug"] in withheld for i in re.findall(r'\sid="([^"]+)"', c["html"])}

    ref_keys = set(re.findall(r'<div id="ref-([^"]+)" class="csl-entry"', refs_html))

    # rewrite headings with numbers + permalink, figures/tables captions, refs, eq tags
    def label_num(lbl):
        return labels.get(lbl, {}).get("num")

    for ch in chapters:
        h = ch["html"]

        def head_sub(m):
            sid = m.group(1)
            meta = heading_meta.get(sid)
            inner = m.group(6)
            if meta and meta.get("num"):
                inner = f'<span class="secnum">{meta["num"]}</span> {inner}'
            pdf = f' data-pdf-page="{meta["page"]}"' if meta and meta.get("page") else ""
            return (f'<section id="{sid}" class="level{m.group(2)}{m.group(3)}">'
                    f'<h{m.group(4)}{m.group(5)}{pdf}>{inner}'
                    f'<a class="anchor" href="#{sid}" aria-label="Link to this section">#</a></h{m.group(4)}>')
        h = head_re.sub(head_sub, h)

        # figures/tables: pandoc keeps the LaTeX label as the element id
        def cap_sub(kind_word, tag):
            def f(m):
                fid = m.group(1)
                num = label_num(fid)
                rest = m.group(2)
                if num:
                    rest = re.sub(r"(<figcaption[^>]*>|<caption[^>]*>)", rf'\1<span class="capnum">{kind_word} {num}:</span> ', rest, count=1)
                return f'<{tag} id="{fid}"' + rest
            return f
        # Figures with subfigures: pandoc nests <figure>s and gives the outer one the last subfigure's
        # label. Number the subfigures first, then give the outer caption the parent number (7a, 7b -> 7).
        def group_open(m):
            return f'<figure class="subfigures"{m.group(2)}>'
        h = re.sub(r'<figure id="([^"]+)"([^>]*)>(?=\s*<figure )', group_open, h)
        h = re.sub(r'<figure id="([^"]+)"((?:(?!<figure).)*?</figure>)', cap_sub("Figure", "figure"), h, flags=re.S)
        def group_cap(m):
            nums = re.findall(r'class="capnum">Figure (\d+)[a-z]?:', m.group(0))
            if not nums:
                return m.group(0)
            return re.sub(r'(</figure>\s*<figcaption>)(?![^<]*<span class="capnum")', rf'\1<span class="capnum">Figure {nums[-1]}:</span> ', m.group(0)[::-1][::-1], count=0)[:0] + m.group(1) + m.group(2) + f'<figcaption><span class="capnum">Figure {nums[-1]}:</span> ' + m.group(3)
        h = re.sub(r'(<figure class="subfigures"[^>]*>)(.*</figure>\s*)<figcaption>((?:(?!<figure).)*?</figcaption>\s*</figure>)', group_cap, h, flags=re.S)
        h = re.sub(r'<table id="([^"]+)"(.*?</table>)', cap_sub("Table", "table"), h, flags=re.S)
        # tables wrapped in a div with the label id (pandoc 3 behaviour)
        def tabdiv(m):
            tid = m.group(1)
            num = label_num(tid)
            inner = m.group(2)
            if num and "<caption" in inner:
                inner = re.sub(r"(<caption[^>]*>)", rf'\1<span class="capnum">Table {num}:</span> ', inner, count=1)
            return f'<div id="{tid}" class="table-wrap">{inner}</div>'
        h = re.sub(r'<div id="(tab[^"]*)"[^>]*>(.*?</table>)\s*</div>', tabdiv, h, flags=re.S)

        # alt text for figures = the figure's caption (pandoc leaves alt empty for LaTeX figures)
        def add_alt(m):
            fig = m.group(0)
            cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", fig, re.S)
            alt = strip_tags(cap.group(1)).strip() if cap else "Figure from the survey"
            alt = html.escape(re.sub(r"\s+", " ", alt)[:300], quote=True)
            return re.sub(r"<img(?![^>]*\balt=)", lambda _m: f'<img alt="{alt}" loading="lazy"', fig)
        h = re.sub(r"<figure\b.*?</figure>", add_alt, h, flags=re.S)

        # equation numbers
        h = re.sub(r"@@EQ:([^@]+)@@", lambda m: label_num(m.group(1)) or "?", h)

        # cross references: pandoc emits data-reference="label"
        def xref(m):
            lbl = m.group(2)
            num = label_num(lbl)
            text = m.group(3)
            # \ref always prints LaTeX's number (from main.aux); pandoc's own figure/table
            # numbering drifts when floats sit outside the chapters (e.g. the taxonomy figure in main.tex).
            if num and ('data-reference-type="ref"' in m.group(1) or text.strip("[]") == lbl or text.strip() in ("", "??")):
                text = num
            target = id_to_chapter.get(lbl)
            href = f"{BASE_PLACEHOLDER}handbook/{target}/#{lbl}" if target else f"#{lbl}"
            if not target and lbl in EXTERNAL_TARGETS:
                return f'<a href="{BASE_PLACEHOLDER}{EXTERNAL_TARGETS[lbl]}"{m.group(1)}>{text}</a>'
            if target in withheld and target != ch["slug"]:
                href = f"{BASE_PLACEHOLDER}handbook/{target}/"
            if not target:
                audit["warnings"].append(f"unresolved cross-reference {lbl}")
            return f'<a href="{href}"{m.group(1)}>{text}</a>'
        h = re.sub(r'<a href="#[^"]*"([^>]*data-reference="([^"]+)"[^>]*)>(.*?)</a>', xref, h, flags=re.S)

        # citations -> global references page, carrying the evidence tier
        def cite(m):
            key = m.group(1)
            if key not in ref_keys:
                audit["warnings"].append(f"citation key not in bibliography: {key}")
                return f'<a class="cite cite-missing" data-missing-cite="{key}" title="Citation missing from the bibliography"'
            tier = tiers.get(key)
            cls = f' class="cite cite-{tier}"' if tier else ' class="cite"'
            return f'<a href="{BASE_PLACEHOLDER}references/#ref-{key}"{cls} data-cite="{key}"'
        h = re.sub(r'<a href="#ref-([^"]+)"', cite, h)
        def other_chapter(m):
            target = id_to_chapter.get(m.group(1))
            if not target or target == ch["slug"]:
                return m.group(0)
            if target in withheld:
                return f'<a href="{BASE_PLACEHOLDER}handbook/{target}/"'
            return f'<a href="{BASE_PLACEHOLDER}handbook/{target}/#{m.group(1)}"'
        h = re.sub(r'<a href="#([^"]+)"', other_chapter, h)
        if "@@UNRENDERED" in h:
            pg = ch.get("page")
            h = re.sub(r"<strong>@@UNRENDERED:(\w+)@@</strong>",
                       lambda m: f'<span class="unrendered">This diagram ({m.group(1)}) is only available in the '
                                 f'<a href="{BASE_PLACEHOLDER}survey.pdf#page={pg or 1}">PDF</a>.</span>', h)
        ch["html"] = h

    # reference entries
    ref_entries = []
    for m in re.finditer(r'<div id="ref-([^"]+)" class="csl-entry"[^>]*>(.*?)</div>', refs_html, re.S):
        ref_entries.append({"key": m.group(1), "text": strip_tags(m.group(2)).strip(),
                            "tier": tiers.get(m.group(1))})
        refs_html = refs_html.replace(m.group(0),
            m.group(0).replace('class="csl-entry"', f'class="csl-entry tier-{tiers.get(m.group(1), "none")}"'), 1)

    # outputs
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "chapters").mkdir(parents=True)
    PRIVATE_OUT.mkdir(parents=True)

    def text_prints(h: str) -> tuple[set, set, set]:
        plain = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"</(p|li|h\d|tr|figcaption|caption)>", "\n", h)))
        sentences = [x for x in re.split(r"(?<=[.!?])\s+|\n", plain) if len(re.sub(r"\s+", " ", x).strip()) >= 40]
        heads = [re.sub(r"^[\dA-Z.]+\s+", "", strip_tags(t).replace("#", "")).strip()
                 for t in re.findall(r"<h[1-6][^>]*>(.*?)</h[1-6]>", h, re.S)]
        words = re.findall(r"[a-z0-9]+", plain.lower())
        shingles = {fingerprint(" ".join(words[i:i + 10])) for i in range(len(words) - 9)}
        return ({fingerprint(x) for x in sentences} | shingles, {fingerprint(x) for x in heads if len(x) >= 4},
                {fingerprint(i) for i in re.findall(r'\sid="([^"]+)"', h)})
    # text that also appears in published chapters (e.g. a generic heading such as "Grokking") is not secret
    public = [text_prints(c["html"]) for c in chapters if c["slug"] not in withheld] + [text_prints(refs_html)]
    pub_s, pub_h, pub_i = (set().union(*[p[i] for p in public]) if public else set() for i in range(3))
    fingerprints = {}
    for ch in chapters:
        if ch["slug"] in withheld:
            (PRIVATE_OUT / f"{ch['slug']}.html").write_text(ch["html"])
            sents, heads, ids = text_prints(ch["html"])
            fingerprints[ch["slug"]] = {
                "sentences": sorted(sents - pub_s),
                "headings": sorted(heads - pub_h - {fingerprint(ch["title"])}),  # the title stays public (navigation)
                "ids": sorted(ids - pub_i - {fingerprint(ch["slug"]), fingerprint(ch["title"])}),
            }
        else:
            (OUT / "chapters" / f"{ch['slug']}.html").write_text(ch["html"])
    (OUT / "references.html").write_text(refs_html)
    (OUT / "withheld-fingerprints.json").write_text(json.dumps(
        {"about": "SHA-256 prefixes of normalised sentences, 10-word sequences, headings and ids of withheld draft chapters. "
                  "tests/site.test.ts checks that none appear anywhere in the built site.", "chapters": fingerprints}, indent=1))

    toc = []
    for ch in chapters:
        subs = []
        for m in head_re.finditer(ch["html"]):
            sid = m.group(1)
            hm = heading_meta.get(sid)
            if hm and hm["level"] in (2, 3) and ch["slug"] not in withheld:
                subs.append({"id": sid, "num": hm["num"], "title": hm["title"], "level": hm["level"], "page": hm["page"]})
        toc.append({"slug": ch["slug"], "num": ch["num"], "title": ch["title"], "appendix": ch["appendix"],
                    "page": ch["page"], "sections": subs, "withheld": ch["slug"] in withheld,
                    "words": len(strip_tags(ch["html"]).split())})

    pdf = ms / f"{stem}.pdf"
    pdf_offset = None
    public_pdf = ROOT / "public" / "survey.pdf"
    if public_pdf.exists():
        public_pdf.unlink()
    if pdf.exists() and publish_pdf:
        shutil.copyfile(pdf, public_pdf)
    if pdf.exists():
        pdf_offset = find_pdf_offset(pdf, toc)
        if pdf_offset is None:
            audit["warnings"].append("could not determine PDF page offset; PDF links point to printed page numbers")

    git = lambda *a: subprocess.run(["git", "-C", str(ms), *a], capture_output=True, text=True).stdout.strip()
    manifest = {
        "provenance": {
            "status": status,
            "source_dir_name": ms.name,
            "source_commit": git("rev-parse", "--short", "HEAD") or None,
            "source_commit_date": git("log", "-1", "--format=%cs") or None,
            "main_tex_sha256": hashlib.sha256((ms / f"{stem}.tex").read_bytes()).hexdigest()[:16],
            "pdf_included": bool(pdf.exists() and publish_pdf),
            "pdf_page_offset": pdf_offset,
            "citations": "natbib labels from the compiled .bbl" if from_bbl else "citeproc (no .bbl found)",
            "generated": dt.date.today().isoformat(),
        },
        "toc": toc,
        "labels": {k: {**v, "chapter": id_to_chapter.get(k)} for k, v in labels.items()
                   if id_to_chapter.get(k) not in withheld or k == id_to_chapter.get(k)},
        "cite_tiers": tiers,
        "references": ref_entries,
        "figures": figures,
        "audit": audit,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    print(f"chapters={len(chapters)} refs={len(ref_entries)} figures={len(figures)} "
          f"removed_comments={audit['removed_comment_macros']} warnings={len(audit['warnings'])} "
          f"dropped_envs={len(audit['dropped_environments'])}")


def find_pdf_offset(pdf: Path, toc: list[dict]):
    """Physical page index minus printed page number, verified on several chapters."""
    try:
        pages = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout.split("\f")
    except Exception:
        return None
    norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
    headings = [norm(f"{c['num']} {c['title']}") for c in toc]
    is_toc_page = [sum(h in norm(t) for h in headings) > 4 for t in pages]
    offsets = []
    for ch in toc[:16]:
        if not (ch.get("page") or "").isdigit():
            continue
        heading = norm(f"{ch['num']} {ch['title']}")
        for i, text in enumerate(pages):
            if is_toc_page[i]:  # table of contents lists every heading
                continue
            if heading in norm(text):
                offsets.append(i + 1 - int(ch["page"]))
                break
    if not offsets:
        return None
    best = max(set(offsets), key=offsets.count)
    return best if offsets.count(best) >= max(2, len(offsets) // 2) else None


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s))


if __name__ == "__main__":
    main()
