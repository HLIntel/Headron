# Package and Tool Catalog

This is a scoped catalog. A tool belongs because it solves a defined engineering problem, not because it is fashionable or widely starred.

## Python

| Package/tool | Purpose | Use when | Avoid/remember |
|---|---|---|---|
| Pydantic | runtime validation/models | external APIs, configs, tool inputs | frozen models do not recursively freeze nested dicts |
| msgspec | fast validation/serialization | hot JSON/MessagePack paths | benchmark against actual workload |
| immutables | immutable mappings | shared config/state | still design explicit ownership |
| attrs | structured/frozen classes | rich Python domain models | frozen is not absolute recursive immutability |
| Pyright | static typing | large/complex Python code | type checks cannot prove runtime behavior |
| Ruff | lint/format | all Python repos | configure intentionally |
| Hypothesis | property testing | parsers, invariants, edge-heavy logic | properties must be meaningful |
| AnyIO | async structure | portable async systems | understand underlying runtime semantics |
| cachetools | bounded cache patterns | TTL/LRU use cases | set capacity deliberately |

## Rust

| Crate/tool | Purpose | Use when | Avoid/remember |
|---|---|---|---|
| Tokio | async runtime | high-concurrency I/O | runtime does not automatically bound work |
| Tower | middleware | service composition/limits | configure limits explicitly |
| Moka | concurrent caching | bounded cache requirements | choose capacity/expiry deliberately |
| Governor | rate limiting | API protection | rate limits are not concurrency limits |
| Serde | serialization | typed data contracts | validate untrusted data appropriately |
| secrecy | secret wrappers | in-memory secret boundaries | minimize exposure through conversions |
| zeroize | clearing sensitive memory | key/secret cleanup | memory clearing is not a complete secret-management strategy |
| proptest | property testing | invariant-heavy code | generators need intentional coverage |
| loom | concurrency testing | synchronization-heavy Rust | model scope can grow; bound tests too |
| cargo-audit | vuln audit | dependency hygiene | vulnerabilities need applicability analysis |
| cargo-deny | dependency policy | licenses/sources/advisories | configure policy to fit the project |

## Go

| Tool/package | Purpose | Use when | Avoid/remember |
|---|---|---|---|
| context | cancellation/deadlines | every request-scoped operation | do not hide contexts in structs |
| x/sync/errgroup | task ownership | parallel work | use SetLimit where appropriate |
| x/sync/semaphore | resource bounds | external/CPU resource limits | semaphore is not a queue by itself |
| x/sync/singleflight | request coalescing | duplicate concurrent work | it reduces duplication, not all overload |
| x/time/rate | rate limiting | burst control | rate and concurrency are distinct |
| race detector | race detection | concurrent code | race-free tests are not proof of correctness |
| staticcheck | static analysis | all serious Go code | supplement, not replace, tests |
| govulncheck | vulnerability analysis | dependency/runtime hygiene | investigate actual reachability |

## TypeScript/JavaScript

| Package/tool | Purpose | Use when | Avoid/remember |
|---|---|---|---|
| TypeScript strict | compile-time guarantees | almost all serious TS code | runtime input still needs validation |
| Ajv | JSON Schema validation | high-volume schema validation | design schemas for stable contracts |
| Valibot | modular runtime validation | application/API boundaries | select based on actual needs |
| Immutable.js | persistent immutable structures | shared immutable state | data-structure overhead can matter |
| Immer | copy-on-write state | controlled mutable-style updates | distinguish from true persistent immutability |
| p-queue | bounded task queue | async job control | set concurrency explicitly |
| Bottleneck | rate/concurrency scheduling | API jobs | configure limits and lifecycle |
| ESLint | linting | JS/TS hygiene | type-aware rules need appropriate parser config |

## Cross-language security/hygiene

| Tool | Purpose | Scope |
|---|---|---|
| Semgrep | semantic/static analysis | multi-language |
| Gitleaks | secret detection | repositories |
| Trivy | vulnerability/container/filesystem scanning | broad |
| CodeQL | semantic security analysis | supported languages |
| OpenSSF Scorecard | OSS security posture | repositories/dependencies |
| Renovate | dependency updates | multi-ecosystem |
| Dependabot | dependency updates/alerts | GitHub ecosystem |
| pre-commit | repeatable local hooks | repository workflow |

## Data/AI infrastructure to evaluate

- OpenTelemetry for traces/metrics/log correlation
- Apache Arrow for columnar data interchange
- Parquet for analytical storage
- DuckDB for local analytical workflows
- Polars for high-performance dataframe work
- SQL engines and clients selected according to workload
- Redis or equivalent only when the actual workload requires networked shared caching/queues
- vector storage only when semantic retrieval is actually required

These should be evaluated through workload, correctness, operational, and dependency criteria rather than popularity alone.