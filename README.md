<!-- CODE-DEVELOPMENT-AGENT: read AGENTS.md and docs/INDEX.md before acting. -->

> **Agent Directive — read first, index always.** Operate as a senior systems, security, distributed-infrastructure, and AI-engineering specialist. Before changing code, read `AGENTS.md`, then `docs/INDEX.md`, then the relevant language/integration/system guide. Preserve the repository invariants: no unbounded resources; immutable-first state; schema-first boundaries; explicit deadlines/cancellation; least privilege; independent verification; auditable changes; and rollback for high-impact mutations. A package default is not a safety guarantee. Prefer official specifications and documentation. When ambiguity remains, choose the strictest safe interpretation and record consequential decisions.

# Code-Development

Advanced code, development systems, programming languages, tooling, workflows, defensive engineering, AI-agent engineering, and high-performance builder patterns.

This repository is a technical reference and builder arsenal rather than a generic language-learning collection.

> How do I build software that is fast, typed, bounded, observable, difficult to mutate accidentally, difficult to misuse, and safe for AI-assisted development?

## Core Engineering Philosophy

### 1. Make invalid states difficult to create
Use static types, runtime schemas, constrained constructors, immutable data where practical, explicit state transitions, and narrow interfaces.

### 2. Prefer bounded systems
Anything that can grow should have an explicit control for memory, tasks, goroutines, queues, batches, retries, recursion, cache entries, cache bytes, JSON size, request bodies, pagination, streams, logs, and agent tool calls.

### 3. Treat mutation as a security and correctness boundary
Separate immutable inputs, owned mutable working state, transactional updates, snapshots, copy-on-write, versioned state, and rollback.

### 4. Make time a first-class limit
Use deadlines, cancellation, TTLs, timeouts, leases, retry budgets, and monotonic clocks instead of waiting indefinitely.

### 5. Validate at boundaries
Untrusted data should be converted into trusted internal representations once, then passed through strongly typed code.

### 6. Use the strongest guarantee the language can provide
Examples include Rust ownership and borrowing, Python static typing and frozen models, Go contexts and bounded concurrency, TypeScript strict typing and runtime schemas, and JSON Schema for language-independent contracts.

### 7. Assume AI-generated code can be wrong
AI coding workflows need requirements, types, linting, tests, property-based testing, fuzzing, dependency auditing, secret scanning, static analysis, sandboxing, command controls, rollback, and approval for high-impact changes.

## Repository Map

docs/
- PYTHON.md
- RUST.md
- GO.md
- TYPESCRIPT.md
- JSON.md
- SECURITY-HYGIENE.md
- AI-AGENT-ENGINEERING.md

patterns/
- NO-UNBOUNDED.md
- ANTI-MUTATION.md
- HIGH-ASSURANCE-WORKFLOW.md

## Python

Best for AI and ML, LLM applications, automation, data work, research, orchestration, and rapid systems prototyping.

### Advanced Python stack

| Tool | Role | Builder value |
|---|---|---|
| Pydantic | Runtime schemas and validation | Strong data contracts at boundaries |
| msgspec | Fast serialization and validation | High-performance JSON and MessagePack paths |
| immutables | Persistent immutable mappings | Shared state without normal dict mutation |
| attrs | Structured and frozen classes | Explicit object constraints |
| dataclasses | Standard-library value objects | frozen and slots options |
| Pyright | Static typing | Finds type and interface errors early |
| Ruff | Lint and format | Fast code hygiene |
| Hypothesis | Property-based testing | Explores edge cases automatically |
| AnyIO | Structured async abstractions | Portable async concurrency |
| cachetools | Bounded caches | Explicit capacity and TTL |

### Python language controls
Use Final, ReadOnly, TypedDict, Protocol, TypeGuard, TypeIs, Literal, Annotated, frozen dataclasses, asyncio.TaskGroup, and asyncio.timeout.

Important: Final controls rebinding intent. It does not recursively freeze the referenced object.

## Rust

Best for systems programming, security-sensitive infrastructure, high-performance services, low-level tooling, memory-safe concurrency, and performance-critical AI infrastructure.

### Advanced Rust stack

- Tokio
- Tower
- Moka
- Governor
- Serde
- serde_json
- bytes
- secrecy
- zeroize
- proptest
- loom
- Clippy
- Miri
- cargo-audit
- cargo-deny

Study Rust for ownership, borrowing, lifetimes, Send and Sync, deterministic cleanup, explicit unsafe boundaries, zero-copy design, and safe concurrency.

## Go

Best for network services, APIs, cloud systems, distributed services, infrastructure, and high-concurrency backend software.

### Advanced Go stack

