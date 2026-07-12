# Base-model licenses and publishing derivatives

A LoRA fine-tune is a **derivative** of the base model, so the base license governs what publishing requires. Check the base (from `training_metadata.json` → `model_name`) against this table and state the relevant line to the user in plain English before upload. This is guidance, not legal advice — for commercial redistribution questions, tell the user to read the actual license.

| Base family | License | What publishing a fine-tune requires |
|---|---|---|
| SmolLM2 (HuggingFaceTB) | Apache-2.0 | Nothing special. Keep an attribution line in the model card. |
| Qwen2.5 (0.5B–72B) | Apache-2.0 | Nothing special. Attribution line. |
| Mistral 7B (base/instruct) | Apache-2.0 | Nothing special. Attribution line. |
| Llama 3.2 / 3.x | Llama Community License | Derivative model name must **start with "Llama"** (e.g. `llama-3.2-email-sorter`); include the license and "Built with Llama" attribution; terms flow down to users of your model. |
| Gemma 2 | Gemma Terms of Use | Derivatives must carry the Gemma terms (use restrictions flow down); include a copy/link in the repo. |
| Phi-3.5 | MIT | Nothing special. Attribution line. |

Practical rules:

- **Apache-2.0 / MIT bases** → publish freely, any name, any visibility; put "Fine-tuned from `<base>` (Apache-2.0)" in the card.
- **Llama bases** → enforce the naming rule yourself when suggesting the repo/model name; add the attribution and license file to the upload.
- **Gemma bases** → include the terms link; mention the use-restriction flow-down in the card.
- A model the user brought from outside the catalog (BYO Hugging Face id) → open its HF page and read the license tag before publishing; if it's gated or non-commercial (e.g. some research-only releases), say so plainly — publishing may not be permitted at all.
