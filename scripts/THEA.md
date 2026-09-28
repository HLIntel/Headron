# `scripts/` — what this place is

the harness — every instrument, gate and generator this repository runs on itself

## A change here proves

- `contract`
- `planted_suite`
- `code_shape`
- `lint`

## Never written by any task contract

- `scripts/agentpolicy.py`
- `scripts/agentaudit.py`
- `scripts/agentrun.py`

## Traps already met here

Each one was committed in this repository at least once. `thea failures` has the full ledger.

- **a_guard_that_crashes_on_another_guards_input** — a broken harness, so the real finding is never reached
- **a_roster_that_resolved_to_nothing** — a clean pass, identical in every character to a real one
- **a_derived_roster_written_out_by_hand** — a plausible bar. It prints percentages that are individually right and a set that is incomplete, and nothing in the output says which languages it never looked for
- **a_mutation_planted_where_the_checker_never_reads** — a mutation test of a code rule
- **a_plant_left_by_a_killed_run** — a real defect in the repository, found by the repository's own checker

Declared in `atlas.yaml/directory_scopes/scripts`; `thea route scripts` prints it as a record.
