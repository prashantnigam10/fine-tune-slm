# Synthetic Data Generation

Use when the user has no dataset, too small a dataset, or evaluation showed data quantity/imbalance is why the goal was missed. You (Claude) write the examples directly — no API calls, no external services.

## Process

1. **Agree on the spec first.** From the interview you know the task, the input domain, and the output format. Write 5 sample examples and show them to the user: "Here's the kind of practice examples I'll create — do these look like your real data?" Adjust until they say yes. This step is not skippable — synthetic data that doesn't resemble real inputs produces a model that fails on real inputs.

2. **Generate in batches** of 20–30, writing directly to `data/synthetic_data.jsonl` in prompt/completion format. Targets: 100–150 for classification, 250–400 for generation tasks. When augmenting an existing dataset after a missed goal, generate specifically for the failure modes found in evaluation (the categories or input styles the model got wrong).

## Diversity requirements (the whole game)

A model fine-tuned on samey data learns the phrasing, not the task. Deliberately vary:

- **Length**: one-liners through multi-paragraph inputs
- **Register**: formal, casual, terse, rambling, typos, ALL CAPS frustration
- **Vocabulary**: don't reuse the same signal words ("angry" emails that never say "angry")
- **Structure**: with/without greetings, signatures, quoted threads, bullet points
- **Hard cases** (~15–20%): sarcasm, mixed signals, borderline examples, negation ("not bad at all"), topic drift
- **Balance**: equal counts per label for classification, unless the user's real-world distribution says otherwise

Anti-pattern check: after generating, scan your own output — if you can predict the label from a single recurring word, regenerate those examples.

## Downloading from Hugging Face instead

When a well-known public dataset fits (e.g., sentiment, spam, common NLP tasks):

1. Search Hugging Face datasets; prefer high-download-count, documented, permissively licensed sets.
2. Confirm the specific dataset with the user before downloading (name, size, license).
3. Download with the `datasets` library (`pip3 install datasets`), sample down to a workable size (a few hundred examples is plenty for LoRA), and map columns into the prompt/completion template with `prepare_data.py`.
4. Keep the user's test set separate: if the user has ANY real data, reserve it all for testing and train on the downloaded/synthetic data — evaluating on real data is what proves the model works.
