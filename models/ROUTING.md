# Dynamic Model, Host, and Entry Routing

Use the smallest model, host, tool, context, and isolation combination that meets the task.

## Task and Host Routing

| Task              | Host / Tool                                  | Isolation                   |
| ----------------- | -------------------------------------------- | --------------------------- |
| mechanical edit   | CLI + direct repo tools                      | current worktree            |
| complex code      | symbols + native toolchain                   | dedicated worktree if broad |
| debugging         | debugger + runtime toolchain                 | current or dedicated        |
| research          | web/connectors + isolated context            | subagent / context          |
| security          | scanners + diff                              | isolated                    |
| benchmark         | profiler / benchmark                         | workload worktree           |
| polyglot boundary | schemas + two toolchains + integration tests | dedicated worktree          |
| autonomous bot    | narrow tools + sandbox                       | sandbox + budget            |

VS Code wins when interactive inspection matters. OpenCode and Antigravity win when terminal autonomy, deep routing, or a dedicated coding workspace matters. All runtimes call the same repository harness commands.

Parallel writers default to separate worktrees (`~/Agents/<agent>/worktrees/`).

## Entry Point Discovery and Routing

Never read the repository breadth-first. Enter via structured discovery:

1. **Instant Autonomous Search (`headron find <query>`)**:
   - Web-like sub-second search indexed over symbols, files, invariants, rules, and task profiles.
   - Supports single-letter queries (`m`), prefixes (`min`), acronyms (`cc` -> `context_cost`), wiki-link pointers (`[[mind]]`), and multi-term queries.
   - Scoped filtering via `--tier` (`frontend`, `middle`, `backend`, `database`), `--shard` (`core`, `mind`, `graph`, `retrieval`, `verification`, `languages`, `adapters`, `docs`), `--path`, and `--snippet`.
2. **Fast Semantic Sweep (`headron sweep [target]`)**:
   - Zero-token-waste repository topology sweep: stack tiers, architectural shards, hard invariants, knowledge pointers, and decision tunnels.
   - Compact line mode (`--line`) or structured record (`--json`).
3. **Targeted Entry (`headron port <path>`)**:
   - Resolves route pack, stack tier, verification gates, lessons from recorded mistakes, and next commands.

## Multi-Agent Harness and Zero-Bleed Isolation

The system is universal across runtimes (Antigravity, Claude Code, OpenAI Codex, Cursor, Hermes, OpenHands, Windsurf, VS Code, Headron Desktop):

- **Zero-Bleed Adapters**: Host adapters only define how an agent enters the repository. They never modify tool configurations or bleed host-specific state into shared repository rules.
- **Clean Harness / Unharness**: Runtimes keep their own native tools; Headron adds routing, verification, and failure ledgering without replacing native capabilities.
- **Sandbox vs. Non-Sandbox Boundaries**:
  - *Sandboxed execution*: Task contracts compile through `scripts/sandboxgen.py docker <contract>` into an isolated container with read-only repository root, disabled network, and write access restricted strictly to the agent's lane worktree.
  - *Non-sandboxed execution*: Direct execution bounded by non-interactive CLI commands, pre-commit enforcement hooks (`scripts/enforce.py install`), and read-only MCP queries.
- **Agent-to-Agent Maximization**:
  - Independent worktree lanes per task branch prevent git index collisions.
  - Machine-checkable artifacts (`tools/atlas-output.schema.json`, `tools/agent-task.schema.json`) cross boundaries without drift or summarization loss.
  - Landing is automated and verified via `branchstate.py --land`.

## Strategic Push, Pull, Merge, and Routing Principles

Learnings and operational laws for autonomous agent coordination:

1. **Routing Cognition (Dual-Mode):**
   - *System 1 (Reflex Fast-Path)*: Low/medium risk modifications with bounded blast radius execute verified commands directly (`system_mode="reflex"`).
   - *System 2 (Deliberate Planning)*: High/critical risk or cross-shard modifications engage multi-gate planning, strict isolation, and full verification (`system_mode="deliberate"`).
2. **Push and Pull Safety:**
   - *Never Bare-Push a Lane*: Direct `git push` creating an unreviewed branch is refused by `.githooks/pre-push` to eliminate stranded work.
   - *Fast-Forward Discipline*: All merges into `main` require linear fast-forwards. Non-fast-forward pushes and force-pushes are strictly rejected.
   - *Automated Landing*: Use `python scripts/branchstate.py --land` (which verifies, rebases, pushes, and arms auto-merge) or land via verified fast-forward merges.
3. **Continuous Receipt Audit:**
   - Every verification run generates a verifiable `headron.receipt v1` record verified by `receipt.verify_bytes()`.
   - Continuous receipt history is tracked across sessions via `headron mind --receipts` to prove deterministic compliance over time.
