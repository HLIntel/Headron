# Model, host and entry routing

Pick the smallest model, host, context and isolation that meet the task.

## By task

| Task              | Tools                                        | Isolation                   |
| ----------------- | -------------------------------------------- | --------------------------- |
| mechanical edit   | CLI + repo tools                             | current worktree            |
| complex code      | symbols + native toolchain                   | own worktree if broad       |
| debugging         | debugger + runtime toolchain                 | current or own              |
| research          | web/connectors                               | subagent                    |
| security          | scanners + diff                              | isolated                    |
| benchmark         | profiler                                     | workload worktree           |
| polyglot boundary | schemas + two toolchains + integration tests | own worktree                |
| autonomous run    | narrow tools + sandbox                       | sandbox + budget            |

Parallel writers each take a worktree (`~/Agents/<agent>/worktrees/`).

## By where it runs

Every runtime calls the same harness commands; an adapter only says where it enters.

- **Chats** (no shell): [CHAT.md](../CHAT.md) or the [chat skill](chat/headron/SKILL.md).
- **Agents** (shell): Claude Code, Codex, Gemini CLI, Antigravity, Cursor, Hermes and the rest of the
  [runtime table](README.md#what-each-runtime-reads-before-it-starts). Each keeps its native tools.
- **Models** (a link): [llms.txt](../llms.txt) or [.agent/bootstrap.json](../.agent/bootstrap.json).

Sandboxed: `python scripts/sandboxgen.py docker <contract>` prints the container a task contract
needs. Otherwise: the commit hook (`headron enforce install`) and read-only MCP.

## Entry

Never read the tree breadth-first.

1. `headron find <query>`: paths, symbols, rules; `--tier`, `--shard`, `--path`, `--snippet`.
2. `headron sweep [target]`: tiers, shards, invariants, pointers; `--line` or `--json`.
3. `headron port <path>`: pack, tier, gates, lessons, next commands.

## Landing

- Land with `python scripts/branchstate.py --land`; `.githooks/pre-push` refuses a bare push of a lane.
- Never force-push.
- Records that cross agents: `tools/atlas-output.schema.json`, `tools/agent-task.schema.json`.
- Verdicts carry receipts: `headron verify --receipt <file>`; history `headron mind --receipts`.
