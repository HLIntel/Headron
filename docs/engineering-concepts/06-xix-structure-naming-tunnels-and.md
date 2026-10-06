# Engineering concepts, each paired with a mechanism — part 6 of 7

[Index](../ENGINEERING-CONCEPTS.md)

## XIX. Structure, naming, tunnels and fault isolation

The tier with the highest hit rate: two items named defects still present when it was read.

| concept | mechanism |
|---|---|
| **Bulkhead isolation** | **Implemented on reading this.** One check was permanently red because credential-shaped strings sit in append-only records that can only be remedied by rotation — a *pending decision*, already tracked with a deadline. Left blocking, it made the whole ledger read NOT CLEAN and hid whether anything **else** broke: one compartment flooding sinks the ship. Failures are now **blocking** or **advisory**; advisory ones still run, print and record, but do not gate. **Moving a check to advisory requires its remedy be tracked somewhere with a date — otherwise it is not advisory, it is ignored.** |
| **Sandwich architecture (imperative shell, functional core)** | **The sharpest unmet one.** Every check here mixes side effects with logic — it reads the tree, probes processes, and decides, all in one pass. That is exactly why testing one needs a temp directory and an overridden `HOME`. A pure core taking a *snapshot* and returning a verdict would be testable with plain inputs. **Named as the largest remaining structural debt.** |
| **Fail-safe defaults** | Honoured where it counts: locks **fail closed**, a resolver refuses rather than printing nothing, an unreadable authority yields no verdict instead of "nothing is wrong". One deliberate exception, stated: the credential scan excludes append-only history by default — fail-*open* on scope, because scanning what cannot be fixed makes a check permanently red. |
| **Layered guardrail architecture** | Partial: enforcement at integration (scheduled, on demand) but **not at generation**. Edit-time checking is the shift-left still undone: the edit hook (`.agent/bootstrap.json` hooks.edit) only routes the agent to the gates that apply — it runs none. |
| **Package by feature (vertical slicing)** | Applied to knowledge: filed by the SHAPE of the lesson, not by subject. Filing by subject put 306 of 544 files in one bucket. *(measured at v1.1.0)* |
| **Single responsibility** | One check, one fault class, one exit code — and **no check may invoke another**, which is SRP stated as decoupling. |
| **Intention-revealing naming** | Uneven, honestly. `write_if_changed`, `is_advisory`, `prev_verdict` and `state-now` say what they do. Loop variables like `st` and `gen` do not, and one cost real time: naming a variable `path` in zsh **destroyed `PATH`** mid-script, because that name is already taken by the shell. **A name can collide with the language, not just with a reader's understanding.** |
| **Symmetrical naming pairs** | Weak: `--read` / `--all` are not opposites, and the apply gate has `apply` and `--verify` but no named `--revert` even though reverting is exactly what it does on failure. The behaviour is symmetrical; the vocabulary is not. |
| **Ubiquitous language** | Strong, and it is why the docblocks work: PAUSED, PHANTOM, DORMANT, FINISHED, advisory, blocking, epitaph, blind spot. Each term means one thing everywhere, so a verdict can be read without re-deriving what it meant. |
| **Encapsulation tunnels** | Each wrapper is the only door to its agent: it owns the environment, preflights the binary, then `exec`s. Nothing else launches an agent directly. |
| **Scoped execution contexts** | Working directory is passed **explicitly** to every delegated task, never inherited — which is why a task can be pointed at another project without changing global state. |
| **Secure tunneling** | **NOT APPLICABLE** — everything is local stdio or loopback. Recorded so its absence is a decision. |
| **Graceful fallbacks** | The `$0`-first ladder is a fallback chain read in the honest direction: the cheapest rung is the *default*, and a higher rung must be justified rather than merely available. |

---

## The practitioner's checklist — what to actually do

Everything above compresses to these. Each line was earned by a specific defect, not chosen for elegance.

**Before building**
1. **Can the cause be deleted?** Prevention → healing → detection, in that order. A check that never fires because the fault is impossible beats one that fires and gets repaired.
2. **Has it happened three times?** Two of the checks in this system were built from a persuasive *concept* with zero prior defects. That is the overfitting trap.
3. **Prefer the shortest description that reproduces the observation.** A parameter chosen after seeing the outcome counts toward the description length.

**While building**
4. **Read the instrument, not its documentation.** The shipped binary's symbol table, `lsof`, `ps`, `--porcelain`. Every wrong verdict in one measured day came from docs or memory; every verdict that held came from an instrument.
5. **Compare inodes before calling two files copies.** `ls` shows duplication; `stat -f %i` shows identity.
6. **An exit code is an interface; a log sentence is an accident.** Anything that branches on another program's prose will break when the prose is reworded.
7. **No destructive step without a postcondition that holds on both branches.** Snapshot, act, verify against the system's own verdict, restore on failure. Salvage before removal, in a separate commit.
8. **A generator is judged on its diff**, not its logic. Write only when content actually changed.

**While testing**
9. **When a test passes first try, check that it could have failed.** Three tests passed and were wrong in one day: a window smaller than the defect, a threshold below the planted value, a target outside the roster.
10. **Mutation-test for sensitivity AND specificity.** A check that fires on correct input gets switched off, and a switched-off check catches nothing. Declare which way the bias runs.
11. **Assert the roster is not empty.** A clean pass and an empty pass must never print the same thing.

**While operating**
12. **Mark the transition, not the repetition.** `NEW FAIL` / `still failing` / `RECOVERED` / nothing.
13. **A cascade is one fault, not N.** No detector may invoke another detector. Fix the root.
14. **Count how often each check fails.** One that fails repeatedly is reporting on its cause or on itself — never on the system.
15. **Print the count resolved and the blind spot, every run.** A number with no scope beside it is rhetoric.
16. **A repeated invocation must not repeat its side effect.** A lock prevents concurrency, not repetition.
17. **Nothing stays paused forever.** A temporary decision carries its own expiry, or it becomes permanent architecture nobody remembers choosing.

---
