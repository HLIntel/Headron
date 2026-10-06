# Engineering concepts, each paired with a mechanism — part 2 of 7

[Index](../ENGINEERING-CONCEPTS.md)

## IX. File topology, navigation and defect-prevention placement

| concept | mechanism |
|---|---|
| **Screaming architecture** | The knowledge store is filed **by the SHAPE of the lesson** — `measurement/`, `silent-failure/`, `guard-design/` — never by subject. Filing by subject put 306 of 544 files in one bucket; the shape is what a future reader searches by. *(measured at v1.1.0)* |
| **Bounded context (max depth 3–4)** | Measured: knowledge store depth **3**, scripts **2**, hub **1**. The one place reaching **6** is a deliberately archived misnamed copy, correctly parked — depth is a smell, not a law, and an archive is allowed to be deep. |
| **Colocation** | **PARTIAL.** Each check carries its rationale, its blind spot and its failure history in its own docblock, so the reasoning travels with the code. But its mutation tests live in commit history, not beside it — a real gap. |
| **Barrel exports / index sanitization** | Generated folder indexes act as the public face of a directory; the generator refuses to rewrite one whose content has not changed, so the index never churns. |
| **AST indexing** | Semantic search over an indexed corpus is reached for **before** any text search. Text search is the fallback, not the default — regex over source is how you miss a symbol. |
| **Software archeology** | Churn is the map: `git log --name-only` over one day named the hot spots exactly — the guard roster (9 edits), the ACP probe (6), the dispatcher (5). **What changes most is what needs the best docblock.** |
| **Shift-left verification** | Checks moved from manual → wired into an existing 4-hourly job → cheap enough to run per-change. The next shift left is edit-time checking, and it is not done: the edit hook (`.agent/bootstrap.json` hooks.edit) only routes the agent to the gates that apply — it runs none. |
| **Sub-tool orchestration (meta-tools)** | One dispatcher fronting every agent, with a per-agent lock, a run ledger and an exit-code contract — so a caller composes one door instead of N. |
| **Custom key-namespace** | A cache keyed on `path + mtime + size`: the key IS the correctness argument, because any edit must change it. Verified by editing a cached file and confirming the re-scan. |
| **Idempotency-key store** | The same principle applied to a lock: a per-agent lock directory holding its owner's PID, with a dead holder announced as STALE rather than silently stolen. |
| **Typestate** | **WEAK here.** The nearest thing is an exit code that means "no answer, but tools ran", which callers branch on. Real typestate would make the invalid call unrepresentable rather than merely detectable. |
| **Signature authentication guard** | **NOT APPLICABLE** — nothing here ingests third-party webhooks. Recorded so its absence is a decision, not an oversight. |

---


## X. Calculation and throughput

| concept | mechanism |
|---|---|
| **Memoization / dynamic programming** | The prose check caches per file on `path + mtime + size`. It did not merely speed up the old job — it made the roster affordable to **triple**, from 814 files to 2,504, which immediately surfaced findings that had been invisible. **A cache's real payoff is often a bigger job, not a faster one.** *(measured at v1.1.0)* |
| **Closed-form expression** | Prefer one pass with an alternation over N passes per pattern: 44 patterns × 811 files was ~35,000 processes and blew a timeout; one alternation gave the same answer in seconds. *(measured at v1.1.0)* |
| **Algorithmic parsimony** | Choose the threshold the defect demands, not the strictest one available. A duplicate-line check at 9 characters flagged status logs; at 60 characters it flags duplicated prose and nothing else. |
| **Vectorization (SIMD)** | **NOT APPLICABLE** — no numeric hot loop here. Recorded so its absence is a decision. |
| **Zero-copy memory access** | Pass a path, not a payload. Checks read files in place rather than shipping contents between processes; the closest violation was piping an 11 MB string into `grep`, which broke on SIGPIPE. *(measured at v1.1.0)* |
| **Backpressure handling** | Per-agent locks that **fail closed** (exit 3) rather than queueing. One process backing off does nothing if its siblings do not, so the throttle is published where siblings read it. |
| **Event-driven / non-blocking** | **PARTIAL.** Agent probes are async over stdio and answer callbacks mid-stream. Everything else polls. |
| **Binary protocol serialization** | **NOT APPLICABLE** — JSON-RPC over stdio is the protocol, and its cost is not the bottleneck. |
| **Zero-overhead abstractions** | A wrapper must add environment and preflight, then `exec` — replacing itself, not wrapping a child. That is what makes process-group cleanup work at all. |

## XI. Instantaneous execution and agent-to-agent

| concept | mechanism |
|---|---|
| **AOT (ahead-of-time) pre-linking — kill cold starts** | Packages are **installed and pinned**, never `npx -y`-ed per launch. That removed a cache that grew 328 MB per invocation *and* made every agent start faster. Cold-start cost and cache growth were the same defect. *(measured at v1.1.0)* |
| **Zero-latency invocation** | Local first, always: a `$0` local router and a local model before any hosted call. The rung below must be proven unable before the next one is used. |
| **JIT (just-in-time) compilation** | **NOT APPLICABLE** — nothing here compiles at runtime. |
| **A2A interoperability** | ACP over JSON-RPC is the protocol; agents are addressed by a declared **agent id**, and a registry is validated against reality in both directions so an id cannot exist in only one place. |
| **In-memory event bus (pub/sub)** | **GAP.** State is passed through files and a run ledger — durable and inspectable, but polled. Nothing subscribes. |
| **Semantic linkage (code-graph)** | The **AST indexing** row in IX: semantic search first for any symbol question, text search as the fallback. |
| **Inlining** | Applied to prose, not code: a pointer beats a copy. The same explanation lived in three files and the next correction had to land in each. |
| **Symbolic references** | Paths are globbed or derived, never pinned: a registry-cached binary is found by `sort -V | tail -1`, and a lazily-loaded skill resolves its versioned directory at call time. A pinned version is a future break. |
| **Macros / metaprogramming** | Generators, not templates: indexes, rosters and project state are produced from the tree, so they cannot disagree with it. |

