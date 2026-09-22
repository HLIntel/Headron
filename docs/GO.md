# Go Advanced Engineering

Go is the reference for concurrent services, networking, cloud infrastructure, and distributed systems.

## Core stack
- context
- golang.org/x/sync
- golang.org/x/time/rate
- race detector
- staticcheck
- govulncheck

## x/sync
Study errgroup, SetLimit, semaphore, and singleflight.

SetLimit is especially important because it makes concurrency bounds explicit.

singleflight is useful for preventing duplicate concurrent work and origin stampedes.

## Context
Every long-running operation should have cancellation and a deadline when waiting on external systems.

## Rate limiting
Use golang.org/x/time/rate where external systems need protection from bursts.

## HTTP and JSON bounds
Explicitly constrain request body size, request duration, response behavior, concurrency, pagination, and retries.

## Race detection
Run go test -race ./... as a standard concurrency feedback layer.

## Security
Use go vet, staticcheck, govulncheck, fuzz tests where valuable, and integration tests.