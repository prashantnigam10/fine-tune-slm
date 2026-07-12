# Publishing to ollama.com

Everything on ollama.com is **public** — there are no private models. Say this before starting; if the user wants private, steer to a private Hugging Face repo instead.

## 1. One-time account + key setup (user does this themselves)

1. User creates an account at https://ollama.com/signup (browser, not you).
2. User links this Mac by adding its Ollama public key: they run

   ```bash
   cat ~/.ollama/id_ed25519.pub
   ```

   and paste the output into ollama.com → account settings → **Keys**. This is a *public* key — safe to display — but the user does the copy/paste themselves. You never open their account pages or handle any credential.

## 2. Make sure the model exists in the local Ollama library

Check `ollama list` (or step 1's `PUBLISH_JSON.in_ollama`). If the model is there, continue to step 3.

If it isn't (the training run skipped export, or the user removed it): fuse on demand and create it — same procedure as fine-tune-slm's `references/ollama-export.md`:

```bash
~/.slm-finetune/venv/bin/python -m mlx_lm fuse \
  --model <base-model-hf-id> --adapter-path <project>/adapters/<name> \
  --save-path <project>/models/<name>-fused
# Modelfile: FROM ./<name>-fused (+ the same PARAMETERs used at training time)
cd <project>/models && ollama create <name> -f Modelfile
```

Verify with one templated prompt, then **delete the fused folder** — Ollama has its own copy now (`rm -rf <project>/models/<name>-fused`).

## 3. Copy under the username and push

```bash
ollama cp <local-name> <username>/<name>
ollama push <username>/<name>
```

**Immediately before `ollama push`, get a fresh confirmation**: "This uploads the full model (~X GB) to ollama.com as `<username>/<name>`, publicly visible and pullable by anyone. Go ahead?" A yes earlier in the conversation does not count.

Push uploads gigabytes — tell the user it will take a while, and that this upload duration is normal.

## 4. Verify and record

- Open (or have the user open) `https://ollama.com/<username>/<name>` and confirm it's live; optionally edit the description on the site (user's job — it's their account).
- Anyone can now run it with `ollama run <username>/<name>` — give the user that command *plus* the prompt template the model expects.
- Record in `summary.json` → `published_to`, and dashboard/`PUBLISHED.md` per SKILL.md step 5.

## Removing it later

`ollama.com` → the model's page → settings → delete (user does it in the browser). Mention this so publishing doesn't feel irreversible — though anyone who already pulled a copy keeps it.
