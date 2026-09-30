# Engineering concepts, each paired with a mechanism — part 3 of 7

[Index](../ENGINEERING-CONCEPTS.md)

## XIV. Failure classification, polyglot parity, and parallel work

| concept | mechanism |
|---|---|
| **Boundary type-guarding (reject at the edge)** | A config candidate is parsed before it is applied, and applied through one gate that reads the application's own loader verdict. Validity is decided once, at the boundary — never rechecked deep inside. |
| **Method-matching precision (405, not a generic catch-all)** | The equivalent for a command surface: an action bound to a key must exist **and** be buildable. A binding that names a real action but passes no required argument loads fine and never fires — that is the local `405`, and it was live for hours while a check reported "all actions exist". |
| **Idempotent state idling (409 prevention)** | Per-agent locks holding an owner PID: a second caller is **refused**, not queued, and a dead holder is announced as STALE rather than silently stolen. Optimistic concurrency, enforced by a directory. |
| **Circuit breaking (502/503/504 isolation)** | Distinguish the codes: a rate-limit says *slow down and retry*, a payment-required says *the budget is gone and every retry is waste*. **Latch on the second, never the first.** Applied to agents: a quota refusal is not retried; a deadline is. |
| **Contract-driven schema generation (anti-drift)** | One declaration per fact, everything else generated from or validated against it — agents, ports, epitaphs, budgets, rosters. Every recurring defect in one measured day was two copies of one fact. |
| **AST-driven cross-language parity** | The polyglot substrate is a routing atlas: one route per language pack, each with a guide, an operating card and a machine-readable tool manifest, resolved by routing a file rather than guessing an idiom. |
| **FFI boundary encapsulation** | **NOT APPLICABLE** — no native bindings here. Its spirit survives as: cross a boundary once, with the environment made explicit, then `exec` rather than wrap. |
| **Atomic design hierarchy** | Applied to knowledge rather than components: a fact, a file, a shape-bucket, a store, an index. Filing by SHAPE rather than subject is what keeps the hierarchy usable — by subject, 306 of 544 files landed in one bucket. *(measured at v1.1.0)* |
| **State-driven determinism (UI = f(state))** | Generated artifacts are a pure function of the tree: indexes, project state and rosters are derived, and the generator refuses to rewrite output whose content has not changed. |
| **CSS-in-JS zero-runtime extraction** | **NOT APPLICABLE** — no authored UI. The analogue that does apply: move work to generation time, so the read path stays cheap. |
| **Reactive push-pull backpressure** | A bounded declaration plus a consumer that refuses when saturated: locks fail closed, budgets are ratchets, and a dead lane is distinguished from a throttled one by a two-stage probe. |
| **Transactional outbox (dual-write consistency)** | The nearest real instance: salvage **before** removal. A worktree held the only copy of a line; it was extracted and committed in its own commit *before* anything was deleted. **Never let the destructive step and the preserving step share a failure mode.** |
| **Short-circuit middleware ordering** | Cheapest check first, always: a name match before a process probe, a cached verdict before a file read, a local `$0` model before a hosted call. The ladder is the middleware order. |
| **Git worktree isolation** | Real, and its failure modes are now guarded: a worktree NESTED inside its own repo (invisible to status, indexed as content), PHANTOM (registered path gone), FINISHED (`ahead=0`, clean), DORMANT (no commit in 21 days). One repo held three copies of itself — 43% of a store *(measured at v1.1.0)*. |
| **Modular monolith ("worktree arms")** | The rule that keeps it honest: **the repository's own path is the main worktree, never a lane.** Lanes merge to the default branch only, and `branch -d` refusing IS the guard — it only deletes a fully merged branch. |
| **Pluggable extension architecture (micro-kernel)** | A tiny core plus declared extensions: one dispatcher resolving an agent id to a wrapper at call time, so adding an agent is a registry row rather than a code change. Each wrapper owns its own environment and preflight. |

**The classification lesson underneath this tier:** an error code is only useful if the caller branches
differently on it. A retry that treats "out of budget" and "try again" identically will burn the budget
proving the difference.

---


## XV. Advanced laws — where they bind, and where they do not

Two of these describe things done here before they were named. Several do not apply at one machine and
one operator, and saying so is more useful than pretending coverage.

| law | how it binds here |
|---|---|
| **Semantic idempotency** (agentic side-effect law) | **THE sharpest one.** Byte-identical idempotency is meaningless for a stochastic agent: two different wordings must still produce ONE downstream state change. The dispatcher has a per-agent **lock**, which prevents *concurrency* — it does **not** prevent a second invocation repeating a side effect. That is a real, named gap: there is no idempotency key on a delegated task. |
| **Algorithmic information decay** (Chaitin-Kolmogorov drift) | Applied today without the name: every agent claim was re-verified against the **raw instrument** — the binary's symbol table, `lsof`, `ps`, `--porcelain` — never against another agent's summary. One agent proposed two settings already configured because it read docs; another proposed routing it already had. **Re-anchor each step to the root source, never to the previous agent's output.** |
| **Gall-Hoare invariant** | *A complex system that works was derived from a simple system that worked.* A fair criticism of building twenty checks in a day. What keeps it honest: each one is mutation-tested individually and composes only through one ledger, so the system is twenty simple things plus an index — not one designed-up-front whole. Worth re-reading whenever a twenty-first is proposed. |
| **Abstraction-defect correlation** (every abstraction leaks) | Honoured by escape hatches: a dispatcher that exposes the underlying wrapper path, a probe that can print the agent's private reasoning on request, a lazily-routed reference that names the exact file to read. **The leak found today: a retry keyed on another script's log prose — the abstraction hid that the interface was a sentence.** |
| **PACELC** | The real trade is Latency vs Consistency with no partition in sight. The memoised prose check chose latency: it trusts `path + mtime + size` rather than re-reading. The key IS the consistency argument, and it was tested by editing a cached file. |
| **Linearizable consistency boundary** | **PARTIAL.** A lock directory with an owner PID gives mutual exclusion, not linearizability. Honest scope: one machine, one operator, no distributed ordering requirement. |
| **Anti-entropy gossip convergence** | **NOT APPLICABLE.** One machine. The analogue that does apply: publish state where siblings *read* it — a run ledger, a lock directory, a guard ledger — rather than each process holding a private view. |
| **Continuous attestation** (zero-trust execution) | **NOT APPLICABLE** at this scale, but its weak form is enforced: verify capability, never identity. A health `200` is not identity; a package being "installed" is not a working binary; an action *existing* is not an action being *buildable*. |
| **Amdahl-Gustafson duality** | Measured the other way: fan-out cost ~15x tokens vs a chat, and token use explains ~80% of performance variance *(measured at v1.1.0)*. So added capacity should buy **deeper verification**, not more parallel opinions — five agents asked for opinions produced one good answer, one useless one, and one needing the prompt rewritten. |
| **Semantic type enclosure** (types as proofs) | **NOT AVAILABLE** in shell. The substitute is a validated registry: a row whose `review_by` is not a date is rejected, because an un-expirable expiry is the whole failure mode. Validation at the boundary, since the type system cannot carry the proof. |

**The one that should change behaviour tomorrow:** semantic idempotency. A delegated task has no
idempotency key, so a repeated delegation repeats its side effects. The lock makes that *unlikely*, not
*impossible* — and "unlikely" is the word that precedes every incident report.

---
