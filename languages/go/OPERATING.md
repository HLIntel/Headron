# Go Operating Card

**Route:** network services, cloud, agents, CLIs, infrastructure, concurrency.

**Fast path:** `gofmt` → `go vet` → `go test ./...` → `go test -race ./...` → targeted fuzz/benchmark.

**Native authority:** Go compiler, `go` command, standard library, race detector, pprof.

**Pair with:** Python for data/AI orchestration; Rust for memory-sensitive native components; SQL for persistence.

**Boundary:** `context.Context` carries cancellation/deadlines; validate request sizes and decode limits; make retries explicit and bounded.

**Avoid:** goroutine leaks, ignored errors, global mutable state, unbounded channels, retry storms, context-less I/O.

**Reliability:** bounded worker pools, backpressure, graceful shutdown, readiness/health endpoints, pprof only behind controlled access.

**Verify:** `gofmt -w` → `go vet ./...` → `go test ./...` → `go test -race ./...`.

**AI learning loop:** start at handler → follow goroutine ownership → trace error path → edit → race/test → benchmark only after correctness.

**Research:** https://go.dev/doc/ · https://go.dev/ref/spec · https://go.dev/doc/effective_go
