# Language Operations Matrix

This page extends each language guide from “how to write it” into “how to keep it correct and running.”

Upstash supports Redis TCP and HTTPS REST. Its HTTP clients are explicitly designed for serverless/edge use; TypeScript and Python have documented first-class clients, and Elixir commonly uses Redix. For other languages, use a mature Redis client, protocol boundary, or host-service adapter rather than inventing an unsupported SDK.

| Language | Cloud / uptime | Redis / DB | Endpoint testing | Mutation / bug prevention | Breakage controls |
|---|---|---|---|---|---|
| Python | ASGI, containers, serverless; OTel + deadlines | upstash-redis REST, redis-py, PostgreSQL/SQLAlchemy | pytest + HTTPX; OpenAPI; Playwright if UI | Hypothesis + mutmut | Pydantic, retries/idempotency, dependency health |
| Rust | Tokio/Axum services, containers | Redis client/REST; SQLx/Postgres | reqwest + contract/integration | proptest/loom/Miri + cargo-mutants | Serde/protobuf/OpenAPI, tracing, graceful shutdown |
| Go | cloud services, containers/K8s, serverless | go-redis/Redis protocol; pgx/Postgres | httptest + integration/contract | fuzzing + Gremlins/go-mutesting where maintained | context, race detector, idempotency, readiness |
| TypeScript | Node, Next.js, serverless, edge | @upstash/redis; PostgreSQL/ORM | Vitest + framework test client + Playwright | StrykerJS + property/schema tests | runtime schemas, OpenAPI, queues/rate limits |
| C | daemon/service/container/embedded | hiredis/protocol or HTTP; libpq/ODBC | libcurl/native harness + integration | fuzzing + sanitizers | ABI/ownership, ASan/UBSan/TSan, watchdog |
| C++ | native service, low-latency, HPC | Redis protocol/client; DB driver | HTTP/gRPC + GoogleTest/Catch2 | fuzzing + sanitizers; Mull only if verified | ABI, sanitizer gates, shutdown, integration |
| Zig | native service/CLI/embedded | mature HTTP/TCP/DB clients where available | std.testing + integration | fuzz/property where supported | allocators, error unions, bounded I/O |
| Mojo | accelerator kernel behind host service | host-language Redis/DB | Python-side endpoint + numerical differential | property/differential + benchmark | Python/ABI/data-layout contracts, device errors |
| Julia | scientific service/job/container | Julia Redis/SQL packages or service boundary | Test + HTTP integration + golden cases | property/differential | project envs, type stability, telemetry |
| Elixir | Phoenix/OTP; supervision is uptime control | Redix/Upstash; Ecto/Postgres | ExUnit + Phoenix/Plug integration | StreamData + failure/restart tests | supervision, mailbox bounds, telemetry |
| Gleam | BEAM/OTP services | Erlang/BEAM DB/Redis packages via interop | native HTTP integration | property/fault injection | typed messages, supervision, package compatibility |
| Nim | native service/container | protocol/HTTP/C bindings | native tests + HTTP integration | fuzz/property | FFI/ownership contracts, health checks |
| V | native service/CLI | supported DB/Redis clients or HTTP | V tests + endpoint smoke | tests/fuzz where supported | Result/Option checks, bounded concurrency |
| Odin | native/data-oriented; host controls uptime | C interop/protocol/service | native + host integration | fuzz/property/differential | allocator/FFI ownership, service boundary |
| Hare | low-level daemon/tool | protocol/C interop | native + external harness | fuzzing + compiler/runtime checks | ABI/resource contracts, host supervision |
| Futhark | GPU/parallel kernel behind host | host handles DB/Redis | kernel golden/property + host E2E | numerical differential + benchmark | shape/layout/dtype contracts |
| Haskell | Warp/Servant services, containers | Redis/Postgres libraries | QuickCheck/Hspec + HTTP contract | QuickCheck; mutation only when mature | types/codecs, timeouts, async failure |
| F# | ASP.NET Core/.NET cloud | StackExchange.Redis + EF Core | xUnit/NUnit + FsCheck + API tests | FsCheck + Stryker.NET | cancellation, resilience policy, migrations |
| Chapel | HPC/distributed jobs | host/service integration | host + parallel correctness tests | property/differential/load | task/locale ownership, bounded distributed resources |
| BQN | data/array core; host owns uptime | host boundary | golden/vector + host integration | differential/golden | shape/rank/value contracts |
| Uiua | data/array core; host owns uptime | host boundary | golden/property + host integration | differential/golden | serialization/shape contracts |
| Lean 4 | verified core; host owns service uptime | extracted/host application | Lean proof + host API tests | kernel proofs + spec/property reasoning | theorem/spec contracts |
| Carbon | experimental native research | C++/service boundary | compiler/tests | fuzz/property; no default mutation gate | explicit ABI + toolchain compatibility |
| Roc | experimental functional core | platform boundary | platform integration + golden/property | fuzz/property/differential | pure core/platform contract |
| Q# | quantum workload via classical/cloud runtime | classical host handles DB/Redis | simulator + host endpoint + selective hardware | circuit/property/differential | shots/noise/backend/version contracts |
| Qiskit | Python/cloud quantum orchestration | Python host handles DB/Redis | pytest + simulator + backend integration | numerical/property/differential | backend/shot/noise contracts |
| Silq | experimental research toolchain | host/service boundary | compiler + simulator/host integration | semantic/property | compiler/runtime compatibility |
| CUDA | GPU kernel on cloud/managed GPU host | DB/Redis stay host-side | CUDA + host API + numerical tests | differential + Compute Sanitizer | device/host, streams/events, memory contracts |
| SQL | managed/self-hosted DB cloud | Redis/Upstash is cache/queue, not source of truth | migration + query + endpoint contracts | query/migration mutation fixtures + invariants | schema versioning, locks/timeouts, rollback |
| Bash | CI/deployment/system glue | redis-cli/HTTP/DB CLI | curl + Bats/smoke | ShellCheck + failure injection | quoting, exit codes, traps, timeouts |
| WebAssembly/WASI | browser/server/edge/sandbox | Upstash REST when HTTP exists; host DB | component + host endpoint + runtime tests | fuzz/property/differential where supported | WIT/component contracts, resource limits |

## Cross-language baseline

Every production-oriented language path should answer:

```text
Where does it run?
How does it fail?
How is it observed?
Where is state stored?
How is Redis/cache bounded?
How is the database migrated?
How is an endpoint tested?
How is a regression killed?
How is mutation detected?
How does a schema/ABI/version mismatch fail?
How is a large code/blob artifact prevented?
```

Sources:
- Upstash Redis compatibility: https://upstash.com/docs/redis/overall/compatibility
- Upstash getting started: https://upstash.com/docs/redis/overall/getstarted
- Upstash TypeScript SDK: https://upstash.com/docs/redis/sdks/ts/overview
- Upstash Python SDK: https://upstash.com/docs/redis/sdks/py/overview
