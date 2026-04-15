# Preflight

Preflight is a hard gate.

## Required alignment topics

- objective
- core score
- secondary metrics
- evaluator command or evaluator script
- success criteria
- stop conditions
- round budget
- writable paths
- primary targets
- cognition source mode

## Confirmation rule

Preflight is not complete until:

1. `run_spec.yaml` has all required fields.
2. `preflight_summary.md` reflects the current plan.
3. `approval.confirmed` is explicitly set to `true`.

Before that point:
- `evolve-db sample`
- `evolve-db record`
- `evolve-db best`
- `evolve-db stats`
- `evolve-eval run`
- `evolve-files write`
- `evolve-summary final`

must refuse to proceed.

## Cognition sources

Two supported seed paths:

1. User-provided knowledge
- Rules of thumb
- Papers
- Existing heuristics
- Desired search directions

2. Approved agent research
- Use subagents only when the user explicitly allows it.
- Summarize the candidate seeds back to the user.
- Only initialize cognition after confirmation.
