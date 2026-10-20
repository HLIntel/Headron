# `models/` — what this place is

one adapter per runtime — how each one loads this atlas and what it loads first

## A change here proves

- `contract`
- `context_cost`

## Never written by any task contract

- `models/chat/thea`

## Traps already met here

Each one was committed in this repository at least once. `thea failures` has the full ledger.

- **a_prerequisite_reported_as_the_capability** — an honest, verified fix that names correctly the one thing it actually checked
  - do: report a capability as working only after one real request went through it end to end; a roster entry, a health 200 or a registered bridge is reported as PREREQUISITE SATISFIED
- **a_success_rendering_read_as_an_answer** — a successful request with a token count beside it
  - do: judge an answer by the fields it must carry; a 200 or an exit 0 with an empty payload is unanswered, and a zero or false stays a value
- **a_count_typed_into_prose** — an accurate sentence, on the day it is written
  - do: generate every count, list and link from its declaration and never type one; stage, `thea check --fix`, stage again
- **a_shape_written_twice** — thorough coverage that disagrees once one copy is fixed
- **a_named_mechanism_that_does_not_exist** — a covered case, with a place named for it

## Read here

- [README.md](README.md)
- [ROUTING.md](ROUTING.md)
- [agents/README.md](agents/README.md)
- [chat/README.md](chat/README.md)
- [claude/README.md](claude/README.md)
- [cursor/README.md](cursor/README.md)
- [hermes/README.md](hermes/README.md)
- [llm/README.md](llm/README.md)
- [openai/README.md](openai/README.md)
- [opencode/README.md](opencode/README.md)
- [prompts/README.md](prompts/README.md)
- [thea-desktop/README.md](thea-desktop/README.md)
- [theaos/README.md](theaos/README.md)
- [vscode/README.md](vscode/README.md)

Declared in `atlas.yaml/directory_scopes/models`; `thea route models` prints it as a record.
