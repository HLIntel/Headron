# Anti-Drift and Anti-Degradation

Drift is divergence between intended contract, indexed representation, implementation, and environment.

## Drift classes
| Drift | Example | Detector |
|---|---|---|
| contract | MODEL vs VERSION mismatch | contract check |
| route | extension points to missing guide | Atlas checker |
| reference | stale local Markdown link | link checker |
| orphan | durable guide loses all inbound references | orphan detector |
| dependency | unused/unlisted dependency | native dependency tools |
| environment | local and CI differ | lockfiles/tool manifests |
| behavior | refactor changes semantics | regression/property tests |
| performance | workload regresses | benchmark baseline |
| security | permission/dependency risk expands | scanners/policy |
| agent | repeated failure/scope expansion | harness telemetry |

## Control order
declare -> detect -> isolate -> verify -> record -> update invariant

Prefer executable checks over prose. Prefer generated/indexed views over duplicated inventories.

## Fitness functions
Protect continuously:
- canonical paths exist
- language guides exist and are indexed
- local documentation links resolve
- durable documents are reachable
- machine and human indexes agree
- workflow permissions and concurrency are explicit
- agent budgets are explicit
- cross-language boundaries have contract tests
- synchronized version surfaces match

Thoughtworks describes architectural fitness functions as automated checks used to protect important qualities as systems evolve:
https://www.thoughtworks.com/en-au/insights/articles/fitness-function-driven-development

## Baselines
For quantitative properties record:
metric -> workload -> environment -> baseline -> tolerance -> date

Never compare measurements across incompatible environments.

## AI directive
Generated code is a proposal. Let deterministic checks catch drift and use specialized verification for the changed failure class.

## What enforces this now

- **Generated blocks and files**: `atlas.py index --write` renders them from the declaration and
  `check` fails on any difference. A hand edit is a write to the output.
- **One value, one declaration**: version sites, the generated-file roster and the packaging
  roster are each asserted both ways. A second copy agrees only until one is edited — the
  reference contract's `atlas_version` drifted five versions before it was added to that check.
- **A cached reading is not a measurement of now**: `staleness_discipline` names, per reading,
  which cache serves it and what defeats that cache. A merge state reported CLEAN while its checks
  were still running; a language bar showed the old number after the fix had merged. Both look
  exactly like a failed change, so the fix that worked gets re-done and then distrusted.
