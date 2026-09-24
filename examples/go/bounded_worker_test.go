package main

import (
	"context"
	"errors"
	"sync/atomic"
	"testing"
	"time"
)

// FuzzPool drives the bounded pool with generated limits and job counts.
//
// WHAT IT IS ACTUALLY LOOKING FOR — a fuzz target that cannot fail is decoration:
//  1. pool() must never panic, whatever it is handed, including a negative or absurd limit.
//  2. concurrency must never exceed the declared limit — the invariant the pool exists for.
//  3. no goroutine may outlive the call: `live` must be zero when it returns.
//  4. a non-positive limit must be REFUSED, not silently treated as one.
//
// Run the corpus:  go test ./examples/go/
// Fuzz it:         go test -run '^$' -fuzz FuzzPool -fuzztime 30s ./examples/go/
func FuzzPool(f *testing.F) {
	f.Add(4, 20)
	f.Add(1, 1)
	f.Add(0, 3)
	f.Add(-2, 5)
	f.Add(64, 0)

	f.Fuzz(func(t *testing.T, limit int, jobs int) {
		// Bound the generated work so the fuzzer explores shapes, not wall-clock time.
		if jobs < 0 {
			jobs = -jobs
		}
		jobs %= 64
		if limit > 64 {
			limit %= 64
		}

		var live, peak int64
		work := func(ctx context.Context) error {
			now := atomic.AddInt64(&live, 1)
			defer atomic.AddInt64(&live, -1)
			for {
				was := atomic.LoadInt64(&peak)
				if now <= was || atomic.CompareAndSwapInt64(&peak, was, now) {
					break
				}
			}
			select {
			case <-time.After(time.Microsecond):
				return nil
			case <-ctx.Done():
				return ctx.Err()
			}
		}

		queue := make([]func(context.Context) error, jobs)
		for i := range queue {
			queue[i] = work
		}

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		err := pool(ctx, limit, queue)

		if limit < 1 {
			if err == nil {
				t.Fatalf("a limit of %d was accepted instead of refused", limit)
			}
			return
		}
		if err != nil && !errors.Is(err, context.DeadlineExceeded) {
			t.Fatalf("limit=%d jobs=%d returned an unexpected error: %v", limit, jobs, err)
		}
		if got := atomic.LoadInt64(&peak); got > int64(limit) {
			t.Fatalf("limit=%d jobs=%d: concurrency peaked at %d, past its declared bound", limit, jobs, got)
		}
		if got := atomic.LoadInt64(&live); got != 0 {
			t.Fatalf("limit=%d jobs=%d: %d goroutine(s) outlived the pool", limit, jobs, got)
		}
	})
}
