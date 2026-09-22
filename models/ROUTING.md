# Dynamic Model Routing

Routing chooses the smallest model/tool/context combination that meets the task's actual requirement.

## Classify
- mechanical
- implementation
- debugging
- architecture
- research
- security
- performance
- release
- autonomous operation

## Route
| Task | Model strategy | Tool strategy | Isolation |
|---|---|---|---|
| mechanical edit | fast | direct repo/language | current worktree |
| complex code | strong coding | symbols + focused files | dedicated worktree if broad |
| debugging | reasoning as needed | VS Code debugger + language/runtime tools | current or dedicated worktree |
| architecture | strongest reasoning | docs + ADR + repo map | read-heavy context |
| research | research-capable | web/connectors | subagent/context |
| security | reasoning + verifier | scanners + diff | isolated |
| benchmark | execution-aware | profiler/benchmark tools + VS Code UI | dedicated workload tree |
| autonomous bot | model with tool reliability | narrow allowlist | sandbox + budget |

## Cost/context routing
Use model quality for uncertainty and reasoning complexity. Use cheaper/faster models for deterministic transformations after the contract is fixed.

## VS Code routing
Use VS Code when interactive state is the advantage: breakpoints, call stacks, variables, test debugging, source navigation, diffs, task launchers, remote targets, or visual inspection.

Use OpenCode when agent autonomy, terminal-native workflows, provider flexibility, persistent execution, or a separate coding workspace is the advantage.

Use both when the work benefits from agentic execution plus interactive debugging/inspection. Keep write ownership explicit and prefer separate worktrees for concurrent tasks.

## Parallelism
VS Code Tasks can launch independent commands in parallel. That is command orchestration, not a replacement for application-level concurrency, scheduler semantics, worker pools, or parallel runtime design.

For multi-agent parallel development:
`Git worktree -> isolated task -> OpenCode/model execution -> VS Code inspect/debug -> verify -> merge`

## Fallback
Finite retry -> finite provider fallback -> controlled failure.

## Handoff
Pass structured facts, file paths, test results, risks, and next actions, not full exploratory transcripts.
