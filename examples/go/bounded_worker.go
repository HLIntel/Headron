package main

import (
	"context"
	"fmt"
	"sync"

	"golang.org/x/sync/errgroup"
)

const maxJobs = 10_000

func run(ctx context.Context, jobs []string) error {
	if len(jobs) > maxJobs {
		return fmt.Errorf("job batch exceeds max size: %d", maxJobs)
	}

	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(32)

	results := make([]string, 0, len(jobs))
	var mu sync.Mutex

	for _, job := range jobs {
		job := job
		g.Go(func() error {
			result, err := process(ctx, job)
			if err != nil {
				return err
			}
			mu.Lock()
			results = append(results, result)
			mu.Unlock()
			return nil
		})
	}

	return g.Wait()
}

func process(ctx context.Context, job string) (string, error) {
	select {
	case <-ctx.Done():
		return "", ctx.Err()
	default:
		return job, nil
	}
}
