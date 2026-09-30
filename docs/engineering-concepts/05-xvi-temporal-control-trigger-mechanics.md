# Engineering concepts, each paired with a mechanism — part 5 of 7

[Index](../ENGINEERING-CONCEPTS.md)

## XVI. Temporal control, trigger mechanics and self-preservation

The tier that diagnosed the loudest problem in this system: **the detectors were level-triggered.**

| concept | mechanism |
|---|---|
| **Edge-triggered vs level-triggered guards** | **The diagnosis, and the fix.** Measured over one day: one check logged the same failure **eight** times and another **seven**, and not one was a new fault — a level-triggered detector re-fires for as long as the condition holds, which buries the transition in repetition and trains the reader to skim. The ledger now marks `NEW FAIL`, `still failing`, `RECOVERED`, or nothing at all. **The transition is the information; the repetition is noise.** |
| **Debounced / throttled evaluation** | The same insight applied to cost: a memoised check keyed on `path + mtime + size` skips work whose input cannot have changed — throttling by content rather than by clock. |
| **Dead man's switch (async interrupt hook)** | Every agent probe carries a budget and dies at it, and a check asserts that no agent process outlives its lock. Three were found alive 6–17 minutes past their runs; one held a port declared to another service. **A hung agent looks exactly like a working one from outside, so the timer must be external.** |
| **Jittered exponential backoff** | Partially applied: a deadline retries once at double the budget, a quota refusal never retries. **Jitter is absent** and that is honest — one operator on one machine has no thundering herd, but siblings sharing one credential are a real herd of a smaller kind. |
| **Token bucket vs leaky bucket** | The per-agent lock is a bucket of exactly one token that does not refill until released: bursts are refused, not queued, so a caller learns immediately instead of waiting. |
| **Backpressure propagation** | Locks fail closed with a distinct exit code, so an upstream caller can branch on *busy* rather than guess from a timeout. |
| **Bounded recursion / context budgeting** | Always-loaded instruction budgets are **ratchets** that only move down, metered per source, with session cost separated from per-request cost. Raising one must name what was added and why it must be read every session. |
| **Graceful degradation (load shedding)** | The healer sheds exactly the right work: it repairs what regenerates and **refuses** what needs judgement, rather than degrading into guessing at config values. |
| **Saga pattern (compensating transactions)** | Two real instances. Config application: apply → restart → read the application's own verdict → **revert on rejection**, with the compensating action defined before the forward one. And salvage-before-removal: a worktree held the only copy of a line, so the extraction was committed in its own commit *before* anything was deleted. **Never let the destructive step and the preserving step share a failure mode.** |
| **Adaptive heartbeat / dynamic cadence** | **PARTIAL.** A fixed 4-hourly schedule plus on-demand runs, with no adaptation to load. A cheap check could run per change and an expensive one back off when quiet — named as undone rather than implied. |
| **Phased duty cycling** | Checks run on a 4-hourly schedule plus on demand, not in a poll loop — the cheap ones are cheap enough to run per change, the expensive ones are scheduled. |

**Why this tier mattered most:** every other improvement made the system *more* correct. This one made it
*readable* — and an unreadable detector is a silenced one, which is the failure mode all the others feed.

---


## XVII. Overfitting, pacing, and not repeating yourself — applied to this document's own system

This tier is the sharpest criticism of the work that produced this file, so the evidence is included
rather than the definitions.

| concept | what the measurement says |
|---|---|
| **Premature generalization ("framework" trap)** | Present here: a dispatcher, a registry, a healer and a ledger were built before a second operator or a second machine existed. Defensible only because each solves a defect that actually occurred; the moment one does not, it is a framework for an audience of one. |
| **Speculative abstraction** | The honest example: a registry of paused things, complete with review dates and a validator, built for six rows. Whether that is foresight or speculation depends entirely on whether row seven ever appears. |
| **Architectural overfitting** | Twenty checks built in one day. Honest audit of prior sightings: one had **four** real instances before it existed (justified), one had **three** (justified), one had **two** (borderline), one was built on **one** condition that then fired eight times, and **two were built from a CONCEPT with zero prior defects.** That last category is the definition of the trap — a detector for a failure that had never occurred here. |
| **One-in, one-out deletion metric** | **177,609 insertions against 174 deletions in one repository in one day.** The metric says high velocity should mean *less* total code. This ratio says the opposite, and no amount of per-file justification changes the aggregate. |
| **Rule of three** | Partially honoured, and the exceptions are now named. The checks with 3–4 prior sightings earned their place; the ones with 0–1 did not, and were built because a concept was persuasive rather than because a defect recurred. |
| **YAGNI** | Violated in at least two places — and the violations are documented above rather than quietly kept. |
| **Goodhart's Law** | The clearest self-inflicted case: **"N guards passing" became a target.** A count of passing checks measures the checks, not the system. Two of them have never reported a fault on the real tree outside their own mutation tests, so the count was partly measuring my own output. |
| **Occam's razor / parsimony** | The defensible core is small: apply-and-verify-with-rollback, one declaration per fact, verify against the instrument, prevention before healing before detection. Most of the value is in those four; the rest is enforcement scaffolding around them. |
| **Regression test coupling** | **Honoured consistently.** Every check was mutation-tested against a planted defect before being trusted, and several were rewritten when the test revealed the check — or the test — was wrong. |
| **Blameless post-mortem** | Structurally enforced by writing every failure into the code that caused it: each check carries its own history of being wrong — the exact-match failure, the SIGPIPE, the roster that reported intent rather than output. **A defect recorded at the site of the defect cannot be re-litigated as someone's fault; it is just the file's history.** |
| **Five whys / root-cause analysis** | Worked, and one chain is worth keeping: a port collision → a leaked process → a probe that signalled only the parent → a package fetched per launch → a package-manager policy permitting exactly one package. **Five levels, and the fix was at the fifth.** |
| **The 15-minute rule (stop rushing)** | **Violated repeatedly.** Three tests passed on the first attempt and were wrong: a window smaller than the defect, a threshold below the planted value, a file outside the roster. Each would have been caught by pausing to ask *"could this test have failed?"* — the cheapest question available and the one most often skipped. |
| **Linter as enforcer / pre-commit** | Partially in place: checks run on a schedule and on demand, but not at edit time. Named as the next shift left, still undone. |

