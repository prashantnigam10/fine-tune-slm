#!/usr/bin/env python3
"""Single-file HTML dashboard for a fine-tuning project run.

One dashboard.html per project. The workflow adds sections and activity-log
entries as it progresses; every command re-renders the whole page, so the user
just refreshes the same file. Offline, no external dependencies.

Commands (all take --project <folder>):
  init      --task "..." [--goal "..."] [--model-label "..."]   start the dashboard
  section   --id data-samples --stage data --title "..."
            (--html-file f.html | --html "<p>...</p>")          add/replace a section
  stage     --id training --status done|running|skipped|pending [--note "..."]
  log       --action "Installed mlx-lm" [--detail "pip3 install mlx-lm"]
            [--category install|download|file|run|other]        append activity entry
  results   [--summary-json summary.json] [--open]              build baseline/final
            sections from results/*/results.json (run after each evaluation)
  render    [--open]                                            re-render only

Scores in results JSONs are 0-1 fractions; values > 1 are assumed to be
percentages and normalized. State lives in report/state/; dashboard.html is
regenerated from it idempotently (updating a section replaces it).
"""

import argparse
import html
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from string import Template

STAGES = [
    ("setup", "Setup & checks"),
    ("data", "Data"),
    ("model", "Model choice"),
    ("baseline", "Before training"),
    ("training", "Training"),
    ("results", "Results"),
    ("export", "Local Ollama"),
]
STAGE_IDS = [s for s, _ in STAGES]
UTIL_TABS = [("files", "Files & disk"), ("activity", "Activity log")]

# curated descriptions for the folder tree (prefix match on relative path)
PATH_DESCRIPTIONS = {
    "data": "Everything the model learned from",
    "data/mlx_format": "The examples converted into the format the training tool needs",
    "data/mlx_format/train.jsonl": "The examples the model practiced on",
    "data/mlx_format/valid.jsonl": "Examples used to check progress during training",
    "data/mlx_format/test.jsonl": "Held-back examples for the fair before/after test",
    "data/mlx_format/test_pairs.jsonl": "The same test examples, kept in question/answer form for scoring",
    "data/synthetic_data.jsonl": "Practice examples that were generated for you",
    "adapters": "The small 'lesson' file training produced (the base model itself was never modified)",
    "models": "Full standalone copies of your customized model",
    "results": "Test scores and every individual prediction",
    "results/baseline": "How the model did BEFORE training",
    "results/final": "How the model did AFTER training",
    "report": "This dashboard and its data",
    "venv": "Python tools for this project (older runs only - newer runs share one set at ~/.slm-finetune)",
    "summary.json": "Plain-language facts about this run, used by this dashboard",
}


def esc(s):
    return html.escape(str(s), quote=True)


def norm_score(x):
    """Scores are 0-1 fractions; tolerate percentages written by mistake."""
    if not isinstance(x, (int, float)):
        return None
    if x > 1:
        x = x / 100.0
    return max(0.0, min(1.0, x))


def pct(x):
    return f"{x * 100:.0f}%" if isinstance(x, (int, float)) else "n/a"


def state_dir(proj):
    d = proj / "report" / "state"
    (d / "sections").mkdir(parents=True, exist_ok=True)
    return d


def load_meta(proj):
    f = state_dir(proj) / "meta.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"task": "", "goal": "", "model_label": "",
            "stages": {s: {"status": "pending", "note": ""} for s in STAGE_IDS}}


def save_meta(proj, meta):
    (state_dir(proj) / "meta.json").write_text(json.dumps(meta, indent=2))


def load_sections(proj):
    secs = []
    for f in (state_dir(proj) / "sections").glob("*.json"):
        try:
            secs.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            pass
    secs.sort(key=lambda s: (STAGE_IDS.index(s.get("stage", "setup"))
                             if s.get("stage") in STAGE_IDS else 99, s.get("order", 0)))
    return secs


def save_section(proj, sec):
    (state_dir(proj) / "sections" / f"{sec['id']}.json").write_text(json.dumps(sec))


