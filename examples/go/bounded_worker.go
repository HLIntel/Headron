// A bounded worker pool with an owner, a deadline and a cancellation path — standard library only.
//
// WHY IT WAS REWRITTEN: this file imported golang.org/x/sync/errgroup with no go.mod beside it, so
// `go run` could not execute it at all. An example that cannot run is a skeleton, and the ladder
// says standard library before dependency: a semaphore is a buffered channel.
//
// Verify: go run examples/go/bounded_worker.go   (exits non-zero if any assertion fails)
package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"sync"
	"sync/atomic"
	"time"
)

// pool runs every job with at most `limit` in flight, stopping on the first error or when ctx ends.
// EVERY GOROUTINE HAS AN OWNER AND A TERMINATION STORY: the WaitGroup owns them, the semaphore
// bounds them, and the context ends them.
func pool(ctx context.Context, limit int, jobs []func(context.Context) error) error {
	if limit < 1 {
		return fmt.Errorf("concurrency limit must be positive, got %d", limit)
	}
	semaphore := make(chan struct{}, limit)
	var wg sync.WaitGroup
	var firstErr atomic.Pointer[error]

	for _, job := range jobs {
		select {
		case <-ctx.Done():
			wg.Wait()
			return ctx.Err()
		case semaphore <- struct{}{}:
		}
		wg.Add(1)
		go func(job func(context.Context) error) {
			defer wg.Done()
			defer func() { <-semaphore }()
			if err := job(ctx); err != nil {
				firstErr.CompareAndSwap(nil, &err)
			}
		}(job)
	}
	wg.Wait()
	if err := firstErr.Load(); err != nil {
		return *err
	}
	return ctx.Err()
}

func check(condition bool, message string) {
	if !condition {
		fmt.Fprintf(os.Stderr, "FAIL: %s\n", message)
		os.Exit(1)
	}
}

func main() {
	var live, peak int64
	work := func(ctx context.Context) error {
		now := atomic.AddInt64(&live, 1)
		for {
			was := atomic.LoadInt64(&peak)
			if now <= was || atomic.CompareAndSwapInt64(&peak, was, now) {
				break
			}
		}
		defer atomic.AddInt64(&live, -1)
		select {
		case <-time.After(5 * time.Millisecond):
			return nil
		case <-ctx.Done():
			return ctx.Err()
		}
	}

	jobs := make([]func(context.Context) error, 20)
	for i := range jobs {
		jobs[i] = work
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	check(pool(ctx, 4, jobs) == nil, "every job completed inside the deadline")
	check(atomic.LoadInt64(&peak) <= 4, fmt.Sprintf("concurrency stayed within the limit, peaked at %d", peak))
	check(atomic.LoadInt64(&live) == 0, "no goroutine outlived the pool")

	// A deadline that cannot be met must surface as a cancellation, not as a silent partial result.
	tight, cancelTight := context.WithTimeout(context.Background(), time.Millisecond)
	defer cancelTight()
	slow := []func(context.Context) error{func(ctx context.Context) error {
		select {
		case <-time.After(time.Second):
			return nil
		case <-ctx.Done():
			return ctx.Err()
		}
	}}
	check(errors.Is(pool(tight, 1, slow), context.DeadlineExceeded), "an overrun surfaced as DeadlineExceeded")
	check(pool(context.Background(), 0, nil) != nil, "a limit of zero was refused rather than defaulted")

	fmt.Println("bounded_worker: 5 assertions held — bounded, owned, cancellable, and zero refused")
}
