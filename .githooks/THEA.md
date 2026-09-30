# `.githooks/` — what this place is

the checks that run on this machine before a commit or a push leaves it

## A change here proves

- `contract`

## Traps already met here

Each one was committed in this repository at least once. `thea failures` has the full ledger.

- **a_verdict_printed_and_not_gated** — a thorough check. At 2.28.0 astshape printed rc=1 for a duplicate structure and the same one-liner committed and landed anyway; CI's required Contract job is what held the merge
  - do: run the gate unpiped, or under `set -o pipefail`, and branch on its own exit code; read long output from the log
- **a_guard_that_crashes_on_another_guards_input** — a broken harness, so the real finding is never reached
  - do: parse every input once, report malformed input as a finding and let every other guard continue; generate YAML values with `safeedit.py quote`, never quote by hand

Declared in `atlas.yaml/directory_scopes/.githooks`; `thea route .githooks` prints it as a record.
