# Engineering concepts, each paired with a mechanism — part 4 of 7

[Index](../ENGINEERING-CONCEPTS.md)

## XV-a. Anti-break — prevent the break, then make silence impossible

**The expensive break is not the loud one. It is the one whose output is identical to success.**
Everything below was found on one machine; each row names the sighting, then the mechanism that
makes that shape unrepresentable rather than merely detectable.

### Tier 0 — the break cannot be expressed

The only tier that scales. A fault that cannot be represented needs no guard, no retry and no alert.

| the break | why it was silent | the mechanism that removes it |
|---|---|---|
| A mutation fixture hard-typed `1.1.0` while `VERSION` moved to `1.2.0`. It indented a line the check no longer read — **the case went green while planting nothing.** | A passing test and a test that tested nothing print the same word: `ok`. | **DERIVE, NEVER TYPE.** The fixture reads `VERSION`. One number, one declaration; a second copy goes stale the first time either is edited. |
| A rate-limit latch assigned `latched_until = ?`, so a 429 rewrote a 402's day-long latch down to 60 s. | Both are "a latch was set". Nothing distinguishes forward from backward. | **A MONOTONIC WRITE.** `MAX(latched_until, excluded.latched_until)` — the latch is structurally incapable of moving backward, so no caller can get the order wrong. |
| A safe/paper route that merely *sets a flag* can be flipped by any caller. | The flag and the real route share one code path. | **STRUCTURAL INCAPABILITY.** The safe route loads no key and takes no nonce. There is nothing to set wrongly. |

### Tier 1 — the break can happen, but it cannot be silent

When tier 0 is unavailable, the requirement is exact: **the failure output must differ from the
success output, and the exit code must differ too.** Either alone has been observed to fail.

| the break | how it stayed silent | the mechanism |
|---|---|---|
| `if (!j.choices) return false` treated an aggregator's `{"error":{…503…}}` inside an HTTP 200 as a valid answer. Six chain members were never tried. | The status said 200. The router branched on the status; the body held the failure. | **BRANCH ON THE BODY, NEVER THE STATUS.** The status is the aggregator's rendering; the body is the identity. |
| `make status` printed `0/12 loaded` and **exited 0**, because its only roster guard was called with `\|\| true`. | The verdict was computed and thrown away. | **NEVER DISCARD AN EXIT CODE.** Assert the exit code in the test, not the presence of the command in the Makefile. |
| An overfitting guard correctly refused a malformed row; three of five callers wrapped it in `except Exception: pass`. | The refusal existed and reached nobody. | **A GUARD'S REFUSAL IS OUTPUT.** Catch the specific exception and print it; never bare-pass a guard. |
| `pytest scripts/atlas_test.py` reports "no tests ran" and **exits 0**. | Zero tests and all tests passing are the same exit code. | **ASSERT THE COUNT, NOT THE PASS.** The harness prints `24/24` and asserts its own case count. |
| A guard suite printed a clean sweep whether it had checked 19 files or 0. | A silent clean pass and a silent empty pass are the same output. | **PRINT WHAT IT RESOLVED TO, EVERY RUN**, and assert it against something independent. *(measured at v1.2.0)* |
| A backup reported `Repository not found` for a live repo for weeks. | A 404 renders "gone" and "this identity cannot see it" identically. | **NAME THE IDENTITY IN THE FAILURE.** Print which credential was refused, not just what was missing. |

### Tier 2 — detect, and only then

A detector nobody runs is a record of what went wrong, not prevention. Two rules keep this tier honest:

- **Mutation-test every detector both ways.** Sensitivity — plant the defect, assert it fails. Specificity — sweep the whole real tree, zero findings, or every finding justified at the exemption. *Mutation testing proves sensitivity and says nothing about specificity*, and the reaction to a noisy guard is never to fix it, it is to silence it.
- **An exemption is a behaviour change.** It invalidates the test that asserted the old behaviour, and that test's next failure will be read as the guard being broken. Update the test in the same commit, and give the exemption its own case — the exemption that disarms a test is usually itself untested.

