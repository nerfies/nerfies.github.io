#!/usr/bin/env python3
"""Give context-dependent quotes their antecedent.

A quote that opens with a pronoun or connective ("This …", "These …", "However, …") reads as a
fragment when shown alone. For each such quote in the curated data, prepend the preceding
sentence(s) of the same paragraph from the manuscript, so the quote stays verbatim and contiguous.

  python3 scripts/data/extend_context.py [--write]
"""
import glob, html, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from reanchor_excerpts import NON_EXCERPT, SECTION_KEYS
ROOT = Path(__file__).resolve().parents[2]
START = re.compile(r'^(However|This|These|That|Those|It|Its|They|Their|Such|Both|Here|Moreover|Thus|Therefore|Hence|Specifically|Similarly|Additionally|Furthermore|Instead|Conversely|Nevertheless|Notably|Importantly|Crucially|In contrast|In particular|For example|As a result|Also|But|And)\b')
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(“\"])")

h = "\n".join(open(f).read() for f in sorted(glob.glob(str(ROOT / "src/generated/chapters/*.html"))))
blocks = [re.sub(r"\s+", " ", b).strip() for b in html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"</(p|li|h\d|tr|figcaption|caption|td|th)>", "\n", h))).split("\n")]
plain = " ".join(b for b in blocks if b)

def extend(q):
    t = q.strip()
    nonempty = [b for b in blocks if b]
    for j, b in enumerate(nonempty):
        i = b.find(t[:80])  # quotes may run on into the next paragraph; anchor on their opening
        if i < 0:
            continue
        # quote opens the paragraph: its antecedent is the end of the previous paragraph (often a run-in heading)
        prev = b[:i].rstrip() if i > 0 else (nonempty[j - 1] if j else "")
        if not prev:
            continue
        before = SENT.split(prev)
        add = []
        while before and (not add or START.match(add[0])) and len(add) < 4:
            add.insert(0, before.pop())
        cand = (" ".join(add) + " " + t).strip()
        if cand in plain and not START.match(cand):
            return cand
    return None

def walk(o, key, stats):
    if key in SECTION_KEYS or key in NON_EXCERPT:
        return o
    if isinstance(o, str):
        if START.match(o.strip()):
            n = extend(o)
            if n:
                stats["extended"] += 1; return n
            stats["unchanged"].append(o[:100])
        return o
    if isinstance(o, list):
        return [walk(x, key, stats) for x in o]
    if isinstance(o, dict):
        return {k: walk(v, k, stats) for k, v in o.items()}
    return o

stats = {"extended": 0, "unchanged": []}
for f in ("src/data/methods.json", "src/data/framework.json"):
    d = json.load(open(ROOT / f))
    d = {k: (walk(v, "" if k in ("methods", "hypotheses") else k, stats) if k not in ("source", "gaps", "families") else v) for k, v in d.items()}
    if "--write" in sys.argv:
        (ROOT / f).write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
print("extended", stats["extended"], "unchanged", len(stats["unchanged"]))
for u in stats["unchanged"]:
    print("  -", u)
