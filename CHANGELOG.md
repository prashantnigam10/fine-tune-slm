# Changelog

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