## XII. Verification methods not yet used

Recorded because naming a method you are **not** using is more honest than implying coverage.

| concept | status here |
|---|---|
| **Property-based testing** | **PARTIAL.** Every check is still mutation-tested against *hand-planted* defects, which were wrong three times in one session (a window smaller than the defect; a threshold below the planted value; a file outside the roster). Generators now cover part of the surface: a seeded property sweep over the router and the entry grammar (`scripts/atlas_test.py`), property tests over the policy core (`scripts/agent_properties_test.py`), and coverage-guided fuzzing (`fuzz/`, `FuzzPool`). The other checks have no generator. |
| **Symbolic execution** | **NOT USED.** Shell and small scripts; the cost would exceed the benefit. |
| **Time-travel debugging** | **PARTIALLY COVERED** by append-only ledgers — guard verdicts, agent runs, heal actions — which reconstruct what happened, though not variable state. |
| **Continuous AST linting** | **NOT REACHED.** Checks run on demand and on a schedule; the edit hook (`.agent/bootstrap.json` hooks.edit) only routes the agent to the gates that apply — it runs none. Edit-time checking is the next shift left and is not done. |
| **Correctness-by-construction** | **ASPIRATION.** The nearest real instance: a config is never edited in place — a candidate is applied through a gate that reads the app's own loader verdict and reverts. |
| **Static invariant verification** | **PARTIAL.** Invariants are asserted at runtime and printed (counts, roster sizes, blind spots) rather than proven statically. |
| **Linear / affine types** | **NOT AVAILABLE** in shell. The substitute is a lock with an owner PID plus an `EXIT` trap — resource discipline by convention, enforced by a check rather than a compiler. |

## XIII. Interface, output and governance

| concept | mechanism |
|---|---|
| **Schema enforcement (data contracts)** | Registries are TSV with a declared header and a validator that fails on a malformed row — including a date field that is not a date, because an un-expirable expiry is the whole failure mode. |
| **Single source of truth** | One declaration per fact, everything else generated or validated against it: agents, ports, epitaphs, budgets. The recurring defect all day was two copies of one fact. |
| **Declarative pipelines** | A registry declares the desired state; a check reconciles it against reality and reports the delta. |
| **Hot module replacement** | **NOT APPLICABLE** — but its spirit is honoured: apply, verify against the app's own verdict, revert on rejection, never require a manual restart to know. |
| **Dynamic dispatch** | One dispatcher resolves an agent id to a wrapper at call time. Adding an agent is a registry row, not a code change. |
| **Content-addressable routing** | The cache key is content-derived (`mtime + size`); an edit cannot hit a stale entry. |
| **Stateless monads** | **NOT APPLICABLE** in shell. The intent survives as: a check reads, computes, prints and exits — it never mutates what it inspects. `selfheal` is the one writer, and it refuses judgement faults. |
| **Progressive disclosure** | The load-bearing token discipline: a lazy body costs nothing until invoked, a description is paid every request. One router replaced fifteen always-on descriptions — ~595 tokens per request down to ~42. *(measured at v1.1.0)* |
| **Affordance-driven design** | One key prefix for the whole agent surface, numbered 1–9, because a keystroke the OS silently swallows is worse than none. |
| **Optimistic UI / micro-frontend** | **NOT APPLICABLE** — no UI is authored here. |
| **Syntactic sanitization** | Config candidates are parsed before they are applied, and a comment-tolerant parse is used where the format allows comments — a strict parser that rejects legal input is a check that gets switched off. |
| **Zero-dependency engineering** | The ladder starts at "needed at all?" and ends at "only then the minimum". A third-party dependency added a 207 MB cache this system cannot bound, because its config is overwritten by a sync. *(measured at v1.1.0)* |
| **Ingest-first queueing · idempotency key store · signature auth** | **NOT APPLICABLE** — see **Signature authentication guard** in IX. The lock registry is the nearest analogue of an idempotency key. |
| **Dependency graph visualization** | **GAP.** Coupling was found by reading a file, not a graph — one check invoked another and lit three at once. A graph would have shown it immediately. |
| **Alignment** | The operating contract is explicit and its rules carry measurements, so a claim can be checked against an instrument rather than a preference. Every verdict is labelled CONFIRMED, REPORTED, INFERRED or UNCERTAIN. |
| **Conway's Law** | One person, one machine — so the architecture mirrors a single operator: one hub, one dispatcher, one store, many entry points. |
| **Postel's Law** | Be liberal in what you accept, conservative in what you emit: parse comment-tolerant config, but publish exit codes as the contract and treat log prose as private. |

---
