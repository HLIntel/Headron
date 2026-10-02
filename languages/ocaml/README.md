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

The avoid list, boundary contract, verify loop and learning loop live in `OPERATING.md` beside this guide.

Official: https://ocaml.org/docs
