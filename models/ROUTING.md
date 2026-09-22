# Dynamic Model and Host Routing

Use the smallest model, host, tool, context, and isolation combination that meets the task.

| Task | Host/tool | Isolation |
|---|---|---|
| mechanical edit | CLI + direct repo tools | current worktree |
| complex code | symbols + native toolchain | dedicated worktree if broad |
| debugging | VS Code debugger + runtime debugger | current or dedicated |
| research | web/connectors + isolated context | subagent/context |
| security | scanners + diff | isolated |
| benchmark | profiler/benchmark + VS Code | workload worktree |
| polyglot boundary | schemas + two toolchains + integration tests | dedicated worktree |
| autonomous bot | narrow tools | sandbox + budget |

VS Code wins when interactive inspection matters. OpenCode wins when terminal autonomy or a dedicated coding workspace matters. Both should call the same repository harness commands.

Parallel writers default to separate worktrees.
