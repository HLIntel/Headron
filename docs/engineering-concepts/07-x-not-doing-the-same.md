# Engineering concepts, each paired with a mechanism — part 7 of 7

[Index](../ENGINEERING-CONCEPTS.md)

## X. Not doing the same work twice — the anti-repetition machinery

The tier that decides how much a change costs the *next* person. Every row below names a mechanism
that exists in this repository today; where nothing implements it, the row says so.

| concept | mechanism that implements it |
|---|---|
| **A document may not assert a present state** | "Currently", "recently", "today" and "for now" are claims a reader cannot check and an instrument cannot compare. Three were found and removed: Dependabot "currently covers GitHub Actions" (it had watched one ecosystem of three since the lock and the Go module landed), a label catalog described as "planned" while a planted defect proves it is enforced, and a topic list restated beside the declaration that owns it. **The replacement is always the same: name the version it was measured at, or name the instrument that answers it now.** |
| **A duplicate in a LIST hides where the loader cannot see it** | The strict YAML loader refuses a duplicate KEY, and a second `pip` entry for the same directory in dependabot.yml slipped past it because list items have no keys to collide. Measured here, by adding it. `check` now refuses a duplicate (ecosystem, directory) pair — a guard for the shape, not for the instance. |
| **A parser must refuse, never choose** | Every YAML read goes through a loader that REFUSES a duplicate key. PyYAML keeps the last one and reports nothing, which moved every F# file to the Forth pack on a diff that read as an addition. A tool that picks a winner where the input is ambiguous produces a confident wrong answer, which is strictly worse than an error. |
| **A transformation ends when the artifact parses** | Every tracked source file must parse, checked FIRST. A mechanical re-indent wrote a harness file that no longer compiled, twice, and the contract printed all of its counts — it validated documents and never asked whether its own code was valid. |
| **Single source of truth (DRY)** | `tools/tools.schema.json` is read by the contract, by the probe and by the skeleton generated into the authoring guide. Nothing restates it: a document that repeats the source of truth drifts from it silently, and the reader cannot tell a current copy from a stale one. |
| **One number, one declaration** | The README's generated facts and `packprobe` reported **884** and **276** declared entries for the same words — one counted positions, the other distinct entries. Neither was wrong; *having two* was, because a reader cannot tell which instrument is lying. Both now call one counting function. |
| **Memoization, and the invalidation seam it needs** | The parsed schema is cached. A mutation test that edited that schema on disk then **passed while planting nothing**, because the harness was checking bytes it already held. A cache with no explicit invalidation seam turns a planted defect invisible; `reset_caches()` is that seam, and it is called around every mutation. |
| **Content-addressable output** | A generator writes only when rendered content actually differs, so a second run leaves no diff. Judge a generator on its **diff**, never on its logic. |
| **Structured handoff (meta-prompting)** | `route --json` and `plan --json` emit a record — route, precedence rule, evidence, card, manifest, gates — so a consumer swaps one context block instead of re-deriving the router by regex over printed lines. |
| **Prompt expansion, as code rather than habit** | `atlas.py plan <path> --task debugging --change source_change` *is* the translation layer: an artifact becomes a route, a task profile, a tool set and the gates that change class requires. The enrichment is declared in `atlas.yaml` and identical every time, instead of improvised per prompt. |
| **Structural uniformity** | Every pack is `README.md` + `OPERATING.md` + `tools.yaml`, at one depth, with the canonical output paths declared in `atlas.yaml`. The contract fails on a pack missing any of the three. Uniformity is the reason one router answers for every language with no special case — and the reason an agent can predict a path it has never seen. |
| **Minimal cognitive overhead** | One door: `atlas.py route <path>` answers language, card, manifest, label, lane and gates in a single call, and says which precedence rule resolved it. An agent that reads six documents to find the seventh spends its budget on navigation. |
| **The roster is the tree, never a listing of it** | The probe walked `languages/*/tools.yaml` and silently skipped the nested `quantum/qsharp` pack — a real pack, absent from every number it printed. `rglob` is the tree; a one-level listing was a rendering of it that agreed until a pack was nested. |
| **Every limit has an owner** | `atlas.yaml/instruments` gives each instrument what it proves, what it does not, and **who closes that**. The contract fails on an empty `closed_by` and on any script the roster does not name, so a blind spot with no owner is unrepresentable rather than discouraged. A table of limits nobody owns ages into a table of defects. |
| **Shift-left verification** | The editor tasks, the devcontainer and CI run the same commands, and CI runs the **mutation tests before the contract**: a harness that cannot catch a planted defect must not be trusted to report a clean tree. |
| **Deterministic pipelines** | **PARTIAL.** Generated output is byte-identical for identical input, and every workflow declares a permission floor, a concurrency group and a timeout — but actions are pinned to a major tag, not a commit SHA. Scorecard reports it; it is named here rather than left implied. |
| **Durable checkpointing / reversible execution** | **GAP, deliberately.** Nothing here runs long enough to need a resume point: the contract is one bounded pass that is safe to re-run. If an agent loop is ever added, its state file belongs beside it and this row becomes a mechanism. |
| **Concurrency isolation (message passing over shared state)** | No concurrency ships here; the **gate** does. A `concurrency_change` requires race detection, cancellation and timeout tests, and the worked examples pass values across bounded queues with an explicit deadline rather than sharing memory. |
| **Pareto–Zipf locality** | The harness files are the hot path: linted, mutation-tested, capped at `atlascore.MAX_CODE_LINES`, split when one crossed it. The packs are documents and are held to structure only. Strictness is spent where execution happens, not spread evenly to look thorough. |
| **Minimal surface area (zero trust)** | Workflows start from `contents: read`; MCP servers activate per task profile, never globally; a symbol is private until a second module imports it. Exporting "in case" is what produced thirty unimported exports in one audit. |

