import json, re, glob, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
D = str(ROOT) + "/"
raw="\n".join(open(f,encoding="utf-8").read() for f in sorted(glob.glob(D+".ingest-plain/*.txt")))
norm=lambda s: re.sub(r"\s+"," ",s).strip()
corpus=norm(raw)
secs=set(re.findall(r"\[\[SECTION id=([^\]]+)\]\]",raw))
d=json.load(open(D+"src/data/methods.json",encoding="utf-8"))
ids={m["id"] for m in d["methods"]}; fams={f["id"] for f in d["families"]}
bad=[];n=0
def chk(where,t):
    global n; n+=1
    if norm(t) not in corpus: bad.append((where,t[:90]))
for f in d["families"]:
    for s in f["sections"]:
        if s not in secs: bad.append(("famsec "+f["id"],s))
for m in d["methods"]:
    if m["family"] not in fams: bad.append(("family",m["id"]))
    for s in m["sections"]+m["mentioned_in"]:
        if s not in secs: bad.append(("sec "+m["id"],s))
    for r in m["related"]:
        if r not in ids: bad.append(("rel "+m["id"],r))
    chk(m["id"]+".def",m["definition"])
    for k in ["assumptions","evaluation","applications","limitations"]:
        for t in m[k]: chk(m["id"]+"."+k,t)
for h in d["hypotheses"]:
    chk(h["id"],h["definition"])
    for s in h["sections"]:
        if s not in secs: bad.append(("hsec",s))
print("excerpts checked:",n,"methods:",len(d["methods"]),"failures:",len(bad))
for b in bad: print(b)