def append_activity(proj, action, detail="", category="other"):
    entry = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "action": action,
             "detail": detail, "category": category}
    with open(state_dir(proj) / "activity.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_activity(proj):
    f = state_dir(proj) / "activity.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


def dir_size(path):
    total = 0
    for root, _, files in os.walk(path, onerror=lambda e: None):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def human(nbytes):
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024 or unit == "GB":
            return f"{nbytes:.1f} {unit}" if unit != "B" else f"{nbytes} B"
        nbytes /= 1024
    return f"{nbytes:.1f} GB"


def describe(rel):
    if rel in PATH_DESCRIPTIONS:
        return PATH_DESCRIPTIONS[rel]
    parts = rel.split("/")
    for i in range(len(parts), 0, -1):
        prefix = "/".join(parts[:i])
        if prefix in PATH_DESCRIPTIONS and i < len(parts):
            return ""  # parent already explained; leave child blank
    if rel.startswith("adapters/") and rel.endswith(".safetensors"):
        return "The learned adjustments (this tiny file is all training produced)"
    if rel.endswith("training_metadata.json"):
        return "A record of the training run: settings, duration, command used"
    if rel.endswith("results.json"):
        return "Scores plus every question, expected answer, and the model's answer"
    return ""


# ---------------------------------------------------------------- files & disk


def build_files_section(proj):
    rows = []

    def walk(d, depth):
        try:
            entries = sorted(d.iterdir(), key=lambda p: (p.is_file(), p.name))
        except OSError:
            return
        for p in entries:
            if p.name in (".DS_Store", "__pycache__") or p.name.startswith(".git"):
                continue
            rel = str(p.relative_to(proj))
            if p.is_dir():
                size = dir_size(p)
                rows.append((rel, depth, True, size, describe(rel)))
                # don't descend into bulky internals
                if p.name not in ("venv", "state", "__pycache__") and depth < 3:
                    walk(p, depth + 1)
            else:
                try:
                    size = p.stat().st_size
                except OSError:
                    size = 0
                rows.append((rel, depth, False, size, describe(rel)))

    walk(proj, 0)
    tree = "".join(
        f'<div class="frow" style="padding-left:{depth * 22}px">'
        f'<span class="fname">{"&#128193; " if is_dir else ""}'
        f'<a href="file://{esc(str(proj / rel))}">{esc(Path(rel).name)}</a></span>'
        f'<span class="fsize">{human(size)}</span>'
        f'<span class="fdesc">{esc(desc)}</span></div>'
        for rel, depth, is_dir, size, desc in rows)

    # disk footprint across the three weight locations
    home = Path.home()
    hf = home / ".cache" / "huggingface"
    ol = home / ".ollama" / "models"
    shared = home / ".slm-finetune"
    proj_size = dir_size(proj)
    locs = [
        (str(proj), proj_size, "This project: your data, the trained adapter, results, and this report.",
         "Delete the whole folder when you no longer need any of it."),
        (str(hf), dir_size(hf) if hf.exists() else 0,
         "Downloaded base models (shared by all your fine-tuning projects).",
         f"Safe to delete — models re-download if ever needed again: <code>rm -rf {esc(str(hf))}</code>"),
        (str(ol), dir_size(ol) if ol.exists() else 0,
         "Ollama's own copies of models, including your custom one. This is what actually runs.",
         "Remove individual models with <code>ollama rm &lt;name&gt;</code>. Keep your custom one while you use it."),
        (str(shared), dir_size(shared) if shared.exists() else 0,
         "The Python training tools, shared by all your fine-tuning projects (installed once).",
         f"Safe to delete when you're done fine-tuning for good: <code>rm -rf {esc(str(shared))}</code>"),
    ]
    disk = "".join(
        f'<div class="dloc"><div><b>{esc(Path(p).name if p != str(proj) else "Project folder")}</b> '
        f'<span class="path">{esc(p)}</span></div>'
        f'<div class="dsize">{human(s)}</div><div class="muted">{what}<br>{reclaim}</div></div>'
        for p, s, what, reclaim in locs if s > 0 or p == str(proj))

    return (f'<h3>Disk space used</h3>{disk}'
            f'<h3 style="margin-top:1.4em">Every file this run created</h3>'
            f'<div class="ftree">{tree}</div>')


def build_activity_section(proj):
    entries = load_activity(proj)
    if not entries:
        return "<p class='muted'>No activity recorded yet.</p>"
    icons = {"install": "&#128230;", "download": "&#11015;&#65039;", "file": "&#128196;",
             "run": "&#9881;&#65039;", "other": "&#8226;"}
    rows = "".join(
        f'<div class="arow"><span class="ats">{esc(e["ts"])}</span>'
        f'<span class="aicon">{icons.get(e.get("category", "other"), "&#8226;")}</span>'
        f'<div><div>{esc(e["action"])}</div>'
        + (f'<details><summary class="muted">details</summary><code>{esc(e["detail"])}</code></details>'
           if e.get("detail") else "")
        + "</div></div>"
        for e in entries)
    return ('<p>Everything the skill did on this computer, as it happened — installs, '
            'downloads, files created, and commands run.</p>' + rows)


# ------------------------------------------------------------------- results


def load_json(path):
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def score_of(res):
    return norm_score(res.get("judge_accuracy", res.get("accuracy")))


def count_lines(path):
    p = Path(path)
    if p.exists():
        return sum(1 for l in p.read_text().splitlines() if l.strip())
    return None


def bar(label, value, color):
    if value is None:
        return ""
    w = max(3, value * 100)
    return (f'<div class="barrow"><div class="barlabel">{esc(label)}</div>'
            f'<div class="bartrack"><div class="barfill" style="width:{w:.0f}%;background:{color}">'
            f'{pct(value)}</div></div></div>')


def build_results_sections(proj, meta, summary):
    """Create/refresh baseline + results (+ try-it) sections from results files."""
    baseline = load_json(proj / "results/baseline/results.json")
    final = load_json(proj / "results/final/results.json")
    tmeta = {}
    for m in sorted(proj.glob("adapters/*/training_metadata.json")):
        tmeta = load_json(m)

    b, f = score_of(baseline), score_of(final)
    n_train = summary.get("n_training_examples") or tmeta.get("training_examples") \
        or count_lines(proj / "data/mlx_format/train.jsonl")
    made = []

    if baseline:
        parts = [f"Before any training, the model was tested on "
                 f"{baseline.get('n_examples', 'the')} held-back examples it will never train on."]
        if b is not None:
            parts.append(f"It scored <b>{pct(b)}</b> — our starting line.")
        save_section(proj, {"id": "baseline", "stage": "baseline", "title": "Before training",
                            "html": f"<p>{' '.join(parts)}</p>" + bar("Before training", b, "#adb5bd")})
        made.append("baseline")
        meta["stages"]["baseline"]["status"] = "done"

    if final:
        goal, goal_met = summary.get("goal_description", ""), summary.get("goal_met")
        badge = ('<span class="badge ok">Goal achieved</span>' if goal_met is True
                 else '<span class="badge warn">Goal not fully reached</span>' if goal_met is False else "")
        goal_warn = ""
        if not goal or goal_met is None:
            # A run without a recorded goal can't judge success or trigger retraining -
            # surface that loudly instead of letting it pass silently.
            print("WARNING: summary.json is missing goal_description/goal_met - the run has "
                  "no success target. Agree on a target with the user and re-evaluate "
                  "against it (see SKILL.md step 2/8).", file=sys.stderr)
            goal_warn = ('<div style="background:#fff3cd;border:1px solid #ffe08a;'
                         'border-radius:8px;padding:10px 14px;margin:10px 0">'
                         '<b>No success target was set for this run.</b> The scores below are '
                         'informational, but nothing checked them against a goal - ask for a '
                         'target and re-evaluate if results matter.</div>')
        impr = (f'<p><b>Improvement: {(f - b) * 100:+.0f} percentage points</b></p>'
                if b is not None and f is not None else "")
        # sample predictions fixed by training
        samples_html = ""
        if baseline.get("predictions") and final.get("predictions"):
            base_map = {p["prompt"]: p for p in baseline["predictions"]}
            fixed = [p for p in final["predictions"]
                     if p.get("correct") and base_map.get(p["prompt"], {}).get("correct") is False]
            for s in (fixed or final["predictions"])[:3]:
                bp = base_map.get(s["prompt"], {})
                before = (f'<div class="pred old">Before: <b>{esc(bp.get("predicted", "")[:120])}</b></div>'
                          if bp else "")
                samples_html += (f'<div class="sample"><div class="prompt">{esc(s["prompt"][:400])}</div>'
                                 f'{before}<div class="pred new">After: <b>{esc(s["predicted"][:120])}</b>'
                                 f' <span class="muted">(expected: {esc(s["expected"])})</span></div></div>')
            if samples_html:
                samples_html = ("<h3>Examples of what changed</h3>"
                                f"<details open><summary>Show examples</summary>{samples_html}</details>")
        save_section(proj, {"id": "results", "stage": "results", "title": "Results", "html":
            goal_warn
            + f'<p><b>The task:</b> {esc(meta.get("task", ""))}'
            + (f'<br><b>Your goal:</b> {esc(goal)} {badge}' if goal else f' {badge}')
            + "</p>" + bar("Before training", b, "#adb5bd") + bar("After training", f, "#2f9e44")
            + impr + samples_html})
        made.append("results")
        meta["stages"]["results"]["status"] = "done"
        meta["score_before"], meta["score_after"] = b, f
        meta["goal_met"] = goal_met

    # training recap (conditional sentences — omit what we don't know)
    if tmeta or n_train:
        bits = []
        if n_train:
            bits.append(f"The model practiced on <b>{n_train}</b> examples.")
        if tmeta.get("training_time_seconds"):
            t = tmeta["training_time_seconds"]
            dur = f"{t / 60:.0f} minutes" if t > 90 else f"{t:.0f} seconds"
            bits.append(f"Training took about <b>{dur}</b>.")
        bits.append("A technique called LoRA gently adjusted a small part of the model — "
                    "entirely on this Mac; nothing was uploaded anywhere.")
        if tmeta.get("command_used"):
            bits.append(f'<details><summary class="muted">exact command</summary>'
                        f'<code>{esc(tmeta["command_used"])}</code></details>')
        save_section(proj, {"id": "training", "stage": "training", "title": "Training",
                            "html": "<p>" + " ".join(bits[:3]) + "</p>" + "".join(bits[3:])})
        made.append("training")

    # try-it section
    ollama_name, template = summary.get("ollama_name"), summary.get("prompt_template", "")
    if ollama_name or final:
        tryit = ""
        if ollama_name:
            tid = "tryitcmd"
            tryit += (
                '<p class="muted">Your model is installed in the Ollama app on this Mac only — '
                'it is not published or uploaded anywhere.</p>'
                '<p>Type your own text below — the command updates as you type. '
                'Copy it and paste into Terminal.</p>'
                f'<textarea id="tryinput" rows="3" placeholder="Paste the text you want the model to handle...">'
                f'</textarea>'
                f'<pre id="{tid}"></pre>'
                f'<button onclick="copyCmd(\'{tid}\')">Copy command</button>'
                f'<script>window.tryitConfig={json.dumps({"name": ollama_name, "template": template})};</script>')
        fused = sorted((proj / "models").glob("*-fused")) if (proj / "models").exists() else []
        if fused:
            tryit += ('<details><summary class="muted">Without Ollama (advanced)</summary>'
                      f'<pre>venv/bin/python -m mlx_lm generate --model {esc(str(fused[-1]))} '
                      '--prompt "..."</pre></details>')
        if tryit:
            save_section(proj, {"id": "tryit", "stage": "export", "title": "Use your model",
                                "html": tryit})
            made.append("tryit")

    if summary.get("next_steps"):
        save_section(proj, {"id": "next", "stage": "results", "title": "Suggested next steps",
                            "order": 9, "html": f"<p>{esc(summary['next_steps'])}</p>"})
    return made


# -------------------------------------------------------------------- render

PAGE = Template(r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>
 :root{--accent:#4263eb;--done:#2f9e44;--muted:#868e96}
 *{box-sizing:border-box} body{font-family:-apple-system,Helvetica,Arial,sans-serif;
   margin:0;color:#1a1a2e;line-height:1.55;background:#f8f9fa}
 header{background:#fff;border-bottom:1px solid #e9ecef;padding:14px 24px;
   position:sticky;top:0;z-index:10}
 h1{font-size:1.15em;margin:0 0 2px} .strip{display:flex;gap:18px;flex-wrap:wrap;
   align-items:center;font-size:.88em;color:#495057}
 .strip b{color:#1a1a2e}
 .badge{display:inline-block;padding:2px 12px;border-radius:12px;font-weight:600;font-size:.85em}
 .badge.ok{background:#d4f7dc;color:#116329}.badge.warn{background:#fff3cd;color:#7a5b00}
 nav{display:flex;gap:4px;flex-wrap:wrap;padding:10px 24px;background:#fff;
   border-bottom:1px solid #e9ecef;position:sticky;top:var(--navtop,64px);z-index:9}
 nav a{display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:18px;
   text-decoration:none;color:#495057;font-size:.86em;border:1px solid transparent}
 nav a.active{background:var(--accent);color:#fff}
 nav a .st{font-size:.95em}
 nav a.util{margin-left:auto} nav a.util ~ a.util{margin-left:0}
 main{max-width:860px;margin:22px auto;padding:0 20px}
 section{display:none;background:#fff;border:1px solid #e9ecef;border-radius:12px;
   padding:20px 26px;margin-bottom:14px}
 section.visible{display:block}
 section h2{margin-top:0;font-size:1.2em} h3{font-size:1.02em}
 .barrow{display:flex;align-items:center;margin:10px 0}
 .barlabel{width:130px;font-weight:600;font-size:.9em}
 .bartrack{flex:1;background:#e9ecef;border-radius:8px;height:28px;overflow:hidden}
 .barfill{height:28px;border-radius:8px;color:#fff;font-weight:700;display:flex;
   align-items:center;justify-content:flex-end;padding-right:9px;min-width:42px;max-width:100%}
 .sample{border:1px solid #e1e4e8;border-radius:10px;padding:12px;margin:10px 0}
 .prompt{white-space:pre-wrap;font-size:.83em;color:#555;background:#fafbfc;
   border-radius:6px;padding:9px;margin-bottom:7px}
 .pred.old b{color:#c0392b}.pred.new b{color:#116329}
 pre,code{background:#f1f3f5;border-radius:6px;font-size:.85em}
 pre{padding:12px;overflow-x:auto;white-space:pre-wrap;word-break:break-all}
 code{padding:1px 5px}
 textarea{width:100%;font:inherit;padding:9px;border:1px solid #ced4da;border-radius:8px}
 button{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:8px 16px;
   font-size:.9em;cursor:pointer;margin-top:6px}
 .muted{color:var(--muted);font-size:.9em} .path{color:#adb5bd;font-size:.8em}
 .frow{display:flex;gap:10px;padding:3px 0;border-bottom:1px solid #f1f3f5;font-size:.88em}
 .fname{min-width:220px} .fsize{min-width:70px;color:#868e96;text-align:right}
 .fdesc{color:#495057}
 .frow a{color:inherit;text-decoration:none}.frow a:hover{text-decoration:underline}
 .dloc{border:1px solid #e9ecef;border-radius:10px;padding:10px 14px;margin:8px 0}
 .dsize{font-weight:700;font-size:1.05em}
 .arow{display:flex;gap:10px;padding:6px 0;border-bottom:1px solid #f1f3f5;font-size:.9em}
 .ats{color:#adb5bd;min-width:150px;font-variant-numeric:tabular-nums}
 details{margin:4px 0} summary{cursor:pointer}
</style></head><body>
<header><h1>$title</h1><div class="strip">$strip</div></header>
<nav id="nav">$nav</nav>
<main>$sections</main>
<script>
function show(id){
  document.querySelectorAll('section').forEach(s=>s.classList.toggle('visible', s.dataset.tab===id));
  document.querySelectorAll('nav a').forEach(a=>a.classList.toggle('active', a.dataset.tab===id));
  history.replaceState(null,'','#'+id);
}
function copyCmd(id){
  const t=document.getElementById(id).textContent;
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t);}
  else{const ta=document.createElement('textarea');ta.value=t;document.body.appendChild(ta);
       ta.select();document.execCommand('copy');ta.remove();}
}
document.querySelectorAll('nav a').forEach(a=>a.onclick=e=>{e.preventDefault();show(a.dataset.tab)});
if(window.tryitConfig){
  const inp=document.getElementById('tryinput'),out=document.getElementById('tryitcmd');
  const upd=()=>{let text=inp.value||'your text here';
    let prompt=tryitConfig.template?tryitConfig.template.replace(/\.\.\./, text):text;
    out.textContent='ollama run '+tryitConfig.name+' "'+prompt.replace(/"/g,'\\"')+'"';};
  inp.addEventListener('input',upd);upd();
}
show(location.hash?location.hash.slice(1):'$first');
</script></body></html>
""")

STATUS_ICON = {"done": "&#10003;", "running": "&#8943;", "skipped": "&#8856;", "pending": "&#9675;"}


def render(proj, open_after=False):
    meta = load_meta(proj)
    secs = load_sections(proj)
    by_stage = {}
    for s in secs:
        by_stage.setdefault(s.get("stage", "setup"), []).append(s)

    # nav: pipeline stages that have content or a non-pending status, then utility tabs
    nav, sections_html, first = [], [], None
    for sid, label in STAGES:
        st = meta["stages"].get(sid, {"status": "pending"})
        has_content = sid in by_stage
        if not has_content and st["status"] == "pending":
            continue
        first = first or sid
        icon = STATUS_ICON.get(st["status"], "&#9675;")
        nav.append(f'<a href="#{sid}" data-tab="{sid}"><span class="st">{icon}</span>{esc(label)}</a>')
        inner = "".join(f"<h2>{esc(s['title'])}</h2>{s['html']}" for s in by_stage.get(sid, [])) \
            or f"<p class='muted'>{esc(st.get('note') or st['status'].capitalize())}.</p>"
        if st["status"] == "skipped" and st.get("note"):
            inner = f"<p class='muted'>Skipped: {esc(st['note'])}</p>" + inner
        sections_html.append(f'<section data-tab="{sid}">{inner}</section>')

    builders = {"files": build_files_section, "activity": build_activity_section}
    for tid, label in UTIL_TABS:
        nav.append(f'<a href="#{tid}" data-tab="{tid}" class="util">{esc(label)}</a>')
        sections_html.append(f'<section data-tab="{tid}"><h2>{esc(label)}</h2>{builders[tid](proj)}</section>')

    # summary strip
    strip = []
    if meta.get("task"):
        strip.append(f"<span><b>{esc(meta['task'])}</b></span>")
    if meta.get("model_label"):
        strip.append(f"<span>Model: <b>{esc(meta['model_label'])}</b></span>")
    if meta.get("score_before") is not None or meta.get("score_after") is not None:
        strip.append(f"<span>Score: <b>{pct(meta.get('score_before'))} &rarr; "
                     f"{pct(meta.get('score_after'))}</b></span>")
    if meta.get("goal_met") is True:
        strip.append('<span class="badge ok">Goal achieved</span>')
    elif meta.get("goal_met") is False:
        strip.append('<span class="badge warn">Goal not fully reached</span>')

    page = PAGE.substitute(
        title="Your fine-tuning run" + (f" — {esc(meta['task'])}" if meta.get("task") else ""),
        strip="".join(strip) or "<span class='muted'>Run in progress…</span>",
        nav="".join(nav), sections="".join(sections_html),
        first="results" if meta["stages"].get("results", {}).get("status") == "done" else (first or "setup"))
    out = proj / "report" / "dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"Dashboard: {out}")
    if open_after:
        subprocess.run(["open", str(out)], check=False)
    return out


# ---------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["init", "section", "stage", "log", "results", "render"])
    ap.add_argument("--project", required=True)
    ap.add_argument("--task"), ap.add_argument("--goal"), ap.add_argument("--model-label")
    ap.add_argument("--id"), ap.add_argument("--title"), ap.add_argument("--stage",
                    choices=STAGE_IDS), ap.add_argument("--html"), ap.add_argument("--html-file")
    ap.add_argument("--order", type=int, default=0)
    ap.add_argument("--status", choices=["done", "running", "skipped", "pending"])
    ap.add_argument("--note", default="")
    ap.add_argument("--action"), ap.add_argument("--detail", default="")
    ap.add_argument("--category", default="other",
                    choices=["install", "download", "file", "run", "other"])
    ap.add_argument("--summary-json")
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()

    proj = Path(a.project).resolve()
    if not proj.exists():
        sys.exit(f"ERROR: project folder not found: {proj}")
    meta = load_meta(proj)

    if a.command == "init":
        for k, v in (("task", a.task), ("goal", a.goal), ("model_label", a.model_label)):
            if v:
                meta[k] = v
        meta["stages"]["setup"]["status"] = "running"
    elif a.command == "section":
        if not (a.id and a.title and (a.html or a.html_file)):
            sys.exit("ERROR: section needs --id, --title, and --html or --html-file")
        content = a.html or Path(a.html_file).read_text()
        save_section(proj, {"id": a.id, "stage": a.stage or "setup", "title": a.title,
                            "html": content, "order": a.order,
                            "updated": time.strftime("%Y-%m-%d %H:%M:%S")})
    elif a.command == "stage":
        if not (a.id and a.status):
            sys.exit("ERROR: stage needs --id and --status")
        if a.id not in STAGE_IDS:
            sys.exit(f"ERROR: unknown stage {a.id}; choose from {STAGE_IDS}")
        meta["stages"][a.id] = {"status": a.status, "note": a.note}
    elif a.command == "log":
        if not a.action:
            sys.exit("ERROR: log needs --action")
        append_activity(proj, a.action, a.detail, a.category)
    elif a.command == "results":
        summary = load_json(a.summary_json or proj / "summary.json")
        if a.model_label:
            meta["model_label"] = a.model_label
        made = build_results_sections(proj, meta, summary)
        print(f"Built sections: {', '.join(made) or 'none (no results files found)'}")

    save_meta(proj, meta)
    render(proj, open_after=a.open)


if __name__ == "__main__":
    main()
