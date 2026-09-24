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

The array languages already routed here (BQN, Uiua) give **notational** density: a line of code
expresses a page of loops. Forth gives **runtime** density: the machine underneath is small enough
to hold in your head. Those are different guarantees, which is why both earn a route.

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
