# Toolbelt

The CLI wrappers live in `skills/evolve/scripts/`.

## Typical sequence

1. Normalize the run brief.
2. Inspect the evaluator.
3. Draft or update `cognition_seed.md`.
4. Initialize cognition.
5. Re-run brief normalization with `--confirmed true` after explicit user approval.
6. Run per-round loops anchored on `sample`, with cognition lookup or web refresh added whenever the next improvement is not already clear.
7. Produce the final summary.

## Concurrency rule

Database commands are serialized per run.

- Wait for `evolve-db record` to finish before calling `evolve-db best`, `evolve-db sample`, or `evolve-db stats` on the same `run_dir`.
- Do not issue multiple `evolve-db` commands in parallel against the same run, even if they look read-only.
- If you need parallelism, parallelize non-database work such as analysis drafting or cognition review instead.

## Commands by stage

### Preflight

- `python skills/evolve/scripts/evolve-brief normalize`
- `python skills/evolve/scripts/evolve-eval inspect`

### Cognition

- `python skills/evolve/scripts/evolve-cognition init`
- `python skills/evolve/scripts/evolve-cognition add`
- `python skills/evolve/scripts/evolve-cognition search`

### Database and sampling

- `python skills/evolve/scripts/evolve-db sample`
- `python skills/evolve/scripts/evolve-db record`
- `python skills/evolve/scripts/evolve-db best`
- `python skills/evolve/scripts/evolve-db stats`

## Sampling algorithm guide

- `random`: use for high-exploration scouting. Best when the search space is poorly understood, the current family looks stale, or you want to sanity-check alternatives.
- `island`: use for broader and more diverse exploration over time. It is the closest option here to a MAP-Elites-style balance of coverage and progress across different families.
- `ucb1`: use when you already have a meaningful signal and want a balanced explore/exploit policy that can keep advancing a promising direction without collapsing too early.
- `greedy`: use for short-horizon exploitation only. It is appropriate when you explicitly want to focus on the current strongest parents and accept reduced diversity.

If unsure, start with `ucb1`. Switch to `island` when diversity matters more, and switch to `random` when you suspect the current search story is overfit or too narrow.

### File and evaluation helpers

- `python skills/evolve/scripts/evolve-files read`
- `python skills/evolve/scripts/evolve-files write`
- `python skills/evolve/scripts/evolve-files diff`
- `python skills/evolve/scripts/evolve-eval run`

### Wrap-up

- `python skills/evolve/scripts/evolve-summary final`

## Round protocol

Every round should follow this order:

1. `python skills/evolve/scripts/evolve-db sample`
2. Design from the sampled parent instead of relying on transient chat context alone.
3. If the next move is not already obvious, run `python skills/evolve/scripts/evolve-cognition search`.
4. If local cognition is insufficient or freshness matters, do targeted external research and write the distilled findings back with `python skills/evolve/scripts/evolve-cognition add`.
5. `python skills/evolve/scripts/evolve-eval run`
6. `python skills/evolve/scripts/evolve-db record`

The per-round database sample is mandatory. Cognition lookup is conditional, but durable memory must come from the database or cognition store rather than from raw conversation context.
Experimental takeaways from the round belong in the recorded node analysis, not in cognition.

## Evaluator placeholders

`evolve-eval run` formats these placeholders inside `evaluation.command`:

- `{workspace_root}`
- `{run_dir}`
- `{step_dir}`
- `{code_path}`
- `{results_path}`
- `{script_path}`
- `{quoted_workspace_root}`
- `{quoted_run_dir}`
- `{quoted_step_dir}`
- `{quoted_code_path}`
- `{quoted_results_path}`
- `{quoted_script_path}`

For robust shell execution, prefer the quoted placeholders in command templates.

## Candidate path note

- `evolve-eval run` materializes the candidate at `steps/<step-name>/code`.
- That path does not get a forced extension or language-specific filename pattern.
- Evaluators should load the candidate by explicit file path, not by assuming suffix-based discovery or import behavior.
- If an evaluator currently depends on a particular filename convention, add a compatibility layer before using it with the skill.

## Cognition seed format

`cognition_seed.md` is a human-readable file that may contain fenced `json` blocks.

Only put reusable external insights in this file.

- Good fits: paper takeaways, benchmark heuristics, geometric tricks, failure patterns found in approved web research, and distilled notes from approved external search.
- Keep out: problem statements, function signatures, evaluator commands, score definitions, writable paths, and lessons learned from your own local experiment rounds.

Example:

````markdown
```json
[
  {
    "content": "Use variable radii and preserve validity checks.",
    "source": "user",
    "metadata": {"kind": "heuristic"}
  }
]
```
````

`evolve-cognition init` loads all JSON blocks and turns them into cognition items.
Those items should help future design decisions, not restate the run spec.

## Recording expectations

When calling `evolve-db record`, provide:

- `--step-name` for the round identifier
- `--name` for the candidate label
- `--code-path` for the evaluated file
- `--motivation` for why this branch existed
- `--analysis` or `--analysis-file` for the lesson from the run
- `--results-file` or `--score` so the database can rank the candidate

Per-round analyses and experimental lessons should stay attached to the node record rather than being copied into cognition.
