#!/usr/bin/env python3
"""Activation patching on GPT-2 small for indirect object identification (IOI).

Produces src/data/experiments/patching_gpt2_ioi.json, which the
"Activation patching" demo renders. Every number on that page comes from this
script; re-run it to reproduce:

    pip install torch transformer-lens==<see output 'versions'>
    python3 scripts/experiments/compute_patching.py

Runs on CPU in a few minutes. Deterministic (no sampling; eval mode).

Setup follows the companion notebook notebooks/03_circuits/01_circuit_discovery.ipynb
(clean prompt vs. a corrupted prompt in which the subject of the second clause is
swapped, metric = logit difference between indirect object and subject), scaled
up to a fixed set of templates and name pairs.
"""
from __future__ import annotations

import json
import platform
import time
from pathlib import Path

import numpy as np
import torch
import transformer_lens
from transformer_lens import HookedTransformer, utils

OUT = Path(__file__).resolve().parents[2] / "src" / "data" / "experiments" / "patching_gpt2_ioi.json"

# All templates tokenise to the same length so that positions align across
# prompts (required for the per-position residual-stream heatmap) and no
# padding is introduced. build_dataset() asserts this.
TEMPLATES = [
    "When {A} and {B} went to the store, {S} gave a drink to",
    "When {A} and {B} went to the park, {S} gave a ball to",
    "When {A} and {B} went to the office, {S} gave a letter to",
    "When {A} and {B} went to the school, {S} gave a book to",
]
NAME_PAIRS = [("Mary", "John"), ("Alice", "Bob"), ("Sarah", "Tom"), ("Anna", "James")]


def build_dataset(model):
    clean, corrupt, io_tok, s_tok, meta = [], [], [], [], []
    for t in TEMPLATES:
        for a, b in NAME_PAIRS:
            for io, s in ((a, b), (b, a)):
                # clean: second-clause subject is S -> answer IO
                clean.append(t.format(A=a, B=b, S=s))
                # corrupted: second-clause subject is IO -> answer flips to S
                corrupt.append(t.format(A=a, B=b, S=io))
                io_tok.append(model.to_single_token(" " + io))
                s_tok.append(model.to_single_token(" " + s))
                meta.append({"template": t, "IO": io, "S": s})
    lengths = {len(model.to_str_tokens(p)) for p in clean + corrupt}
    assert len(lengths) == 1, f"prompts must tokenise to equal length, got {lengths}"
    toks_c = model.to_tokens(clean)
    toks_x = model.to_tokens(corrupt)
    return toks_c, toks_x, torch.tensor(io_tok), torch.tensor(s_tok), clean, corrupt, meta


def logit_diff(logits, io, s, per_prompt=False):
    last = logits[:, -1, :]
    d = last.gather(1, io[:, None]).squeeze(1) - last.gather(1, s[:, None]).squeeze(1)
    return d if per_prompt else d.mean()


