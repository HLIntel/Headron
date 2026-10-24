# `.claude/` — what this place is

the Claude Code project settings that wire scripts/claude_hook.py in as the PreToolUse adapter

## A change here proves

- `contract`

## Traps already met here

Each one was committed in this repository at least once. `thea failures` has the full ledger.

- **a_guard_that_crashes_on_another_guards_input** — a broken harness, so the real finding is never reached
  - do: parse every input once, report malformed input as a finding and let every other guard continue; generate YAML values with `safeedit.py quote`, never quote by hand

Declared in `atlas.yaml/directory_scopes/.claude`; `thea route .claude` prints it as a record.
