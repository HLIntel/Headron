# `tools/` — what this place is

the machine contracts every runtime and consumer reads — the schemas and the reference task

## A change here proves

- `contract`
- `agent_controls`

## Never written by any task contract

- `tools/agent-task.schema.json`

## Traps already met here

Each one was committed in this repository at least once. `thea failures` has the full ledger.

- **a_validator_that_diverges_from_its_spec** — a correct schema refusing correct data. At 2.28.0 `^https://` refused every https URL because the validator used re.fullmatch — JSON Schema patterns are unanchored searches — and all eighteen existing patterns happened to be anchored at both ends. The reference cross-check that would have caught it covered manifests only, a window smaller than the defect
- **a_round_trip_that_drops_what_the_format_allowed** — a clean diff of the change you intended, with a suspicious number of DELETIONS beside it

## Read here

- [README.md](README.md)

Declared in `atlas.yaml/directory_scopes/tools`; `thea route tools` prints it as a record.
