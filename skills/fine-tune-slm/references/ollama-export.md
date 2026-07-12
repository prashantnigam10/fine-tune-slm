# Installing into local Ollama

Goal: the user types `ollama run <task-name>` and their fine-tuned model answers.

**This is entirely local.** `ollama create` registers the model in the Ollama app's library on this Mac (`~/.ollama/models`) — it does not upload anything, and the model is not visible to anyone else. Publishing to ollama.com requires a separate explicit `ollama push` with an account, which this skill never does. Make sure the user understands this distinction — "export to Ollama" sounds like publishing, and it isn't.

**Fused-model lifecycle (important for disk usage):** the fused model exists *only* to feed `ollama create` — Ollama can't import an adapter+base pair, but everything else can run one (`mlx_lm generate --adapter-path`). So:

- **Ollama not installed → do NOT fuse.** Skip this file entirely; the try-it fallback is the adapter+base command below. Fusing can happen later, on demand, if the user installs Ollama.
- **Ollama import succeeded and verified → delete the fused folder.** Ollama keeps its own converted copy in `~/.ollama/models`; the fused safetensors (~GBs) has served its purpose. It can always be regenerated from adapter + base in ~a minute.

## 1. Fuse the adapter

Only reach this step when Ollama is installed (preflight's `has_ollama`). LoRA training produces a small adapter file; `ollama create` needs a full standalone model. Merge them:

```bash
~/.slm-finetune/venv/bin/python -m mlx_lm fuse \
  --model <base-model-hf-id> \
  --adapter-path <project>/adapters/<task-name> \
  --save-path <project>/models/<task-name>-fused
```

This writes a complete safetensors model (~same size as the base model download — check disk first). Log it (`--category file`) and note in chat that this copy is temporary and will be removed after the Ollama import.

## 2. Create the Ollama model

Ollama imports safetensors directly via a Modelfile. Write `<project>/models/Modelfile`:

```
FROM ./<task-name>-fused
PARAMETER temperature 0.1
PARAMETER num_predict 64
SYSTEM ""
```

- `temperature 0.1` and short `num_predict` suit classification/extraction; relax for generation tasks (temperature 0.7, num_predict 256).
- Then:

```bash
cd <project>/models && ollama create <task-name> -f Modelfile
```

If `ollama create` rejects the safetensors architecture (Ollama supports fewer architectures for import than MLX does — Llama, Mistral, Gemma, Qwen families are safe; others may fail), fall back gracefully: delete the fused folder (it has no further purpose — see lifecycle above), mark the export stage skipped with the reason, and point the user at the adapter+base command:

```bash
~/.slm-finetune/venv/bin/python -m mlx_lm generate \
  --model <base-model-hf-id> \
  --adapter-path <project>/adapters/<task-name> \
  --prompt "..."
```

## 3. Verify, then clean up

1. Run one real test prompt through `ollama run <task-name> "<prompt built with the training template>"` and confirm the output format matches training. Remind the user: the model expects the same prompt shape it was trained on — include that exact template in the report's "how to use it" section.
2. **Only after that verification succeeds**, delete the fused folder and log it:

```bash
rm -rf <project>/models/<task-name>-fused
```

Log to the dashboard (`--category file`), e.g. "Removed temporary fused model (reclaimed 3.4 GB) — Ollama keeps its own copy in ~/.ollama/models". Tell the user in chat too: their model lives in Ollama now; the adapter (~30 MB) plus the cached base model can regenerate the fused copy at any time.
