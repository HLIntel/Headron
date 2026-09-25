# Context and Token Efficiency

Reduce repeated context and tool traffic without reducing correctness, evidence, uncertainty, or requested output detail.

Use three information layers: always-loaded invariants, task-specific reference, and deep implementation detail.

Prefer indexes, focused line ranges, symbols, diffs, compact structured handoffs, stable prefixes, deterministic tool lists, isolated subagents, and cached/static context where supported.

Use semantic code compression: table-driven logic, declarative configuration, generated repetitive code, shared validators, reusable bounded executors, common error models.

Do not optimize line count with opaque one-liners, hidden side effects, hidden retries, global mutable state, or reflection-heavy magic.

## What enforces this now

This page was advice until the cost was measured. `scripts/contextcost.py` reports what the
repository **hands over before a route is resolved** — the agent entry path and the human one,
each held to a declared BAND in `atlas.yaml/context_policy/entry_paths`.

A band rather than a point, because three of the four agent-entry files are generated and a point
target would fire on correct work — and the reaction to a noisy guard is never to fix it, it is to
silence it. A rise past the ceiling is refused; so is slack accumulating beneath it, because a
budget nobody is near absorbs the next addition instead of refusing it.

**The instrument was wrong in its SCOPE before it was right.** It summed three instruction
conventions no runtime loads together, overstating the cost by roughly the number of conventions
served — which would then have been "paid for" by deleting one. It now costs the worst single
alternative plus what every runtime reads regardless.

Measured against a real model: routing scored the same as handing over every pack's declarations
at **29.4% of the prompt tokens**, and more context scored *worse*. `scripts/abtest.py`.
