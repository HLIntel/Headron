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
| architecture | strongest reasoning | docs + ADR + repo map | read-heavy context |
| research | research-capable | web/connectors | subagent/context |
| security | reasoning + verifier | scanners + diff | isolated |
| benchmark | execution-aware | profiler/benchmark tools | dedicated workload tree |
| autonomous bot | model with tool reliability | narrow allowlist | sandbox + budget |

## Cost/context routing
Use model quality for uncertainty and reasoning complexity. Use cheaper/faster models for deterministic transformations after the contract is fixed.

## Fallback
Finite retry -> finite provider fallback -> controlled failure.

## Handoff
Pass structured facts, file paths, test results, risks, and next actions, not full exploratory transcripts.