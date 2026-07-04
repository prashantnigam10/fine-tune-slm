#!/usr/bin/env python3
"""Preflight check for local SLM fine-tuning. Prints human-readable results
and emits a JSON summary line for the calling agent. Exit 0 = OK to proceed,
1 = hard blocker (e.g., not Apple Silicon)."""

import json
import platform
import shutil
import subprocess
import sys


def sysctl(key):
    try:
        return subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def main():
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

    # Dependencies
    for mod in ("mlx", "mlx_lm", "huggingface_hub"):
        try:
            __import__(mod)
            result[f"has_{mod}"] = True
        except ImportError:
            result[f"has_{mod}"] = False
            result["warnings"].append(f"Python package '{mod}' not installed (pip3 install {mod.replace('_','-')}).")

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
    print(f"  mlx / mlx-lm: {result.get('has_mlx')} / {result.get('has_mlx_lm')}")
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
