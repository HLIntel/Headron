package main

import (
	"context"
	"sync"
	"golang.org/x/sync/errgroup"
)

func run(ctx context.Context, jobs []string) error {
	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(32)

	var mu sync.Mutex
	results := make([]string, 0, len(jobs))

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