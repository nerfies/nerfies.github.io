#!/usr/bin/env python3
"""Write plain-text dumps of the ingested chapters to .ingest-plain/ (gitignored).

Section boundaries are marked [[SECTION id=…]]; figures/tables [[FIGURE id=…]].
The curated-data scripts and their verbatim checks read these files.
"""
import glob, html, os, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".ingest-plain"
OUT.mkdir(exist_ok=True)
for f in sorted(glob.glob(str(ROOT / "src/generated/chapters/*.html"))):
    h = open(f).read()
    h = re.sub(r'<section id="([^"]+)" class="level(\d)[^"]*">', lambda m: f'\n\n[[SECTION id={m.group(1)}]]\n', h)
    h = re.sub(r'<(figure|table)[^>]*id="([^"]+)"', lambda m: f'\n[[{m.group(1).upper()} id={m.group(2)}]]\n<x', h)
    h = re.sub(r'</(p|li|h\d|tr|figcaption|caption)>', '\n', h)
    t = html.unescape(re.sub(r'<[^>]+>', '', h))
    (OUT / (Path(f).stem + '.txt')).write_text(re.sub(r'\n{3,}', '\n\n', t))
print("wrote", OUT)
