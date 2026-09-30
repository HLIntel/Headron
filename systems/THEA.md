# `systems/` — what this place is

system-design decisions and the backend architecture they resolve to

## A change here proves

- `contract`

## Traps already met here

Each one was committed in this repository at least once. `thea failures` has the full ledger.

- **a_claim_made_before_it_was_verified** — a finished task, to everyone but the person looking
- **a_second_declaration_of_one_value** — nothing, until the stale copy is the one being read
  - do: generate every count, list and link from its declaration and never type one; stage, `thea check --fix`, stage again

## Read here

- [AGENT-HARNESS.md](AGENT-HARNESS.md)
- [BACKEND-ARCHITECTURE.md](BACKEND-ARCHITECTURE.md)
- [DATA-RESEARCH-BOTS.md](DATA-RESEARCH-BOTS.md)
- [OPERATIONS-UPTIME.md](OPERATIONS-UPTIME.md)
- [POLYGLOT-ENGINEERING.md](POLYGLOT-ENGINEERING.md)
- [README.md](README.md)
- [STORAGE-STATE.md](STORAGE-STATE.md)

Declared in `atlas.yaml/directory_scopes/systems`; `thea route systems` prints it as a record.
