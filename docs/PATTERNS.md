# Engineering patterns

Nine rules for code that people and agents both change. Each section gives the rule, then **Enforced by**:
the check in this repository that refuses a break. A rule with no check is advice.

| Pattern | Rule in one line |
|---|---|
| [Small parts](#small-parts) | No file, function, artifact or payload grows past what one reader can hold |
| [No drift](#no-drift) | One value has one declaration; every copy is generated and checked |
| [Controlled change](#controlled-change) | Every piece of state is immutable, owned, or transactional |
| [No orphans](#no-orphans) | Every durable file has an owner and a route that reaches it |
| [Safe boundaries](#safe-boundaries) | Every connection declares its schema, version, timeout and failure behaviour |
| [Local reasoning](#local-reasoning) | State, side effects and failure are visible where the code is read |
| [Small context](#small-context) | Hand over the route, not the repository |
| [Build in order](#build-in-order) | Define, constrain, implement, verify, inspect, release |
| [Everything bounded](#everything-bounded) | Every resource has a size, time or lifecycle limit |

## Small parts

A blob is a module, artifact or payload that has grown past what one reader can reason about.

- **Code:** review a file near the line cap (`atlascore.MAX_CODE_LINES`) or a function near the cap
  `astshape.py` prints, and any module that mixes domains, side effects, routing, or generated and hand-written code.
  Split by owner, domain, lifecycle or failure boundary.
- **Artifacts:** never commit build output, caches, binaries, model weights, credentials, dumps, logs or
  archives (`atlascore.MAX_BLOB_BYTES`). Use releases, registries, object storage, Git LFS, or regenerate.
- **Payloads:** every large external payload has a schema, a size limit, a streaming plan, retention, cleanup and one source of truth.
- **Agents:** map a large file's responsibilities and dependencies before asking an agent to rewrite it.
  A large rewrite changes meaning by accident.

**Enforced by:** `scripts/astshape.py` refuses two functions with the same shape once names, literals
and docstrings are erased; it merged two invariants written apart that compiled the same. The function
cap only falls: 278 → 262 → 259 → 239 → 232 → 221 → 210 → 202, each step a refused function and a split.
`context_policy/install_footprint` bounds the wheel in bytes; moving maintenance out of it cut a consumer
install from 212 KiB to 160 KiB (measured at v2.25.0).

## No drift

Drift is a gap between the declared rule, its indexed copy, the code and the environment.

| Drift | Example | Caught by |
|---|---|---|
| contract | MODEL.md and VERSION disagree | contract check |
| route | an extension points at a missing guide | `atlas.py check` |
| reference | a local Markdown link is stale | link check |
| orphan | a guide loses every inbound link | orphan check |
| dependency | unused or unlisted package | the language's dependency tool |
| environment | local and CI differ | lockfiles, tool manifests |
| behaviour | a refactor changes meaning | regression and property tests |
| performance | a workload slows | benchmark baseline |
| security | permissions or dependencies widen | scanners, policy |
| agent | repeated failure, scope creep | harness records |

Order: declare → detect → isolate → verify → record → tighten the invariant. Prefer a check to prose and a
generated view to a second hand-kept list. For a measured property record metric, workload, environment,
baseline, tolerance and date, and never compare across environments. Generated code is a proposal until a
check passes ([fitness functions](https://www.thoughtworks.com/en-au/insights/articles/fitness-function-driven-development)).

**Enforced by:** `atlas.py index --write` renders every generated block and file, and `check` fails on any
difference, so a hand edit is an edit to output. Version sites and the generated and packaging rosters are
asserted both ways; the reference contract's `atlas_version` drifted five versions before it joined that
check. `staleness_discipline` names, per reading, which cache serves it and what defeats the cache: a
cached "merge CLEAN" while checks still ran looks exactly like a failed change.

## Controlled change

Change to state is fine; change nobody controls is not.

| State | Use for |
|---|---|
| immutable | config, ids, contracts, snapshots, messages, history, shared cache values |
| owned mutable | local work, buffers, builders, temporaries, with one named owner |
| transactional | persistent, financial and config state, and high-impact agent actions |

Five layers: **prevent** (ownership types, frozen models, readonly APIs, capability-limited tools) →
**detect** (types, static analysis, race detection, property tests, fuzzing, mutation tests, CodeQL) →
**isolate** (processes, sandboxes, path fences, read-only mounts, one writer per worktree) → **version**
(hashes, commits, snapshots, append-only records, lockfiles) → **recover** (transactions, WAL, backups, rollback, replay).

Mutation testing checks the test suite, not production state. Run it after functional tests exist, on
changed or high-value code, with a time budget and a baseline: mutmut (Python), cargo-mutants (Rust),
StrykerJS (TypeScript), Stryker.NET (F#/.NET). Where no mature tool exists, use property tests, fuzzing,
golden tests, sanitizers or fault injection. A cache that returns a shared mutable object lets a caller
change cached state: return immutable values or copies. Agents touch code, config, CI, credentials,
memory, tools and services, so a high-impact change needs a policy check, a snapshot, a diff, an audit
entry, approval and a rollback.

**Enforced by:** `atlas.yaml/governance_tiers`, because a wall that cannot move gets worked around:
**hard** refuses outright (irreversible or visible outside the repository); **bounded** may move only
when the move names what earned it; **dynamic** is free because its output is checked. Every ratchet
must sit in the bounded tier. `agent_policy` refuses rather than warns, and `agent_failure_modes` records
the mistakes made here, each of which looked like success.

## No orphans

An orphan is a durable file with no owner, route, reference, test or declaration: a doc, guide, adapter,
script, dependency, schema, workflow or generated file. Find them by walking tracked files → links →
index → routes → adapters → scripts and workflows → dependency tools (for example
[Knip](https://knip.dev/) for TypeScript, [deptry](https://deptry.com/) for Python). Treat a hit as
evidence, since dynamic entry points and config create real gaps.

Repair: decide whether it is generated, dynamic or an entry point → find its owner → add a reference or
declaration → add a check where the gap would recur → delete only when no owner and no route are proven →
rerun. Agents may propose a removal; the harness classifies before anything is deleted.

**Enforced by:** `context_policy/example_coverage` counts packs that ship nothing runnable, and
`exrun.py` prints coverage beside its pass count. Every `scripts/*.py` must be in `atlas.yaml/instruments`
and either shipped or marked development-only; a shipped module importing a development-only one fails.
Every route must appear in a `language_selection` axis, so no pack is reachable only by name.

## Safe boundaries

Most serious multi-language failures happen where two systems connect.

| Boundary | Prevent | Detect | Recover |
|---|---|---|---|
| HTTP/API | schema, version, idempotency | contract and integration tests | compatible rollout, rollback |
| webhook | signature, replay and size policy | fixtures, smoke test | replay, dead letter |
| RPC/message | versioned schema | compatibility tests | dual read/write, rollback |
| C/C++ ABI | layout, ownership, calling convention | compile, link, integration | pinned ABI |
| Python/native | dtype, shape, ownership, errors | binding tests | isolate the native part |
| database | compatible migrations | migration and query tests | backup, rollback |
| cache | TTL, capacity, source of truth | load tests | bypass, rebuild |
| queue | idempotency, order, visibility | end-to-end worker test | replay, dead letter |
| model/tool | schema, permission, budget | tool contract tests | disable, restore snapshot |
| CI/action | permissions, version, inputs | workflow CI | revert |
| cloud | health, readiness, dependencies | synthetic tests | shift traffic, roll back |

Every connection declares owner, schema, version, timeout, retry rule, idempotency, observability and
failure behaviour. Test: valid input succeeds; a bad schema is rejected; a timeout cancels; a duplicate
is idempotent; an outage degrades; old producer with new consumer, and the reverse, each have a decision.
The smallest useful check is the boundary test that fails when the connection breaks. An agent changing a
boundary reads both sides.

**Enforced by:** `authority_classes/boundary` is empty on purpose and names its closers: the polyglot
boundary test and the schema both sides read. `risk_modifiers` add gates to `api_change`
(`breaking_endpoint`, `auth_boundary`, `webhook`, `public_schema`) and only ever add. `published_interfaces`
lists names outside readers resolve, so renaming one is an API change, not a find-and-replace.
`gate_tools` marks a gate no tool can run as `role: none` with its closer.

## Local reasoning

Write code a person or model can reason about from where they stand: make state, ownership, failure,
blocking, growth, side effects, invariants and cancellation visible. Keep I/O, network, files,
subprocesses, writes and model calls at narrow edges. Raise density with precise names, types, schemas
and tables, never by hiding control flow. Before changing a shared primitive, list its callers, blast
radius and rollback. Keep one source for contracts, endpoints, timeouts and policy.

**Enforced by:** `atlas.yaml/code_shape` ([Small parts](#small-parts)), `governance_tiers`
([Controlled change](#controlled-change)) and `agent_failure_modes`.

## Small context

Cut repeated context and tool traffic without cutting correctness, evidence or requested detail. Use
three layers: always-loaded rules, task reference, deep detail. Prefer indexes, line ranges, symbols,
diffs, short structured handoffs, stable prefixes and cached context. Compress code by meaning (tables,
declarative config, generated repetition, shared validators), never with opaque one-liners, hidden
retries, global state or reflection.

**Enforced by:** `scripts/contextcost.py` measures what the repository hands over before a route is
resolved, for the agent and human entry paths, each held to a band in `context_policy/entry_paths`. A
band, because the entry files are generated and a point target would fire on correct work. A rise past
the ceiling is refused, and so is slack under it. It costs the worst single instruction convention plus
what every runtime reads, not the sum of conventions no runtime loads together. Against a real model,
routing scored the same as every pack's declarations at **29.4% of the prompt tokens** (measured at v2.25.0),
and more context scored worse (`scripts/abtest.py`).

## Build in order

1. **Define:** goal, inputs, outputs, invariants, non-goals, budgets, security boundaries, failure behaviour.
2. **Constrain:** types, schemas, timeouts, limits, permissions, allowed paths, tools and network.
3. **Implement:** small interfaces, explicit state, pure functions, immutable edges, bounded concurrency, structured errors.
4. **Verify:** format, lint, types, unit, integration, property, fuzz, race tests, security and dependency audits.
5. **Inspect agent changes:** diff, dependencies, permissions, file and network behaviour, tests, bounds, rollback.
6. **Release:** reproducible builds, lockfiles, actions pinned by digest, signed artifacts with provenance,
   versioned schemas, a changelog, rollback steps. No "where appropriate": every action is pinned to a commit
   and every release is attested ([CERTIFICATION.md](CERTIFICATION.md)).

Before shipping, answer: which inputs are invalid; what partial failure does; what a slow dependency does;
what grows and to what limit; who owns each mutable object; what the agent can read, write and run; which
actions need approval; whether high-impact state can be rolled back.

**Enforced by:** every instrument declares what it does not prove and who closes that gap
(`atlas.yaml/instruments` refuses an empty `closed_by`). `atlas_test.py` and `agent_test.py` plant a
defect per rule and assert their own case counts. `gate_tools` maps each gate to the command that runs it;
`tool_claims` separates declared, available, compatible, executed, passed and authoritative. `bench.py`
reports a chance baseline and marks arms it cannot run as NOT RUN. `atlas check --fix` repairs only what is mechanical.

## Everything bounded

| Resource | Limit |
|---|---|
| memory | byte quota |
| tasks, goroutines | semaphore or worker limit |
| queue | fixed capacity and backpressure |
| cache | entries or bytes, plus expiry |
| retries | attempt budget and deadline |
| requests | timeout and rate limit |
| files, streams | byte (and duration) limit |
| JSON | size, depth, item limits |
| pagination, recursion | page or depth budget |
| logs | bounded buffer |
| agent loops | tool, depth, runtime and file budgets |

Never retry forever, start unbounded tasks, queue or cache without limit, read files of any size, parse
large untrusted input unchecked, or start background work that cannot be cancelled. A retry plan names
attempts, total time, backoff, jitter and which errors retry. A full queue rejects, sheds, blocks with a
timeout, drops, or persists: pick one. A cache names size, expiry, invalidation, staleness and stampede
protection. An agent names iterations, tool calls, runtime, files changed, bytes written, network calls
and approvals. Aim for controlled degradation.

**Enforced by:** bounds count what actually grows, usually bytes. `install_footprint` and `entry_paths`
are banded byte limits. `agent_policy/audit/max_stream_bytes` refuses rather than prunes, because pruning
would delete the evidence. `branch_policy/unpushed_bound` counts unpushed commits, not branches: three
branches and two worktrees met every branch cap while eight commits sat unpushed for three hours.
`example_coverage` counts packs with nothing runnable.
