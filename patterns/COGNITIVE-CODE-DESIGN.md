# Cognitive Code Design

Design code so humans and models can reason locally.

Make state, ownership, failure, blocking, growth, side effects, invariants, and cancellation obvious.

Keep I/O, network, filesystem, subprocess, database writes, and model/tool calls at narrow boundaries.

Increase semantic density with precise names, types, schemas, tables, domain objects, and declarative configuration. Do not increase density by obscuring control flow.

Before changing a shared primitive, identify callers, systems, agents, APIs, deployment paths, blast radius, and rollback options.

Prefer one source of truth for contracts, endpoints, timeouts, and policy.