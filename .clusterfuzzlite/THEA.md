# `.clusterfuzzlite/` — what this place is

the fuzzing entry the CI fuzz job builds, whose value is the inputs nobody thought to write

## A change here proves

- `contract`

## Traps already met here

Each one was committed in this repository at least once. `thea failures` has the full ledger.

- **a_check_proven_on_one_shape_of_input** — a verified command, and a hook that suddenly rejects good code; a passing MCP probe, and a client that cannot connect
- **a_mutation_harness_scored_over_zero_runs** — a perfect score. At 2.27.0 a zsh `$S:scripts` (`:s` is a substitution modifier) failed before any test ran and scored 5 of 5 mutants KILLED; fixed, the suite's own sys.path insert shadowed every mutant and scored 6 of 6 SURVIVED over the real module

Declared in `atlas.yaml/directory_scopes/.clusterfuzzlite`; `thea route .clusterfuzzlite` prints it as a record.
