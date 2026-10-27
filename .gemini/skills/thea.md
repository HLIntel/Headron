# Thea — Engineering Atlas skill

Route first. Load only what the route names. Never read breadth-first.

## Entry

```bash
python scripts/atlas.py port <file|dir|.> --frame agent --json
```

Returns: route, tier, gates, lessons, next steps. Every other command follows from the port.

```bash
python scripts/atlas.py find <query> [--snippet] [--exact]  # instant autonomous search
python scripts/atlas.py sweep [target] [--line]             # fast semantic sweep of tiers & shards
python scripts/atlas.py gate <path> <gate>                  # cheapest single-gate answer
python scripts/atlas.py plan <path> --task <t> --change <class> --json
python scripts/atlas.py check                               # contract validity; exit code is verdict
python scripts/verify.py                                    # full done-set; exit code is verdict
python scripts/atlas.py doctor --json                       # environment health
python scripts/atlas.py failures                            # mistake ledger
python scripts/branchstate.py --land                        # land a branch (never bare-push)
```

Hooks: shell `thea shell --json "<cmd>"` · edit `thea port <file> --line` · done `thea verify`

## Rules that fail the build

1. No count typed into prose — generate it or name the instrument that prints it.
2. No calendar date — stamp with contract version.
3. No tool name in prose — tools live in `languages/<route>/tools.yaml`; documents name gates.
4. Refuse rather than invent — `none` is a real answer.
5. Every limit names its closer — all instruments carry `proves`, `does_not_prove`, `closed_by`.
6. Never raise a cap to fit your code — `code_shape` and `context_policy` ratchets only fall.
7. A change ends when the artifact parses — every tracked source and JSON file must parse.
8. A control with no enforcer is refused.

## Change classes

`source_change` · `api_change` · `dependency_change` · `security_sensitive` ·
`concurrency_change` · `performance_change` · `retrieval_change`

Pick the class, satisfy its gates, verify on the exit code — never on a line of output.

## Done-set gates

`contract` · `planted_suite` · `agent_controls` · `code_shape` · `examples` · `context_cost` ·
`markdown` · `cli_smoke` · `cidrift` · `index_check` · `invariants` · `lint` · `format` ·
`typecheck` · `own_enforcement` · `secret_scan` · `workflow_lint` · `workflow_audit`

## Where to put what

- Repeated fact: `atlas.yaml` plus a generated block.
- Language tool: its pack's `tools.yaml`.
- New rule: its own `*_errors()` and planted defect.
- Example: `examples/`, and it must run.

## Intents

Asked to *use / install / open / run / pull / report*? → `llms.txt`, then *When asked to*.
Directed into a role? → `thea role`. Picking up interrupted work? → `thea resume`.
`--json` records are frozen in `tools/atlas-output.schema.json`: depend on those ids.
