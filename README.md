# fine-tune-slm

**Fine-tune a small language model on your own Mac — no AI engineering background required.**

This is an [Agent Skill](https://code.claude.com/docs/en/skills) for [Claude Code](https://claude.com/claude-code) that walks anyone with basic technical comfort through fine-tuning a small language model (SLM) locally on Apple Silicon. You describe your task in plain English and point at your data (or let the skill create data for you) — the skill handles the engineering: hardware checks, model selection, data preparation, LoRA training with Apple's MLX framework, before/after evaluation, export to Ollama, and a plain-English HTML report of everything that happened.

Born from the tutorial series [Small Language Models: The Future of Local AI](https://dev.to/prashant/small-language-model-sml-the-future-of-local-ai-part-1-3dp6).

## What it does

1. **Checks your Mac** — chip, RAM, disk, dependencies; fails gracefully if requirements aren't met
2. **Interviews you in plain English** — what should the model learn, what does a perfect answer look like, how good does it need to be. Never asks you about hyperparameters.
3. **Prepares your data** — converts CSV/JSON/JSONL into training format; if you have no data (or too little), offers to generate synthetic examples or download a public dataset from Hugging Face
4. **Picks a model for your hardware** — from a vetted catalog of open-weight SLMs (SmolLM2, Qwen2.5, Llama 3.2, Gemma 2, Phi-3.5, Mistral), sized to your RAM; you can also bring your own Hugging Face model
5. **Measures a baseline** — tests the untrained model first, so improvement is provable
6. **Trains with LoRA** — minutes, not hours; entirely on-device, nothing uploaded anywhere
7. **Evaluates against your goal** — and if the goal is missed, diagnoses why (data quantity? imbalance? template?) and offers a targeted fix
8. **Exports to Ollama** — so `ollama run your-model` just works
9. **Reports in plain language** — a single interactive HTML dashboard with before/after scores, what changed, a full activity log of everything the run did, every file explained with disk-cleanup guidance, and a ready-to-copy command to use your model

## What can I build with this?

Everyday things people fine-tune a local SLM for — no AI background needed for any of them:

- **Email triage** — sort your inbox by urgency, trained on ~50–100 of your own labeled emails
- **Expense categorizer** — cryptic bank-statement lines → budget categories; exactly the data you *don't* want in the cloud
- **Meeting-notes action extractor** — paste raw notes, get back the action items with owners
- **Personal style rewriter** — blunt drafts → your own polite email voice, trained on pairs from your Sent folder
- **Support-ticket router** — billing / bug / how-to / feature-request, with priority
- **Recipe dietary tagger** — vegetarian, gluten-free, contains nuts — no data needed; the skill generates it
- **Journal mood tagger** — tag entries by mood and theme; deeply personal data that stays on your Mac
- **Log-severity classifier** — a local triage model for your app's log lines
- **Homework question sorter** — bucket practice questions by subject and difficulty for worksheets
- **Customer-review digester** — sentiment plus a one-phrase topic ("negative — shipping delay")

The privacy-heavy ones (expenses, journal, email) are where local fine-tuning shines: the model, the training data, and every prediction stay on your machine.

## Requirements

- Mac with Apple Silicon (M1 or newer) — the skill uses Apple's [MLX](https://github.com/ml-explore/mlx) framework
- 8 GB RAM minimum (16 GB+ recommended for larger models)
- ~15 GB free disk space
- Python 3.9+
- [Claude Code](https://claude.com/claude-code)

Support for other platforms (Linux/Windows via PyTorch) is planned.

## Install

```bash
git clone https://github.com/prashantnigam10/fine-tune-slm.git
cp -R fine-tune-slm/skills/fine-tune-slm ~/.claude/skills/
```

Then in any Claude Code session, just describe what you want:

> fine-tune a small model to sort my support emails into urgent / normal / low

Claude picks up the skill automatically. No further setup — the skill installs its own Python dependencies into a per-project virtual environment when it runs.

## Example result

From the original email-sentiment project this skill is based on: SmolLM2-1.7B went from **62% → 99% accuracy** on email sentiment classification after a ~5-minute LoRA fine-tune on a MacBook, with the trained adapter weighing ~35 MB.

## Repository layout

```
skills/fine-tune-slm/    the skill itself (copy this folder into ~/.claude/skills/)
├── SKILL.md             the workflow Claude follows
├── scripts/             deterministic steps: preflight, data prep, training, evaluation, dashboard
└── references/          model catalog, data formats, synthetic data, Ollama export, troubleshooting
```

## License

[MIT](LICENSE)
