#!/usr/bin/env python3
"""Discover and catalogue the companion notebooks.

    python3 scripts/catalogue_notebooks.py --repo /path/to/Interpretability_Survey_Safety [--verify-links]

Everything in the catalogue is read from the notebooks themselves (titles, the
"Survey Reference" line, overview text, imports, model names, saved outputs).
Compute requirements are *estimated* from the model names the code loads and
are labelled as estimates on the site. Writes src/data/notebooks.json and
preview images to public/notebook-previews/.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "data" / "notebooks.json"
PREV = ROOT / "public" / "notebook-previews"
GH = "TSGLAB/Interpretability_Survey_Safety"

# approximate parameter counts (billions) for models referenced in the notebooks
MODEL_SIZES = [
    (r"llama-3\.3-70b", 70), (r"qwen3\.6-27b", 27), (r"llama-2-13b", 13), (r"gemma-2-9b", 9), (r"llama-3\.1-8b", 8),
    (r"qwen3-8b", 8), (r"qwen2\.5-7b", 7), (r"qwen3\.5-4b", 4), (r"gemma-2-2b", 2.6), (r"qwen3-1\.7b", 1.7),
    (r"gpt2-large", 0.774), (r"qwen2\.5-0\.5b", 0.5), (r"gpt2-medium", 0.355), (r"gpt2-small", 0.124), (r"^gpt2$", 0.124),
]
GATED = [r"^meta-llama/", r"^google/gemma", r"^gemma-2"]
PYPI_NAMES = {"sklearn": "scikit-learn", "yaml": "pyyaml", "dotenv": "python-dotenv", "transformer_lens": "transformer-lens",
              "sae_lens": "sae-lens", "tuned_lens": "tuned-lens", "huggingface_hub": "huggingface-hub"}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) or {  # Python < 3.10 fallback
    "os", "sys", "re", "json", "io", "math", "random", "time", "typing", "pathlib", "functools", "itertools", "collections",
    "copy", "dataclasses", "contextlib", "textwrap", "tempfile", "threading", "urllib", "http", "gzip", "pickle", "abc",
    "warnings", "logging", "string", "subprocess", "shutil", "glob", "csv", "datetime", "enum", "hashlib", "base64"}
LOCAL_OR_UNPUBLISHED = {"model", "jlens", "nla_inference"}
SECTION_ORDER = ["01_core_hypotheses", "02_feature_extraction", "03_circuits", "04_intermediate_computation",
                 "05_representation_analysis", "06_safety_applications"]


def md_cells(nb):
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown"]


def code_text(nb):
    return "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")


def first_heading(mds):
    for m in mds:
        for line in m.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return None


def survey_reference(mds):
    for m in mds:
        mm = re.search(r"\*\*Survey Reference:?\*\*:?\s*(.+)", m)
        if mm:
            return mm.group(1).strip()
    return None


def overview(mds):
    """First prose paragraph under an Overview/Introduction heading, else first paragraph after the title."""
    text = "\n".join(mds[:3])
    m = re.search(r"#+\s*(Overview|Introduction|Motivation)[^\n]*\n+(.+?)(\n\n|\n#|$)", text, re.S)
    para = m.group(2) if m else None
    if not para:
        for block in re.split(r"\n\s*\n", text):
            b = block.strip()
            if b and not b.startswith("#") and not b.startswith("**Survey") and not b.startswith("---"):
                para = b
                break
    return re.sub(r"\s+", " ", para).strip() if para else None


def objectives(mds):
    for m in mds:
        mm = re.search(r"#+\s*(Learning (Objectives|Goals|Outcomes)|What you(?:'|’)ll learn|Objectives|Goals)[^\n]*\n+((?:\s*(?:[-*]|\d+\.)\s+.+\n?)+)", m, re.I)
        if mm:
            return [re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", l).strip() for l in mm.group(3).strip().splitlines() if l.strip()]
    return []


def key_methods(mds):
    for m in mds:
        mm = re.search(r"#+\s*Key (Methods|Concepts|Topics)[^\n]*\n+((?:\s*(?:[-*]|\d+\.)\s+.+\n?)+)", m, re.I)
        if mm:
            return [re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", l).strip() for l in mm.group(2).strip().splitlines() if l.strip()]
    return []


def models_in(code):
    found = set(re.findall(r"""["']((?:gpt2(?:-(?:small|medium|large|xl))?|google/[\w.-]+|EleutherAI/[\w.-]+|meta-llama/[\w.-]+|Qwen/[\w.-]+|gemma-2-[\w.-]+|pythia-[\w.-]+))["']""", code))
    # SAE release names (e.g. gpt2-small-res-jb) are not models
    return sorted(m for m in found if not re.search(r"-res-|-jb$|-att-", m))


def size_of(model):
    name = model.split("/")[-1].lower()
    for pat, b in MODEL_SIZES:
        if re.search(pat, name):
            return b
    return None


def compute_estimate(models, code):
    sizes = [s for s in (size_of(m) for m in models) if s]
    biggest = max(sizes) if sizes else 0
    if not models:
        tier = "cpu"
    elif biggest <= 1.0:
        tier = "cpu"
    elif biggest <= 9:
        tier = "gpu"
    else:
        tier = "large-gpu"
    return {"tier": tier, "largest_model_b": biggest or None,
            "basis": "Estimated from the largest model loaded in the code" if models else "No pretrained model loaded (toy or synthetic data)"}


def external_services(code):
    svc = []
    if re.search(r"^\s*(import openai|from openai)|OpenAI\(", code, re.M):
        svc.append("OpenAI API key")
    if re.search(r"^\s*(import anthropic|from anthropic)|Anthropic\(", code, re.M):
        svc.append("Anthropic API key")
    if re.search(r"login\(|HF_TOKEN|use_auth_token|token=", code):
        svc.append("Hugging Face token")
    if re.search(r"urllib\.request|httpx\.|requests\.get|urlopen\(", code):
        svc.append("Downloads data at runtime")
    return svc


def imports_in(code):
    mods = set(re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", code, re.M))
    return sorted(m for m in mods if m not in STDLIB)


def requirements(repo):
    req = (repo / "requirements.txt").read_text() if (repo / "requirements.txt").exists() else ""
    names = {re.split(r"[<>=\[ ]", l.strip())[0].lower() for l in req.splitlines() if l.strip() and not l.strip().startswith("#")}
    return names


def save_preview(nb, rel):
    for c in nb["cells"]:
        for o in c.get("outputs", []) if c["cell_type"] == "code" else []:
            data = o.get("data", {})
            if "image/png" in data:
                PREV.mkdir(parents=True, exist_ok=True)
                name = re.sub(r"[^a-z0-9]+", "-", rel.lower()).strip("-") + ".png"
                (PREV / name).write_bytes(base64.b64decode(data["image/png"]))
                return name
    return None


def url_ok(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "mi-survey-site-build"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--verify-links", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()
    reqs = requirements(repo)
    commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or None
    if PREV.exists():
        for f in PREV.glob("*.png"):
            f.unlink()

    items = []
    for p in sorted(repo.glob("notebooks/**/*.ipynb")):
        if ".ipynb_checkpoints" in p.parts:
            continue
        rel = p.relative_to(repo).as_posix()
        nb = json.loads(p.read_text())
        mds, code = md_cells(nb), code_text(nb)
        imps = imports_in(code)
        models = models_in(code)
        missing = sorted({PYPI_NAMES.get(m, m) for m in imps if m not in LOCAL_OR_UNPUBLISHED}
                         - {r.replace("_", "-") for r in reqs} - {r for r in reqs} - {"IPython", "ipywidgets"})
        local = sorted(set(imps) & LOCAL_OR_UNPUBLISHED)
        has_outputs = any(c.get("outputs") for c in nb["cells"] if c["cell_type"] == "code")
        colab = f"https://colab.research.google.com/github/{GH}/blob/{a.branch}/{rel}"
        src = f"https://github.com/{GH}/blob/{a.branch}/{rel}"
        raw = f"https://raw.githubusercontent.com/{GH}/{a.branch}/{rel}"
        colab_blockers = []
        if local:
            colab_blockers.append(f"imports modules not on PyPI or kept beside the notebook ({', '.join(local)}); clone the repo first")
        comp = compute_estimate(models, code)
        if comp["tier"] == "large-gpu":
            colab_blockers.append("largest model exceeds a free Colab GPU")
        items.append({
            "path": rel,
            "section_dir": p.parent.name,
            "order": SECTION_ORDER.index(p.parent.name) if p.parent.name in SECTION_ORDER else 99,
            "title": first_heading(mds) or p.stem.replace("_", " "),
            "survey_reference": survey_reference(mds),
            "overview": overview(mds),
            "key_methods": key_methods(mds),
            "learning_objectives": objectives(mds),
            "models": models,
            "gated_models": [m for m in models if any(re.search(g, m) for g in GATED)],
            "compute": comp,
            "uses_cuda_if_available": "cuda" in code,
            "external": external_services(code),
            "imports": imps,
            "deps_missing_from_requirements": missing,
            "local_modules": local,
            "cells": len(nb["cells"]),
            "has_saved_outputs": has_outputs,
            "preview_image": save_preview(nb, rel),
            "links": {"source": src, "colab": colab, "raw": raw},
            "colab_blockers": colab_blockers,
            "link_check": None,
        })
    if a.verify_links:
        for it in items:
            it["link_check"] = {"source_exists_on_github": url_ok(it["links"]["raw"])}
    items.sort(key=lambda x: (x["order"], x["path"]))
    out = {"repo": GH, "branch": a.branch, "commit": commit, "notebooks": items,
           "requirements": sorted(reqs), "link_check_run": a.verify_links}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"{len(items)} notebooks; previews={sum(1 for i in items if i['preview_image'])}; "
          f"links verified={a.verify_links and sum(1 for i in items if i['link_check']['source_exists_on_github'])}")


if __name__ == "__main__":
    main()
