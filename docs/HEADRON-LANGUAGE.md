# The `.headron` surface

A task contract, written the way a person writes one. It compiles to
[`tools/agent-task.schema.json`](../tools/agent-task.schema.json) and to nothing else: the same
record the five path/command/budget/approval/scope verdicts and the effects verdict already refuse
against. There is no second representation and no separate runtime — the fork between the two forms
is one function, `headronlang.load_contract`, and everything downstream of it is unchanged.

```bash
headron plan <path> --task <profile> --change <class> --headron --objective "…"   # a starter program
headron compile <program>.headron                                                 # the contract it becomes
python scripts/agentrun.py <program>.headron                                   # run it under the controls
python scripts/sandboxgen.py docker <program>.headron                          # the host sandbox it needs
```

`--headron` derives the allowances from the gate commands the plan resolved, and the effects from those
allowances, so the program is consistent with its own plan before anyone edits it. It refuses without
`--objective`: that is the one sentence nothing in the tree can derive, and a placeholder would ship a
program that validates and says nothing.

## The whole vocabulary

<!-- BEGIN generated: headron-surface (python scripts/atlas.py index --write) -->
| write | in | becomes, in the contract |
|---|---|---|
| `task <id> { … }` | the whole program | `task_id` |
| `objective <value>` — quoted | the task body | `objective` |
| `target <value>` | the task body | `target` |
| `route <value>` | the task body | `route` |
| `profile <value>` | the task body | `task_profile` |
| `change <value>` | the task body | `change_class` |
| `status <value>` | the task body | `status` |
| `base <value>` | the task body | `base_commit` |
| `model <value>` | the task body | `model` |
| `agent <value>` | the task body | `agent_role` |
| `allow <path>` | `scope { … }` | `allowed_paths` |
| `forbid <path>` | `scope { … }` | `forbidden_paths` |
| `allow <path>` | `commands { … }` | `allowed_commands` |
| `network <value>` | `effects { … }` | `network` |
| `side_effects <value>` | `effects { … }` | `acceptance.side_effects` |
| a bare effect: `delegate`, `deploy`, `execute`, `external`, `money`, `network` | `effects { … }` | `effects` |
| `tool_calls <value>` | `budget { … }` | `budgets.tool_calls` |
| `wall_clock_seconds <value>` | `budget { … }` | `budgets.wall_clock_seconds` |
| `files_changed <value>` | `budget { … }` | `budgets.files_changed` |
| `lines_changed <value>` | `budget { … }` | `budgets.lines_changed` |
| `retries <value>` | `budget { … }` | `budgets.retries` |
| `output_bytes <value>` | `budget { … }` | `budgets.output_bytes` |
| `tool_calls <value>` | `delegate { … }` | `delegate_budget.tool_calls` |
| `wall_clock_seconds <value>` | `delegate { … }` | `delegate_budget.wall_clock_seconds` |
| `files_changed <value>` | `delegate { … }` | `delegate_budget.files_changed` |
| `lines_changed <value>` | `delegate { … }` | `delegate_budget.lines_changed` |
| `retries <value>` | `delegate { … }` | `delegate_budget.retries` |
| `output_bytes <value>` | `delegate { … }` | `delegate_budget.output_bytes` |
| a bare name | `uses { … }` | `uses` |
| a bare name | `skills { … }` | `skills` |
| a bare name | `prove { … }` | `required_gates` |
| a bare name | `accept { … }` | `acceptance.required_checks` |
| a bare name | `risk { … }` | `risk_modifiers` |
| a bare name | `approval { … }` | `approval_required` |
| a bare name | `watch { … }` | `watch` |

Refused rather than accepted: `schema`, `atlas_version` — these are DERIVED, from the schema's own `const` and from `VERSION`, and writing either one in a program is a second declaration of a value that already has one. An unknown key, a repeated key, an unclosed block and a bare word where a quoted string belongs are each refused with the line that holds them.
<!-- END generated: headron-surface -->

