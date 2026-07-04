# Exporting to Ollama

Goal: the user types `ollama run <task-name>` and their fine-tuned model answers. Two steps: fuse the LoRA adapter into the base model, then register with Ollama.

## 1. Fuse the adapter

LoRA training produces a small adapter file; Ollama needs a full standalone model. Merge them:

```bash
python3 -m mlx_lm fuse \
  --model <base-model-hf-id> \
  --adapter-path <project>/adapters/<task-name> \
  --save-path <project>/models/<task-name>-fused
```

This writes a complete safetensors model (~same size as the base model download — check disk first).

## 2. Create the Ollama model

Check Ollama is installed (`which ollama`); if not, offer `brew install ollama` or skip this step gracefully (the fused model still works via `mlx_lm generate`).

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

If `ollama create` rejects the safetensors architecture (Ollama supports fewer architectures for import than MLX does — Llama, Mistral, Gemma, Qwen families are safe; others may fail), fall back gracefully: tell the user the model still runs locally with:

```bash
python3 -m mlx_lm generate --model <project>/models/<task-name>-fused --prompt "..."
```

## 3. Verify

Run one real test prompt through `ollama run <task-name> "<prompt built with the training template>"` and confirm the output format matches training. Remind the user: the model expects the same prompt shape it was trained on — include that exact template in the report's "how to use it" section.
