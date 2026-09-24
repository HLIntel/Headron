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

## The order of work, and why it is declared rather than advised

`atlas.yaml/build_order` declares five steps and, for each, the gate class that judges it:

<!-- BEGIN generated: build-order (python scripts/atlas.py index --write) -->
| # | step | gate that judges it |
|---|---|---|
| 1 | `schema_and_types` | `api_change` |
| 2 | `state_machine` | `source_change` |
| 3 | `integration_tests` | `source_change` |
| 4 | `api_contract` | `api_change` |
| 5 | `presentation` | `source_change` |

**A step may not begin until the step above it has passed its gate.**
<!-- END generated: build-order -->

**The rule beside it is the part that bites:** a step may not begin until the step above it has
passed its gate. The failure this prevents is a presentation layer built against an interface that
does not exist yet, which then dictates the schema underneath it — the schema ends up shaped by a
screen instead of by the domain, and every later constraint is a migration.

Two consequences worth stating in full:

- **A plain command line must be able to do everything the product can do**, before anything is
  styled. If it cannot, the capability lives in the presentation layer, where no gate here can
  reach it.
- **The state machine is pure.** Transitions take a state and an input and return a state; the
  store, the clock and the network stay outside. That is what makes the third step — integration
  tests against a real store — able to fail for one reason at a time.
