---
name: fine-tune-slm
description: Fine-tune a small language model (SLM) locally on Apple Silicon using MLX + LoRA, designed for people who are NOT AI engineers. Handles everything end-to-end - hardware check, model selection, data preparation, synthetic data generation, training, evaluation, Ollama export, and a plain-English HTML report. Use this skill whenever the user wants to fine-tune, train, customize, specialize, or "teach" a local/small/open-source language model on their own data (classification, extraction, style, Q&A), asks which local model they can train on their Mac, or wants to create a custom local AI model - even if they don't say "fine-tune" explicitly.
---

# Fine-Tune a Small Language Model Locally (Apple Silicon)

Guide a user with general tech literacy — but **no AI engineering background** — through fine-tuning a small language model on their own Mac. You (Claude) are the AI engineer; the user only answers plain-English questions about their problem. Never ask the user to pick hyperparameters, LoRA ranks, or learning rates. Translate their answers into config yourself.

**Golden rules for this skill:**
- Talk to the user in plain language. Say "teaching the model" not "gradient updates"; "practice examples" not "training samples" is fine too. Briefly define any term you must use.
- Everything runs locally. Never upload their data anywhere.
- Fail gracefully: check hardware first, and if something can't work, say why and what would work instead.
- Keep all artifacts inside a project folder the user can see and delete.

## Workflow overview

1. Preflight (hardware + software check) — `scripts/preflight.py`
2. Interview the user (plain-English questions)
3. Data: validate user's data, or synthesize/download a dataset
4. Recommend a model from the catalog based on their hardware
5. Show the plan, get one confirmation
6. Baseline evaluation (measure the un-tuned model)
7. Train (LoRA via mlx_lm)
8. Final evaluation + compare to baseline and to the user's goal
9. If goal missed: diagnose; if data quantity is the cause, offer synthetic augmentation and retrain
10. Export to Ollama
11. Generate the plain-English HTML report — `scripts/report.py`

## Step 1: Preflight

Run `scripts/preflight.py` from this skill's directory. It checks: Apple Silicon chip, RAM, free disk (needs ~15GB), Python 3.9+, and whether `mlx`/`mlx-lm` are installed.

