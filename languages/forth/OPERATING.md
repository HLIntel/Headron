# Forth Operating Card

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
