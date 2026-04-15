# Toolbelt

The CLI wrappers live in `skills/evolve/scripts/`.

## Commands

- `python skills/evolve/scripts/evolve-brief normalize`
- `python skills/evolve/scripts/evolve-eval inspect`
- `python skills/evolve/scripts/evolve-eval run`
- `python skills/evolve/scripts/evolve-cognition init`
- `python skills/evolve/scripts/evolve-cognition add`
- `python skills/evolve/scripts/evolve-cognition search`
- `python skills/evolve/scripts/evolve-db sample`
- `python skills/evolve/scripts/evolve-db record`
- `python skills/evolve/scripts/evolve-db best`
- `python skills/evolve/scripts/evolve-db stats`
- `python skills/evolve/scripts/evolve-files read`
- `python skills/evolve/scripts/evolve-files write`
- `python skills/evolve/scripts/evolve-files diff`
- `python skills/evolve/scripts/evolve-summary final`

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

## Cognition seed format

`cognition_seed.md` is a human-readable file that may contain fenced `json` blocks.

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