- If **not Apple Silicon**: stop gracefully. Explain the skill currently supports Apple Silicon Macs only (it uses Apple's MLX framework), and that cloud or PyTorch-based alternatives exist but aren't automated here. Do not attempt workarounds.
- If deps are missing: create a virtual environment in the project folder and `pip3 install mlx mlx-lm` (plus `huggingface_hub`). Use `python3`/`pip3`.
- Note the RAM figure — it drives model selection.

Create a project folder (ask the user where, default `./slm-finetune-<task-name>/`) with subfolders: `data/`, `adapters/`, `results/baseline/`, `results/final/`, `report/`.

## Step 2: Interview the user

Ask only what you need, in plain English (use AskUserQuestion if available):

1. **What should the model learn to do?** (e.g., "sort my emails into urgent/normal/low")
2. **Do you have example data?** If yes, where is the file? If no → Step 3b.
3. **What does a perfect answer look like?** (defines the output: a label, a short phrase, a paragraph)
4. **How good does it need to be?** (e.g., "right 9 times out of 10" → 90% target)

From these, infer the task type (classification / extraction / generation / Q&A) and design the prompt template yourself. See `references/data-formats.md` for templates per task type.

## Step 3a: User has data

Run `scripts/prepare_data.py` to convert their file (CSV, JSON, JSONL, or plain text) into MLX training format and split it into train/valid/test sets. Inspect their file first to map columns to input→output; confirm your mapping with the user by showing 2 example conversions.

Data quantity guidance (warn, don't block):
- Classification: 50+ examples recommended; below 50, offer synthetic augmentation now (Step 3b) or proceed with a caveat.
- Generation/style/Q&A: 200+ recommended.
- Also check label balance for classification; if skewed, offer to synthesize the minority class.

## Step 3b: User has no data (or not enough)

Two options — present both, let the user choose:

1. **Synthetic generation (you write it):** Generate diverse, realistic examples yourself following `references/synthetic-data.md`. Show the user ~5 samples for approval before generating the full set. Save to `data/synthetic_data.jsonl` in prompt/completion format, then run `prepare_data.py` on it.
2. **Download from Hugging Face:** Search for a reputable public dataset matching the task (prefer high-download, well-documented datasets). Confirm the specific dataset with the user before downloading, then map it into training format with `prepare_data.py`.

## Step 4: Choose the model

Read `references/models.md` (the vetted catalog with RAM requirements). Filter by the user's RAM from preflight, pick one recommended default plus 1–2 alternatives, and explain the choice in one sentence ("small enough to train on your 16GB Mac, strong at short classification answers"). The user may override with any MLX-compatible Hugging Face model — but warn about the constraints listed in the catalog (no GGUF/Ollama-only models, no gated models without a HF token, size ceiling by RAM).

## Step 5: Show the plan

Before anything heavy runs, show one short summary: model chosen, number of examples, estimated training time, disk needed, and the success target. Get a single "go ahead" — then run the rest without stopping for permission at each step.

## Step 6: Baseline evaluation

Before training, measure the un-tuned model on the held-out test set:

```bash
python3 scripts/evaluate.py --model <base-model> --test-data <project>/data/mlx_format/test.jsonl \
  --output <project>/results/baseline/results.json
```

For classification/extraction this gives exact-match accuracy automatically. For open-ended generation, the script saves the model's outputs; grade a sample of ~20 yourself against the expected answers (be strict and consistent) and record the score in the results JSON under `"judge_accuracy"`.

Tell the user the baseline in plain terms: "Before training, the model gets it right about 6 times out of 10."

## Step 7: Train

Pick hyperparameters yourself (never ask the user). Defaults that work:

| Setting | Default | Adjust when |
|---|---|---|
| LoRA layers | 16 | 8 for ≤1B models |
| Batch size | 2 | 1 if RAM ≤ 8GB or model ≥ 3B |
| Learning rate | 5e-5 | — |
| Iterations | ~min(1000, examples × 60 / batch_size), floor 200 | more data → cap at 1000 |

Run training (from inside the project venv):

```bash
python3 -m mlx_lm lora --model <base-model> --train \
  --data <project>/data/mlx_format \
  --batch-size 2 --iters <N> --learning-rate 5e-5 \
  --adapter-path <project>/adapters/<task-name> \
  --steps-per-report 10 --steps-per-eval 100 --save-every 200
```

Run it in the background and monitor output. Watch for:
- **Out of memory** → halve batch size, or drop to a smaller model from the catalog.
- **Validation loss rising while training loss falls** → overfitting; stop and use the last good checkpoint, or reduce iterations.
- Save a `training_metadata.json` in the adapter folder (model, iterations, examples, wall time, settings) — the report needs it.

More failure modes: `references/troubleshooting.md`.

## Step 8: Final evaluation

Re-run `scripts/evaluate.py` with `--adapter-path <project>/adapters/<task-name>`, output to `results/final/results.json`. Compare against baseline and against the user's target.

- **Target met** → Step 10.
- **Target missed** → diagnose before retrying. Look at the actual wrong answers:
  - Wrong answers scattered/random and dataset small → **data quantity**: offer synthetic augmentation (Step 3b) — generate more examples focused on the failing categories, merge, retrain once.
  - Errors concentrated in one category → data imbalance: synthesize that category.
  - Outputs malformed (rambling, wrong format) → prompt template issue: fix the template, rebuild data, retrain.
  - Already near ceiling but short of goal → suggest a larger model from the catalog if RAM allows.
  - Limit retraining to 2 attempts; after that, present honest results and options rather than looping.

## Step 9: Export to Ollama

Follow `references/ollama-export.md`: fuse the adapter into the base model with `mlx_lm fuse`, write a Modelfile, and `ollama create <task-name>`. If Ollama isn't installed, offer `brew install ollama` or skip the step gracefully. Verify with one test prompt through `ollama run`.

## Step 10: The report (always do this)

Generate the final HTML report:

```bash
python3 scripts/report.py --project <project-folder> --open
```

The script builds `report/report.html` from `results/baseline/`, `results/final/`, and `training_metadata.json`. It is written for a non-AI audience: what was done (as a simple journey), before-vs-after scores with a visual bar comparison, sample predictions, how to use the model now (Ollama command, copy-pasteable), and where every file lives (clickable `file://` links). Pass extra context the script can't know via `--summary-json` (see the script's `--help`): task description in the user's own words, goal, whether the goal was met, synthetic-data notes.

Open it in the browser (or send it to the user) and close with a 3-sentence plain-English recap in chat.
