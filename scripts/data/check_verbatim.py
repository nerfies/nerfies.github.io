#!/usr/bin/env python3
"""Check curated JSON against the ingested manuscript, exactly as tests/data.test.ts does.

  python3 scripts/data/check_verbatim.py FILE.json [FILE.json ...]

Prints every excerpt (string > 25 chars under an excerpt key) that is not verbatim in the
manuscript plain text, and every section id that does not exist. Exit code 1 if any.
"""
import glob, html, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from reanchor_excerpts import NON_EXCERPT, SECTION_KEYS  # same key lists as the test

ROOT = Path(__file__).resolve().parents[2]
h = "\n".join(open(f).read() for f in sorted(glob.glob(str(ROOT / "src/generated/chapters/*.html"))))
plain = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"</(p|li|h\d|tr|figcaption|caption)>", "\n", h)))).strip()
ids = set(re.findall(r'\sid="([^"]+)"', h))
bad = []

def walk(o, key, path):
    if key in SECTION_KEYS:
        for s in (o if isinstance(o, list) else [o]):
            if isinstance(s, str) and " (" not in s and s not in ids:
                bad.append(f"{path}: unknown section id {s!r}")
        return
    if key in NON_EXCERPT:
        return
    if isinstance(o, str):
        if len(o) > 25 and re.sub(r"\s+", " ", o).strip() not in plain:
            bad.append(f"{path}: not verbatim: {o[:120]}")
    elif isinstance(o, list):
        for i, x in enumerate(o):
            walk(x, key, f"{path}[{i}]")
    elif isinstance(o, dict):
        for k, v in o.items():
            walk(v, k, f"{path}.{k}")

for f in sys.argv[1:]:
    d = json.load(open(f))
    if isinstance(d, dict) and "methods" in d and isinstance(d["methods"], list):
        walk(d["methods"], "", f"{f}:methods"); walk(d.get("hypotheses", []), "", f"{f}:hypotheses")
    else:
        walk(d, "", f)
print("\n".join(bad) or "OK: all excerpts verbatim, all section ids exist")
sys.exit(1 if bad else 0)
