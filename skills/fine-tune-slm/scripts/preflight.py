#!/usr/bin/env python3
"""Preflight check for local SLM fine-tuning. Prints human-readable results
and emits a JSON summary line for the calling agent. Exit 0 = OK to proceed,
1 = hard blocker (e.g., not Apple Silicon).

Also supports:
  --check-model <hf-id>   report whether a Hugging Face model is already fully
                          cached locally (so the skill can say "reusing, no
                          download" instead of guessing). Prints MODEL_CACHE_JSON.

Dependencies live in ONE shared environment reused by every project
(~/.slm-finetune/venv), created from the skill's pinned requirements.txt.
Preflight checks that env - not the system Python - so a fresh project never
reinstalls or re-resolves packages.
"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SHARED_ENV = Path.home() / ".slm-finetune" / "venv"


def sysctl(key):
    try:
        return subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def dir_size_gb(path):
    total = 0
    for p in Path(path).rglob("*"):
        try:
            # skip symlinks: HF snapshots symlink into blobs/ and would double-count
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            pass
    return total / (1024 ** 3)


def check_model_cache(model_id):
    """Is this HF model fully downloaded already? (accurate download messaging)"""
    cache = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + model_id.replace("/", "--"))
    result = {"model": model_id, "cached": False, "complete": False, "size_gb": 0.0,
              "path": str(cache)}
    if cache.exists():
        result["cached"] = True
        incomplete = list(cache.rglob("*.incomplete"))
        result["complete"] = not incomplete
        result["size_gb"] = round(dir_size_gb(cache), 2)
    if result["complete"]:
        print(f"Model {model_id} is already on disk ({result['size_gb']} GB) - "
              "it will be reused, no download needed.")
    elif result["cached"]:
        print(f"Model {model_id} is partially downloaded - the download will resume.")
    else:
        print(f"Model {model_id} is not downloaded yet - it will download once and be "
              "reused by all future projects.")
    print("MODEL_CACHE_JSON: " + json.dumps(result))


def shared_env_status():
    """Check the shared env's own Python for the pinned packages."""
    py = SHARED_ENV / "bin" / "python"
    if not py.exists():
        return {"exists": False, "ok": False}
    r = subprocess.run([str(py), "-c", "import mlx, mlx_lm, huggingface_hub"],
                       capture_output=True, text=True)
    return {"exists": True, "ok": r.returncode == 0}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-model", metavar="HF_ID",
                    help="only check whether this model is already cached, then exit")
    args = ap.parse_args()
    if args.check_model:
        check_model_cache(args.check_model)
        return

    result = {"ok": True, "blockers": [], "warnings": []}

    # Platform
    result["os"] = platform.system()
    result["arch"] = platform.machine()
    if platform.system() != "Darwin":
        result["ok"] = False
        result["blockers"].append(
            f"This skill requires macOS on Apple Silicon; detected {platform.system()}.")
    elif platform.machine() != "arm64":
        result["ok"] = False
        result["blockers"].append(
            "Apple Silicon (M1 or newer) required. This Mac (or this Python) is running "
            "x86_64. If the Mac IS Apple Silicon, Python is running under Rosetta - "
            "install an arm64 Python (e.g. brew install python@3.12).")

    # Chip + RAM
    result["chip"] = sysctl("machdep.cpu.brand_string") or "unknown"
    try:
        ram_gb = round(int(sysctl("hw.memsize")) / (1024 ** 3))
    except ValueError:
        ram_gb = 0
    result["ram_gb"] = ram_gb
    if 0 < ram_gb < 8:
        result["ok"] = False
        result["blockers"].append(f"Only {ram_gb}GB RAM - 8GB minimum for training even tiny models.")
    elif ram_gb == 8:
        result["warnings"].append("8GB RAM: limited to models around 1.5B parameters or smaller, batch size 1-2.")

    # Disk
    free_gb = round(shutil.disk_usage(".").free / (1024 ** 3))
    result["free_disk_gb"] = free_gb
    if free_gb < 15:
        result["warnings"].append(
            f"Only {free_gb}GB free disk. Model download + fused export can need 15GB+; "
            "small models may still fit.")

    # Python
    v = sys.version_info
    result["python"] = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) < (3, 9):
        result["ok"] = False
        result["blockers"].append(f"Python 3.9+ required, found {result['python']}.")

    # Shared environment (one env for all projects; created from pinned requirements.txt)
    env = shared_env_status()
    result["shared_env_path"] = str(SHARED_ENV)
    result["shared_env_exists"] = env["exists"]
    result["shared_env_ok"] = env["ok"]
    req = Path(__file__).parent.parent / "requirements.txt"
    result["requirements_file"] = str(req)
    if env["ok"]:
        pass  # ready - no install needed this run
    elif env["exists"]:
        result["warnings"].append(
            f"Shared env at {SHARED_ENV} exists but packages are broken/missing - "
            f"reinstall with: {SHARED_ENV}/bin/pip install -r {req}")
    else:
        result["warnings"].append(
            f"Shared env not created yet (first run). Create once with: "
            f"python3 -m venv {SHARED_ENV} && {SHARED_ENV}/bin/pip install -r {req} "
            "- all projects reuse it; later runs skip installation entirely.")

    # Ollama (optional, for export step)
    result["has_ollama"] = shutil.which("ollama") is not None
    if not result["has_ollama"]:
        result["warnings"].append("Ollama not installed - export step will offer 'brew install ollama' or be skipped.")

    # Human-readable output
    print("=" * 56)
    print("  Fine-tuning preflight check")
    print("=" * 56)
    print(f"  Chip:        {result['chip']}")
    print(f"  RAM:         {result['ram_gb']} GB")
    print(f"  Free disk:   {result['free_disk_gb']} GB")
    print(f"  Python:      {result['python']} ({result['arch']})")
    print(f"  Shared env:  {'ready' if env['ok'] else ('broken' if env['exists'] else 'not created yet')} ({SHARED_ENV})")
    print(f"  Ollama:      {result['has_ollama']}")
    for b in result["blockers"]:
        print(f"  BLOCKER: {b}")
    for w in result["warnings"]:
        print(f"  warning: {w}")
    print("=" * 56)
    print("PREFLIGHT_JSON: " + json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
