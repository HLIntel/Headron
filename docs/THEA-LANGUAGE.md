# The `.thea` surface

A task contract, written the way a person writes one. It compiles to
[`tools/agent-task.schema.json`](../tools/agent-task.schema.json) and to nothing else: the same
record the five path/command/budget/approval/scope verdicts and the effects verdict already refuse
against. There is no second representation and no separate runtime — the fork between the two forms
is one function, `thealang.load_contract`, and everything downstream of it is unchanged.

```bash
thea plan <path> --task <profile> --change <class> --thea --objective "…"   # a starter program
thea compile <program>.thea                                                 # the contract it becomes
python scripts/agentrun.py <program>.thea                                   # run it under the controls
python scripts/sandboxgen.py docker <program>.thea                          # the host sandbox it needs
```

`--thea` derives the allowances from the gate commands the plan resolved, and the effects from those
allowances, so the program is consistent with its own plan before anyone edits it. It refuses without
`--objective`: that is the one sentence nothing in the tree can derive, and a placeholder would ship a
program that validates and says nothing.

## The whole vocabulary

<!-- BEGIN generated: thea-surface (python scripts/atlas.py index --write) -->
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
| a bare name | `prove { … }` | `required_gates` |
| a bare name | `accept { … }` | `acceptance.required_checks` |
| a bare name | `risk { … }` | `risk_modifiers` |
| a bare name | `approval { … }` | `approval_required` |

Refused rather than accepted: `schema`, `atlas_version` — these are DERIVED, from the schema's own `const` and from `VERSION`, and writing either one in a program is a second declaration of a value that already has one. An unknown key, a repeated key, an unclosed block and a bare word where a quoted string belongs are each refused with the line that holds them.
<!-- END generated: thea-surface -->

## The places a program can work in

Every task contract names `allowed_paths`, so every task already works in terms of PLACES — and
until `directory_scopes` no place declared anything. A program whose paths reach one of these
carries that place's proofs and its forbidden paths, or `agentpolicy.contract_errors` refuses it.
The trap column counts shapes already committed in that directory: the ledger is global, the traps
are local, and an agent editing one place should not have to read all of them.

<!-- BEGIN generated: thea-places (python scripts/atlas.py index --write) -->
| place | label | proves | traps |
|---|---|---|---|
| [`benchmarks/`](../benchmarks/THEA.md) | `area/atlas` | `contract` | 4 |
| [`config/`](../config/THEA.md) | `area/ci` | `contract` | 2 |
| [`docs/`](../docs/THEA.md) | `area/docs` | `contract`, `context_cost` | 3 |
| [`examples/`](../examples/THEA.md) | `area/polyglot` | `contract`, `examples` | 2 |
| [`fuzz/`](../fuzz/THEA.md) | `area/atlas` | `contract` | 2 |
| [`integrations/`](../integrations/THEA.md) | `area/mcp` | `contract` | 3 |
| [`languages/`](../languages/THEA.md) | `area/polyglot` | `contract`, `own_enforcement` | 3 |
| [`models/`](../models/THEA.md) | `area/model` | `contract`, `context_cost` | 2 |
| [`patterns/`](../patterns/THEA.md) | `area/docs` | `contract` | 2 |
| [`prompts/`](../prompts/THEA.md) | `area/model` | `contract` | 2 |
| [`research/`](../research/THEA.md) | `area/research` | `contract` | 3 |
| [`scripts/`](../scripts/THEA.md) | `area/atlas` | `contract`, `planted_suite`, `code_shape`, `lint` | 5 |
| [`skills/`](../skills/THEA.md) | `area/agent` | `contract`, `context_cost` | 2 |
| [`systems/`](../systems/THEA.md) | `area/atlas` | `contract` | 2 |
| [`tools/`](../tools/THEA.md) | `area/agent` | `contract`, `agent_controls` | 2 |
| [`wiki/`](../wiki/THEA.md) | `area/wiki` | `contract` | 2 |
<!-- END generated: thea-places -->

## The program the parity test runs on

[`tools/agent-task.example.thea`](../tools/agent-task.example.thea) must compile to
[`tools/agent-task.example.json`](../tools/agent-task.example.json) by contract hash. That is what
keeps this notation from drifting away from the contract it claims to be a surface for: the check is
not that the parser is self-consistent, it is that the parser agrees with the reference contract CI
already runs.

Every tracked program is also asserted to survive its own printer — `parse(render(x)) == x` — because
a key the reader accepts and the printer forgets reads afterwards as a contract that never named it.
