# `.github/` — what this place is

the authoritative verification surface — every workflow, the required checks, the review and ownership rules

## A change here proves

- `contract`

## Never written by any task contract

- `.github/workflows`

## Traps already met here

Each one was committed in this repository at least once. `thea failures` has the full ledger.

- **a_verdict_printed_and_not_gated** — a thorough check. At 2.28.0 astshape printed rc=1 for a duplicate structure and the same one-liner committed and landed anyway; CI's required Contract job is what held the merge
  - do: run the gate unpiped, or under `set -o pipefail`, and branch on its own exit code; read long output from the log
- **a_pushed_lane_nothing_will_merge** — done, from the terminal
  - do: land with `branchstate.py --land` — pull, rebase, push, open and arm the merge together — and close or delete a branch only after `thea landed` exits 0
- **a_local_green_read_as_a_verdict** — a green ladder; the absent thing is absent HERE only

## Read here

- [copilot-instructions.md](copilot-instructions.md)
- [pull_request_template.md](pull_request_template.md)

Declared in `atlas.yaml/directory_scopes/.github`; `thea route .github` prints it as a record.
