#!/usr/bin/env node
/**
 * fine-tune-slm skill installer.
 *
 * Copies the Agent Skills shipped in this package (skills/fine-tune-slm and
 * skills/publish-slm) into the skills directory of the AI coding agents found
 * on this machine. Pure Node stdlib, no dependencies.
 *
 *   npx fine-tune-slm                 # detect agents, install to all found
 *   npx fine-tune-slm --agent claude  # just Claude Code
 *   npx fine-tune-slm --dir <path>    # any agent: copy into a custom skills dir
 *   npx fine-tune-slm --skill fine-tune-slm   # only one of the two skills
 *   npx fine-tune-slm --list          # show what would happen, change nothing
 */

"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

const PKG_ROOT = path.resolve(__dirname, "..");
const SKILLS = ["fine-tune-slm", "publish-slm"];

// Where each agent looks for user-level Agent Skills.
// status: validated = tested end-to-end | experimental = documented location,
// not yet validated by us | manual = no stable copy target, print instructions.
const AGENTS = {
  claude: {
    label: "Claude Code",
    dir: path.join(os.homedir(), ".claude", "skills"),
    status: "validated",
  },
  codex: {
    label: "OpenAI Codex CLI",
    dir: path.join(os.homedir(), ".codex", "skills"),
    status: "experimental",
  },
  cursor: {
    label: "Cursor",
    dir: path.join(os.homedir(), ".cursor", "skills"),
    status: "experimental",
  },
  antigravity: {
    label: "Google Antigravity",
    dir: null,
    status: "manual",
    note:
      "Antigravity uses a skills registry rather than a fixed folder: open its " +
      "settings and add this package's skills/ path (printed below) to the registry.",
  },
};

function parseArgs(argv) {
  const args = { agents: [], skills: [], dirs: [], list: false, force: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--agent") args.agents.push(argv[++i]);
    else if (a === "--dir") args.dirs.push(argv[++i]);
    else if (a === "--skill") args.skills.push(argv[++i]);
    else if (a === "--list") args.list = true;
    else if (a === "--force") args.force = true;
    else if (a === "--help" || a === "-h") {
      console.log(
        "Usage: npx fine-tune-slm [--agent claude|codex|cursor|antigravity]... " +
          "[--dir <skills-dir>]... [--skill <name>]... [--list] [--force]"
      );
      process.exit(0);
    } else if (a !== "install") {
      console.error(`Unknown option: ${a} (try --help)`);
      process.exit(2);
    }
  }
  return args;
}

function copySkill(skill, destRoot, force) {
  const src = path.join(PKG_ROOT, "skills", skill);
  const dest = path.join(destRoot, skill);
  if (!fs.existsSync(src)) throw new Error(`missing in package: ${src}`);
  const existed = fs.existsSync(dest);
  if (existed && !force) {
    return { dest, action: "already installed - kept as is (use --force to update)" };
  }
  fs.mkdirSync(destRoot, { recursive: true });
  fs.cpSync(src, dest, {
    recursive: true,
    force: true,
    filter: (p) =>
      !p.includes("__pycache__") && !p.endsWith(".DS_Store") && !p.endsWith(".pyc"),
  });
  return { dest, action: existed ? "updated" : "installed" };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const skills = args.skills.length ? args.skills : SKILLS;
  for (const s of skills) {
    if (!SKILLS.includes(s)) {
      console.error(`Unknown skill "${s}". Available: ${SKILLS.join(", ")}`);
      process.exit(2);
    }
  }

  if (process.platform !== "darwin") {
    console.warn(
      "Note: the fine-tune-slm skill trains via Apple's MLX and only runs on " +
        "Apple Silicon Macs. Installing the skill files anyway.\n"
    );
  }

  // Build the target list: explicit --dir wins; else --agent; else auto-detect.
  const targets = [];
  const manualNotes = [];
  if (args.dirs.length) {
    for (const d of args.dirs) targets.push({ label: `custom (${d})`, dir: path.resolve(d) });
  } else {
    const wanted = args.agents.length ? args.agents : Object.keys(AGENTS);
    for (const key of wanted) {
      const agent = AGENTS[key];
      if (!agent) {
        console.error(`Unknown agent "${key}". Available: ${Object.keys(AGENTS).join(", ")}`);
        process.exit(2);
      }
      if (agent.status === "manual") {
        // only surface manual agents when explicitly asked for
        if (args.agents.length) manualNotes.push(agent);
        continue;
      }
      const parentExists = fs.existsSync(path.dirname(agent.dir));
      const explicitlyAsked = args.agents.length > 0;
      if (parentExists || explicitlyAsked) {
        targets.push({ label: `${agent.label} [${agent.status}]`, dir: agent.dir });
      }
    }
  }

  if (!targets.length && !manualNotes.length) {
    console.error(
      "No supported agents detected. Use --agent <name> to force one, or " +
        "--dir <path> to point at any skills directory."
    );
    process.exit(1);
  }

  for (const t of targets) {
    console.log(`${args.list ? "Would install" : "Installing"} to ${t.label}: ${t.dir}`);
    for (const skill of skills) {
      if (args.list) {
        console.log(`  - ${skill} -> ${path.join(t.dir, skill)}`);
        continue;
      }
      const r = copySkill(skill, t.dir, args.force);
      console.log(`  - ${skill}: ${r.action} at ${r.dest}`);
    }
    if (t.label.includes("experimental")) {
      console.log(
        "    (this agent's skills location is documented but not yet validated by " +
          "this project - please report success/failure in a GitHub issue)"
      );
    }
  }

  for (const agent of manualNotes) {
    console.log(`\n${agent.label}: ${agent.note}`);
    console.log(`  skills path to register: ${path.join(PKG_ROOT, "skills")}`);
  }

  if (!args.list && targets.length) {
    console.log(
      '\nDone. Start your agent and say something like: "fine-tune a small model ' +
        'that sorts my support emails" - the skill handles the rest.'
    );
  }
}

main();