- context
- golang.org/x/sync
- golang.org/x/time/rate
- race detector
- staticcheck
- govulncheck

High-value pattern: structured goroutine ownership plus explicit concurrency limits.

## TypeScript and JavaScript

Best for AI applications, APIs, full-stack systems, tool interfaces, and large application architectures.

### Advanced stack

- TypeScript strict mode
- Ajv
- Valibot
- Immutable.js
- Immer
- p-queue
- Bottleneck
- ESLint
- typescript-eslint

TypeScript types do not exist at runtime. External data still needs runtime validation.

## JSON and Data Contracts

JSON is a data interchange format. Treat it as a contract boundary rather than an unvalidated internal object.

Core technologies:
- JSON Schema
- Ajv
- Pydantic JSON Schema
- msgspec
- JSON Type Definition

Bound input using maxBytes, maxDepth, maxItems, maxProperties, maxStringLength, numeric ranges, required properties, and explicit additional-property policy.

Also study duplicate-key ambiguity, prototype pollution, deep nesting, giant arrays, parser differentials, schema drift, unsafe deserialization, resource exhaustion, and canonicalization.

## Defensive Engineering

### No Unbounded
Core rule: if a resource can grow, the implementation should make the growth boundary visible unless unbounded behavior is deliberately justified.

- Memory -> byte quota or allocation strategy
- Tasks -> semaphore, worker limit, or structured concurrency
- Goroutines -> semaphore or errgroup limit
- Queue -> fixed capacity and backpressure
- Cache -> maximum entries or bytes plus expiration
- Retries -> maximum attempts plus deadline
- Requests -> timeout plus rate limit
- Files -> maximum bytes
- Pagination -> page budget
- Recursion -> depth budget
- Streams -> duration and byte budget
- Logs -> bounded buffer
- Agent tools -> call, depth, runtime, and file-change budgets

See patterns/NO-UNBOUNDED.md.

### Anti-Mutation
Use layered controls:

PREVENT -> DETECT -> ISOLATE -> VERSION -> RECOVER

Examples include Rust ownership, frozen Python models, immutable mappings, TypeScript readonly APIs, static analysis, race detection, process boundaries, snapshots, content hashes, transactions, WAL, and rollback.

See patterns/ANTI-MUTATION.md.

## Caching

Caching is a correctness and resource-management problem, not only a performance feature.

Every cache should specify capacity, eviction policy, TTL, stale policy, negative caching policy, key normalization, versioning, invalidation, serialization, memory budget, and concurrency behavior.

Useful technologies include Python cachetools and immutables, Rust Moka, and explicit bounded cache patterns in Go and TypeScript.

Questions:
- Can entries grow without bound?
- Can payload size grow without bound?
- Can stale data survive indefinitely?
- Can concurrent misses stampede the origin?
- Can an older value overwrite a newer value?
- Does shared cache state expose mutable references?

## Concurrency

Core concepts:
- structured concurrency
- cancellation
- deadlines
- semaphores
- bounded worker pools
- rate limiting
- backpressure
- single-flight and request coalescing
- circuit breakers
- load shedding
- queue limits
- graceful shutdown

Avoid unmanaged fire-and-forget work, one-task-per-input without a limit, unbounded goroutine creation, retry loops without budgets, infinite queues, and background work with no cancellation path.

## Security and Hygiene

Core tools:
- Semgrep
- Gitleaks
- Trivy
- CodeQL
- OpenSSF Scorecard
- Renovate
- Dependabot
- pre-commit
- cargo-audit
- cargo-deny
- govulncheck
- staticcheck
- Ruff
- Pyright
- Clippy

Recommended quality pipeline:

format -> lint -> type-check -> unit tests -> property and fuzz tests -> SAST -> secret scan -> dependency audit -> build -> integration tests -> artifact verification

## AI and Agent Engineering

AI coding systems should be treated as software operators with capabilities, not just autocomplete.

An agent can potentially read files, write files, modify code, alter CI, install dependencies, access network resources, inspect credentials, change persistent memory, create helper programs, and chain operations.

Core controls:
- tool policy
- path fencing
- sandboxing
- capability restrictions
- approval gates
- memory integrity
- snapshots
- diff inspection
- rollback
- audit logs

### Railguard
Railguard is the exact project found for the Railguard reference: https://github.com/railyard-dev/railguard

It is a Rust runtime for Claude Code focused on tool-call policy and execution containment.

Study its concepts of allow/block/ask decisions, command classification, pipe and evasion analysis, path fencing, sensitive-file detection, content inspection, OS-level sandboxing, multi-agent coordination, file snapshots, replay, recovery, memory-write controls, and content-hash integrity.

