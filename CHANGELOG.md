# Changelog

## [Unreleased]

- New: `publish-slm` companion skill (#15) — a separate, independent skill
  (skills/publish-slm) that publishes a *tested* fine-tune-slm project to
  ollama.com (public) or Hugging Face (private-first, adapter-only by default).
  Deliberately kept out of the training flow: test first, publish later. Every
  upload is consent-gated with a fresh confirmation naming what/where/visibility;
  credentials are never handled (the user logs in themselves); model-card numbers
  must come from scripts/check_project.py, which reads only evaluate.py-produced
  results files and warns loudly on regressions, unmet goals, and private
  training data. Includes base-license guidance (Llama naming rule, Gemma terms
  flow-down) and fuse-on-demand when the local Ollama copy is missing (per #12)
- Changed: fused-model lifecycle (#12) — the fused model is created only when
  Ollama is installed (it exists solely to feed `ollama create`), and is deleted
  once the Ollama import is verified, reclaiming ~3+ GB per run; Ollama keeps its
  own copy and the adapter + cached base model can regenerate the fused copy on
  demand. Without Ollama, nothing is fused and the dashboard's "Without Ollama"
  command now uses `mlx_lm generate --adapter-path` (adapter + base) instead of
  pointing at a fused folder that may not exist

## [0.3.0] - 2026-07-05

Second fix pass, from validation runs of v0.2.0.

- New: one shared Python environment (~/.slm-finetune/venv) reused by all
  projects — no more per-run reinstalls; preflight checks it and prints exact
  setup instructions on first run
- New: pinned requirements.txt (mlx / mlx-lm / transformers / datasets) — a
  tested-together set that ends the recurring mlx-lm↔transformers version
  mismatch; troubleshooting entry added with the recovery command
- New: `preflight.py --check-model <hf-id>` reports whether a model is already
  in the local cache, so runs say "already on disk, reusing" instead of wrongly
  announcing downloads
- Fixed: a run could reach training with no accuracy goal recorded, silently
  disabling the goal check and retrain loop — the goal is now required before
  training (with a proposed default if the user has none), the dashboard shows
  a visible warning when it's missing, and a weak improvement triggers
  diagnosis even without a goal
- README: added "What can I build with this?" with ten everyday use cases

## [0.2.0] - 2026-07-04

Fix pass from the first real end-to-end test run.

- New: single interactive HTML dashboard per run (scripts/dashboard.py) replaces
  the one-shot report — clickable pipeline navigation (done/running/skipped per
  stage), sticky summary strip, one section visible at a time
- New: Activity log tab — a timestamped record of every install, download, file,
  and command the run performed on the machine
- New: Files & disk tab — annotated folder tree with sizes plus disk usage across
  the project folder, Hugging Face cache, and Ollama library, with cleanup guidance
- New: "Use your model" section with a live-updating, copyable `ollama run`
  command (and an mlx_lm fallback when Ollama isn't installed)
- New: scripts/train.py training wrapper — always records training metadata,
  streams progress, hints on out-of-memory, flags rising validation loss
- Fixed: scores rendered as thousands of percent when a results file mixed
  percentages and fractions — scores are now normalized and bars clamped
- Fixed: report sentences showed bare "—" when metadata was missing — sentences
  are now built conditionally and counts are derived from the data files
- Changed: anything needing user review (data samples, mappings, model options)
  is rendered into the dashboard before asking — never inside question-widget
  previews, which some clients don't display
- Changed: model selection now shows a hardware-filtered comparison with a marked
  recommendation, and always offers a bring-your-own Hugging Face model option
- Changed: missing Ollama is a normal "skipped" stage with a working fallback
- Removed: scripts/report.py (superseded by the dashboard)

## [0.1.0] - 2026-07-04

Initial version.

- End-to-end workflow: preflight → plain-English interview → data preparation →
  hardware-based model selection → baseline evaluation → LoRA training (MLX) →
  final evaluation with goal check → Ollama export → HTML report
- Vetted model catalog (SmolLM2, Qwen2.5, Llama 3.2, Gemma 2, Phi-3.5, Mistral)
  with RAM requirements and license notes
- Synthetic data generation and Hugging Face dataset download when the user has
  no (or not enough) data
- Scripts: preflight.py, prepare_data.py, evaluate.py, report.py
- Verified end-to-end on a real run (email sentiment, SmolLM2-1.7B, 33% → 100%
  on held-out test)
