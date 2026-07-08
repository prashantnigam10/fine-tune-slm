---
name: Bug report
about: Something went wrong during a fine-tuning run
title: ""
labels: bug
assignees: ""
---

**What happened?**
A clear description of what went wrong.

**What did you expect?**

**Run context (the dashboard makes this easy)**
- Skill version / commit:
- Mac + RAM (from the dashboard's Setup or preflight output):
- Base model fine-tuned (e.g. SmolLM2-1.7B-Instruct):
- Agent driving the skill (e.g. Claude Code + Sonnet, Antigravity):
- Data path: own data / synthetic / Hugging Face download

**Evidence**
If you can, attach or paste:
- The relevant lines from the dashboard's **Activity log** tab (timestamped record of what ran)
- `results/baseline/results.json` and `results/final/results.json` accuracy values
- The failing command's output

**Anything else?**