**The verdict this tier forces:** the system is defensible where a defect recurred and speculative where a
concept was persuasive. **Two detectors should probably be deleted, and that is the owner's call, not the
builder's** — recorded here so the question is asked rather than forgotten.

---


## XVIII. Formal foundations — and the two that change a decision here

Most of this tier is background. Two of them are directly load-bearing, and one is a formal restatement
of a rule already earned the hard way in quantitative work.

| formulation | where it binds |
|---|---|
| **Hoare triple — `{P} C {Q}`** | The config-application gate **is** a Hoare triple, and naming it that way makes the missing piece obvious. `P`: a known-accepted snapshot exists. `C`: write the candidate, restart, read the application's own loader verdict. `Q`: either the new config is accepted, or the accepted snapshot is restored. **The postcondition is what makes the operation safe to attempt** — without a guaranteed `Q`, every config edit is a gamble. Generalise it: no destructive step without a stated postcondition that holds on both branches. |
| **Kolmogorov complexity — `K(s) = min{|p| : U(p) = s}`** | **This is a formal statement of the overfitting rule.** A model that needs many parameters to describe its data has high `K` relative to the data — it is *memorising*, not compressing, and memorised noise does not generalise. It gives the discipline a precise form: **prefer the hypothesis with the shortest description that still reproduces the observation**, and treat a parameter added after seeing the outcome as part of the description length. It also bounds refactoring: code that cannot be made shorter without losing behaviour is already minimal, and further "cleanup" is churn. |
| **Master theorem — `T(n) = aT(n/b) + f(n)`** | The honest model for fan-out. `a` subproblems, and `f(n)` is the **combine** cost — reading, verifying and reconciling what came back. Measured here: five agents answered in parallel in minutes, but the combine step (checking each claim against the instrument) was serial and dominated. **When `f(n)` dominates, more parallelism buys nothing.** |
| **Amdahl vs Gustafson** | The serial fraction in agent work is the *human or orchestrator reading the results*. Amdahl bounds it: parallel agents cannot speed up what only one reader can verify. Gustafson's escape is real but specific — spend added capacity on **deeper verification of the same question**, not on more opinions about it. |
| **Shannon entropy — `H(X) = -Σ P(x)log₂P(x)`** | Two uses. Detecting formulaic phrasing is an entropy argument: the flagged patterns are *low-entropy* — highly predictable given the context — which is exactly why they read as machine-written. And it bounds telemetry: a ledger row carrying a verdict, a duration and a count is near the useful minimum; adding prose to it adds bytes, not information. |
| **Curry-Howard — `Programs ≅ Proofs`** | The formal reason a type system beats a runtime check, and the formal reason shell scripts cannot have one. With no compiler to carry the proof, the substitute is an assertion at every boundary that **prints what it resolved** — a proof obligation discharged at runtime and made visible, since it cannot be discharged at compile time. |
| **PACELC** | Covered above; restated formally here: with no partition, the trade is Latency vs Consistency, and a cache is that trade made explicit. |

### For quantitative work specifically

Three of these bear directly on trading analysis, where the cost of being wrong is money rather than churn:

- **Kolmogorov** formalises why a strategy with many tuned parameters fails forward: its description length is
  large relative to its sample, so it encodes noise. **Report description length alongside performance** —
  a rule needing six conditions on 14 observations has effectively memorised them.
- **Shannon** bounds how much signal a channel can carry. A market that is efficient-minus-fee at the ask
  has, by construction, little extractable information at that price; a strategy claiming otherwise is
  claiming a channel capacity the measurement does not support.
- **Master theorem / Amdahl** govern backtest cost honestly: parallelising a grid search does not reduce
  the number of hypotheses tested, and **the count of hypotheses is what inflates false positives.**
  Faster search makes overfitting cheaper to commit, not less likely.

---
