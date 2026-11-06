# `examples/` — what this place is

runnable programs per route, each asserting something a reader can check by running it

## A change here proves

- `contract`
- `examples`

## Traps already met here (ledger: `headron failures`)

- **an_arm_that_shipped_and_could_never_run** — coverage. The capability is in the roster, in the package, and in the docs, and the first consumer to call it gets an empty result rather than an error
- **a_fixture_that_names_what_it_could_read** — a passing test that planted nothing
  - do: plant a defect whose text differs from the original and assert the refusal by its message, never by a literal that later moves

## Read here

- [README.md](README.md)

Declared in `atlas.yaml/directory_scopes/examples`; `headron route examples` prints it as a record.
