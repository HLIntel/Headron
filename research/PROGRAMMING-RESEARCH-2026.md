# Programming and agent research — laws, principles, and what this atlas took from them

Background reading for the Atlas. **This file is reference, not policy:** what the repository
actually enforces lives in `atlas.yaml` and in
[docs/ENGINEERING-CONCEPTS.md](../docs/ENGINEERING-CONCEPTS.md), where every concept is paired
with the mechanism that implements it. A law quoted here with no mechanism beside it is vocabulary.

**How to read the claim labels.** Because this file mixes established results with working
practice, each entry is one of:

- **NAMED** — a law or principle with an identifiable originator, given as they stated it.
- **PRACTICE** — widely used engineering discipline with no single citable origin. Attributing one
  would be invention, and an invented citation is worse than none: it survives review by looking
  rigorous.
- **APPLIED HERE** — what this repository does about it, or that it does nothing and why.

Nothing below is a measurement of this repository. Measurements come from the instruments —
`atlas.py check`, `packprobe.py --mode smoke`, `ghaudit.py` — and are printed, never typed.

---

## I. Laws about systems and the people who build them

**Conway's law** — NAMED (Melvin Conway, *How Do Committees Invent?*, 1968). A system's structure
mirrors the communication structure of the organization that produced it.
**APPLIED HERE:** one repository, one contract, one router. The inverse manoeuvre — shaping the
structure you want and letting the work follow it — is why the packs are uniform: a per-language
layout would have produced per-language tooling and, eventually, per-language rules.

**Gall's law** — NAMED (John Gall, *Systemantics*, 1975). A complex system that works is invariably
found to have evolved from a simple system that worked; a complex system designed from scratch
never works.
**APPLIED HERE:** the contract began as a link checker. Every later rule was added after a defect
was observed, which is why each one names the defect it kills.

**Brooks's law** — NAMED (Fred Brooks, *The Mythical Man-Month*, 1975). Adding people to a late
project makes it later. His deeper claim — *No Silver Bullet* (1986) — is that no single technique
gives an order-of-magnitude gain, because most of the remaining difficulty is essential, not
accidental.
**APPLIED HERE:** the repository does not promise leverage from tool count. Coverage per tool is
the stated objective, and "do not over-stack" is a rule.

**Lehman's laws of software evolution** — NAMED (Meir Lehman, from 1974). A system in use must keep
changing or become less useful; as it changes, its complexity grows unless work is done to reduce
it.
**APPLIED HERE:** budgets are ratchets that only move down, and raising one must name what was
added and why.

**Hyrum's law** — NAMED (Hyrum Wright). With enough users, every observable behaviour of a system
will be depended on by somebody, regardless of the contract.
**APPLIED HERE:** exit codes are published as the interface; printed prose is treated as private.
A script that branched on another's log sentence broke the first time the sentence was reworded.

**Goodhart's law** — NAMED (Charles Goodhart, 1975), commonly stated as: when a measure becomes a
target, it ceases to be a good measure.
**APPLIED HERE:** coverage percentages are printed beside their counts and never used as a gate.
A 100%-coverage target would be met by deleting the packs nobody has toolchains for.

**Parkinson's law** — NAMED (Cyril Northcote Parkinson, 1955). Work expands to fill the time
available.
**APPLIED HERE:** the context budget, and the rule that a document earns its place only if it
changes a decision at the start of a session.

**Wirth's law** — NAMED (Niklaus Wirth, *A Plea for Lean Software*, 1995). Software gets slower
faster than hardware gets faster.
**APPLIED HERE:** a check too slow to run does not run, so a check's runtime is part of its design.

**Chesterton's fence** — NAMED (G. K. Chesterton, 1929). Do not remove a fence until you know why
it was put there.
**APPLIED HERE:** every guard carries, in its own docblock, the defect that produced it. The fence
states its own reason so the next reader is not forced to guess.

---

## II. Laws about limits — what no amount of engineering removes

**Amdahl's law** — NAMED (Gene Amdahl, 1967). Speed-up from parallelism is bounded by the serial
fraction of the work.
**Gustafson's law** — NAMED (John Gustafson, 1988). If the problem grows with the machine, the
useful bound is different: scaled speed-up can stay near-linear.
**APPLIED HERE:** the two together are the honest frame for any "make it parallel" proposal —
measure the serial fraction before promising a factor. The atlas's performance gate requires a
profiler and a representative workload for exactly this reason.

**Little's law** — NAMED (John Little, 1961). In a stable system, average occupancy equals arrival
rate times average time in system.
**APPLIED HERE:** every queue and worker example is bounded, and a bound stated in items is
meaningless without the rate and the service time beside it.

