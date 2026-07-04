#!/usr/bin/env python3
"""Convert user data (CSV / JSON / JSONL) into MLX fine-tuning format.

Input must resolve to prompt/completion pairs. For CSV/JSON with other column
names, pass --input-cols and --output-col plus a --template; the template uses
{colname} placeholders and must end with a cue (e.g. "Sentiment:").

Outputs into <out-dir>: train.jsonl / valid.jsonl / test.jsonl, each line
{"text": prompt + completion}, plus test_pairs.jsonl (prompt/completion kept
separate, used by evaluate.py). Prints a JSON summary line (DATA_JSON: ...).
"""

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path


def load_rows(path):
    p = Path(path)
    if p.suffix.lower() == ".csv":
        with open(p, newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    text = p.read_text(encoding="utf-8-sig").strip()
    if p.suffix.lower() == ".jsonl" or "\n" in text and text.lstrip().startswith("{"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    return data if isinstance(data, list) else [data]


def to_pairs(rows, args):
    pairs = []
    for row in rows:
        if "prompt" in row and "completion" in row:
            prompt, completion = str(row["prompt"]), str(row["completion"])
        elif args.template and args.output_col:
            try:
                prompt = args.template.format(**{k: str(v) for k, v in row.items()})
            except KeyError as e:
                sys.exit(f"ERROR: template placeholder {e} not found in row keys {list(row.keys())}")
            completion = str(row.get(args.output_col, "")).strip()
        else:
            # try common key conventions
            for pk, ck in (("input", "output"), ("question", "answer"), ("text", "label")):
                if pk in row and ck in row:
                    prompt, completion = str(row[pk]), str(row[ck])
                    break
            else:
                sys.exit(f"ERROR: cannot map row keys {list(row.keys())}. "
                         "Pass --template and --output-col.")
        completion = completion.strip()
        if not prompt.strip() or not completion:
            continue  # drop empty examples
        if not completion.startswith(" "):
            completion = " " + completion
        pairs.append({"prompt": prompt, "completion": completion})
    return pairs


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="CSV / JSON / JSONL file")
    ap.add_argument("--out-dir", required=True, help="output directory (MLX data dir)")
    ap.add_argument("--template", help="prompt template with {column} placeholders, ending in a cue")
    ap.add_argument("--output-col", help="column holding the expected answer")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-chars", type=int, default=8000, help="drop examples longer than this")
    args = ap.parse_args()

    rows = load_rows(args.input)
    pairs = to_pairs(rows, args)

    # dedupe on prompt
    seen, deduped = set(), []
    for p in pairs:
        if p["prompt"] not in seen:
            seen.add(p["prompt"])
            deduped.append(p)
    n_dupes = len(pairs) - len(deduped)
    pairs = deduped

    too_long = [p for p in pairs if len(p["prompt"]) + len(p["completion"]) > args.max_chars]
    pairs = [p for p in pairs if len(p["prompt"]) + len(p["completion"]) <= args.max_chars]

    if len(pairs) < 12:
        sys.exit(f"ERROR: only {len(pairs)} usable examples after cleaning - need at least 12 "
                 "to make train/valid/test splits. Consider synthetic data generation.")

    random.Random(args.seed).shuffle(pairs)
    n = len(pairs)
    n_valid = max(4, n // 10)
    n_test = max(4, n // 10)
    test, valid, train = pairs[:n_test], pairs[n_test:n_test + n_valid], pairs[n_test + n_valid:]

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, subset in (("train", train), ("valid", valid), ("test", test)):
        with open(out / f"{name}.jsonl", "w") as f:
            for p in subset:
                f.write(json.dumps({"text": p["prompt"] + p["completion"]}) + "\n")
    with open(out / "test_pairs.jsonl", "w") as f:
        for p in test:
            f.write(json.dumps(p) + "\n")

    # label stats (short completions => classification-like)
    completions = [p["completion"].strip() for p in pairs]
    label_counts = dict(Counter(completions)) if len(set(completions)) <= 20 else None

    summary = {
        "total_usable": n, "train": len(train), "valid": len(valid), "test": len(test),
        "dropped_duplicates": n_dupes, "dropped_too_long": len(too_long),
        "label_counts": label_counts, "out_dir": str(out.resolve()),
    }
    print(f"Prepared {n} examples -> train {len(train)} / valid {len(valid)} / test {len(test)}")
    if n_dupes or too_long:
        print(f"Dropped {n_dupes} duplicates, {len(too_long)} over-length examples")
    if label_counts:
        print("Label counts:", label_counts)
    print("DATA_JSON: " + json.dumps(summary))


if __name__ == "__main__":
    main()