Railguard belongs here as an architecture reference for AI-agent containment, not merely as a package.

## AI Coding Guardrail Architecture

USER INTENT -> SPEC -> AI PLAN -> GENERATED CODE -> STATIC ANALYSIS -> TYPE CHECK -> TEST -> PROPERTY/FUZZ -> SECURITY SCAN -> DIFF/POLICY CHECK -> APPROVAL -> BUILD/RELEASE

For high-impact operations:
AI -> TOOL REQUEST -> POLICY ENGINE -> SANDBOX/CAPABILITY BOUNDARY -> EXECUTION -> AUDIT/SNAPSHOT

Independent verification should decide whether generated code is acceptable. The model should not be the only enforcement layer.

## Advanced Patterns

- immutable state
- copy-on-write
- content addressing
- single-flight
- idempotency
- retry budgets
- exponential backoff and jitter
- circuit breakers
- load shedding
- bounded worker pools
- structured concurrency
- deadline propagation
- cancellation propagation
- zero-copy
- arena allocation
- transaction boundaries
- append-only logs
- event sourcing
- snapshots
- WAL
- deterministic serialization
- schema evolution
- capability security
- sandboxing
- least privilege
- fail-closed behavior
- graceful degradation
- fuzzing
- formal verification

## Language Routing

Each language has its own scoped README containing purpose, when to use it, core tools, project structure, performance concerns, worktree workflow, AI-agent rules, and verification.

| Language | Guide |
|---|---|
| Python | [languages/python/README.md](languages/python/README.md) |
| Rust | [languages/rust/README.md](languages/rust/README.md) |
| Go | [languages/go/README.md](languages/go/README.md) |
| TypeScript/JS | [languages/typescript/README.md](languages/typescript/README.md) |
| C++ | [languages/cpp/README.md](languages/cpp/README.md) |
| Zig | [languages/zig/README.md](languages/zig/README.md) |
| Mojo | [languages/mojo/README.md](languages/mojo/README.md) |
| Julia | [languages/julia/README.md](languages/julia/README.md) |
| Elixir/OTP | [languages/elixir/README.md](languages/elixir/README.md) |
| Lean 4 | [languages/lean4/README.md](languages/lean4/README.md) |

## Languages in This Repository

| Language | Primary role |
|---|---|
| Python | AI, orchestration, research, automation |
| Rust | Safety, systems, security, high-performance infrastructure |
| Go | Concurrent services, networking, cloud infrastructure |
| TypeScript | AI applications, APIs, typed product systems |
| C++ | Native high-performance systems, graphics, HPC |
| Zig | Low-level tooling and explicit memory management |
| Mojo | AI-oriented systems and HPC exploration |
| Julia | Scientific and numerical computing |
| Elixir | Fault-tolerant distributed applications |
| Lean 4 | Formal verification and proof-oriented programming |

## Builder Checklist

Correctness:
- inputs validated
- state transitions explicit
- errors modeled
- cancellation handled
- timeouts present
- concurrency bounded
- retries bounded
- queues bounded
- caches bounded

Mutation:
- mutable state minimized
- ownership clear
- shared references controlled
- snapshots or versioning considered
- rollback path exists for high-impact state

Security:
- secrets excluded
- dependencies audited
- static analysis enabled
- untrusted input isolated
- filesystem access constrained
- dangerous commands policy-gated
- CI permissions minimized

AI-generated code:
- generated code reviewed
- diff inspected
- dependencies inspected
- types checked
- tests run
- edge cases tested
- fuzz or property testing considered
- agent actions bounded
- high-impact changes gated
- recovery available

## Official Documentation Targets

- Python: https://docs.python.org/
- Python typing specification: https://typing.python.org/
- Rust: https://www.rust-lang.org/
- Rust docs: https://docs.rs/
- Go: https://go.dev/
- Go packages: https://pkg.go.dev/
- TypeScript: https://www.typescriptlang.org/
- JSON Schema: https://json-schema.org/
- Pydantic: https://docs.pydantic.dev/
- msgspec: https://jcristharif.com/msgspec/
- Ajv: https://ajv.js.org/
- Semgrep: https://semgrep.dev/
- OpenSSF Scorecard: https://github.com/ossf/scorecard
- Railguard: https://github.com/railyard-dev/railguard

## Repository Intent

This repository is intended to become a high-signal personal engineering knowledge base for advanced programming, AI-assisted development, systems programming, high-performance computing, defensive coding, secure coding, data contracts, concurrency, memory and state management, infrastructure, developer tooling, agent tooling, formal verification, and production engineering.

The standard is not popularity. The standard is meaningful capability, strong guarantees, operational usefulness, and relevance to serious software.