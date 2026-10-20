# Tool Orchestration

The cleanest agent workflow is a bounded composition of specialized tools, not a universal tool dump.

## Tool-inside-tool model

```text
model/runtime
   |
   v
Atlas router
   |
   +--> native compiler / LSP / debugger / tests
   +--> semantic repository context
   +--> GitHub repository/PR/issue state
   +--> current docs
   +--> browser/UI
   +--> database
   +--> security analysis
   |
   v
independent verifier
   |
   v
CI / release gate
```

A higher-level tool can orchestrate lower-level tools, but each lower layer keeps one authoritative responsibility.

## Composition rule

1. Route by artifact and task.
2. Load native language tooling first.
3. Add one semantic repository layer when symbol/context retrieval materially helps.
4. Add GitHub only when GitHub state or automation is needed.
5. Add docs only when current external API information is needed.
6. Add browser/database/security only for those capability classes.
7. Finish with deterministic verification.

## Capability graph

| Capability      | Authority                   | Extension                    |
| --------------- | --------------------------- | ---------------------------- |
| compile/type    | compiler/type checker       | LSP                          |
| symbols/context | LSP                         | Serena                       |
| repo/PR state   | Git/gh/GitHub               | GitHub MCP                   |
| current docs    | upstream docs               | Context7                     |
| browser         | browser runtime             | Playwright                   |
| database        | native client/query plan    | DBHub                        |
| source security | CodeQL/native scanner       | Semgrep                      |
| dependencies    | package manager + lockfile  | Dependabot/dependency review |
| secrets         | secret manager/environment  | GitHub secret scanning       |
| proof           | Lean kernel                 | AI assistant                 |
| runtime         | profiler/telemetry          | observability backend        |
| review          | diff + deterministic checks | AI review of the diff        |

## Profiles

`core-code` = native + GitHub + Serena where supported.

`docs` = upstream docs + Context7 when needed.

`browser` = native HTTP tests + Playwright.

`database` = native DB tooling + DBHub read-only exploration.

`security` = CodeQL/native + Semgrep + dependency/secret controls.

`polyglot` = native tools on both sides + schema/ABI + boundary tests.

## Claude, Codex, and IDE-agent delivery

Use roles, not a chain of agent brands. One task has one mutable writer, one declared
acceptance owner, and one independently run verdict. A capability may be supplied by a
different runtime without changing those responsibilities.

| Role                           | Owns                                                                                                                 | Must return                                                                                     | Must not do                                                                     |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Claude                         | architecture, task boundary, invariants, and acceptance criteria                                                     | a scoped task contract and the evidence that made each constraint necessary                     | edit the implementation lane while another writer owns it                       |
| Codex                          | the routed implementation, integration, focused tests, and landing evidence                                          | changed paths, exact commands with exit codes, the diff audit, and every unrun proof obligation | turn an architecture gap into an invented requirement                           |
| IDE agent (for example GoLand) | language-aware symbol navigation, local refactor preview, type/error inspection, and the smallest safe edit proposal | symbols inspected, files proposed, IDE diagnostics, and any edit handed to the lane owner       | own Git state, merge a branch, or treat an IDE inspection as a passing verifier |
| independent verifier           | rerun the declared checks against the received diff                                                                  | a pass, fail, or NOT RUN verdict with its command and output boundary                           | repair the same change it is judging                                            |

The IDE connection is task-scoped: load it only when its symbol or diagnostic context changes the
decision. Native compiler, test, and Git exit codes remain authoritative; an IDE's green rendering
is evidence to investigate, not proof to land.

### Handoff record

Before the writer starts, Claude or Codex emits the same bounded record that
`atlas.py plan --json` and the task schema already support:

```text
goal · acceptance criteria · base SHA · branch/worktree owner
allowed + forbidden paths · route + task profile · planned gates
rollback point · deadline/budget
```

The writer returns it completed, not replaced by a narrative:

```text
changed paths · commit SHA · commands and exit codes · results/NOT RUN
diff and dependency review · unresolved risk · handoff recipient
```

Do not pass a repository dump between agents. Pass the route, task contract, base SHA, and the
smallest relevant symbols. If the base SHA or allowed paths change, stop and re-plan; a stale
handoff is not a permission to reconcile unrelated work.

### Delivery loop

```text
Claude: define acceptance and boundaries
  -> Codex: route + plan + reserve one writer/worktree
  -> IDE agent: inspect only the named symbols when native IDE context helps
  -> Codex: implement, run the planned gates, and record the receipt
  -> independent verifier: rerun the receipt against the diff
  -> branchstate --land: create the merge path
  -> merge, remove the worktree, and sweep the roster
```

Parallelism earns its cost only for disjoint scopes: discovery and a read-only review may run beside
one writer, but two writers never share a worktree or a generated surface. A verifier that changes
the patch becomes the next writer and requires a fresh independent review.

## The “inside tools” rule

Use a tool as an orchestrator only when it reduces duplicated context or control.

Good:
`Atlas route -> language guide -> Serena semantic lookup -> exact symbol edit -> compiler/test`

Good:
`GitHub MCP -> issue/PR state -> focused file retrieval -> local/native verification`

Avoid:
`agent -> MCP -> agent -> MCP -> shell -> browser -> database` for a task that one native tool can solve.

## Tool budgets

Bound model/tool calls, repository reads, browser/database queries, retries, execution time, changed paths, and external side effects.

The best tool is the smallest one that crosses the required capability boundary.

## Verification ladder

**This page used to state its own order, and it was the fourth in the tree.** `atlas.yaml`
declares the tiers, [docs/VERIFY.md](../VERIFY.md) renders them in a generated block, and
`MODEL.md` names them — so a fourth ordering here could only disagree with three documents at
once. The tiers are `fast → standard → deep → release`, cheapest sufficient first, and what each
one adds is generated from the declaration rather than written here.

Ask the atlas for the answer to one change:

```bash
python scripts/atlas.py plan path/to/file.ext --task debugging --change source_change --json
```

## What enforces this now

- **What may activate unasked** is capped: `policy.default_tools` per pack, with a declared
  ceiling, because a manifest that defaults to everything is not a bounded tool surface.
- **A gate is a command, not a word**: `gate_tools` joins every declared gate to the manifest role
  that runs it, and `role: none` is a real answer that names its closer rather than resolving to
  the nearest command that would print a zero.
- **Six claims, not one**: `tool_claims` separates declared, available, version-compatible,
  executed, passed and authoritative. A manifest entry asserts only the first.
- **An enabled MCP server is paid for on every request**, not the one that uses it —
  `developer_baseline/mcp`, and `mcp_is_task_scoped` fails the build on a server no profile names.
