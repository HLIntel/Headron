# Boundary Breakage Prevention

Most serious polyglot failures happen at connections: API contracts, schemas, ABIs, queues, databases, caches, model/tool boundaries, or deployment interfaces.

| Boundary | Prevent | Detect | Recover |
|---|---|---|---|
| HTTP/API | schema/version/idempotency | contract + integration tests | compatible rollout/rollback |
| webhook | signature/replay/size policy | fixtures + smoke test | replay/dead-letter |
| RPC/message | versioned schema | compatibility tests | dual-read/write or rollback |
| C/C++ ABI | layout/ownership/calling convention | compile/link/integration | pinned ABI/versioned release |
| Python/native | dtype/shape/ownership/errors | binding tests | isolate native component |
| DB | migration compatibility | migration/query tests | backup/rollback |
| Redis/cache | TTL/capacity/source-of-truth | load/integration | bypass/rebuild |
| queue | idempotency/order/visibility | end-to-end worker test | replay/dead-letter |
| model/tool | schema/permission/budget | tool contract tests | disable/restore snapshot |
| CI/action | permissions/version/input | workflow CI | revert/update |
| cloud | health/readiness/dependency | synthetic/integration | traffic shift/rollback |

## Connection contract

Every connection should define:

`owner + schema + version + timeout + retryability + idempotency + observability + failure behavior`

## Breakage test

```text
valid input -> expected success
invalid schema -> deterministic rejection
timeout -> bounded cancellation
duplicate -> defined idempotency
dependency outage -> graceful failure/degradation
old producer -> new consumer -> compatibility decision
new producer -> old consumer -> compatibility decision
```

The smallest useful verification is the boundary test that would fail if the connection broke.

AI agents changing a boundary must inspect both sides whenever accessible.
