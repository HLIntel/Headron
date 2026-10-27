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

1. **Instant Autonomous Search (`thea find <query>`)**:
   - Web-like sub-second search indexed over symbols, files, invariants, rules, and task profiles.
   - Supports single-letter queries (`m`), prefixes (`min`), acronyms (`cc` -> `context_cost`), wiki-link pointers (`[[mind]]`), and multi-term queries.
   - Scoped filtering via `--tier` (`frontend`, `middle`, `backend`, `database`), `--shard` (`core`, `mind`, `graph`, `retrieval`, `verification`, `languages`, `adapters`, `docs`), `--path`, and `--snippet`.
2. **Fast Semantic Sweep (`thea sweep [target]`)**:
   - Zero-token-waste repository topology sweep: stack tiers, architectural shards, hard invariants, knowledge pointers, and decision tunnels.
   - Compact line mode (`--line`) or structured record (`--json`).
3. **Targeted Entry (`thea port <path>`)**:
   - Resolves route pack, stack tier, verification gates, lessons from recorded mistakes, and next commands.

## Multi-Agent Harness and Zero-Bleed Isolation

The system is universal across runtimes (Antigravity, Claude Code, OpenAI Codex, Cursor, Hermes, OpenHands, Windsurf, VS Code, Thea Desktop):

- **Zero-Bleed Adapters**: Host adapters only define how an agent enters the repository. They never modify tool configurations or bleed host-specific state into shared repository rules.
- **Clean Harness / Unharness**: Runtimes keep their own native tools; Thea adds routing, verification, and failure ledgering without replacing native capabilities.
- **Sandbox vs. Non-Sandbox Boundaries**:
  - *Sandboxed execution*: Task contracts compile through `scripts/sandboxgen.py docker <contract>` into an isolated container with read-only repository root, disabled network, and write access restricted strictly to the agent's lane worktree.
  - *Non-sandboxed execution*: Direct execution bounded by non-interactive CLI commands, pre-commit enforcement hooks (`scripts/enforce.py install`), and read-only MCP queries.
- **Agent-to-Agent Maximization**:
  - Independent worktree lanes per task branch prevent git index collisions.
  - Machine-checkable artifacts (`tools/atlas-output.schema.json`, `tools/agent-task.schema.json`) cross boundaries without drift or summarization loss.
  - Landing is automated and verified via `branchstate.py --land`.
