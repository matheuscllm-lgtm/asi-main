# Run Spec

The run spec is stored in `.evolve_runs/<run-name>/run_spec.yaml`.

## Required top-level fields

```yaml
objective: ""
evaluation:
  core_score: ""
  secondary_metrics: []
  command: ""
  script_path: ""
  success_criteria: []
budget:
  max_rounds: 0
  patience: 0
stop_conditions: []
mutation_scope:
  writable_paths: []
  primary_targets: []
sampling:
  algorithm: "ucb1"
  sample_n: 3
cognition:
  source_mode: ""
  seed_files: []
  seed_notes: []
approval:
  confirmed: false
```

## Notes

- `evaluation.command` can use placeholders such as `{code_path}` and `{results_path}`.
- `evaluation.script_path` is for explicit script inspection and documentation.
- `approval.confirmed` must stay `false` until the user explicitly confirms the preflight summary.
- `mutation_scope.writable_paths` are enforced by `evolve-files`.
