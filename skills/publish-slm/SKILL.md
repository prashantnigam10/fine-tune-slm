---
name: publish-slm
description: Publish a locally fine-tuned small language model (a completed fine-tune-slm project) to ollama.com or Hugging Face Hub, deliberately and consent-gated. Use this skill whenever the user wants to publish, share, upload, or push their fine-tuned/custom local model to ollama.com, Hugging Face, "the hub", or "make my model public/available to others" - including sharing just the LoRA adapter. This skill is separate from training on purpose: models should be thoroughly tested before anything leaves the machine. Do NOT use it for the training/fine-tuning itself (that's fine-tune-slm) or for installing a model into the local Ollama app (that's part of training, not publishing).
---

# Publish a Fine-Tuned SLM (ollama.com / Hugging Face)

Walk a user - general tech literacy, no ML background - through publishing a model they fine-tuned with the `fine-tune-slm` skill. You are the engineer; they answer plain-English questions.

**Publishing is the opposite of the training skill's privacy promise.** fine-tune-slm guarantees nothing leaves the Mac; this skill's entire purpose is to upload something. That makes every step consent-gated:

- Never publish, create remote repos, or push anything without an explicit "yes" to a clearly described action ("this uploads X to Y, visible to Z").
- **Never handle credentials.** The user runs every login/key step themselves in their own terminal (`hf auth login`, pasting their Ollama key into ollama.com settings). Never ask for a token in chat, never type one, never read one from disk.
- **Only measured numbers.** Any score in a model card must come from the project's `results/*/results.json` (produced by fine-tune-slm's `evaluate.py`). No estimated or remembered accuracy - ever. `scripts/check_project.py` extracts the citable numbers for you.
- Plain language throughout; briefly define any term you must use (repo, model card, adapter).

## Workflow

### 1. Locate and verify the project

Ask for the project folder (the one fine-tune-slm created). Run:

```bash
python3 <skill>/scripts/check_project.py --project <folder>
```

It prints `PUBLISH_JSON` with: adapter path, base model, `ollama_name`, goal/`goal_met`, measured baseline/final scores, whether the model exists in the local Ollama library, and whether a fused copy is on disk. Everything you say downstream comes from this - not from memory.

If the folder isn't a completed fine-tune-slm project (no adapter or no final results), stop and explain what's missing.

### 2. The test-first gate

Publishing untested or failing models is how people get hurt by their own tools. Before offering destinations:

- **`goal_met` true** → recap the measured result ("scored 95% on 21 held-back examples, goal was 90%") and proceed.
- **`goal_met` false or missing, or final ≤ baseline** → say so plainly and recommend NOT publishing yet. If the user still wants to, require an explicit confirmation that names the real number ("publish anyway, knowing it measured 62%?"). Never soften the number.
- Ask one more plain question: **"Was the training data private (your emails, expenses, company data)?"** If yes, warn clearly: a model can memorize and reproduce fragments of its training data, so publishing the model can leak the data. Public destinations need a deliberate yes after this warning; suggest a private Hugging Face repo as the safer option.

### 3. Choose the destination

Present the two options as a short comparison (chat table is fine - this is a decision, not review content):

| | ollama.com | Hugging Face |
|---|---|---|
| Visibility | **Public only** | Private or public (recommend starting private) |
| What uploads | Full model (GBs) | Adapter only (~30 MB, recommended) or full model |
| Consumers run it with | `ollama run <user>/<name>` | MLX/transformers + adapter, or download |
| Account needed | ollama.com account + one-time key | HF account + write token (user logs in themselves) |

Also check the **base model's license** before anything uploads - see `references/licenses.md`. Some bases (Llama, Gemma) attach conditions to derivatives (naming, terms flow-down); Apache-2.0 bases (SmolLM2, Qwen) are unrestricted. State what applies in one sentence.

### 4a. Publish to ollama.com

Follow `references/ollama-com.md`. Summary: user creates the account and adds their key (they run `cat ~/.ollama/id_ed25519.pub` and paste it into ollama.com settings themselves); if the model isn't in the local Ollama library (check step 1's JSON - e.g. export was skipped), fuse on demand and `ollama create` first, exactly as fine-tune-slm's export step does, then delete the fused copy after; then `ollama cp <local> <user>/<name>` and `ollama push <user>/<name>` - each with a "this makes it public to everyone" confirmation immediately before the push.

### 4b. Publish to Hugging Face

Follow `references/huggingface.md`. Summary: user logs in themselves (`hf auth login`); default recommendation is **adapter-only, private repo**; you write the model card (base model, task, prompt template, measured scores with test-set size, data provenance incl. synthetic note, base license) and show it to the user before upload; upload with the shared env's `hf upload`. Full-model upload only on explicit request (fuse on demand, warn about size, delete the fused copy after).

### 5. Record and close out

- Verify the published artifact (pull/view it once, or open the repo page) before declaring success.
- Write what happened into the project: add `published_to` (destination, URL/name, date, what was uploaded) to `summary.json`, and - if the fine-tune-slm skill is installed alongside - append a "Published" section and activity-log entries via its `scripts/dashboard.py`. If it isn't, write a short `PUBLISHED.md` in the project folder instead.
- Recap in chat: what's now public/private, where, and the one command someone else needs to use it. Mention how to unpublish (`references` cover deletion for both destinations).
