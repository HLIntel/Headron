# Operations and Uptime

Reliability begins in code design and continues through runtime operations.

## Availability model

```text
capacity
 + timeouts
 + retries
 + backpressure
 + observability
 + graceful degradation
 + recovery
 = resilience
```

## Required service properties
- bounded concurrency
- request deadlines
- cancellation
- retry classification
- circuit breaking where justified
- health/readiness signals
- structured logs
- metrics
- tracing where valuable
- graceful shutdown
- durable recovery path

## Don't retry everything

Retry only operations known to be retry-safe or idempotent, and only inside a finite budget.

```text
attempt 1
  ↓
backoff
  ↓
attempt 2
  ↓
deadline?
  ├─ yes -> stop
  └─ no  -> final attempt
```

## Observability

Track:
- request count
- error count
- latency
- queue depth
- active work
- cache hit/miss
- retry count
- circuit state
- resource saturation
- dependency health

## Shutdown

Every background worker needs a lifecycle.

```text
stop accepting new work
  ↓
cancel in-flight work
  ↓
drain bounded queue
  ↓
flush required state
  ↓
exit
```

## SLO-oriented thinking

Measure user-visible service behavior instead of only host health. A server can be CPU-healthy while its external dependency, queue, or cache is failing.

## Uptime anti-patterns
- infinite retries
- health checks that only test process existence
- unbounded queues
- synchronous heavy work in webhook handlers
- cache with no eviction
- background jobs with no cancellation
- logs that can consume the disk indefinitely
- deploys without rollback