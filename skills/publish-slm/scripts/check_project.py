#!/usr/bin/env python3
"""Verify a fine-tune-slm project folder is publishable and extract the facts.

Prints a human-readable report plus a PUBLISH_JSON line for the calling agent.
Every number the agent may cite in a model card comes from here - which reads
only files produced by fine-tune-slm's scripts (results.json from evaluate.py,
training_metadata.json from train.py, summary.json) - never from memory.

Exit codes: 0 = publishable, 1 = not a completed fine-tune-slm project.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


def norm_score(v):
    """Scores are 0-1 fractions; tolerate accidental percentages (same rule as dashboard.py)."""
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v / 100 if v > 1 else v


def score_of(results):
    return norm_score(results.get("judge_accuracy", results.get("accuracy")))


def ollama_has(name):
    if not name or not shutil.which("ollama"):
        return False
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True,
                             timeout=15).stdout
        return any(line.split()[0].split(":")[0] == name
                   for line in out.splitlines()[1:] if line.strip())
    except (subprocess.SubprocessError, OSError):
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    args = ap.parse_args()
    proj = Path(args.project).expanduser().resolve()

    problems = []
    if not proj.is_dir():
        print(f"Not a folder: {proj}")
        sys.exit(1)

    # adapter + its training metadata (train.py always writes it)
    adapter_dir, tmeta = None, {}
    for meta in sorted(proj.glob("adapters/*/training_metadata.json")):
        adapter_dir, tmeta = meta.parent, load_json(meta)
    if adapter_dir is None:  # fall back: adapter without metadata
        cands = sorted(p.parent for p in proj.glob("adapters/*/*.safetensors"))
        adapter_dir = cands[-1] if cands else None
    if adapter_dir is None or not list(adapter_dir.glob("*.safetensors")):
        problems.append("no trained adapter found under adapters/")

    summary = load_json(proj / "summary.json")
    baseline = load_json(proj / "results/baseline/results.json")
    final = load_json(proj / "results/final/results.json")
    if not final:
        problems.append("no final evaluation (results/final/results.json missing) - "
                        "the model was never measured; do not publish unmeasured models")

    fused = sorted((proj / "models").glob("*-fused"))
    ollama_name = summary.get("ollama_name")

    info = {
        "project": str(proj),
        "publishable": not problems,
        "problems": problems,
        "adapter_path": str(adapter_dir) if adapter_dir else None,
        "adapter_size_mb": round(sum(f.stat().st_size for f in adapter_dir.rglob("*")
                                     if f.is_file()) / 1e6, 1) if adapter_dir else None,
        "base_model": tmeta.get("model_name") or summary.get("model_label") or None,
        "task_description": summary.get("task_description", ""),
        "prompt_template": summary.get("prompt_template", ""),
        "goal_description": summary.get("goal_description", ""),
        "goal_met": summary.get("goal_met"),
        "data_source": summary.get("data_source", ""),
        "synthetic_note": summary.get("synthetic_note", ""),
        "baseline_score": score_of(baseline),
        "final_score": score_of(final),
        "n_test_examples": final.get("n_examples") or baseline.get("n_examples"),
        "regression": (score_of(final) is not None and score_of(baseline) is not None
                       and score_of(final) <= score_of(baseline)),
        "ollama_name": ollama_name,
        "in_ollama": ollama_has(ollama_name),
        "fused_on_disk": str(fused[-1]) if fused else None,
        "already_published": summary.get("published_to") or None,
    }

    # human-readable report
    print(f"Project: {proj}")
    for p in problems:
        print(f"  BLOCKER: {p}")
    if info["base_model"]:
        print(f"  Base model: {info['base_model']}")
    if info["adapter_path"]:
        print(f"  Adapter: {info['adapter_path']} ({info['adapter_size_mb']} MB)")
    b, f = info["baseline_score"], info["final_score"]
    if f is not None:
        line = f"  Measured: final {f:.1%}"
        if b is not None:
            line += f" (baseline {b:.1%})"
        if info["n_test_examples"]:
            line += f" on {info['n_test_examples']} held-out examples"
        print(line)
    if info["regression"]:
        print("  WARNING: REGRESSION - final <= baseline. This model got WORSE with "
              "training; publishing it is almost certainly a mistake.")
    if info["goal_met"] is False:
        print(f"  WARNING: goal not met ({info['goal_description'] or 'no goal recorded'}).")
    elif info["goal_met"] is None:
        print("  WARNING: no goal verdict recorded in summary.json.")
    print(f"  In local Ollama: {'yes (' + ollama_name + ')' if info['in_ollama'] else 'no'}")
    if info["already_published"]:
        print(f"  NOTE: already published: {info['already_published']}")

    print("\nPUBLISH_JSON: " + json.dumps(info))
    sys.exit(0 if info["publishable"] else 1)


if __name__ == "__main__":
    main()
