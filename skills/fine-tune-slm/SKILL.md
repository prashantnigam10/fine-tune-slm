---
name: fine-tune-slm
description: Fine-tune a small language model (SLM) locally on Apple Silicon using MLX + LoRA, designed for people who are NOT AI engineers. Handles everything end-to-end - hardware check, model selection, data preparation, synthetic data generation, training, evaluation, Ollama export, and a plain-English HTML dashboard of the whole run. Use this skill whenever the user wants to fine-tune, train, customize, specialize, or "teach" a local/small/open-source language model on their own data (classification, extraction, style, Q&A), asks which local model they can train on their Mac, or wants to create a custom local AI model - even if they don't say "fine-tune" explicitly.
---

# Fine-Tune a Small Language Model Locally (Apple Silicon)

Guide a user with general tech literacy — but **no AI engineering background** — through fine-tuning a small language model on their own Mac. You (Claude) are the AI engineer; the user only answers plain-English questions about their problem. Never ask the user to pick hyperparameters, LoRA ranks, or learning rates. Translate their answers into config yourself.

**Golden rules for this skill:**
- Talk to the user in plain language. Briefly define any term you must use.
- Everything runs locally. Never upload their data anywhere.
- Fail gracefully: check hardware first; if something can't work, say why and what would work instead.
- **The dashboard is the single artifact.** One HTML file per run (`report/dashboard.html`, managed by `scripts/dashboard.py`) collects everything: plans, data samples, model options, results, files, and an activity log. Add to it at every step; tell the user to keep it open and refresh.
- **Anything the user must review goes in the dashboard first, then ask.** Never put review content (sample data, converted examples, model tables) inside AskUserQuestion options or previews — users often can't see those. Sequence: add dashboard section → open/point to it → ask the plain question.
- **Log as you go.** Every install, download, file created, or long command runs through `dashboard.py log ...` the moment it happens — the user may have auto-approve on and deserves a full record of what touched their machine. `train.py` logs itself; everything else is your habit.

## The dashboard in one minute

```bash
DASH="python3 <skill>/scripts/dashboard.py"   # always the skill's copy
$DASH init    --project <proj> --task "sort emails by sentiment" --goal "90% accuracy"
$DASH section --project <proj> --id samples --stage data --title "Sample training emails" --html-file /tmp/samples.html
$DASH stage   --project <proj> --id training --status running   # done | skipped (--note why)
$DASH log     --project <proj> --action "Installed mlx-lm 0.31" --detail "pip3 install mlx-lm" --category install
$DASH results --project <proj> --open                            # builds baseline/results/try-it sections
```

Every command re-renders the page. Stages: setup, data, model, baseline, training, results, export — shown as a clickable pipeline with done/running/skipped markers. "Files & disk" (annotated folder tree + disk usage + cleanup guidance) and "Activity log" tabs are generated automatically on every render. Scores are 0–1 fractions everywhere; the dashboard normalizes accidental percentages, but don't create them.

## Workflow

### 1. Preflight

Run `scripts/preflight.py`. It checks Apple Silicon, RAM, disk (~15GB), Python 3.9+, mlx/mlx-lm, and Ollama, and prints a `PREFLIGHT_JSON` line — keep `ram_gb` (drives model choice) and `has_ollama` (drives the export step).

- **Not Apple Silicon** → stop gracefully: explain the skill needs Apple's MLX framework, mention that PyTorch/cloud alternatives exist but aren't automated here. No workarounds.
- Missing deps → create a venv inside the project folder, `pip3 install mlx mlx-lm huggingface_hub`. Log each install.

Create the project folder (ask where; default `./slm-finetune-<task-name>/`) with `data/`, `adapters/`, `results/baseline/`, `results/final/`, `report/`. Then `dashboard.py init` with the task and goal, mark stage `setup` done, and tell the user where the dashboard lives.

### 2. Interview

Plain-English questions only (AskUserQuestion is fine here — these are questions, not review content):

1. **What should the model learn to do?**
2. **Do you have example data?** (file path, or no → 3b)
3. **What does a perfect answer look like?** (label / short phrase / paragraph)
4. **How good does it need to be?** ("right 9 of 10 times" → 90%)

Infer the task type and design the prompt template yourself — see `references/data-formats.md`.

### 3a. User has data

Inspect their file, design the column→prompt mapping, then **show 2 example conversions in a dashboard section** (stage `data`) and confirm the mapping with the user. Then run `scripts/prepare_data.py` (converts CSV/JSON/JSONL → MLX format, dedupes, splits train/valid/test). Add a short data-summary section (counts, label balance) and mark stage `data` done.

