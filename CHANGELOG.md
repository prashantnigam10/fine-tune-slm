# Changelog

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
