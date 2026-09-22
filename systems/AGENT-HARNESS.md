# Agent Harness Engineering

A coding agent should operate inside a measurable harness, not as a free-form editor.

## Harness loop
~~~text
classify -> scope -> retrieve -> plan -> edit
-> fast verify -> full verify -> diff audit -> accept -> record
~~~

Deterministic constraints belong in the harness; uncertain reasoning belongs to the model.

## Task contract
~~~yaml
objective: "..."
allowed_paths: ["..."]
forbidden_paths: ["..."]
commands:
  - ["python", "scripts/atlas.py", "check"]
budgets:
  tool_calls: 40
  runtime_seconds: 900
  files_changed: 20
  retries: 3
acceptance:
  required_checks: ["contract", "tests", "diff"]
  side_effects: "none"
~~~

If a task exceeds its budget, stop and re-plan instead of silently expanding scope.

## Context engineering
Load:
1. control invariants
2. exact files/symbols plus callers/tests
3. deeper implementation only when evidence requires it

Use lexical search, symbol navigation, and dependency relationships before whole-repository context.

ContextBench evaluates coding-agent context retrieval using recall, precision, and efficiency; Agent Retrieval Bench evaluates whether agents find the repository files they need next and finds structural and semantic retrieval complementary. Sources: https://arxiv.org/abs/2602.05892 and https://arxiv.org/abs/2607.24882.

## Roles
scout -> relevant paths/evidence
planner -> plan/acceptance
coder -> isolated implementation
tester -> regression checks
security -> trust/permission/dependency review
benchmarker -> performance evidence
release -> diff/provenance

Only implementation/release roles normally mutate a worktree. Parallel writers use separate Git worktrees.

## Verification hierarchy
~~~text
syntax/typecheck
 -> focused test
 -> boundary/integration test
 -> property/fuzz
 -> security/dependency scan
 -> benchmark/regression
 -> full repository check
~~~

Use cheap failure localization before expensive verification.

## Anti-degradation
Compare tests, changed files, dependency delta, public API/schema delta, relevant performance baselines, resource bounds, security findings, and documentation/index impact.

## Self-improvement
Record structured outcomes:
~~~json
{"task":"...","agent":"...","status":"verified","changed_files":[],"tests":[],"failures":[],"tool_calls":0,"runtime_s":0,"notes":[]}
~~~

Promote recurring failures into deterministic checks, skills, fixtures, or regression tests. Do not enlarge prompts when a schema, verifier, tool, or environment control can enforce the rule.

Evaluate harness changes on representative and held-out tasks. Measure success with context events, tool calls, retries, changed files, failure classes, runtime, and cost where available.

SWE-PolyBench and Multi-SWE-bench motivate language-diverse coding-agent evaluation rather than Python-only evaluation:
https://arxiv.org/abs/2504.08703
https://arxiv.org/abs/2504.02605

## Security
The harness is not the security boundary. Use sandboxing, least-privilege credentials, CI policy, protected environments, and approval for high-impact actions.
