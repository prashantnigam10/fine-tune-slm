# Publishing to Hugging Face Hub

Hugging Face supports **private** repos — recommend starting private ("only you can see it; flip to public later in repo settings when you're ready"). Default recommendation: **adapter-only, private**.

## 1. One-time login (user does this themselves)

The user needs an HF account and a **write** token (huggingface.co → settings → Access Tokens). They log in themselves, in their own terminal:

```bash
~/.slm-finetune/venv/bin/hf auth login        # newer CLI
# or: ~/.slm-finetune/venv/bin/huggingface-cli login   # older name
```

You never ask for, see, or type the token. If the CLI isn't in the shared env, it ships with the pinned `huggingface_hub` — do not install anything new without logging it.

## 2. What to upload

**Adapter-only (recommended).** ~30 MB, uploads in seconds, and anyone can combine it with the public base model:

- Upload the `adapters/<name>/` folder (the `.safetensors` + `adapter_config.json` + `training_metadata.json`).
- Consumers run it with:
  ```bash
  python3 -m mlx_lm generate --model <base-hf-id> --adapter-path <downloaded-adapter> --prompt "..."
  ```

**Full fused model (only on explicit request).** GBs; only when the user wants a standalone model. Fuse on demand (see fine-tune-slm `references/ollama-export.md`), upload the fused folder, then delete the local fused copy after the upload is verified.

**Privacy note applies to BOTH:** a LoRA adapter is distilled from the training data just as much as full weights are — adapter-only is a size choice, not a privacy protection. The step-2 private-data warning from SKILL.md stands either way.

## 3. Write the model card first

Create a `README.md` for the repo and **show it to the user before anything uploads** (render into a file they can read, or paste in chat — it's short). Required content, all from `check_project.py`'s JSON — no remembered numbers:

- What the model does (the task, in the user's words from `summary.json`)
- Base model (link) and that this is a LoRA fine-tune of it
- **The exact prompt template** — the model only works with it
- Measured results: baseline → final accuracy with test-set size ("0.95 on 21 held-out examples"); if goal wasn't met, say so honestly
- Data provenance: user data / synthetic (say which, per `synthetic_note`) — never imply data quality that wasn't there
- License: the base model's license governs the derivative (see `licenses.md`); set the repo's license tag to match

## 4. Create the repo and upload

```bash
HF=~/.slm-finetune/venv/bin/hf
"$HF" repo create <name> --private          # confirm public explicitly if not private
"$HF" upload <username>/<name> <project>/adapters/<name> .
"$HF" upload <username>/<name> /path/to/README.md README.md
```

Immediately before the first upload, one fresh confirmation naming what/where/visibility: "Upload the ~30 MB adapter + model card to huggingface.co/<username>/<name> as a **private** repo?"

## 5. Verify and record

- Open the repo page (or `"$HF" repo info`) and confirm files + card render.
- Give the user the consumer command (adapter-only: the `mlx_lm generate` line with their repo id).
- Record in `summary.json` → `published_to`, and dashboard/`PUBLISHED.md` per SKILL.md step 5.

## Removing it later

Repo settings → delete repo (user, in browser), or `"$HF" repo delete <username>/<name>`. Private repos can also simply stay private forever.
