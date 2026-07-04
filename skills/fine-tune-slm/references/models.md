# Vetted Model Catalog

Curated open-weight small language models known to work with MLX-LM LoRA fine-tuning on Apple Silicon. Filter by the user's RAM (from preflight), then pick the default by task fit. All are pulled from Hugging Face by ID on first use (one-time download).

## Selection table

| Model (HF ID) | Params | Min RAM to train | Download | Best for | License |
|---|---|---|---|---|---|
| `HuggingFaceTB/SmolLM2-360M-Instruct` | 360M | 8 GB | ~0.7 GB | quick experiments, very simple classification | Apache 2.0 |
| `Qwen/Qwen2.5-0.5B-Instruct` | 0.5B | 8 GB | ~1 GB | simple classification, short extraction | Apache 2.0 |
| `Llama-3.2-1B-Instruct` (`mlx-community/Llama-3.2-1B-Instruct-4bit` or Meta original) | 1B | 8 GB | ~2.5 GB | classification, extraction | Llama license (gated on Meta repo; mlx-community mirror is not) |
| `Qwen/Qwen2.5-1.5B-Instruct` | 1.5B | 8 GB | ~3 GB | classification, extraction, short generation | Apache 2.0 |
| `HuggingFaceTB/SmolLM2-1.7B-Instruct` | 1.7B | 16 GB (8 GB works, slower) | ~3.4 GB | **proven default** — classification, extraction, short-form tasks | Apache 2.0 |
| `google/gemma-2-2b-it` | 2.6B | 16 GB | ~5 GB | reasoning-ish classification, nuanced text | Gemma license (gated — needs HF token) |
| `Qwen/Qwen2.5-3B-Instruct` | 3B | 16 GB | ~6 GB | generation, style transfer, Q&A | Qwen research license |
| `Llama-3.2-3B-Instruct` | 3B | 16 GB | ~6.5 GB | generation, Q&A, instructions | Llama license (gated on Meta repo) |
| `microsoft/Phi-3.5-mini-instruct` | 3.8B | 16 GB | ~7.5 GB | reasoning, structured output | MIT |
| `Qwen/Qwen2.5-7B-Instruct` | 7B | 32 GB (24 GB marginal) | ~15 GB | complex generation, best quality | Apache 2.0 |
| `mistralai/Mistral-7B-Instruct-v0.3` | 7B | 32 GB | ~14 GB | complex generation | Apache 2.0 |

## How to choose

1. **Filter by RAM** (training needs more headroom than inference — the "Min RAM" column already accounts for LoRA training at batch size 2).
2. **Default picks by task:**
   - Classification / labeling / routing → `SmolLM2-1.7B-Instruct` (16 GB) or `Qwen2.5-1.5B-Instruct` (8 GB)
   - Extraction (pull fields out of text) → `Qwen2.5-1.5B-Instruct` or `Qwen2.5-3B-Instruct`
   - Style / tone rewriting, generation, Q&A → `Qwen2.5-3B-Instruct`; `Qwen2.5-7B-Instruct` if ≥32 GB RAM
3. **Prefer non-gated models** (Apache/MIT) so no Hugging Face account is required. Only suggest gated models (Llama on Meta's repo, Gemma) if the user has or is willing to create a HF token — otherwise use `mlx-community/` mirrors when available.
4. Present one default + up to two alternatives. Do not present the whole table.

## User overrides — what works and what doesn't

The user may name any model. Accept it if it is:
- Hosted on Hugging Face in **safetensors/PyTorch format** with an architecture MLX-LM supports (Llama, Qwen, Mistral, Gemma, Phi, SmolLM, StableLM, and most mainstream decoder models).

Explain and decline (with the closest catalog alternative) if it is:
- **GGUF-only / an Ollama model name** (e.g., "llama3.2 from Ollama") — GGUF is an inference format and cannot be trained. Fine-tune the original HF weights instead; the Ollama export step at the end gets it back into Ollama.
- **Gated without a token** — needs license acceptance + `huggingface-cli login`.
- **Too big for RAM** — rough ceiling: 3B on 8 GB, 8B on 16 GB (tight), 7–8B comfortable on 32 GB+.
- **An exotic architecture** MLX-LM doesn't implement — the download will succeed but training will error; check `mlx_lm` support if unsure.
