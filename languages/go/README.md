# Go

Purpose: APIs, network services, cloud infrastructure, distributed systems, concurrent workers, and operational tooling.

## When to choose Go
- Need simple deployable services with strong standard-library networking.
- Need high concurrency without a large runtime model.
- Need operational simplicity and fast builds.

## Core stack
- `context`
- `golang.org/x/sync/errgroup`
- `golang.org/x/sync/semaphore`
- `golang.org/x/sync/singleflight`
- `golang.org/x/time/rate`
- race detector
- staticcheck
- govulncheck

## Module/workspace discipline
Keep service/library boundaries explicit with `go.mod`.

`go.work` is useful for multi-module local development, but do not casually check in a workspace file that changes CI dependency selection. Go's module documentation explicitly calls out this risk.

Official: https://go.dev/ref/mod

## Concurrency
Every goroutine needs an ownership and termination story.

Use `errgroup` for related goroutines, `SetLimit` for explicit concurrency, semaphores for resource limits, and context cancellation for lifecycle.

Use `singleflight` to coalesce duplicate concurrent work; it is not a general overload control.

## HTTP and JSON
Bound request bodies, timeouts, pagination, concurrent handlers, and downstream calls.

Validate external JSON into explicit structures before business logic.

## Performance
Use `pprof`, benchmarks, tracing, and workload tests.

Do not optimize based on allocation counts alone; check tail latency and real system throughput.

## Verification
```bash
gofmt -w .
go vet ./...
go test ./...
go test -race ./...
go test -fuzz=Fuzz -run=^$ ./...
staticcheck ./...
govulncheck ./...
```

## AI-specific guidance
- Never generate a large fan-out loop without discussing a bound.
- Check every goroutine for cancellation and error handling.
- Check every external call for timeout/deadline propagation.
- Review generated error paths, especially partial failure.

## Worktree
```bash
git worktree add -b feat/go-task ../Code-Development-wt/go-task main
```

Docs: https://go.dev/ and https://pkg.go.dev/