### The ordering, stated once

**Can the break be made unrepresentable? → Can it be made impossible to be silent? → Only then, detect it.**
A check added at tier 2 for a fault that tier 0 could have deleted is work that must be maintained forever.

**The tell that you are at the wrong tier:** the fix you are writing is a fudge factor reconciling
two code paths, an exemption list, or a retry. All three say the shape should have been removed
one tier up.

---

## XV-b. The classical laws — the five that were missing, and the eight already here

A 14-law set was proposed for harvest at v1.2.0. **Eight were already in this document** —
Goodhart, Conway, Hyrum, Demeter, Gall, Postel, the Rule of Three and the Law of Least Knowledge —
so adding them would have been duplication, which is the cheapest thing to add and the worst to
own. Only these five were genuinely absent. Each is paired with a mechanism here or marked as not
binding; a law with no mechanism beside it is vocabulary.

| law | how it binds here |
|---|---|
| **Chesterton's Fence** — *never tear down a fence until you know why it was put up* | **THE sharpest one, and it was worked live the day it was added.** `port-audit.sh` skips `expect=ondemand` rows; a mutation test asserting the opposite failed 1-of-74 and the GUARD was blamed in writing. The fence had been put up the day before, because colima's `lima-hostagent` legitimately reparents to init and was being faulted on a healthy machine. **The mechanism that saved it: the exemption carried its reason INLINE**, so the fence explained itself in thirty seconds instead of being torn down. An exemption without its reason is a fence with no sign on it — and the next reader removes it. |
| **The 90-90 Rule** (Cargill) — *the last 10% of the code takes the other 90% of the time* | Binds hard, and the local name for it is **the last wire**. Surveying two live desks produced the same shape three times in one report: a `halt` table with a reader and no writer; a roster guard whose exit code is discarded by `\|\| true`; an overfitting guard whose refusal is swallowed by `except: pass`. Each defence was designed, built, measured — and left one wire short, while reading as covered. **The second 90% is not polish, it is connection**, which is why shipping-and-parity §1 says *build it, wire it, or delete it; never the middle state.* |
| **Brooks's Law** — *adding manpower to a late project makes it later* | **Transformed, not inherited.** Sub-agents need no onboarding, so the classical cost is absent — but the cost that replaces it is real and larger: **every agent claim must be re-anchored to the raw instrument before it can be acted on.** Measured at v1.2.0 over five agents in one session: two returned findings that were acted on directly, one *corrected a conclusion this operator had already written down*, and two returned expired timers with nothing new. The scaling limit is not communication paths, it is **verification bandwidth** — one operator can only re-derive so many claims. See the Chaitin-Kolmogorov row above: never verify one agent against another agent's summary. |
| **Kernighan's Law** — *debugging is twice as hard as writing, so code at your cleverest is undebuggable* | Binds as a **comment policy**, not a cleverness policy. The dense one-liners here are deliberate and survive because the docblock above them records what was measured, what was refuted, and what breaks if the next reader "fixes" it. The rule as applied: **you may write it at your cleverest if you also write down why** — clean-go's *document WHY, not HOW*. Where that note is missing, the cleverness is a defect regardless of whether the code is correct. |
| **Law of Triviality** (bike-shedding) — *disproportionate weight to trivial matters* | **NOT APPLICABLE in its classic form** — there is no committee here. The polarity-flipped version does bind and is worth naming: with an agent, **the trivial thing gets done instantly, which makes it tempting to keep doing trivial things.** A session can produce twenty clean cosmetic commits and never touch the unwired halt table. The counter is the ranked survey: money and data-loss first, cosmetics last, and the ranking written down BEFORE the work starts. |

**The one that should change behaviour tomorrow:** the 90-90 rule, under its local name. Every survey
of this system's own projects finds defences that are built and unconnected, and they read as coverage
from the roster. **Before building a new check, ask which existing one is one wire short.**

---
