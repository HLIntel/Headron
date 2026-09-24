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

## The ordering rule, stated once

**Prevention → healing → detection.**

1. **Can the cause be deleted?** Then do that. A check that never fires because the fault is impossible beats one that fires and gets repaired.
2. **If not, can it be healed?** Only if the thing regenerates — a cache, an index, generated output. **Never heal a decision.**
3. **Only then detect.** And a detector nobody runs is a record of what went wrong, not prevention.

**The tell that you are in the wrong tier:** count how often each check fails. If one fails repeatedly,
it is reporting on its own cause or on itself — not on the system.
