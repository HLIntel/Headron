# No Unbounded

Core rule: every resource-consuming operation should have an explicit growth, time, or lifecycle boundary unless unbounded behavior is deliberately justified.

| Resource | Boundary |
|---|---|
| Memory | byte quota or allocation strategy |
| Tasks | semaphore or worker limit |
| Goroutines | semaphore or errgroup SetLimit |
| Queue | fixed capacity and backpressure |
| Cache | entries or bytes plus expiration |
| Retries | attempt budget plus deadline |
| Requests | timeout plus rate limit |
| Files | byte limit |
| JSON | size, depth, and item limits |
| Pagination | maximum page budget |
| Recursion | depth budget |
| Streams | byte and duration budgets |
| Logs | bounded buffer |
| Agent loops | tool, depth, runtime, and file budgets |

## Anti-patterns
- retry forever
- start a task per input with no limit
- queue indefinitely
- cache indefinitely
- read arbitrary file sizes
- parse huge untrusted structures without limits
- create background work with no cancellation

## Retry budget
Specify maximum attempts, maximum elapsed time, backoff, jitter, retryable errors, and non-retryable errors.

## Queue discipline
Choose what happens when a queue is full: reject, shed, block with timeout, drop oldest, drop newest, or persist externally.

## Cache discipline
Specify maximum size, expiration, invalidation, stale behavior, and stampede protection.

## Agent discipline
Set explicit maximum iterations, tool calls, runtime, files changed, bytes written, network calls, and approval gates.

The target is controlled degradation rather than runaway behavior.