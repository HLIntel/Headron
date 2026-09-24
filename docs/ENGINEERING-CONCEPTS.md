# Engineering concepts, each paired with a mechanism

**A concept with no mechanism beside it is vocabulary.** Every entry below names the concept, then the
thing that actually implements it — or states plainly that nothing does yet. That second column is the
point; the definitions are available everywhere.

Ordered by leverage: **prevention first, detection last.**

---

## I. Structural prevention — the fault cannot be expressed

The highest-leverage tier. A fault that cannot be represented needs no guard, no healer and no retry.

| concept | mechanism that implements it |
|---|---|
| **Make illegal states unrepresentable** | A port registry whose `match` field names the *binary*, not one of its roles. Declaring `opencode` instead of `opencode-chat` ended a recurring "collision" that was a program using its own port — the fault became inexpressible instead of detectable. |
| **Poka-Yoke (mistake-proofing)** | A safe route that is *structurally incapable*, never flagged safe: it loads no key and takes no nonce, so there is nothing to set wrongly. |
| **Parse, don't validate** | Config candidates are parsed and applied through one gate that restarts the app and reads the app's **own** loader verdict, then reverts. Validity is decided at the boundary, once. |
| **Design by Contract** | An exit code is the contract between two scripts. Replacing `grep -q '<a log sentence>'` with `exit 3` removed an implicit interface that a reworded log line would have silently broken. |
| **Total functions** | A resolver that always answers: the authoritative path, or an explicit refusal. Never silence. **Absent is not zero.** |
| **Pure zero-defects (eliminate recovery paths)** | Removing `npx -y` from a wrapper deleted the cache that grew 328 MB per invocation. No rotation policy can beat deleting the writer. |

## II. Determinism and reproducibility

| concept | mechanism |
|---|---|
| **Idempotency** | Generators write only when content actually changed, comparing with the timestamp line masked. Idempotent in *effect* is not enough — judge a generator on its **diff**. |
| **Deterministic serialization** | The same masked comparison: byte-identical output for identical input, so version control stays quiet and caching is trivial. |
| **Hermeticity** | Every wrapper sets `PATH` explicitly and preflights its binary, because GUI-launched processes inherit a stub environment — no profile, no keys. One agent was invisible for a month for exactly this. |
| **Provenance** | **GAP.** Knowledge files do not record which agent wrote them. Named as a failure mode in the literature ("provenance collapse") and not yet closed here. |

## III. Decoupling

| concept | mechanism |
|---|---|
| **Orthogonality** | No detector may invoke another detector. One leaked process once lit three of them and read as three problems. **A cascade is one fault, not N.** An aggregate is permitted only if it declares itself one. |
| **Law of Demeter** | Same rule, stated as coupling: a checker that reaches through another checker cannot fail independently. |
| **Composability** | One dispatcher, one door: `<tool> <agent> "<task>" <cwd>`. Every agent is reachable the same way, so pipelines compose without special cases. |
| **Abstraction / polymorphism** | One route parameter instead of two implementations. Two code paths for "safe" and "real" drift until a fudge factor is needed to reconcile them — that number is the cost of having two. |

## IV. Observability — and its limits

| concept | mechanism |
|---|---|
| **Observability** | Every check prints the **count it resolved** and its **own blind spot**, every run. A silent clean pass and a silent empty pass must never look identical. |
| **Grounding** | Verify against the shipped instrument — the binary's own symbol table, `lsof`, `ps`, `--porcelain` — never against documentation. Every wrong verdict in one measured day came from docs or memory; every verdict that held came from an instrument. |
| **Cybernetics (self-regulating loops)** | Budgets are **ratchets**: they only move down, and raising one must name what was added and why. A threshold that drifts upward silently is not a bound. |
| **Shadow validation** | A new check must (1) fail on a planted defect and (2) sweep the entire existing tree clean before it is trusted. Sensitivity proves nothing about specificity. |
| **Contextual drift** | Always-loaded instructions are metered and budgeted separately from lazily-loaded bodies. A description is paid on every request; a body is not. **An unused cluster is a subscription.** |

## V. Minimalism

| concept | mechanism |
|---|---|
| **Parsimony (Occam's razor)** | The ladder, in order: needed at all? → already present? → standard library? → platform? → installed dependency? → one line? → only then the minimum new thing. |
| **Tree-shaking / dead-code elimination** | A symbol is private until a second module imports it. Exporting "in case" produced 30 unimported exports in one audit; one of them was a refuted implementation still callable — not dead code, a **trap**. |
| **Idling eviction** | Load reference material on demand through a routing table rather than preloading it. One router replaced fifteen always-on descriptions: the cost went from ~595 tokens per request to ~42. |
| **Payload minimalization** | Read version control terse: `--porcelain`, `--oneline`, `--stat` then a named path. Measured on one repository, same information: **94,247 B → 6,116 B**. |

## VI. Detection — the last resort

| concept | mechanism |
|---|---|
| **Heuristic hardening** | A check that fires on correct input gets switched off, and a switched-off check catches nothing. Prefer a **false pass** to a false alarm, and declare which way it is biased. |
| **Verifiability** | Judge on the **exit code**, never a line of output. One harness printed "54/54 pass" over seven real failures. |
| **Hyrum's Law** | Assume every observable behaviour will be depended on. Publish exit codes as interfaces; treat log prose as private. |
| **Wirth's Law** | A check too slow to run does not run. One sweep of 44 patterns over 811 files exceeded its timeout; a single alternation pass gave the same answer in 11 s. |

---

## The ordering rule, stated once

**Prevention → healing → detection.**

1. **Can the cause be deleted?** Then do that. A check that never fires because the fault is impossible beats one that fires and gets repaired.
2. **If not, can it be healed?** Only if the thing regenerates — a cache, an index, generated output. **Never heal a decision.**
3. **Only then detect.** And a detector nobody runs is a record of what went wrong, not prevention.

**The tell that you are in the wrong tier:** count how often each check fails. If one fails repeatedly,
it is reporting on its own cause or on itself — not on the system.