Quantity guidance (warn, don't block): classification 50+, generation/Q&A 200+. Too few or imbalanced → offer synthetic augmentation (3b).

### 3b. User has no data (or not enough)

Two options — present both: **synthetic generation** (you write the examples — follow `references/synthetic-data.md`) or **download from Hugging Face** (confirm the specific dataset first). For synthetic: write ~5 samples, render them into a dashboard section (stage `data`), tell the user to look at the dashboard, and only generate the full set after they approve the style. Never show the samples only inside a question widget.

### 4. Choose the model

Read `references/models.md`, filter the catalog by `ram_gb`, and build a comparison table **as a dashboard section** (stage `model`): model, size, download, best-for, rough training time — with your recommendation clearly marked and the one-sentence reason stated. Then ask via AskUserQuestion: recommended model first, 1–2 alternatives, **and always an explicit "I'll provide my own model (Hugging Face link or ID)" option**. Validate user-supplied models against the catalog's override rules (MLX-supported architecture, not GGUF/Ollama-only, not gated without a token, fits RAM); if it fails, explain why and offer the closest catalog model. Mark stage `model` done and pass the chosen model as `--model-label` on the next `results` call.

### 5. Show the plan

One short summary — model, examples, estimated time, disk, success target — as chat text plus a dashboard section. Get a single "go ahead"; then run the rest without step-by-step permission.

### 6. Baseline evaluation

```bash
python3 scripts/evaluate.py --model <base-model> \
  --test-data <proj>/data/mlx_format/test_pairs.jsonl \
  --output <proj>/results/baseline/results.json
```

Exact-match accuracy for classification/extraction. For open-ended generation use `--no-score`, grade ~20 outputs yourself (strict, consistent), and add `"judge_accuracy"` — **as a 0–1 fraction** — to the script's JSON. Results files always come from `evaluate.py`; never hand-write them. Then `dashboard.py results` (builds the baseline section) and tell the user the score in plain terms.

### 7. Train

Pick hyperparameters yourself:

| Setting | Default | Adjust when |
|---|---|---|
| LoRA layers | 16 | 8 for ≤1B models |
| Batch size | 2 | 1 if RAM ≤ 8GB or model ≥ 3B |
| Learning rate | 5e-5 | — |
| Iterations | ~min(1000, examples × 60 / batch_size), floor 200 | — |

Always train through the wrapper (it streams progress, writes `training_metadata.json`, logs to the dashboard, detects OOM and rising validation loss):

```bash
python3 scripts/train.py --model <base-model> --data <proj>/data/mlx_format \
  --adapter-path <proj>/adapters/<task-name> --iters <N> --batch-size 2 \
  --project <proj>
```

Run in the background, monitor, set stage `training` running → done. On OOM follow the wrapper's hint (batch 1 → smaller model). More failure modes: `references/troubleshooting.md`.

### 8. Final evaluation

Re-run `evaluate.py` with `--adapter-path`, output to `results/final/results.json`. Write `summary.json` in the project root (plain-language fields the dashboard uses: `task_description`, `goal_description`, `goal_met`, `data_source`, `n_training_examples`, `synthetic_note`, `ollama_name`, `prompt_template`, `next_steps`) — then `dashboard.py results --open`.

- **Target met** → step 9.
- **Target missed** → diagnose from the actual wrong answers before retrying: scattered errors + small dataset → synthetic augmentation focused on failures; one bad category → synthesize that category; malformed outputs → fix the template and rebuild; near ceiling → suggest a larger catalog model. Max 2 retrains, then present honest results and options.

### 9. Export to Ollama

Consume the preflight signal — don't discover failure at export time:

- **Ollama installed** → follow `references/ollama-export.md` (fuse → Modelfile → `ollama create` → verify with one templated prompt). Set `ollama_name` in summary.json, re-run `dashboard.py results` so the "Use your model" section (editable command + copy button) appears. Mark stage `export` done.
- **Not installed** → offer `brew install ollama`; if declined, mark stage `export` skipped (`--note "Ollama not installed"`), and make sure the dashboard's try-it section still shows the `mlx_lm generate` fallback. This is a normal path, not an error — say so.

### 10. Close out

Final pass: confirm `summary.json` is complete, `dashboard.py results --open`, and give a 3-sentence plain-English recap in chat. The dashboard's Files & disk tab already explains every file, sizes, and how to reclaim space — point the user to it, especially if they ask about the ~GBs used. Offer (never do silently): clearing the Hugging Face model cache if they're done fine-tuning for now (`rm -rf ~/.cache/huggingface` — re-downloads if needed).
