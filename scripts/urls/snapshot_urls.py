"""Record every published page and anchor of a built site (dist/) as the
public-URL registry, src/data/published-urls.json.

Run once per release, after `npm run build`, *before* the next change that may
move URLs. tests/urls.test.ts then fails if any recorded URL or anchor stops
resolving (directly, through a redirect page, or through an anchor alias).

    python3 scripts/urls/snapshot_urls.py --merge   # add new URLs, keep old ones
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
OUT = ROOT / "src" / "data" / "published-urls.json"
SKIP = ("pagefind/", "_astro/")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", action="store_true", help="keep URLs already in the registry")
    ap.add_argument("--note", default="", help="where this snapshot came from")
    args = ap.parse_args()
    pages: dict[str, list[str]] = {}
    for f in sorted(DIST.rglob("index.html")):
        rel = f.relative_to(DIST).parent.as_posix()
        path = "" if rel == "." else rel + "/"
        if path.startswith(SKIP):
            continue
        h = f.read_text()
        if 'name="mi-survey:redirect"' in h:
            continue  # redirect pages are aliases, not published content
        ids = sorted(set(re.findall(r'\sid="([^"]+)"', h)))
        # only anchors that are content (sections, figures, tables, equations, references)
        pages[path] = [i for i in ids if not i.startswith(("astro-", "main", "menu-", "theme-", "site-nav", "nav-", "chapter-nav", "search"))]
    old = json.loads(OUT.read_text()) if (args.merge and OUT.exists()) else {"pages": {}}
    merged = old["pages"]
    for p, ids in pages.items():
        merged[p] = sorted(set(merged.get(p, [])) | set(ids))
    out = {
        "about": "Every URL and in-page anchor published at https://tsglab.github.io/mi_survey/. "
                 "These must keep resolving; see docs/MAINTAINING.md#stable-urls.",
        "snapshots": old.get("snapshots", []) + [{"date": dt.date.today().isoformat(), "note": args.note}],
        "pages": dict(sorted(merged.items())),
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(merged)} pages, {sum(len(v) for v in merged.values())} anchors -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
