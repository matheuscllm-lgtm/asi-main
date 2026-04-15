---
name: "evolve"
description: "Use when Codex should run an explicit preflight-and-iterate evolution workflow: align goals and scoring with the user, confirm the evaluation command/script, initialize cognition from user notes or approved subagent research, then drive round-by-round code evolution with the bundled Evolve CLI instead of the repository pipeline."
---

# Evolve Skill

Use this skill when the user wants Codex to run an `ASI-Evolve` style search loop where the agent decides the next step itself.

## Rule 1: Always start with preflight
- Do not start evolving immediately.
- First align with the user on:
  - objective
  - core score
  - secondary metrics
  - evaluation command or script
  - stop conditions and round budget
  - writable file scope
  - cognition source
- Only start evolving after the user explicitly confirms the preflight summary.

## Rule 2: Do not use the repository pipeline
- Do not run `python main.py`.
- Do not import or rely on `pipeline/` agents for orchestration.
- Use the bundled CLI wrappers and decide the loop yourself.

## Core workflow
1. Normalize the run brief with `scripts/evolve-brief normalize`.
2. Inspect the evaluator with `scripts/evolve-eval inspect`.
3. Draft or update `cognition_seed.md`, then initialize cognition with `scripts/evolve-cognition init`.
4. Re-run `scripts/evolve-brief normalize --confirmed true` only after the user explicitly approves the preflight summary.
5. During each evolve round:
   - sample context from the database
   - search cognition
   - choose patch vs rewrite
   - modify files only within allowed scope
   - run the evaluator
   - analyze results
   - record the node and update best snapshot
   - decide whether to continue or stop

## Subagent usage
- Only use subagents for cognition candidate gathering when the user explicitly allows it.
- Treat subagent output as candidate material.
- Summarize the candidate cognition back to the user before initializing the cognition store.

## Files to read when needed
- `references/preflight.md`: preflight gate and confirmation behavior.
- `references/run_spec.md`: run spec schema and required fields.
- `references/toolbelt.md`: CLI wrappers and placeholder variables.
- `references/architecture.md`: run directory layout and vendored runtime pieces.

## Practical defaults
- Prefer `ucb1` unless the user wants a diversity-heavy search.
- Treat `approval.confirmed=false` as a hard stop for evolve execution.
- Keep all run artifacts in `.evolve_runs/<run-name>/`.
- Use `cognition_seed.md` for human-readable seed drafting, with JSON code blocks for machine-readable items.
