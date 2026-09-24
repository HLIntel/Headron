# OCaml Operating Card

**Route:** typed functional services, compilers, analysis tools, proof-adjacent code.

**Fast path:** `dune build` → `ocamlformat` → `dune test` → property tests where the invariant is stated.

**Native authority:** the OCaml compiler, dune, the module system and the type checker.

**Pair with:** Rust or C for a native core over the FFI; Python for orchestration; Lean 4 when a property must be proved rather than tested.

**Boundary:** a module signature (`.mli`) IS the contract — write it first and let the compiler refuse anything the signature does not permit.

**Avoid:** `Obj.magic`, exceptions as control flow across a module boundary, mutable global state, unbounded `Lwt`/`Eio` fibres with no cancellation.

**Reliability:** explicit effects or an explicit scheduler, bounded concurrency, and a timeout on every external call.

**Verify:** `dune build` → `ocamlformat` → `dune test` → property tests where the invariant is stated.

**AI learning loop:** read the `.mli` → trace one function → change the signature on purpose and watch what breaks → test → measure.

**Research:** https://ocaml.org/manual/ · https://ocaml.org/docs · https://dune.readthedocs.io/
