# Backend Architecture

Select a backend shape based on workload and failure model.

## Common components
`gateway -> API -> service -> worker -> storage`

Supporting paths:
`webhook -> validator -> queue -> worker`
`agent -> policy -> tool -> service`
`researcher -> source -> normalizer -> store -> analysis`

## Bound every layer
- gateway: body/connection/rate limits
- API: timeout/concurrency
- queue: capacity/backpressure
- worker: concurrency/deadline/retry budget
- storage: connection pool/query limits
- agent: tool/runtime/cost/file-change budget

## Stateless vs stateful
Keep service instances stateless where practical. Put durable shared state behind an explicit storage contract.

## Failure domains
Define what can fail independently and how failure propagates.

## Backpressure
A slow downstream system should reduce upstream work rather than create unlimited queues.

## Deployment units
Prefer a deployable unit when the service boundary provides operational value. Do not split one simple application into microservices solely because the architecture diagram looks advanced.

## Language boundaries
Python is often a strong orchestration layer; Rust/Go/C++/Mojo can own specialized cores; Elixir/Gleam can own actor-oriented subsystems; TypeScript can own product/API surfaces.

Keep cross-language communication schema-based.