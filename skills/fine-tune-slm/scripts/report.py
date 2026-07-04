#!/usr/bin/env python3
"""Build the plain-English HTML report comparing baseline vs fine-tuned results.

Reads from the project folder:
  results/baseline/results.json   (from evaluate.py)
  results/final/results.json      (from evaluate.py)
  adapters/*/training_metadata.json  (optional)
  summary.json or --summary-json  (agent-provided plain-language context)

summary.json keys (all optional, all plain language):
  task_description, goal_description, goal_met (bool), model_label,
  data_source ("your file" / "created by Claude" / "downloaded from ..."),
  n_training_examples, synthetic_note, ollama_name, prompt_template, next_steps

Writes <project>/report/report.html. --open opens it in the default browser.
"""

import argparse
import html
import json
import subprocess
import sys
from pathlib import Path


def load_json(path):
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def pct(x):
    return f"{x * 100:.0f}%" if isinstance(x, (int, float)) else "n/a"


def score_of(results):
    if not results:
        return None
    return results.get("judge_accuracy", results.get("accuracy"))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", required=True, help="project folder")
    ap.add_argument("--summary-json", help="path to summary.json (default <project>/summary.json)")
    ap.add_argument("--open", action="store_true", help="open the report in the browser")
    args = ap.parse_args()

    proj = Path(args.project).resolve()
    baseline = load_json(proj / "results/baseline/results.json")
    final = load_json(proj / "results/final/results.json")
    summary = load_json(args.summary_json or proj / "summary.json")
    meta = {}
    for m in sorted(proj.glob("adapters/*/training_metadata.json")):
        meta = load_json(m)

    b, f = score_of(baseline), score_of(final)
    b_pct, f_pct = pct(b), pct(f)
    improvement = f"{(f - b) * 100:+.0f} percentage points" if isinstance(b, (int, float)) and isinstance(f, (int, float)) else ""

    task = summary.get("task_description", "your task")
    goal = summary.get("goal_description", "")
    goal_met = summary.get("goal_met")
    model_label = summary.get("model_label", (final.get("model") or "the model").split("/")[-1])
    data_source = summary.get("data_source", "your examples")
    n_train = summary.get("n_training_examples", meta.get("training_examples", "—"))
    train_time = meta.get("training_time_seconds")
    train_time_str = f"{train_time / 60:.0f} minutes" if isinstance(train_time, (int, float)) and train_time > 90 \
        else (f"{train_time:.0f} seconds" if isinstance(train_time, (int, float)) else "—")
    ollama_name = summary.get("ollama_name")
    template = summary.get("prompt_template", "")

    e = html.escape

    def badge():
        if goal_met is True:
            return '<span class="badge ok">Goal achieved</span>'
        if goal_met is False:
            return '<span class="badge warn">Goal not fully reached</span>'
        return ""

    def bar(label, value, color):
        w = max(2, (value or 0) * 100)
        return (f'<div class="barrow"><div class="barlabel">{e(label)}</div>'
                f'<div class="bartrack"><div class="barfill" style="width:{w}%;background:{color}">'
                f'{pct(value)}</div></div></div>')

    # sample predictions: up to 3 fixed-by-training, else first 3 finals
    samples = []
    if baseline.get("predictions") and final.get("predictions"):
        base_map = {p["prompt"]: p for p in baseline["predictions"]}
        fixed = [p for p in final["predictions"]
                 if p.get("correct") and base_map.get(p["prompt"], {}).get("correct") is False]
        samples = (fixed or final["predictions"])[:3]
    elif final.get("predictions"):
        samples = final["predictions"][:3]

    sample_html = ""
    for s in samples:
        base_pred = ""
        if baseline.get("predictions"):
            bp = next((p for p in baseline["predictions"] if p["prompt"] == s["prompt"]), None)
            if bp:
                base_pred = f'<div class="pred old">Before training it said: <b>{e(bp["predicted"][:120])}</b></div>'
        sample_html += f"""
        <div class="sample">
          <div class="prompt">{e(s["prompt"][:400])}</div>
          {base_pred}
          <div class="pred new">Now it says: <b>{e(s["predicted"][:120])}</b>
             <span class="expected">(expected: {e(s["expected"])})</span></div>
        </div>"""

    steps = [
        ("Checked your Mac", "Confirmed your computer has the chip, memory, and disk space needed."),
        ("Prepared the practice examples",
         f"Used {e(str(data_source))} — {e(str(n_train))} examples the model learned from, "
         "plus a held-back set it never saw, used only for fair testing."),
        ("Tested the model before training",
         f"The untrained model ({e(model_label)}) scored <b>{b_pct}</b> on the held-back test — our starting line."),
        ("Trained it on your examples",
         f"A technique called LoRA gently adjusted a small part of the model. Took about {train_time_str}, entirely on your Mac — nothing was uploaded."),
        ("Tested it again", f"Same test, after training: <b>{f_pct}</b>."),
    ]
    if ollama_name:
        steps.append(("Installed it into Ollama",
                      f"Your model is now available as <code>{e(ollama_name)}</code> — see below."))
    if summary.get("synthetic_note"):
        steps.insert(2, ("Created extra practice examples", e(summary["synthetic_note"])))

    steps_html = "".join(
        f'<div class="step"><div class="num">{i+1}</div><div><b>{t}</b><br>{d}</div></div>'
        for i, (t, d) in enumerate(steps))

    def filelink(rel, label):
        p = proj / rel
        return (f'<li><a href="file://{e(str(p))}">{e(label)}</a> '
                f'<span class="path">{e(str(p))}</span></li>') if p.exists() else ""

    files_html = "".join([
        filelink("results/baseline/results.json", "Before-training test results"),
        filelink("results/final/results.json", "After-training test results"),
        filelink("data/mlx_format", "Training data"),
        filelink("adapters", "The trained adapter (the 'lesson' the model learned)"),
        filelink("models", "The full merged model"),
        filelink("report/report.html", "This report"),
    ])

    usage_html = ""
    if ollama_name:
        usage_html = f"""<h2>How to use your model</h2>
        <p>Open Terminal and run:</p>
        <pre>ollama run {e(ollama_name)} "{e(template[:200]) if template else 'your input here'}"</pre>
        <p class="muted">Tip: the model works best when you phrase requests the same way it was
        trained{' — the template above shows the shape it expects' if template else ''}.</p>"""

    next_html = f"<h2>Suggested next steps</h2><p>{e(summary['next_steps'])}</p>" if summary.get("next_steps") else ""

    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Your fine-tuned model — results</title>
