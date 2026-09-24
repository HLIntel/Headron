# Engineering concepts, each paired with a mechanism

**A concept with no mechanism beside it is vocabulary.** Every entry below names the concept, then the
thing that actually implements it — or states plainly that nothing does yet. That second column is the
point; the definitions are available everywhere.

Ordered by leverage: **prevention first, detection last.**

---

## I. Structural prevention — the fault cannot be expressed

The highest-leverage tier. A fault that cannot be represented needs no guard, no healer and no retry.

| concept | mechanism that implements it |
|---|---|
| **Make illegal states unrepresentable** | A port registry whose `match` field names the *binary*, not one of its roles. Declaring `opencode` instead of `opencode-chat` ended a recurring "collision" that was a program using its own port — the fault became inexpressible instead of detectable. |
| **Poka-Yoke (mistake-proofing)** | A safe route that is *structurally incapable*, never flagged safe: it loads no key and takes no nonce, so there is nothing to set wrongly. |
| **Parse, don't validate** | Config candidates are parsed and applied through one gate that restarts the app and reads the app's **own** loader verdict, then reverts. Validity is decided at the boundary, once. |
| **Design by Contract** | An exit code is the contract between two scripts. Replacing `grep -q '<a log sentence>'` with `exit 3` removed an implicit interface that a reworded log line would have silently broken. |
| **Total functions** | A resolver that always answers: the authoritative path, or an explicit refusal. Never silence. **Absent is not zero.** |
| **Pure zero-defects (eliminate recovery paths)** | Removing `npx -y` from a wrapper deleted the cache that grew 328 MB per invocation. No rotation policy can beat deleting the writer. |

## II. Determinism and reproducibility

| concept | mechanism |
|---|---|
| **Idempotency** | Generators write only when content actually changed, comparing with the timestamp line masked. Idempotent in *effect* is not enough — judge a generator on its **diff**. |
| **Deterministic serialization** | The same masked comparison: byte-identical output for identical input, so version control stays quiet and caching is trivial. |
| **Hermeticity** | Every wrapper sets `PATH` explicitly and preflights its binary, because GUI-launched processes inherit a stub environment — no profile, no keys. One agent was invisible for a month for exactly this. |
| **Provenance** | **GAP.** Knowledge files do not record which agent wrote them. Named as a failure mode in the literature ("provenance collapse") and not yet closed here. |

## III. Decoupling

| concept | mechanism |
|---|---|
| **Orthogonality** | No detector may invoke another detector. One leaked process once lit three of them and read as three problems. **A cascade is one fault, not N.** An aggregate is permitted only if it declares itself one. |
| **Law of Demeter** | Same rule, stated as coupling: a checker that reaches through another checker cannot fail independently. |
| **Composability** | One dispatcher, one door: `<tool> <agent> "<task>" <cwd>`. Every agent is reachable the same way, so pipelines compose without special cases. |
| **Abstraction / polymorphism** | One route parameter instead of two implementations. Two code paths for "safe" and "real" drift until a fudge factor is needed to reconcile them — that number is the cost of having two. |

## IV. Observability — and its limits

| concept | mechanism |
|---|---|
| **Observability** | Every check prints the **count it resolved** and its **own blind spot**, every run. A silent clean pass and a silent empty pass must never look identical. |
| **Grounding** | Verify against the shipped instrument — the binary's own symbol table, `lsof`, `ps`, `--porcelain` — never against documentation. Every wrong verdict in one measured day came from docs or memory; every verdict that held came from an instrument. |
| **Cybernetics (self-regulating loops)** | Budgets are **ratchets**: they only move down, and raising one must name what was added and why. A threshold that drifts upward silently is not a bound. |
| **Shadow validation** | A new check must (1) fail on a planted defect and (2) sweep the entire existing tree clean before it is trusted. Sensitivity proves nothing about specificity. |
| **Contextual drift** | Always-loaded instructions are metered and budgeted separately from lazily-loaded bodies. A description is paid on every request; a body is not. **An unused cluster is a subscription.** |

## V. Minimalism

