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

## Staying alive, and who is allowed to decide it

**A process that must outlive the session that started it declares itself to a supervisor.** Not a
terminal, not a detached shell, not a wrapper that hopes. The supervisor is the platform's —
`launchd`, `systemd`, a Windows service, a container restart policy, a scheduler — and the reason
is mechanical: **an orphan is a process whose parent is init and whose supervisor is nobody.**
Nothing restarts it and nothing stops it, so it survives exactly until it does not, and its absence
is discovered by whatever depended on it.

The corollary is the part usually skipped: **the expectation outlives the process.** A registry
that names what should be running is what turns a stopped feed into a reported `GONE` instead of a
quiet zero. Declare the name, the match pattern and the probe together, or the only detector is a
person noticing.

### Keeping a machine awake is a platform capability, never a program's business

`caffeinate` on macOS, `systemd-inhibit` on Linux, an execution-state request on Windows: each is
the platform's own answer, and each is *scoped to a command* rather than switched on globally.

**The rule that matters more than the flag:** a job that needs the machine awake should be run by
something that can WAKE it — a scheduler with a wake capability, or a machine that does not sleep —
not by a program that asks the machine to stay awake and has no recourse when it does not. An
inhibitor held for a long job is a bet; a scheduled wake is a mechanism.

### A liveness probe that calls a dependency adopts that dependency's outage

Keep the three apart, because they answer different questions and one of them is a trap:

| probe | asks | must not |
|---|---|---|
| liveness | is this process wedged and worth restarting? | touch a dependency — a database blip then restarts every healthy replica |
| readiness | can it serve traffic right now? | be cached, or it will keep advertising a capacity it lost |
| capability | can it do the specific thing it exists for? | be a 200 with no body — **a health 200 is not identity** |

**Probe a capability, never liveness alone.** A router that answers an error as an answer, and a
service that returns 200 from a handler that touches nothing, print exactly what a working system
prints.

### Restarts, drains and the cold-start anti-pattern

- **Bounded restarts with backoff, and the crash loop is a DECLARED state.** A supervisor that
  restarts forever converts a hard failure into a slow one and removes the signal that would have
  named it.
- **Graceful shutdown has a deadline.** Stop accepting, drain in flight, then exit — and the drain
  is bounded, because an unbounded drain is a process that never leaves.
- **Do not ping your own service to keep it warm.** It hides the cold-start cost from the metric
  that would justify fixing it, and it bills you for the concealment. Measure the cold start, state
  it, and decide; a warm-up ping is a fudge factor with a cron entry.

### Self-diagnosis, before anything else runs

`python scripts/atlas.py doctor` is the shape this repository uses: one command that reports which
capabilities exist, marks each REQUIRED or OPTIONAL, and — for every one missing — names **what
stops working because of it**. A warning that does not say what it costs gets read as noise, and a
tool that silently does nothing looks exactly like a tool that found nothing.
