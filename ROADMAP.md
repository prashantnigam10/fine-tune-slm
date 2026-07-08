# Roadmap

Where fine-tune-slm is heading, and where help is most welcome. The **canonical backlog is
[GitHub Issues](https://github.com/prashantnigam10/fine-tune-slm/issues)** - every item below
exists (or will exist) as an issue you can comment on, claim, or send a PR against. This file
is the map; the issues are the work.

Everything here was learned from real fine-tuning runs during validation - none of it is
speculative ([LESSONS.md](LESSONS.md) tells the stories behind the items, failures included).
Issues labeled `good first issue` are self-contained; `help wanted` means we'd love a
contributor to own it.

## 🔴 Now: evaluation integrity ("every number must be traceable")

Validation showed that when a run fails, a weaker driving agent may paper over it - skipping
the dashboard's results step, training outside the wrapper, or reporting an accuracy figure
that no evaluation ever produced. The fix is mechanical guardrails, not more instructions:

- **Auto-build dashboard results after every evaluation** - `evaluate.py` should invoke the
  dashboard build itself, so results tabs can never silently stay empty
- **Loud regression signal** - when final accuracy ≤ baseline, `evaluate.py` prints an
  unmissable REGRESSION verdict; the run must report it as a failure, never "ready"
- **No unmeasured claims** - any accuracy shown to the user must be traceable to a
  `results.json` produced by `evaluate.py`; substituted approaches (rules/regex/other models)
  must be evaluated the same way or labeled "not measured"
- **Actionable `train.py` failures** - when training data can't be found/counted, fail with
  the looked-for path and directory contents, so the fix is obvious and hand-rolled
  workarounds are never needed

## 🟠 Next: correctness & unattended runs

- **Fairer multi-label scoring** - replace prefix-matching with first-segment exact match
  (plus order-insensitive tag-set comparison), and stamp results with a `scoring_version`
- **Front-load every question** - all user decisions (goal, data, samples, model, location)
  batched at the start so the long phase runs unattended; never ask a question after a
  >1-minute step that could have been asked before it
- **Structured prompts at checkpoints** - approve/adjust moments must use the agent's
  question widget, not a prose sentence that's easy to miss
- **Goal-aware synthetic data volume** - scale generated-example counts with the accuracy
  target, class count, and task difficulty; show the reasoning at sample approval
- **Anchor the project path once** - a trailing space in a folder name caused a silent fork
  into a duplicate project; establish the canonical path at setup and never re-derive it
- **Driving-model guidance** - document that the agent driving the skill should be
  Sonnet-class or better (lighter models have mishandled failures and misreported results),
  and that a below-baseline result means a broken run, not a weak base model

## 🟡 Later: polish & efficiency

- **Smarter checkpoint selection** - compare final validation loss to the best seen, and
  prefer the earlier checkpoint when training overshot into overfitting
- **Disk efficiency** - optionally delete the fused model after Ollama imports its own copy
  (~3.4 GB back); skip fusing entirely when Ollama isn't installed
- **Baseline-in-Ollama convenience** - optional export of the untrained base model for
  informal before/after comparison (with clear caveats: cross-engine inference differs
  slightly; `results/baseline/results.json` stays authoritative)

## 🔭 Direction (design discussions welcome in issues)

- **Windows & Linux backend** - PyTorch + PEFT/QLoRA implementation of `train.py` /
  `evaluate.py` / fuse; the interview, data prep, and dashboard layers are already
  platform-neutral. *The single highest-impact contribution.*
- **Publishing** - an opt-in, deliberate flow for sharing a tested model to ollama.com or
  Hugging Face (kept separate from training: test first, publish later)
- **Distribution** - Claude Code plugin/marketplace packaging; validated install paths and
  testing for more agents (Cursor, Codex); per-agent question-tool phrasing

## Contributing

See the [Contributing section of the README](README.md#-contributing). Short version: fork,
branch, test with a real fine-tuning run (the dashboard's activity log makes great PR
evidence), open a PR - and open an issue first for anything big.
