# Data Formats and Prompt Templates

## The pipeline format

Everything converges to **prompt/completion JSONL** — one JSON object per line:

```json
{"prompt": "Classify the sentiment of this email as positive, negative, or neutral.\n\nSubject: Great job\nEmail: The deliverables exceeded expectations.\n\nSentiment:", "completion": " positive"}
```

Rules that matter:
- The completion **starts with a single space** (tokenization behaves better).
- The prompt **ends with a cue** the model completes (`Sentiment:`, `Answer:`, `Summary:`) — the same cue used later at inference time.
- One consistent template across ALL examples. Inconsistency is the #1 silent killer of fine-tune quality.

`prepare_data.py` converts this to MLX's `{"text": prompt + completion}` format and splits into `train.jsonl` / `valid.jsonl` / `test.jsonl` (80/10/10, minimum 4 valid + 4 test). MLX-LM expects a **directory** containing these files.

## Designing the prompt template per task type

**Classification** — state the allowed labels in the prompt; keep completions to the bare label:
```
Classify this support ticket as urgent, normal, or low priority.

Ticket: {text}

Priority:
```
completion: ` urgent`

**Extraction** — show the fields wanted; completion is the structured answer:
```
Extract the person's name and company from this email signature.

Text: {text}

Name and company:
```
completion: ` Jane Doe, Acme Corp`

**Style / rewriting**:
```
Rewrite this message in a friendly, professional tone.

Original: {text}

Rewritten:
```

**Q&A / knowledge**:
```
Answer the question using a short, direct answer.

Question: {text}

Answer:
```

## Mapping user files

- **CSV/Excel**: identify the input column(s) and the output column. Multiple input columns get labeled in the prompt (like Subject/Email above). Show the user 2 converted examples before proceeding.
- **JSON/JSONL with other keys** (`input`/`output`, `question`/`answer`, `text`/`label`): map to prompt/completion via the template.
- **Plain text or documents**: there's no supervision signal — work with the user to define input→output pairs, or go synthetic.

## Quality checks before training

- Deduplicate exact-duplicate prompts (keep first).
- Classification: report label counts; flag if any label is under ~20% of its fair share.
- Flag examples whose prompt+completion exceed ~2048 tokens (roughly 8000 characters) — truncate or drop with user consent.
- Spot-check 5 random examples yourself: does the completion actually answer the prompt?
