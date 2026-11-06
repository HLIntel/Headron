# `ci/` — what this place is

the job definitions .github/ci-local.sh replays on the maintainer's machine — the contract jobs, the polyglot packs, the fuzz campaign; no GitHub runner starts them

## A change here proves

- `contract`

## Never written by any task contract

- `ci`

## Traps already met here (ledger: `headron failures`)

- **a_verdict_printed_and_not_gated** — a thorough check. At 2.28.0 astshape printed rc=1 for a duplicate structure and the same one-liner committed and landed anyway; CI's required Contract job is what held the merge
  - do: run the gate unpiped, or under `set -o pipefail`, and branch on its own exit code; read long output from the log
- **a_local_green_read_as_a_verdict** — a green ladder; the absent thing is absent HERE only

Declared in `atlas.yaml/directory_scopes/ci`; `headron route ci` prints it as a record.
