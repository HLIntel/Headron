# `fuzz/` — what this place is

property and fuzz targets, whose value is the input shapes nobody thought to write

## A change here proves

- `contract`

## Traps already met here

Each one was committed in this repository at least once. `thea failures` has the full ledger.

- **a_check_proven_on_one_shape_of_input** — a verified command, and a hook that suddenly rejects good code; a passing MCP probe, and a client that cannot connect
- **a_mutation_planted_where_the_checker_never_reads** — a mutation test of a code rule

Declared in `atlas.yaml/directory_scopes/fuzz`; `thea route fuzz` prints it as a record.
