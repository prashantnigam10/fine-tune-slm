# Lessons from real runs

This skill was built by running it, watching it fail, and fixing what broke. These are the
failures that shaped the design — kept here because they'll save you (and future
contributors) from re-learning them. Every one maps to a fix that shipped or an
[open issue](https://github.com/prashantnigam10/fine-tune-slm/issues).

## 1. A percentage met a fraction, and the report said "3330%"

One run stored baseline accuracy as `33.3` (a percent) while the final was `1.0` (a
fraction). The report trusted both and rendered a 3330% bar and "-3230 points improvement."
**Lesson:** numbers need a contract. Scores are 0–1 fractions everywhere now, results files
may only be produced by `evaluate.py`, and the dashboard normalizes and clamps defensively.

## 2. Training made the model worse — and the run called it a success

A broken training run produced a final score *below* the untrained baseline (the model had
collapsed to guessing one label). The session summary still declared a "production-ready
classifier" — and quoted an accuracy figure that appeared in no evaluation file at all.
**Lesson:** an agent under pressure to succeed will narrate success. Honesty must be
mechanical: every number traceable to a results file, an unmissable regression verdict when
final ≤ baseline, and a substituted approach counts as unmeasured until evaluated the same
way. This is the top of the roadmap.

## 3. The best model was at step 100; training ran to step 1000

Validation loss bottomed early and drifted upward for 900 more iterations — classic
overfitting on a small dataset. The simple "last three losses rising" check didn't fire
because the final reading dipped slightly. **Lesson:** compare the final checkpoint to the
*best* checkpoint seen, not to its immediate neighbors. The snapshots are already on disk;
choosing well is free.

## 4. Identical model, "different" baselines: 3% vs 24%

Two runs of the same task measured wildly different baselines for the same untrained model.
Cause: different test samples — plus a scoring rule that gave credit when a prediction merely
*started with* the expected answer, which an untrained model parroting all labels exploits.
**Lesson:** a baseline is model + test set + scoring rule, not a property of the model. And
lenient matching helps exactly the failure modes you most need to see.

## 5. Instructions don't survive weaker drivers; scripts do

Across runs driven by different agent models, everything scripted (preflight, data prep,
training wrapper, evaluation) behaved identically — and nearly everything left to the
agent's memory eventually got skipped by someone: writing metadata, building the results
dashboard, even using the training wrapper at all. **Lesson:** the design principle of this
repo. Deterministic scripts do the heavy lifting; the agent does judgment. When a step
matters, a script must own it.

## 6. A trailing space forked a project

A working directory with a trailing space in its name caused a run to silently recreate the
project in a sibling folder (same name, no space), orphaning the approved data and the
recorded goal. **Lesson:** resolve the project path once and reuse the exact string;
re-typing paths across commands is where they quietly mutate.

## 7. Unpinned installs broke on a schedule

`pip install mlx-lm` plus "latest transformers" worked until a new transformers release
didn't. Two separate runs lost time to the same mismatch. **Lesson:** one shared
environment, built only from a pinned, tested-together `requirements.txt`. Boring, standard,
effective.

## 8. The question nobody saw

An approval checkpoint asked for review as a plain sentence in chat; the user skimmed past
it and the run appeared to have never asked. Another run buried review content inside a
question widget's collapsed options. **Lesson:** review content goes in the dashboard where
it's visible first; the ask itself uses the agent's structured question tool. And all
questions belong up front — never after a long-running step that could have waited.

---

*The dashboard's activity log exists because of these runs too: when things go sideways, a
timestamped record of every install, download, and command is the difference between a
diagnosis and a shrug.*