---

## XI. Generation, governance and the order of work

Harvested from a proposed framework for directing AI code generation and backend construction.
Every row names what implements it here, or says plainly that nothing does.

| concept | mechanism that implements it |
|---|---|
| **Functionality first** | The build order is DECLARED in `atlas.yaml/build_order`: schema and types → state machine → integration tests → API contract → presentation, each step naming the gate class that judges it. The rule beside it is that a step may not begin until the one above it has passed. A plain CLI must be able to do everything the product can do before anything is styled. |
| **Schema-first generation** | The manifest schema existed before the manifests were rewritten to satisfy it, and the grammar REFUSES what it cannot classify. Generating logic before the schema is locked is how prose ended up in a field an instrument then had to skip. |
| **The defensive contract (explicit error types)** | Every example added at 2.2.0 returns a typed refusal rather than a partial success: Rust `Outcome::GaveUp`, Go `(error)` with `context.DeadlineExceeded`, C returning −1 rather than a truncation, and `${VAR:?}` in shell. **A truncation reported as success is the silent break.** |
| **Treat generated output as untrusted input** | `atlas_test.py` plants a defect for every rule the contract claims, CI runs the mutation tests BEFORE the contract, and `exrun.py` executes every example. Output that cannot be executed is not evidence. |
| **The ratchet (quality moves one way)** | Three of them: the context budget only moves down; the OpenSSF Scorecard floors are declared **per check** and only move up; and the dependency lock is hash-pinned, so an install either matches the recorded bytes or fails. |
| **Local fix versus global masking** | A cascade is one fault, not N — no detector may invoke another, and a fix that moves a symptom downstream is a defect with a new address. The pull-request template asks for a breakage review, not a test count. |
| **Strict aggregation (bulkheads, no leaky abstractions)** | Boundary contracts at every edge, and an aggregate is permitted only if it DECLARES itself one. The bounded-queue and worker-pool examples refuse work past their limit rather than degrading the whole run. |
| **Idempotency and transaction boundaries** | The Rust example is the worked case: the same key returns the FIRST result rather than producing a second effect, and the retry is bounded by a time budget rather than an attempt count. A lock prevents concurrency, not repetition. |
| **Fail closed** | Every workflow starts from `contents: read`; every instrument REFUSES rather than reporting when it cannot measure — `ghaudit` with no API, `packprobe` with no PyYAML, `doctor` with a missing requirement. A green line from a check that never ran is the failure this repository is built around. |
| **Licence and IP gatekeeping, automated** | `deny-licenses` on the required Dependency Review check: a copyleft dependency arriving through a transitive bump would change what the whole tree may be used for, silently, in a pull request nobody read that far into. |
| **CQRS (commands separated from queries)** | **NOT IMPLEMENTED HERE, and it would be cargo cult if it were:** this repository has no mutable store. It is named because the gate that would judge it (`api_change`) already exists, so a consuming system can adopt the split without inventing a new class of verification. |

---

## The ordering rule, stated once

**Prevention → healing → detection.**

1. **Can the cause be deleted?** Then do that. A check that never fires because the fault is impossible beats one that fires and gets repaired.
2. **If not, can it be healed?** Only if the thing regenerates — a cache, an index, generated output. **Never heal a decision.**
3. **Only then detect.** And a detector nobody runs is a record of what went wrong, not prevention.

**The tell that you are in the wrong tier:** count how often each check fails. If one fails repeatedly,
it is reporting on its own cause or on itself — not on the system.
