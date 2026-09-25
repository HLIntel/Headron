# Go

**Status:** production

## Purpose
Cloud services, APIs, network software, workers, distributed systems, and operational tooling.

## Stack
Go modules -> gofmt -> go vet -> tests -> race detector -> fuzzing -> staticcheck -> govulncheck -> pprof/trace -> PGO where justified.
Core packages: context, x/sync, x/time/rate, log/slog, OpenTelemetry.

## Structure
Prefer small packages with clear ownership. Use internal packages for non-public implementation details.

## State
Keep request-scoped state in context boundaries and explicit function parameters. Avoid stuffing mutable business state into global singletons.

## Concurrency
Every goroutine needs an owner and termination story. Use errgroup, SetLimit, semaphore, singleflight, bounded channels, and cancellation.

## Common mistakes
- goroutine leaks
- ignoring context cancellation
- unbounded fan-out
- copying mutex-containing structs
- treating sync.Map as the default map
- retrying non-idempotent operations
- ignoring race detector results

## Streamline
Use the standard library first. Add a dependency when it solves a real missing capability or removes meaningful complexity.

## Performance
Use pprof and benchmarks. Inspect CPU, allocations, blocking, GC, queue depth, and tail latency. Go's PGO can be evaluated after representative profiling data exists.

## Learn into
context -> structured concurrency -> profiling -> service observability -> PGO -> distributed failure modes.

## AI directive
Check every goroutine, channel, retry, and external call for a bound and cancellation path. Do not generate fan-out code until the concurrency limit is explicit.

## Verify
`gofmt -l .`, `go vet ./...`, `go test ./...`, `go test -race ./...`, targeted fuzz tests, staticcheck, govulncheck.

Official: https://go.dev/doc/
