#!/usr/bin/env python3
"""Run LoRA fine-tuning via mlx_lm and ALWAYS record training_metadata.json.

Thin wrapper around `python3 -m mlx_lm lora` that streams training output,
measures wall time, counts training examples, and writes
<adapter-path>/training_metadata.json on success — so the dashboard and report
never have missing numbers. If --project is given, it also appends entries to
the dashboard's activity log.

Exit codes: 0 success, 1 training failed (stderr tail is printed with a hint).
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def count_lines(path):
    p = Path(path)
    return sum(1 for l in p.read_text().splitlines() if l.strip()) if p.exists() else None


def log_activity(project, action, detail="", category="run"):
    if not project:
        return
    script = Path(__file__).parent / "dashboard.py"
    subprocess.run([sys.executable, str(script), "log", "--project", project,
                    "--action", action, "--detail", detail, "--category", category],
                   capture_output=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True, help="directory containing train/valid.jsonl")
    ap.add_argument("--adapter-path", required=True)
    ap.add_argument("--iters", type=int, required=True)
    ap.add_argument("--batch-size", type=int, default=2)
    ap.add_argument("--learning-rate", type=float, default=5e-5)
    ap.add_argument("--num-layers", type=int, help="LoRA layers (mlx_lm default if omitted)")
    ap.add_argument("--max-seq-length", type=int)
    ap.add_argument("--project", help="project folder, for dashboard activity logging")
    args = ap.parse_args()

    cmd = [sys.executable, "-m", "mlx_lm", "lora",
           "--model", args.model, "--train", "--data", args.data,
           "--batch-size", str(args.batch_size), "--iters", str(args.iters),
           "--learning-rate", str(args.learning_rate),
           "--adapter-path", args.adapter_path,
           "--steps-per-report", "10", "--steps-per-eval", "100",
           "--save-every", "200"]
    if args.num_layers:
        cmd += ["--num-layers", str(args.num_layers)]
    if args.max_seq_length:
        cmd += ["--max-seq-length", str(args.max_seq_length)]

    n_train = count_lines(Path(args.data) / "train.jsonl")
    print(f"Training {args.model} on {n_train} examples for {args.iters} iterations")
    print("Command:", " ".join(cmd), "\n")
    log_activity(args.project, f"Started training on {n_train} examples "
                 f"({args.iters} iterations)", " ".join(cmd))

    t0 = time.time()
    tail = []
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    val_losses = []
    for line in proc.stdout:
        print(line, end="")
        tail = (tail + [line])[-30:]
        m = re.search(r"Val loss ([\d.]+)", line)
        if m:
            val_losses.append(float(m.group(1)))
    proc.wait()
    elapsed = time.time() - t0

    if proc.returncode != 0:
        joined = "".join(tail).lower()
        hint = ""
        if "memory" in joined or "metal" in joined:
            hint = ("\nHint: looks like the Mac ran out of memory. Retry with a smaller "
                    "--batch-size (try 1), a smaller --max-seq-length, or a smaller model.")
        log_activity(args.project, "Training FAILED", "".join(tail[-5:]))
        sys.exit(f"Training failed (exit {proc.returncode}).{hint}")

    if len(val_losses) >= 3 and val_losses[-1] > val_losses[-2] > val_losses[-3]:
        print("\nNote: validation loss was rising at the end - possible overfitting. "
              "An earlier checkpoint in the adapter folder may generalize better.")

    metadata = {
        "model_name": args.model,
        "training_time_seconds": round(elapsed, 1),
        "training_examples": n_train,
        "iterations": args.iters,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "num_layers": args.num_layers,
        "val_losses": val_losses,
        "command_used": " ".join(cmd),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    meta_path = Path(args.adapter_path) / "training_metadata.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(metadata, indent=2))

    dur = f"{elapsed / 60:.0f} min" if elapsed > 90 else f"{elapsed:.0f} s"
    print(f"\nDone in {dur}. Adapter: {args.adapter_path}\nMetadata: {meta_path}")
    log_activity(args.project, f"Training finished in {dur}; adapter saved",
                 str(meta_path))


if __name__ == "__main__":
    main()