## The lessons a program carries

`watch { <shape> … }` names the `agent_failure_modes` entries this task checks its own steps against.
`headron plan --headron` fills it from `headron failures --for <target>`; `agentvocab.watch_errors` refuses a
shape the ledger does not hold; `agentrun.py` prints each shape's tell, and the move its paired
`agent_success_patterns` entry names, before the gates and records the list in the audit stream. What an agent reads is what it checks its next step against, so the lesson is
part of the task rather than a page read once.

## The places a program can work in

Every task contract names `allowed_paths`, so every task already works in terms of PLACES — and
until `directory_scopes` no place declared anything. A program whose paths reach one of these
carries that place's proofs and its forbidden paths, or `agentpolicy.contract_errors` refuses it.
The trap column counts shapes already committed in that directory: the ledger is global, the traps
are local, and an agent editing one place should not have to read all of them.

<!-- BEGIN generated: headron-places (python scripts/atlas.py index --write) -->
| place | label | proves | traps |
|---|---|---|---|
| [`.agent/`](../.agent/HEADRON.md) | `area/agent` | `contract`, `context_cost` | 2 |
| [`.claude/`](../.claude/HEADRON.md) | `area/agent` | `contract` | 1 |
| [`.claude-plugin/`](../.claude-plugin/HEADRON.md) | `area/model` | `contract`, `agent_controls` | 2 |
| [`.devcontainer/`](../.devcontainer/HEADRON.md) | `area/ci` | `contract` | 2 |
| [`.gemini/`](../.gemini/HEADRON.md) | `area/agent` | `contract` | 1 |
| [`.githooks/`](../.githooks/HEADRON.md) | `area/ci` | `contract` | 2 |
| [`.github/`](../.github/HEADRON.md) | `area/ci` | `contract` | 3 |
| [`.junie/`](../.junie/HEADRON.md) | `area/agent` | `contract` | 1 |
| [`.vscode/`](../.vscode/HEADRON.md) | `area/ide` | `contract` | 2 |
| [`benchmarks/`](../benchmarks/HEADRON.md) | `area/atlas` | `contract` | 4 |
| [`config/`](../config/HEADRON.md) | `area/ci` | `contract` | 2 |
| [`docs/`](../docs/HEADRON.md) | `area/docs` | `contract`, `context_cost` | 6 |
| [`examples/`](../examples/HEADRON.md) | `area/polyglot` | `contract`, `examples` | 2 |
| [`fuzz/`](../fuzz/HEADRON.md) | `area/atlas` | `contract` | 2 |
| [`integrations/`](../integrations/HEADRON.md) | `area/mcp` | `contract` | 3 |
| [`languages/`](../languages/HEADRON.md) | `area/polyglot` | `contract`, `own_enforcement` | 3 |
| [`models/`](../models/HEADRON.md) | `area/model` | `contract`, `context_cost` | 5 |
| [`scripts/`](../scripts/HEADRON.md) | `area/atlas` | `contract`, `planted_suite`, `code_shape`, `lint` | 5 |
| [`skills/`](../skills/HEADRON.md) | `area/agent` | `contract`, `context_cost` | 2 |
| [`tools/`](../tools/HEADRON.md) | `area/agent` | `contract`, `agent_controls` | 2 |
<!-- END generated: headron-places -->

## The program the parity test runs on

[`tools/agent-task.example.headron`](../tools/agent-task.example.headron) must compile to
[`tools/agent-task.example.json`](../tools/agent-task.example.json) by contract hash. That is what
keeps this notation from drifting away from the contract it claims to be a surface for: the check is
not that the parser is self-consistent, it is that the parser agrees with the reference contract CI
already runs.

Every tracked program is also asserted to survive its own printer — `parse(render(x)) == x` — because
a key the reader accepts and the printer forgets reads afterwards as a contract that never named it.
