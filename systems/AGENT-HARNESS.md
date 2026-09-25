# Agent Harness Engineering

A coding agent should operate inside a measurable harness, not as a free-form editor.

## Harness loop
~~~text
classify -> scope -> retrieve -> plan -> edit
-> fast verify -> full verify -> diff audit -> accept -> record
~~~

Deterministic constraints belong in the harness; uncertain reasoning belongs to the model.

## Task contract — shipped, not sketched

This page once showed the contract as a YAML sketch. It is now a schema with an enforcer, and the
difference is the point of the whole page: **a sketch is followed by whoever agrees with it.**

- the shape: [tools/agent-task.schema.json](../tools/agent-task.schema.json), validated by the
  same validator the tool manifests use — two validators agree only until one learns a keyword
- a worked one: [tools/agent-task.example.json](../tools/agent-task.example.json), which CI runs
  on every pull request, so the enforcement path cannot rot unnoticed
- the controls and their enforcers: `atlas.yaml/agent_policy`

Five controls, each naming the FUNCTION that decides it. `atlas.py check` refuses a control whose
enforcer does not resolve, exactly as it refuses an invariant with no owner:

| control | refuses |
|---|---|
| `narrow_tools` | a command outside the allowance, or matching a declared denial whatever the contract allows |
| `sandbox` | a read or write outside the declared paths, or escaping by traversal or symlink |
| `budget` | the call that would cross a ceiling, checked BEFORE it runs — afterwards is a report |
| `approval` | an action whose token is absent, expired, or bound to a different contract, commit or diff |
| `audit` | nothing at write time; it records a hash chain, and a removed event is named by sequence |

A contract may declare **less** than the ceiling and never more, because a contract is written by
the same agent these controls bound. And no contract may allow a write to the policy, the audit
stream, or any generated file.

If a task exceeds its budget it stops and re-plans. That is enforced rather than asked:
`budget_verdict` refuses the call that would cross the line.

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

## Self-improvement — the outcome is the same record as the plan

`scripts/agentrun.py` writes the outcome INTO the contract that planned it, so a good-looking plan
and a different change cannot both be true. Every planned gate appears in the result **including
the ones that did not run**, because a missing gate and a passing gate are otherwise the same
absence. A dry run reports `controls_verified`; `verified` is reserved for a run that executed
them, and borrowing the word would be the exact claim this record exists to refuse.

The mistakes an agent actually makes here are recorded in `atlas.yaml/agent_failure_modes` — every
one committed in this tree, with what it LOOKS like from outside, how often it recurred, and what
refuses it now. Read the shapes rather than the fixes: the same shape arrives wearing a different
file each time.

Promote recurring failures into deterministic checks, skills, fixtures, or regression tests. Do not enlarge prompts when a schema, verifier, tool, or environment control can enforce the rule.

Evaluate harness changes on representative and held-out tasks. Measure success with context events, tool calls, retries, changed files, failure classes, runtime, and cost where available.

SWE-PolyBench and Multi-SWE-bench motivate language-diverse coding-agent evaluation rather than Python-only evaluation:
https://arxiv.org/abs/2504.08703
https://arxiv.org/abs/2504.02605

## Security

**The harness is not the security boundary, and that is declared rather than disclaimed.** It
refuses what it is ASKED about; an agent that never calls it is bounded only by the host. So
`atlas.yaml/agent_policy/sandbox_requirements` marks every row with who observes it, `agentrun.py`
prints the host-observed rows as UNOBSERVED rather than as satisfied, and
[config/agent-sandbox.json](../config/agent-sandbox.json) states what a host must provide —
no home directory, default-deny network, non-root, bounded cpu and memory, an isolated workspace.

A retrieved instruction is an injection surface: `knowledge_layers` declares that the retrieved
layer holds facts and never the rules for how to answer. See [SECURITY.md](../SECURITY.md).
