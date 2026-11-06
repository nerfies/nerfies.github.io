#!/usr/bin/env python3
"""Map every published anchor that no longer exists to its closest section in the current manuscript.

Matches stay within the chapter the old page now redirects to; anything below 0.7 lands on the chapter top.

Run after `npm run build`, when a new manuscript version has been ingested:

  python3 scripts/urls/suggest_anchor_redirects.py --old-ref main [--write]

For each anchor in src/data/published-urls.json that is missing from its (redirected) page,
it looks for, in order: the same id in any chapter; else the section of the new manuscript
whose title best matches the old section's title (old titles come from the manifest at
--old-ref); else the top of the chapter the page now redirects to. It prints the proposed
`anchors` entries for src/data/redirects.json, with the match score, and writes them with --write.
Review the low-scoring ones by hand.
"""
import argparse, difflib, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"


def norm(s):
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower().replace("behavior", "behaviour").replace("ization", "isation").replace("izing", "ising").replace("color", "colour"))
    return " ".join(w for w in s.split() if w not in {"the", "a", "an", "of", "and", "for", "in", "to", "on", "as", "via", "sec", "subsec", "fig", "tab"})


def final_path(path, pages):
    for _ in range(6):
        if path in pages:
            path = pages[path]
        else:
            return path
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-ref", default="main")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    reg = json.loads((ROOT / "src/data/published-urls.json").read_text())["pages"]
    red = json.loads((ROOT / "src/data/redirects.json").read_text())
    new = json.loads((ROOT / "src/generated/manifest.json").read_text())
    old = json.loads(subprocess.run(["git", "show", f"{a.old_ref}:src/generated/manifest.json"], cwd=ROOT,
                                    capture_output=True, text=True, check=True).stdout)

    head_re = re.compile(r'<section id="([^"]+)" class="level(\d)[^"]*">\s*<h\d[^>]*>(.*?)</h\d>', re.S)
    strip = lambda t: re.sub(r"<[^>]+>", "", t)

    def headings(html):
        return [(m.group(1), int(m.group(2)), strip(m.group(3))) for m in head_re.finditer(html)]

    # every heading (all levels, incl. \paragraph) of the old and new chapter fragments
    old_titles = {}
    files = subprocess.run(["git", "ls-tree", "--name-only", f"{a.old_ref}:src/generated/chapters/"], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.split()
    for f in files:
        h = subprocess.run(["git", "show", f"{a.old_ref}:src/generated/chapters/{f}"], cwd=ROOT, capture_output=True, text=True).stdout
        for sid, _, t in headings(h):
            old_titles.setdefault(sid, t)
    cands, tops = [], {}  # (slug, id, title)
    for ch in new["toc"]:
        h = (ROOT / "src/generated/chapters" / f"{ch['slug']}.html").read_text()
        hs = headings(h)
        if hs:
            tops[ch["slug"]] = hs[0][0]
        cands += [(ch["slug"], sid, t) for sid, _, t in hs]

    def page_has(path, id_):
        f = DIST / path / "index.html"
        return f.exists() and f' id="{id_}"' in f.read_text()

    out, report = {}, []
    for path, ids in reg.items():
        if not path.startswith("handbook/"):
            continue
        end = final_path(path, red["pages"])
        for id_ in ids:
            if page_has(end, id_) or f"{path}#{id_}" in red["anchors"]:
                continue
            # 1. same id elsewhere
            hit = next(((c[0], c[1]) for c in cands if c[1] == id_), None)
            score = 1.0
            if not hit:
                title = norm(old_titles.get(id_, id_.replace("-", " ")))
                best, score = None, 0.0
                here = end.split("/")[1]
                for slug, sid, t in cands:
                    if slug != here:  # a wrong section elsewhere is worse than the chapter top
                        continue
                    r = difflib.SequenceMatcher(None, title, norm(t)).ratio()
                    if r > score:
                        best, score = (slug, sid), r
                hit = best if score >= 0.7 else None
            if not hit:  # 3. top of the chapter the page now points to
                slug = end.split("/")[1]
                first = tops.get(slug)
                if not first:
                    report.append((0, f"{path}#{id_}", "?? no target"))
                    continue
                hit, score = (slug, first), 0.0
            target = f"handbook/{hit[0]}/#{hit[1]}"
            out[f"{path}#{id_}"] = target
            report.append((round(score, 2), f"{path}#{id_}", target))

    for r in sorted(report):
        print(*r, sep="  ")
    print(f"{len(out)} anchor redirects")
    if a.write:
        red["anchors"].update(out)
        (ROOT / "src/data/redirects.json").write_text(json.dumps(red, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
