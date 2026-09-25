# Cognitive Code Design

Design code so humans and models can reason locally.

Make state, ownership, failure, blocking, growth, side effects, invariants, and cancellation obvious.

Keep I/O, network, filesystem, subprocess, database writes, and model/tool calls at narrow boundaries.

Increase semantic density with precise names, types, schemas, tables, domain objects, and declarative configuration. Do not increase density by obscuring control flow.

Before changing a shared primitive, identify callers, systems, agents, APIs, deployment paths, blast radius, and rollback options.

Prefer one source of truth for contracts, endpoints, timeouts, and policy.

## What enforces this now

- **Shape, not text**: `scripts/astshape.py` erases names, literals and docstrings and refuses a
  repeated canonical AST. It caught two invariants written separately that compiled identically.
- **Caps that only fall**: `atlas.yaml/code_shape`, 278 → 202 across this repository's life, every
  step a function the gate refused and a split that earned it — never a raised number.
- **Which rules may bend**: `governance_tiers` separates what refuses outright from what may move
  if the move NAMES what earned it, because a rule that cannot move gets worked around instead.
- **What readers actually get wrong here**: `agent_failure_modes`, every entry committed in this
  tree, each recorded with what it looks like from outside — all of them look like success.