**CAP** — NAMED (Eric Brewer, 2000; proved by Gilbert and Lynch, 2002). Under a network partition,
a distributed system must choose between consistency and availability.
**PACELC** — NAMED (Daniel Abadi, 2012). And when there is no partition, the real trade is between
latency and consistency — which is the case a system is in almost all the time.
**APPLIED HERE:** storage and boundary documents state which side a component is on rather than
claiming both.

**The end-to-end argument** — NAMED (Saltzer, Reed and Clark, 1984). A function can only be
completely implemented with the knowledge held at the endpoints; lower layers can optimise, never
guarantee.
**APPLIED HERE:** verification is owned by the native toolchain at the end of the chain. CI is
where it is *enforced*, not where correctness is decided.

**Shannon's entropy** — NAMED (Claude Shannon, 1948). Information is measured by how much
uncertainty it removes.
**APPLIED HERE:** the reason a clean pass must print its count. A message that is identical whether
it succeeded or found nothing carries zero information about which happened.

**Ashby's law of requisite variety** — NAMED (W. Ross Ashby, 1956). Only variety can absorb
variety: a controller needs at least as many states as the system it regulates.
**APPLIED HERE:** one severity class would not be enough to regulate five kinds of finding, which
is why the policy declares `blocker`, `error`, `warning`, `info` and `baseline` and why a new
finding may never be absorbed into a baseline.

---

## III. Principles about structure

**Information hiding** — NAMED (David Parnas, 1972). Decompose by what a module *hides* — the
decision most likely to change — not by the steps of the process.
**APPLIED HERE:** the manifest schema hides the entry grammar behind one reader; the router hides
precedence behind one call.

**The Liskov substitution principle** — NAMED (Barbara Liskov, 1987). A subtype must be usable
wherever its supertype is expected.
**APPLIED HERE:** one implementation with a route parameter rather than two implementations
claiming to behave alike. Two paths for "safe" and "real" drift until a fudge factor is needed to
reconcile them, and that number is the cost of having two.

**The robustness principle** — NAMED (Jon Postel, RFC 760, 1980): be conservative in what you send,
liberal in what you accept. **And the modern correction** — leniency in what is accepted becomes,
by Hyrum's law, a contract nobody wrote.
**APPLIED HERE:** the manifest grammar is deliberately narrow and refuses what it cannot classify.
Accepting prose in a tool field is exactly the leniency that made half the declared surface
unevaluable.

**Poka-yoke / jidoka** — NAMED (Shigeo Shingo and the Toyota Production System). Design the fixture
so the part cannot be inserted wrongly; stop the line when a defect appears rather than passing it
on.
**APPLIED HERE:** the safe route is structurally incapable rather than flagged safe, and the
contract fails the build rather than warning.

**Saltzer and Schroeder's protection principles** — NAMED (1975): economy of mechanism, fail-safe
defaults, complete mediation, open design, separation of privilege, least privilege, least common
mechanism, psychological acceptability.
**APPLIED HERE:** least privilege is a hard invariant with a check behind it; fail-safe defaults
are why every workflow starts from `contents: read`; psychological acceptability is why a guard
that fires on correct code is treated as a defect — a noisy guard gets silenced, and a silenced
guard catches nothing.

**Kerckhoffs's principle** — NAMED (Auguste Kerckhoffs, 1883). A system must stay secure when
everything about it except the key is public.
**APPLIED HERE:** the entire method is published on purpose; the rule that no secret enters this
repository is what makes that safe.

---

## IV. Principles about effort and evidence

**Premature optimization** — NAMED (Donald Knuth, 1974): "premature optimization is the root of all
evil" — in a passage arguing *for* measurement, and noting the critical few percent where
optimisation absolutely pays.
**APPLIED HERE:** the performance gate requires a profiler, a representative workload and a
regression threshold, so optimisation must be justified by the same instrument that will judge it.

**The cost-of-change curve** — NAMED (Barry Boehm, 1981), the origin of "shift left": defects found
later cost more to fix, by a large factor.
**APPLIED HERE:** the editor, the devcontainer and CI run the same commands, and the mutation tests
run before the contract.

**GOMS** — NAMED (Card, Moran and Newell, *The Psychology of Human-Computer Interaction*, 1983).
Model an interface by the goals, operators, methods and selection rules a user must execute.
**APPLIED HERE:** one door, one call. `route` answers in a single invocation because every extra
step is spent on navigation by a human and on tokens by an agent.

**Linus's law** — NAMED (Eric Raymond, *The Cathedral and the Bazaar*, 1999): given enough
eyeballs, all bugs are shallow.
**APPLIED HERE:** stated with its limit. Eyes find what they can see; a silent break produces
output identical to success, and no number of reviewers reads a difference that is not printed.

