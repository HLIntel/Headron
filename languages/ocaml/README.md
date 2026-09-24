# OCaml

**Status:** production

## Purpose
Compilers, static analysis, proof-adjacent tooling, financial systems, and long-lived typed services where a module boundary has to be enforced by the compiler.

## Why this route exists
It fills the ML family with an industrial native compiler and a first-class module system. A language earns a route here only by contributing a distinct guarantee,
runtime property, ecosystem or performance characteristic — not by being popular.

## Stack
opam -> dune -> ocamlformat -> ocamlopt -> dune test -> property tests -> perf.

## Common mistakes
- using `Obj.magic` to escape the type system
- exceptions crossing a module boundary that does not declare them
- a `.ml` with no `.mli`, so every internal detail is public
- unbounded concurrent fibres with no cancellation path
- `List` functions on large inputs where the stack depth was never considered

## AI directive
`obj.magic`, exceptions as control flow across a module boundary, mutable global state, unbounded `lwt`/`eio` fibres with no cancellation — check for these before generating code, and state the
boundary contract (a module signature (`.mli`) IS the contract — write it first and let the compiler refuse anything the signature does not permit) before writing the logic that crosses it.

## Verify
`dune build` → `ocamlformat` → `dune test` → property tests where the invariant is stated

## Learn into
read the `.mli` → trace one function → change the signature on purpose and watch what breaks → test → measure

Official: https://ocaml.org/docs
