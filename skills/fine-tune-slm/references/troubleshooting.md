# Troubleshooting

## During setup
- **`pip3 install mlx` fails / "not a supported wheel"** — almost always an Intel Mac or Rosetta Python. Verify `python3 -c "import platform; print(platform.machine())"` prints `arm64`. If `x86_64`, the Python itself is Intel — install an arm64 Python (e.g., `brew install python@3.12`).
- **Model download fails with 401/403** — gated model. Either the user accepts the license on Hugging Face + `huggingface-cli login`, or switch to a non-gated catalog model / `mlx-community` mirror.
- **Download extremely slow / stalls** — resume is automatic; also check disk space, HF downloads fail confusingly when disk fills.

## During training
- **Out of memory (Metal OOM, process killed, machine crawls)** — in order: batch size → 1; reduce `--max-seq-length` if long inputs; smaller model from the catalog. Ask the user to close memory-hungry apps.
- **Validation loss rises while train loss falls** — overfitting. Stop, use the last checkpoint before the rise (`--save-every` checkpoints are in the adapter folder), or rerun with fewer iterations. Small datasets overfit fast — this is expected with <100 examples.
- **Loss is NaN or explodes** — bad examples (empty completions, enormous outliers) or too-high LR. Re-validate data; halve learning rate.
- **Loss barely moves** — check the data actually has a learnable pattern (spot-check examples); make sure the completion isn't accidentally empty after formatting.

## During evaluation
- **Model outputs rambling text instead of the label** — the inference prompt doesn't match the training template exactly. The evaluate script must use the same template, same cue word, same whitespace. Also set a small max-tokens and low temperature for classification.
- **Accuracy stuck near baseline after training** — adapter not loaded (check `--adapter-path` is passed and points at the right folder), or trained on wrong data. Verify the adapter folder has recent `adapters.safetensors`.
- **Great on test set, bad on the user's real examples** — synthetic training data didn't match real inputs. Collect a handful of real examples, add them (plus synthetic look-alikes), retrain.

## Ollama export
- **`ollama create` fails on architecture** — Ollama's safetensors import supports fewer families than MLX. Fall back to `mlx_lm generate` usage (see ollama-export.md).
- **Fused model answers differently than adapter did** — usually prompt template drift again; test with the byte-identical training template.
