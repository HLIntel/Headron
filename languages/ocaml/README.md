# OCaml

**Status:** production

## Purpose
Compilers, static analysis, proof-adjacent tooling, financial systems, and long-lived typed services where a module boundary has to be enforced by the compiler.

## Why this route exists
It fills the ML family with an industrial native compiler and a first-class module system.

## Stack
opam -> dune -> ocamlformat -> ocamlopt -> dune test -> property tests -> perf.

## Common mistakes
- using `Obj.magic` to escape the type system
- exceptions crossing a module boundary that does not declare them
- a `.ml` with no `.mli`, so every internal detail is public
- unbounded concurrent fibres with no cancellation path
- `List` functions on large inputs where the stack depth was never considered

The avoid list, boundary contract, verify loop and learning loop live in the [operating card](#operating-card) below.

Official: https://ocaml.org/docs

## Operating card

**Route:** typed functional services, compilers, analysis tools, proof-adjacent code.

**Fast path:** `dune build` → `ocamlformat` → `dune test` → property tests where the invariant is stated.

**Native authority:** the OCaml compiler, dune, the module system and the type checker.

**Pair with:** Rust or C for a native core over the FFI; Python for orchestration; Lean 4 when a property must be proved rather than tested.

**Boundary:** a module signature (`.mli`) IS the contract — write it first and let the compiler refuse anything the signature does not permit.

**Avoid:** `Obj.magic`, exceptions as control flow across a module boundary, mutable global state, unbounded `Lwt`/`Eio` fibres with no cancellation.

**Reliability:** explicit effects or an explicit scheduler, bounded concurrency, and a timeout on every external call.

**Verify:** the fast path above, every step.

**AI learning loop:** read the `.mli` → trace one function → change the signature on purpose and watch what breaks → test → measure.

**Research:** https://ocaml.org/manual/ · https://ocaml.org/docs · https://dune.readthedocs.io/