<style>
 body{{font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:820px;margin:40px auto;
      padding:0 20px;color:#1a1a2e;line-height:1.55}}
 h1{{font-size:1.7em}} h2{{margin-top:1.8em;border-bottom:2px solid #eee;padding-bottom:6px}}
 .badge{{display:inline-block;padding:4px 14px;border-radius:14px;font-weight:600;margin-left:8px;font-size:.8em}}
 .badge.ok{{background:#d4f7dc;color:#116329}} .badge.warn{{background:#fff3cd;color:#7a5b00}}
 .hero{{background:#f6f8fa;border-radius:12px;padding:22px 26px;margin:22px 0}}
 .barrow{{display:flex;align-items:center;margin:10px 0}}
 .barlabel{{width:140px;font-weight:600;font-size:.92em}}
 .bartrack{{flex:1;background:#e9ecef;border-radius:8px;height:30px}}
 .barfill{{height:30px;border-radius:8px;color:#fff;font-weight:700;display:flex;
          align-items:center;justify-content:flex-end;padding-right:10px;min-width:44px}}
 .step{{display:flex;gap:14px;margin:14px 0}}
 .num{{background:#4263eb;color:#fff;border-radius:50%;width:28px;height:28px;flex:none;
      display:flex;align-items:center;justify-content:center;font-weight:700}}
 .sample{{border:1px solid #e1e4e8;border-radius:10px;padding:14px;margin:12px 0}}
 .prompt{{white-space:pre-wrap;font-size:.85em;color:#555;background:#fafbfc;
         border-radius:6px;padding:10px;margin-bottom:8px}}
 .pred.old b{{color:#c0392b}} .pred.new b{{color:#116329}}
 .expected{{color:#888;font-size:.85em}}
 pre{{background:#1a1a2e;color:#e8e8f0;padding:14px;border-radius:8px;overflow-x:auto}}
 .path{{color:#999;font-size:.8em}} .muted{{color:#777;font-size:.9em}}
 li{{margin:6px 0}}
</style></head><body>
<h1>Your custom AI model is ready {badge()}</h1>
<p>You now have a small AI model, trained on your own examples, that runs entirely on this Mac —
no cloud, no subscription, and your data never left your computer.</p>
<div class="hero">
  <p style="margin-top:0"><b>The task:</b> {e(task)}{f"<br><b>Your goal:</b> {e(goal)}" if goal else ""}</p>
  {bar("Before training", b, "#adb5bd")}
  {bar("After training", f, "#2f9e44")}
  {f'<p style="margin-bottom:0"><b>Improvement: {e(improvement)}</b></p>' if improvement else ""}
</div>
<h2>What was done, step by step</h2>
{steps_html}
{f'<h2>Examples of what changed</h2>{sample_html}' if sample_html else ""}
{usage_html}
<h2>Where everything lives</h2>
<p class="muted">Everything is inside <code>{e(str(proj))}</code> — delete that folder and it's all gone.</p>
<ul>{files_html}</ul>
{next_html}
<p class="muted" style="margin-top:3em">Generated by the fine-tune-slm skill · {e(final.get("timestamp", ""))}</p>
</body></html>"""

    out = proj / "report" / "report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"Report written to {out}")
    if args.open:
        subprocess.run(["open", str(out)], check=False)


if __name__ == "__main__":
    main()
