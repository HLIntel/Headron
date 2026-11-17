# Forth

**Status:** production, and older than most of what replaced it

## Purpose
Sophisticated computation on hardware that has almost nothing: bootloaders, instrument control,
spacecraft and industrial controllers, and any target where the whole runtime has to fit in
kilobytes and be understood completely.

## Why this route exists
It fills **an execution model no other route here has.** Every other language in this atlas
compiles to a register machine or runs on a managed runtime. Forth is a stack machine with
threaded code: a program is a dictionary of words, each a list of addresses of other words, and
the interpreter is small enough to read in an afternoon. That is not nostalgia — it is the reason
a Forth system can be self-hosting in a few kilobytes with direct access to memory and registers.

Notational density (the array routes) versus runtime density (this one): the verdict is recorded in
[ATLAS.md](../ATLAS.md).

## Stack
`gforth` for development on a workstation → the target board's own Forth for deployment →
`ttester` for the standard test harness → a cycle counter or a scope pin for measurement.

## Common mistakes
- a word that leaves the stack unbalanced, which corrupts every caller instead of failing
- no stack comment `( args -- results )`, so the only contract is in the author's memory
- unbounded recursion on a return stack measured in cells, not megabytes
- assuming cell width; a program that works on 64-bit gforth and not on a 16-bit target
- using `VARIABLE` where a value on the stack would do, turning a pure word into global state

## AI directive
State the stack effect before writing the word, and check it after: `( n addr -- flag )` is the
type signature and there is no compiler to infer it. Never generate a word whose depth effect you
have not stated. On a target, state the instruction and memory budget before the implementation —
"it fits" is not a measurement.

## Verify
`gforth -e "include file.fs bye"`, the `ttester` suite, and a stack-depth assertion around anything
that loops.

## Learn into
stack discipline → the dictionary and immediate words → `CREATE ... DOES>` → assembling your own
control structures → cross-compiling to a target → reading the interpreter itself.

Official: https://gforth.org/manual/

## Operating card

**Route:** embedded targets, bootloaders, instrument control, and any system where the runtime must
be small enough to be read in full.

**Fast path:** state the stack effect → write the word → `gforth -e "include file.fs bye"` → assert
the stack depth → measure on the target, never on the workstation.

**Native authority:** the Forth system itself. The dictionary, `see` to decompile a word, and the
stack are the debugger, the disassembler and the type system.

**Pair with:** C for an existing driver over the classic ABI; Python on the host for orchestration
and measurement capture.

**Boundary:** a stack comment `( args -- results )` on every word, and a memory-mapped register
boundary documented by address, width and side effect. There is no compiler to check either.

**Avoid:** unbalanced words, unbounded recursion on the return stack, assumed cell width, global
`VARIABLE` state where a stack value would do, and any word whose depth effect is undeclared.

**Reliability:** a bounded loop with an explicit counter, a watchdog on the target, and a
power-on self test that refuses to continue rather than running degraded.

**Verify:** `gforth` on the host for logic, the target for timing and memory. A cycle count from a
workstation is not a measurement of a microcontroller.

**AI learning loop:** read the word → decompile it with `see` → change one word → re-run the stack
assertions → measure the instruction budget.

**Research:** https://forth-standard.org/ · https://gforth.org/manual/
