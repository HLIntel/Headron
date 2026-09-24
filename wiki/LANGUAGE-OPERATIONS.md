# Language operations — the questions, not a second tool matrix

This page carried a per-language matrix of clients, test tools and mutation tools. **Every column
of it restated something `languages/<route>/tools.yaml` already declares** — and it had gone stale
in both directions: it omitted five routes and carried a row for Qiskit, which is an SDK with no
route at all. The per-language answer comes from the router; what belongs here is the set of
questions a change has to answer whatever the language.

```bash
python scripts/atlas.py route path/to/file.ext --json     # the pack, its card, its manifest
python scripts/atlas.py plan  path/to/file.ext --task reliability --change source_change
```

## The five dimensions every production change answers

| dimension | the question | where the per-route answer lives |
|---|---|---|
| **runtime shape** | container, serverless, edge, embedded, or a long-lived process with a supervisor? | the pack's operating card, plus [systems/OPERATIONS-UPTIME.md](../systems/OPERATIONS-UPTIME.md) |
| **state** | what store, and what happens when it is slow rather than down? | the pack's `authority.package_manager` and its `profiles.endpoint`; [systems/STORAGE-STATE.md](../systems/STORAGE-STATE.md) |
| **endpoint** | what proves the contract holds — schema, contract test, integration? | `profiles.endpoint`, and the `api_change` gate |
| **defect prevention** | property tests, fuzzing, mutation — which of these is *mature* for this language? | `authority.fuzz` and `authority.mutation`, where `none` is an honest answer |
| **breakage control** | timeout, cancellation, idempotency, readiness, rollback | `profiles.reliability`, and the `concurrency_change` gate |

**A `none` in a manifest is a finding about the ecosystem, not a gap in the pack.** Mutation
testing is mature in a handful of languages and absent in most; writing a plausible tool name into
this page for the rest is what produced a matrix nobody could check.

## The one thing that is not derivable

Managed data services differ in what they support from an edge or serverless runtime: some offer
an HTTP interface designed for it, others assume a long-lived TCP connection and a connection pool
that a per-request runtime cannot give them. **Check the service's own documentation for the
runtime you are actually deploying to**, and prefer a mature client or an explicit protocol
boundary over an SDK that was never designed for that shape. This is guidance about other people's
products, so it carries no tool names and no version claims — those rot faster than anything else
in this repository.