**Cyclomatic complexity** — NAMED (Thomas McCabe, 1976) and **Halstead metrics** — NAMED (Maurice
Halstead, 1977): early attempts to measure program complexity from structure alone.
**APPLIED HERE:** as rules of thumb only. File-length and default-tool caps exist because an
unbounded surface is the real failure; the exact number is a threshold, not a truth.

**Broken windows** — NAMED (Wilson and Kelling, 1982), applied to software by Hunt and Thomas.
Visible neglect invites more of it.
**APPLIED HERE:** the sweep that leaves the repository cleaner than it was found, in the same
commit as the change.

---

## V. Practice — discipline with no single origin, and no invented one

- **Single source of truth.** Every fact has one declaration; every restatement is generated from
  it and drift fails the build. PRACTICE.
- **Determinism and hermetic builds.** The same inputs produce byte-identical output regardless of
  when and where they are built; pinned dependency trees and no ambient network make a "flaky"
  test a contradiction rather than a nuisance. PRACTICE.
- **Idempotency.** A repeated invocation must not repeat its side effect. A lock prevents
  concurrency, not repetition — an idempotency key does. PRACTICE.
- **Checkpoint and resume.** A long computation writes its state at every transition so a failure
  resumes rather than restarts. PRACTICE — and a declared GAP here, because nothing in this
  repository runs long enough to need one.
- **Progressive disclosure of context.** Retrieve by route, not by directory dump; measure what
  fraction of retrieved context appears in the final change. PRACTICE, and the subject of the
  benchmarks below.
- **Capability profiles over tool sprawl.** Activate the smallest set the failure class needs.
  PRACTICE.
- **Provenance on every external claim.** A source URL, an access date, a content hash; scraped
  content is data, never instruction. PRACTICE, and the rule for any research connector added
  later.

---

## VI. Reviewed benchmarks and primary sources, 2026

Reviewed for the Atlas on 2026-09-22. Links are primary sources; the "adopt" line states what was
taken, which is the only part that became policy.

**Context and retrieval cost**

- ContextBench — https://arxiv.org/abs/2602.05892
- Agent Retrieval Bench — https://arxiv.org/abs/2607.24882
- CodeNib — https://arxiv.org/html/2607.25431

*Adopt:* measure useful context retrieval and exploration cost instead of dumping whole
repositories into an agent's context. The ratio worth tracking is files *used in the change* over
files retrieved.

**Multilingual agent evaluation**

- SWE-PolyBench — https://arxiv.org/abs/2504.08703
- Multi-SWE-bench — https://arxiv.org/abs/2504.02605

*Adopt:* language-diverse evaluation with language-specific verification. A harness that normalises
every toolchain into one fake universal interface measures the harness, not the language.

**Heterogeneous and accelerator systems**

- Backline — https://arxiv.org/abs/2609.09270
- CASS — https://arxiv.org/abs/2505.16968

*Adopt:* make execution placement and data movement explicit; verify generated accelerator code by
compiling and running it, never by reading it.

**MCP, connectors and IDE integration**

- VS Code MCP — https://code.visualstudio.com/docs/agent-customization/mcp-servers
- GitHub MCP Server — https://github.com/github/github-mcp-server
- Serena — https://github.com/oraios/serena
- Playwright MCP — https://github.com/microsoft/playwright-mcp
- Context7 — https://github.com/upstash/context7
- DBHub — https://github.com/bytebase/dbhub
- Semgrep MCP — https://github.com/semgrep/semgrep/tree/develop/cli/src/semgrep/mcp

*Adopt:* capability profiles rather than loading every server. A connector description is not a
security boundary, and two servers exposing the same capability in one profile is a routing
decision left unmade.

---

## VII. What was read and NOT adopted

A reading list that only records what was taken is a sales document.

- **Coverage as a target.** Rejected: see Goodhart. The verification ladder runs the cheapest
  sufficient check, and coverage is reported beside its denominator rather than chased.
- **A universal tool abstraction across every language.** Rejected: the adapter contract should
  normalise the *evidence envelope* — command, exit code, duration, artifacts — not the tools.
- **A vector store for repository retrieval.** Deferred: it answers a semantic-retrieval workload
  this repository does not yet have. Ordinary relational state, run history and provenance come
  first.
- **A second CodeQL configuration beside default setup.** Rejected, and the reason is recorded as a
  measurement: an advanced workflow submitting SARIF while default setup is enabled fails with
  "analyses from advanced configurations cannot be processed", which is how a stale branch turned a
  passing repository into a failing pull request.