| concept | mechanism |
|---|---|
| **Parsimony (Occam's razor)** | The ladder, in order: needed at all? → already present? → standard library? → platform? → installed dependency? → one line? → only then the minimum new thing. |
| **Tree-shaking / dead-code elimination** | A symbol is private until a second module imports it. Exporting "in case" produced 30 unimported exports in one audit; one of them was a refuted implementation still callable — not dead code, a **trap**. |
| **Idling eviction** | Load reference material on demand through a routing table rather than preloading it. One router replaced fifteen always-on descriptions: the cost went from ~595 tokens per request to ~42. |
| **Payload minimalization** | Read version control terse: `--porcelain`, `--oneline`, `--stat` then a named path. Measured on one repository, same information: **94,247 B → 6,116 B**. |

## VI. Detection — the last resort

| concept | mechanism |
|---|---|
| **Heuristic hardening** | A check that fires on correct input gets switched off, and a switched-off check catches nothing. Prefer a **false pass** to a false alarm, and declare which way it is biased. |
| **Verifiability** | Judge on the **exit code**, never a line of output. One harness printed "54/54 pass" over seven real failures. |
| **Hyrum's Law** | Assume every observable behaviour will be depended on. Publish exit codes as interfaces; treat log prose as private. |
| **Wirth's Law** | A check too slow to run does not run. One sweep of 44 patterns over 811 files exceeded its timeout; a single alternation pass gave the same answer in 11 s. |

---


## VII. Decay — the system rots while the code stands still

Nothing in this tier is about writing code badly. It is about correct code becoming wrong because the
world around it moved.

| concept | mechanism |
|---|---|
| **Bit rot / software entropy** | Measured instance: a package manager's script policy permitted exactly one package, so four *unchanged* CLIs silently became stub binaries — correct code, changed environment, a misleading error. The check verifies the file the launcher points at is a program, not that the package is "installed". |
| **Epitaph-driven design (self-expiring code)** | An explicit registry of everything paused, disabled or deferred, each row carrying a `review_by` date and the exact command that settles it. A check **fails** once a date passes. Two ways to settle: re-test and bump, or delete the thing and remove the row. "Leave it and look away" is not one of them. Before this existed, six things were paused in one day and **none** had an expiry. |
| **Zimmerman's Law of tech-debt decay** | The same registry carries the security rows — exposed credentials awaiting rotation — with the nearest dates, because a stale dependency that survives long enough becomes an attack surface through transitive sub-dependencies. |
| **Architectural drift** | A machine-readable registry of what exists, validated against reality **in both directions**: every declared thing must be present, *and* every present thing must be declared. The reverse direction is the one that catches something added through a UI and recorded nowhere. |
| **Code sclerosis** | The tell is measurable: count how often each check fails. One that fails repeatedly is reporting on its own cause or on itself. Chase the repeat count before adding another check. |
| **Deprecation friction** | Keep the old route runnable behind a declared switch, or every prior measurement loses its baseline. A paused thing is *wired and out of quota*, never deleted — and it carries a review date so "paused" cannot quietly mean "gone". |
| **Strangler fig** | Replace an implementation and **delete the old one in the same commit**. A superseded implementation left exported is not dead code, it is a trap: the next reader takes the obvious name. |
| **Continuous garbage collection of code** | Checks for dead imports, unreachable modules and unimported exports, with the bar set at *declaration-only* — the looser "not imported" rule flagged 30 symbols and was wrong about 26, which would have forced an exemption list, and an exemption list is a silenced check. |
| **Lehman's Law of continuing change** | Complexity grows unless work is done to reduce it. The counter-pressure here is a **ratchet**: the always-loaded instruction budget only moves down, and raising it must name what was added and why it must be read every session. |
| **Hyrum's Law in reverse (erosion of guarantees)** | Upgrades break consumers who depended on old *behaviour*, not the contract. Hence: publish exit codes as the interface and treat log prose as private — a lesson learned by depending on my own log sentence within hours of writing it. |

---


## VIII. Agent protocol, telemetry and durable state

| concept | mechanism |
|---|---|
| **Dynamic capability discovery** | Ask the agent what it can do instead of assuming. Each agent was made to enumerate its own callable tools, and they differed enormously — one carried ~25 web-research tools, another carried persistent memory and delegation. **Routing by measured capability beats routing by reputation.** |
| **JSON-RPC 2.0 framing over stdio** | The probe speaks the protocol directly: `initialize` → `session/new(cwd)` → `session/prompt`, and answers the agent's own callbacks. An agent waiting on its client is indistinguishable from a broken one unless you answer it. |
| **Sampling (nested invocations)** | An orchestrator that can delegate: one door, `<tool> <agent> "<task>" <cwd>`, with a per-agent lock so two callers never double-spend one credential. |
| **Agentic telemetry** | Every run appends to a ledger — agent, exit code, duration, working directory — so a sibling process can see what was spent without reading logs. A verdict store, not a log file. |
| **Headless process introspection** | Check the process table, not console output. The invariant: **an agent process may exist only while a lock is held for it.** Three were found alive 6–17 minutes past their runs, and one held a port declared to another service. |
| **Durable state machine execution** | State is written to a file at every transition, and a resolver answers *which* file is authoritative for a given directory — never assumed. It refuses rather than printing nothing when the declared file is absent. |
| **Reconciliation loop (desired state)** | A registry declares what should exist; a check compares it to reality **in both directions**. The reverse direction is the one that catches something added through a UI and recorded nowhere. |
| **Contextual checkpointing** | Session state is compressed into a capped, overwritten file — not an append-only history. A 13,000-character "current state" file is a blob in the one place read first. |
| **Resource URI subscriptions** | **GAP.** Everything here polls. Nothing subscribes, so a context change reaches an agent only when something asks. |

**The protocol lesson that cost the most:** an exit code is an interface, log prose is not. A retry that
keyed on another script's log sentence would have broken silently the moment that sentence was reworded.

---


## IX. File topology, navigation and defect-prevention placement

| concept | mechanism |
|---|---|
| **Screaming architecture** | The knowledge store is filed **by the SHAPE of the lesson** — `measurement/`, `silent-failure/`, `guard-design/` — never by subject. Filing by subject put 306 of 544 files in one bucket; the shape is what a future reader searches by. |
| **Bounded context (max depth 3–4)** | Measured: knowledge store depth **3**, scripts **2**, hub **1**. The one place reaching **6** is a deliberately archived misnamed copy, correctly parked — depth is a smell, not a law, and an archive is allowed to be deep. |
| **Colocation** | **PARTIAL.** Each check carries its rationale, its blind spot and its failure history in its own docblock, so the reasoning travels with the code. But its mutation tests live in commit history, not beside it — a real gap. |
| **Barrel exports / index sanitization** | Generated folder indexes act as the public face of a directory; the generator refuses to rewrite one whose content has not changed, so the index never churns. |
| **AST indexing** | Semantic search over an indexed corpus is reached for **before** any text search. Text search is the fallback, not the default — regex over source is how you miss a symbol. |
| **Software archeology** | Churn is the map: `git log --name-only` over one day named the hot spots exactly — the guard roster (9 edits), the ACP probe (6), the dispatcher (5). **What changes most is what needs the best docblock.** |
| **Shift-left verification** | Checks moved from manual → wired into an existing 4-hourly job → cheap enough to run per-change. The next shift left is edit-time, and it is not done. |
| **Sub-tool orchestration (meta-tools)** | One dispatcher fronting every agent, with a per-agent lock, a run ledger and an exit-code contract — so a caller composes one door instead of N. |
| **Custom key-namespace** | A cache keyed on `path + mtime + size`: the key IS the correctness argument, because any edit must change it. Verified by editing a cached file and confirming the re-scan. |
| **Idempotency-key store** | The same principle applied to a lock: a per-agent lock directory holding its owner's PID, with a dead holder announced as STALE rather than silently stolen. |
| **Typestate** | **WEAK here.** The nearest thing is an exit code that means "no answer, but tools ran", which callers branch on. Real typestate would make the invalid call unrepresentable rather than merely detectable. |
| **Signature authentication guard** | **NOT APPLICABLE** — nothing here ingests third-party webhooks. Recorded so its absence is a decision, not an oversight. |

---


## X. Calculation and throughput

| concept | mechanism |
|---|---|
| **Memoization / dynamic programming** | The prose check caches per file on `path + mtime + size`. It did not merely speed up the old job — it made the roster affordable to **triple**, from 814 files to 2,504, which immediately surfaced findings that had been invisible. **A cache's real payoff is often a bigger job, not a faster one.** |
| **Closed-form expression** | Prefer one pass with an alternation over N passes per pattern: 44 patterns × 811 files was ~35,000 processes and blew a timeout; one alternation gave the same answer in seconds. |
| **Algorithmic parsimony** | Choose the threshold the defect demands, not the strictest one available. A duplicate-line check at 9 characters flagged status logs; at 60 characters it flags duplicated prose and nothing else. |
| **Vectorization (SIMD)** | **NOT APPLICABLE** — no numeric hot loop here. Recorded so its absence is a decision. |
| **Zero-copy memory access** | Pass a path, not a payload. Checks read files in place rather than shipping contents between processes; the closest violation was piping an 11 MB string into `grep`, which broke on SIGPIPE. |
| **Backpressure handling** | Per-agent locks that **fail closed** (exit 3) rather than queueing. One process backing off does nothing if its siblings do not, so the throttle is published where siblings read it. |
| **Event-driven / non-blocking** | **PARTIAL.** Agent probes are async over stdio and answer callbacks mid-stream. Everything else polls. |
| **Binary protocol serialization** | **NOT APPLICABLE** — JSON-RPC over stdio is the protocol, and its cost is not the bottleneck. |
| **Zero-overhead abstractions** | A wrapper must add environment and preflight, then `exec` — replacing itself, not wrapping a child. That is what makes process-group cleanup work at all. |

## XI. Instantaneous execution and agent-to-agent

| concept | mechanism |
|---|---|
| **AOT (ahead-of-time) pre-linking — kill cold starts** | Packages are **installed and pinned**, never `npx -y`-ed per launch. That removed a cache that grew 328 MB per invocation *and* made every agent start faster. Cold-start cost and cache growth were the same defect. |
| **Zero-latency invocation** | Local first, always: a `$0` local router and a local model before any hosted call. The rung below must be proven unable before the next one is used. |
| **JIT (just-in-time) compilation** | **NOT APPLICABLE** — nothing here compiles at runtime. |
| **A2A interoperability** | ACP over JSON-RPC is the protocol; agents are addressed by a declared **agent id**, and a registry is validated against reality in both directions so an id cannot exist in only one place. |
| **In-memory event bus (pub/sub)** | **GAP.** State is passed through files and a run ledger — durable and inspectable, but polled. Nothing subscribes. |
| **Semantic linkage (code-graph)** | Semantic search over an index is the first move for any symbol question; text search is the fallback. |
| **Inlining** | Applied to prose, not code: a pointer beats a copy. The same explanation lived in three files and the next correction had to land in each. |
| **Symbolic references** | Paths are globbed or derived, never pinned: a registry-cached binary is found by `sort -V | tail -1`, and a lazily-loaded skill resolves its versioned directory at call time. A pinned version is a future break. |
| **Macros / metaprogramming** | Generators, not templates: indexes, rosters and project state are produced from the tree, so they cannot disagree with it. |

## XII. Verification methods not yet used

Recorded because naming a method you are **not** using is more honest than implying coverage.

| concept | status here |
|---|---|
| **Property-based testing** | **GAP.** Every check is mutation-tested against *hand-planted* defects. A generator would explore inputs I did not think of — and my hand-written tests were wrong three times today (a window smaller than the defect; a threshold below the planted value; a file outside the roster). |
| **Symbolic execution** | **NOT USED.** Shell and small scripts; the cost would exceed the benefit. |
| **Time-travel debugging** | **PARTIALLY COVERED** by append-only ledgers — guard verdicts, agent runs, heal actions — which reconstruct what happened, though not variable state. |
| **Continuous AST linting** | **NOT REACHED.** Checks run on demand and on a schedule. Edit-time is the next shift left and is not done. |
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
| **Progressive disclosure** | The load-bearing token discipline: a lazy body costs nothing until invoked, a description is paid every request. One router replaced fifteen always-on descriptions — ~595 tokens per request down to ~42. |
| **Affordance-driven design** | One key prefix for the whole agent surface, numbered 1–9, because a keystroke the OS silently swallows is worse than none. |
| **Optimistic UI / micro-frontend** | **NOT APPLICABLE** — no UI is authored here. |
| **Syntactic sanitization** | Config candidates are parsed before they are applied, and a comment-tolerant parse is used where the format allows comments — a strict parser that rejects legal input is a check that gets switched off. |
| **Zero-dependency engineering** | The ladder starts at "needed at all?" and ends at "only then the minimum". A third-party dependency added a 207 MB cache this system cannot bound, because its config is overwritten by a sync. |
| **Ingest-first queueing · idempotency key store · signature auth** | **NOT APPLICABLE** — nothing here receives third-party webhooks. The lock registry is the nearest analogue of an idempotency key. |
| **Dependency graph visualization** | **GAP.** Coupling was found by reading a file, not a graph — one check invoked another and lit three at once. A graph would have shown it immediately. |
| **Alignment** | The operating contract is explicit and its rules carry measurements, so a claim can be checked against an instrument rather than a preference. Every verdict is labelled CONFIRMED, REPORTED, INFERRED or UNCERTAIN. |
| **Conway's Law** | One person, one machine — so the architecture mirrors a single operator: one hub, one dispatcher, one store, many entry points. |
| **Postel's Law** | Be liberal in what you accept, conservative in what you emit: parse comment-tolerant config, but publish exit codes as the contract and treat log prose as private. |

---


## XIV. Failure classification, polyglot parity, and parallel work

| concept | mechanism |
|---|---|
| **Boundary type-guarding (reject at the edge)** | A config candidate is parsed before it is applied, and applied through one gate that reads the application's own loader verdict. Validity is decided once, at the boundary — never rechecked deep inside. |
| **Method-matching precision (405, not a generic catch-all)** | The equivalent for a command surface: an action bound to a key must exist **and** be buildable. A binding that names a real action but passes no required argument loads fine and never fires — that is the local `405`, and it was live for hours while a check reported "all actions exist". |
| **Idempotent state idling (409 prevention)** | Per-agent locks holding an owner PID: a second caller is **refused**, not queued, and a dead holder is announced as STALE rather than silently stolen. Optimistic concurrency, enforced by a directory. |
| **Circuit breaking (502/503/504 isolation)** | Distinguish the codes: a rate-limit says *slow down and retry*, a payment-required says *the budget is gone and every retry is waste*. **Latch on the second, never the first.** Applied to agents: a quota refusal is not retried; a deadline is. |
| **Contract-driven schema generation (anti-drift)** | One declaration per fact, everything else generated from or validated against it — agents, ports, epitaphs, budgets, rosters. Every recurring defect in one measured day was two copies of one fact. |
| **AST-driven cross-language parity** | The polyglot substrate is a routing atlas: 29 language routes, each with a guide, an operating card and a machine-readable tool manifest, resolved by routing a file rather than guessing an idiom. |
| **FFI boundary encapsulation** | **NOT APPLICABLE** — no native bindings here. Its spirit survives as: cross a boundary once, with the environment made explicit, then `exec` rather than wrap. |
| **Atomic design hierarchy** | Applied to knowledge rather than components: a fact, a file, a shape-bucket, a store, an index. Filing by SHAPE rather than subject is what keeps the hierarchy usable — by subject, 306 of 544 files landed in one bucket. |
| **State-driven determinism (UI = f(state))** | Generated artifacts are a pure function of the tree: indexes, project state and rosters are derived, and the generator refuses to rewrite output whose content has not changed. |
| **CSS-in-JS zero-runtime extraction** | **NOT APPLICABLE** — no authored UI. The analogue that does apply: move work to generation time, so the read path stays cheap. |
| **Reactive push-pull backpressure** | A bounded declaration plus a consumer that refuses when saturated: locks fail closed, budgets are ratchets, and a dead lane is distinguished from a throttled one by a two-stage probe. |
| **Transactional outbox (dual-write consistency)** | The nearest real instance: salvage **before** removal. A worktree held the only copy of a line; it was extracted and committed in its own commit *before* anything was deleted. **Never let the destructive step and the preserving step share a failure mode.** |
| **Short-circuit middleware ordering** | Cheapest check first, always: a name match before a process probe, a cached verdict before a file read, a local `$0` model before a hosted call. The ladder is the middleware order. |
| **Git worktree isolation** | Real, and its failure modes are now guarded: a worktree NESTED inside its own repo (invisible to status, indexed as content), PHANTOM (registered path gone), FINISHED (`ahead=0`, clean), DORMANT (no commit in 21 days). One repo held three copies of itself — 43% of a store. |
| **Modular monolith ("worktree arms")** | The rule that keeps it honest: **the repository's own path is the main worktree, never a lane.** Lanes merge to the default branch only, and `branch -d` refusing IS the guard — it only deletes a fully merged branch. |
| **Pluggable extension architecture (micro-kernel)** | A tiny core plus declared extensions: one dispatcher resolving an agent id to a wrapper at call time, so adding an agent is a registry row rather than a code change. Each wrapper owns its own environment and preflight. |

**The classification lesson underneath this tier:** an error code is only useful if the caller branches
differently on it. A retry that treats "out of budget" and "try again" identically will burn the budget
proving the difference.

---

## The ordering rule, stated once

**Prevention → healing → detection.**

1. **Can the cause be deleted?** Then do that. A check that never fires because the fault is impossible beats one that fires and gets repaired.
2. **If not, can it be healed?** Only if the thing regenerates — a cache, an index, generated output. **Never heal a decision.**
3. **Only then detect.** And a detector nobody runs is a record of what went wrong, not prevention.

**The tell that you are in the wrong tier:** count how often each check fails. If one fails repeatedly,
it is reporting on its own cause or on itself — not on the system.
