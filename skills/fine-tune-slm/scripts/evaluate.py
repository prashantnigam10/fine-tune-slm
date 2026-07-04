#!/usr/bin/env python3
"""Evaluate a model (optionally with a LoRA adapter) on a held-out test set.

Reads test_pairs.jsonl (lines of {"prompt", "completion"}), generates an answer
for each prompt, and scores by normalized exact match - right for classification
and short extraction. For open-ended generation the accuracy number is not
meaningful; use --no-score to just record outputs, then have the agent grade a
sample by judgment and add "judge_accuracy" to the JSON.

Writes results JSON: accuracy, per-example predictions, and (for label-like
tasks) a per-label breakdown.

IMPORTANT: accuracy (and any judge_accuracy added by hand afterwards) is ALWAYS
a 0-1 fraction (0.62 = 62%), never a percentage. The results files under
results/baseline/ and results/final/ must be produced by this script - never
hand-written - so the dashboard's math stays consistent.
"""

import argparse
import json
import re
import time
from pathlib import Path


def normalize(s):
    return re.sub(r"[^a-z0-9 ]", "", s.strip().lower())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="HF model id or local path")
    ap.add_argument("--adapter-path", help="LoRA adapter dir (omit for baseline)")
    ap.add_argument("--test-data", required=True, help="test_pairs.jsonl")
    ap.add_argument("--output", required=True, help="results JSON path")
    ap.add_argument("--max-tokens", type=int, default=16)
    ap.add_argument("--limit", type=int, help="evaluate only first N examples")
    ap.add_argument("--no-score", action="store_true", help="record outputs without exact-match scoring")
    args = ap.parse_args()

    from mlx_lm import load, generate  # deferred so --help works without mlx

    print(f"Loading model {args.model}" + (f" + adapter {args.adapter_path}" if args.adapter_path else " (baseline)"))
    model, tokenizer = load(args.model, adapter_path=args.adapter_path)

    pairs = [json.loads(l) for l in open(args.test_data) if l.strip()]
    if args.limit:
        pairs = pairs[:args.limit]

    results, correct = [], 0
    t0 = time.time()
    for i, p in enumerate(pairs):
        pred = generate(model, tokenizer, prompt=p["prompt"], max_tokens=args.max_tokens)
        expected = p["completion"].strip()
        # model may emit extra text; compare against the first line/expected-length head
        pred_head = pred.strip().splitlines()[0] if pred.strip() else ""
        ok = (normalize(pred_head) == normalize(expected)
              or normalize(pred_head).startswith(normalize(expected)))
        if not args.no_score and ok:
            correct += 1
        results.append({"prompt": p["prompt"], "expected": expected,
                        "predicted": pred.strip(), "correct": ok})
        print(f"  [{i+1}/{len(pairs)}] {'OK ' if ok else 'MISS'} expected={expected!r} got={pred_head!r}")

    elapsed = time.time() - t0
    out = {
        "model": args.model,
        "adapter_path": args.adapter_path,
        "n_examples": len(pairs),
        "accuracy": round(correct / len(pairs), 4) if pairs and not args.no_score else None,
        "seconds_total": round(elapsed, 1),
        "seconds_per_example": round(elapsed / max(len(pairs), 1), 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "predictions": results,
    }

    # per-label breakdown when the task looks label-like
    labels = {r["expected"] for r in results}
    if len(labels) <= 20 and not args.no_score:
        out["per_label"] = {
            lab: {
                "n": sum(1 for r in results if r["expected"] == lab),
                "correct": sum(1 for r in results if r["expected"] == lab and r["correct"]),
            } for lab in sorted(labels)
        }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)

    if out["accuracy"] is not None:
        print(f"\nAccuracy: {out['accuracy']:.1%} ({correct}/{len(pairs)})")
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