@torch.no_grad()
def main():
    torch.manual_seed(0)
    t0 = time.time()
    model = HookedTransformer.from_pretrained("gpt2", device="cpu")
    model.eval()
    toks_c, toks_x, io, s, clean, corrupt, meta = build_dataset(model)
    n_layers, n_heads, seq = model.cfg.n_layers, model.cfg.n_heads, toks_c.shape[1]

    logits_c, cache_c = model.run_with_cache(toks_c)
    logits_x = model(toks_x)
    ld_clean = logit_diff(logits_c, io, s).item()
    ld_corrupt = logit_diff(logits_x, io, s).item()
    per_prompt_clean = logit_diff(logits_c, io, s, True).tolist()
    acc_clean = float((logit_diff(logits_c, io, s, True) > 0).float().mean())

    def recovery(ld):
        return (ld - ld_corrupt) / (ld_clean - ld_corrupt)

    # 1) residual stream (resid_pre) patching: every layer x position
    resid = np.zeros((n_layers, seq))
    for layer in range(n_layers):
        name = utils.get_act_name("resid_pre", layer)
        for pos in range(seq):
            def hook(act, hook, pos=pos):
                act[:, pos, :] = cache_c[hook.name][:, pos, :]
                return act
            lg = model.run_with_hooks(toks_x, fwd_hooks=[(name, hook)])
            resid[layer, pos] = recovery(logit_diff(lg, io, s).item())

    # 2) attention-head output patching (z, all positions)
    heads = np.zeros((n_layers, n_heads))
    for layer in range(n_layers):
        name = utils.get_act_name("z", layer)
        for h in range(n_heads):
            def hook(act, hook, h=h):
                act[:, :, h, :] = cache_c[hook.name][:, :, h, :]
                return act
            lg = model.run_with_hooks(toks_x, fwd_hooks=[(name, hook)])
            heads[layer, h] = recovery(logit_diff(lg, io, s).item())

    # 3) attribution patching (first-order approximation) for the same heads
    with torch.enable_grad():
        grads = {}
        def save_grad(g, hook):
            grads[hook.name] = g.detach()
        model.reset_hooks()
        for layer in range(n_layers):
            model.add_hook(utils.get_act_name("z", layer), save_grad, dir="bwd")
        _, cache_x = model.run_with_cache(toks_x)
        lg = model(toks_x)
        logit_diff(lg, io, s).backward()
        model.reset_hooks()
    attr = np.zeros((n_layers, n_heads))
    for layer in range(n_layers):
        name = utils.get_act_name("z", layer)
        delta = cache_c[name] - cache_x[name]  # [batch, pos, head, d_head]
        # grads are of the batch-MEAN metric, so summing over the batch gives the
        # first-order estimate of the change in that mean
        contrib = (delta * grads[name]).sum(dim=(0, 1, 3))  # [head]
        attr[layer] = (contrib / (ld_clean - ld_corrupt)).numpy()

    corr = float(np.corrcoef(heads.ravel(), attr.ravel())[0, 1])
    str_tokens = model.to_str_tokens(toks_c[0])

    out = {
        "description": "Activation patching on GPT-2 small, IOI task. Values are fractional recovery "
                       "of the clean-vs-corrupted logit difference: 0 = corrupted baseline, 1 = clean.",
        "model": "gpt2 (124M) via transformer_lens HookedTransformer.from_pretrained",
        "n_prompts": len(clean),
        "templates": TEMPLATES,
        "name_pairs": NAME_PAIRS,
        "example": {"clean": clean[0], "corrupt": corrupt[0], "IO": meta[0]["IO"], "S": meta[0]["S"]},
        "tokens_example": str_tokens,
        "metric": "mean over prompts of logit(IO) - logit(S) at the final position",
        "logit_diff_clean": ld_clean,
        "logit_diff_corrupt": ld_corrupt,
        "clean_accuracy": acc_clean,
        "per_prompt_logit_diff_clean": per_prompt_clean,
        "resid_pre_recovery": resid.round(4).tolist(),
        "head_z_recovery": heads.round(4).tolist(),
        "head_attribution_patching": attr.round(4).tolist(),
        "pearson_activation_vs_attribution": corr,
        "versions": {"torch": torch.__version__, "transformer_lens": getattr(transformer_lens, "__version__", None)
                     or _pkg_version("transformer-lens"), "python": platform.python_version()},
        "runtime_seconds": round(time.time() - t0, 1),
        "generated": time.strftime("%Y-%m-%d"),
        "script": "scripts/experiments/compute_patching.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(f"clean LD {ld_clean:.3f} corrupt LD {ld_corrupt:.3f} acc {acc_clean:.2f} r(act,attr)={corr:.3f} -> {OUT}")


def _pkg_version(name):
    from importlib.metadata import version
    try:
        return version(name)
    except Exception:
        return None


if __name__ == "__main__":
    main()
