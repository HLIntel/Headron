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
A total-coverage target would be met by deleting the packs nobody has toolchains for.

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

Reviewed for the Atlas at contract v1.0.0 and extended at v1.3.0. Links are primary sources; the "adopt" line states what was
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

## VIII. Systems built outside the Anglophone tooling default

The default tool list in most English-language engineering writing omits a body of production
systems built at very large scale elsewhere. They are read here for what they demonstrate
**mechanically**, not for where they were built, and each row states what transfers.

**CloudWeGo — ByteDance** (https://github.com/cloudwego · https://www.cloudwego.io/about/).
Kitex (Go RPC), Hertz (Go HTTP), Netpoll (non-blocking I/O built for RPC rather than general
sockets), Volo (Rust RPC), Sonic (JSON). Two mechanisms transfer:

1. **One set of code internally and externally, iterated as a whole** — the published repository
   *is* the internal dependency. This is the strongest organisational answer to the rule that two
   implementations of one thing drift until a fudge factor is needed to reconcile them.
2. **The runtime assumption was measured, not inherited.** Netpoll exists because Go's general
   `net` model did not fit the RPC workload. The transferable discipline is naming the assumption
   a framework makes about your workload before adopting it — not the specific library.

**Alibaba — Arthas, Sentinel, and the Java Coding Guidelines**
(https://github.com/alibaba/arthas · https://github.com/alibaba/Sentinel ·
https://github.com/alibaba/Alibaba-Java-Coding-Guidelines).

- **Arthas** attaches to a *running* production JVM with no restart and no code change, and is
  explicitly an observer that never suspends application threads. The principle is one this atlas
  already needs and states weakly: **observation must not perturb the observed system.** A probe
  that changes behaviour is a second system.
- **Sentinel** treats flow control, circuit breaking and load shedding as a first-class library
  rather than an afterthought bolted on at the proxy. Where a limit lives decides whether it is
  enforced or advisory — the same distinction as declared/configured/enforced here.
- **The Java Coding Guidelines ship WITH their linter** (IDE plugins and rule sets, the P3C
  project). That is the whole difference between a style guide and an enforced standard, and it is
  this repository's own rule restated: a rule with no executable form decays into a comment.

**Preferred Networks — Optuna** (https://github.com/optuna/optuna ·
https://arxiv.org/abs/1907.10902). Define-by-run search spaces: the space is expressed in the code
that consumes it rather than declared up front, with explicit pruning of unpromising trials and
distributed execution. What transfers is not the library but the shape — **a search that prints
its trial count and prunes explicitly** is auditable; one that reports only its winner is not. That
is the same requirement as printing K and the chance baseline beside any selected result.

**The Toyota Production System lineage** — jidoka (stop the line on a defect), poka-yoke, andon,
kaizen. Already load-bearing in [ENGINEERING-CONCEPTS](../docs/ENGINEERING-CONCEPTS.md); noted here
because "stop the line" is precisely what a required status check does, and because the lineage is
older and better evidenced than the software-native framings that restate it.

**What is deliberately NOT imported:** velocity culture, and structural-uniformity mandates
without the tooling that makes uniformity cheap. Uniformity pays here only because a router and a
contract enforce it for free; mandated by memo, it is a tax.

---

## IX. Typed decision engines — reviewed rather than harvested

A class of non-autoregressive decision engine answers TYPED questions — a label with
probabilities, an ordinal level on a rubric, a binary as a probability — over arbitrary text in a
single forward pass, routing by detected script and language to one checkpoint or another, with
the route overridable per call.

**The project that prompted this review is deliberately not named here.** What transferred is the
SHAPE, and a shape does not need an attribution to be argued with; a name would invite "just drop
it in", which is exactly what the last two paragraphs of this section refuse. Its published
latency and calibration figures are likewise omitted: a reported number without its source is not
evidence, and this repository does not keep numbers it cannot re-measure.

**Four things transfer, and they are why it was worth reading:**

1. **The System-1 / System-2 split is a routing decision, not a model preference.** A typed
   classification does not need a generative model. This atlas's ladder already starts at a
   deterministic router; the rung *above* it need not jump straight to autoregressive generation.
2. **A router must declare what it dispatched on.** `atlas.py route --json` reports `resolved_by`
   and `evidence` for this reason: a dispatch you cannot inspect cannot be debugged, and an
   explicit match and a lucky guess must not look alike.
3. **A declared token budget per option — and the failure mode past it.** When a fixed budget is
   shared across enumerated options, each label eventually receives a handful of tokens and the
   labels stop being DISTINGUISHABLE. **This is the sharpest available statement of a rule this
   repository keeps rediscovering: the options do not disappear, they stop being distinguishable,
   and nothing prints.** Adopted for any enumerated set an agent chooses from — a list that
   outgrows its budget is split or scored, never silently truncated.
4. **Calibration is part of the claim.** A score published without a calibration statement is a
   rendering of confidence, not a measurement of one.

**Two things do not transfer, and saying so now prevents a later "just drop it in":**

- **It cannot become a dependency of the contract.** The harness runs in a bare checkout with one
  dependency; a model checkpoint is not that. Any adoption is an OPTIONAL adapter behind a task
  profile, never a default.
- **Base checkpoints in this class score near chance on typed decisions zero-shot**, with
  fine-tuning required for production accuracy. Adoption therefore requires labelled data from
  this domain, which does not exist here. That is a prerequisite, not a caveat.

## IX-b. A three-way harvest, judged rather than absorbed

A research summary arrived covering three fields that share one word — *tunnel* — and nothing
else. Recording the split matters more than the material: **the failure mode of a harvest is
taking all of it**, because every item looks like an upgrade in isolation and the cost of the
wrong ones is paid later, by a reader who cannot tell which parts were argued for.

**TAKEN — structural code representation.** `atlasindex` declares its own limit: the dense arm is
TF-IDF, it matches vocabulary overlap, and a paraphrase sharing no terms is missed. The named
closer is now precise: a representation carrying **structure** — syntax tree and control flow —
rather than a bigger model. That is the same insight the shape gate already enforces by comparing
canonical ASTs with names and literals erased: two functions can share no tokens and be the same
control flow. `retrieval_policy/semantic_closer` records it, and `evaluation` records that a
replacement scorer is measured on a held-out set rather than adopted for being newer.

**TAKEN, NARROWLY — zero-copy and on-device inference as ROUTES.** Kernel-bypass data paths and
quantised on-device models are real domains with real packs behind them, so they are issue routes
pointing at the manual-memory packs. They are **not** harness work: this harness is a Python
contract and will never move a packet. Routing them is the whole of what this repository can
honestly do with them.

**DECLINED — tunnel boring, pipe jacking and embedded sensing in civil engineering.** Real
research, wrong sense of the word. It has no artifact here, no pack, no gate and no reader, and
adopting it would put a section in this document that exists only to look thorough. Recorded so it
is not proposed again with the reasoning lost.

**The rule this applied:** a harvest is scored against *already exists · refuted · worth building,
in this order · needs an instrument before it is even a proposal*. Most items land in the first
two, and a summary that yields one adoption and one refusal has been read correctly.

---

## X. Curated lists — a source, never a dependency

`academic/awesome-datascience`, `krzjoa/awesome-python-data-science` and `r0f1/datascience` are
useful as *search surfaces*. The harvest policy is the same one this repository applies to its own
rosters: **take an entry only when it answers a failure class the atlas already names, and record
the verdict where the decision is made.** Importing the list itself would add a roster that nobody
can verify, that narrows silently as the field moves, and that no instrument here can check —
three of the failure shapes this repository exists to prevent, adopted in one paste.

---

## XI. Computation per unit of hardware, and the discipline compression needs

The question this section answers: **what lets you do sophisticated work with almost no hardware,
and what does a claim about that have to state before it means anything?** Everything here is
REPORTED — external technique, not measured in this repository — and the last paragraph is the
part that transfers.

**Two kinds of density, routinely confused.**

- **Notational density** — a line expresses a page. The array and tacit family: APL and its
  descendants J, K, BQN and Uiua. The win is in what a reader can hold at once and in how few
  places a bug can hide; it is NOT automatically a win in memory or instructions.
- **Runtime density** — the machine underneath is small. Forth is the case that is hard to beat: a
  stack machine with threaded code, self-hosting in kilobytes, reaching memory and registers
  directly. This atlas routes both kinds, and [languages/ATLAS.md](../languages/ATLAS.md) records
  why one language from each family earned a route while the rest carry a trigger.

**The parameter-compression ladder, as engineering rather than folklore.** Reducing a model's cost
runs through several independent axes, and they compose in ways that are measured, not assumed:

- **Numeric width:** FP32 → FP16 or BF16 → INT8 → INT4 → ternary and binary. Each step halves or
  better, and each moves the failure mode: BF16 keeps FP32's exponent range and loses mantissa;
  INT8 needs a scale per tensor or per channel; below INT4 the interesting question stops being
  accuracy and becomes whether the hardware has an instruction for it at all.
- **Post-training quantization versus quantization-aware training** — the first is cheap and
  reveals which layers were fragile; the second costs a training run and usually recovers most of
  what the first lost.
- **Pruning** (structured or unstructured), **distillation** into a smaller student, and
  **low-rank decomposition** of weight matrices. These attack parameter *count* rather than
  parameter *width*, which is why they stack with the ladder above rather than replacing it.
- **Where it lands:** TinyML on microcontrollers, edge inference, sensor networks. The binding
  constraint is usually not FLOPs but memory bandwidth and the size of the weights that must live
  in on-chip RAM.

**THE PART THAT TRANSFERS, and the only part this repository enforces.** A compression result is
three numbers or it is rhetoric: **the metric, the baseline, and the hardware.** "4× smaller" with
no accuracy delta beside it, on unnamed hardware, against an unnamed baseline, is the same defect
as a coverage percentage with no denominator — and it is more persuasive, which makes it worse.
The atlas's `performance_change` gate already demands a profiler, a representative workload and a
regression threshold; a compression claim is a performance claim and takes the same three.

**AST canonicalization belongs in this section too**, because it is the same idea pointed at source
rather than weights: erase what does not carry meaning — names, literals, spacing, docstrings —
hash what remains, and two things that differ only in rendering become one thing.
`scripts/astshape.py` is that instrument here, and it found no duplicate structures and three blobs
on its first run, with the caps declared in `atlas.yaml/code_shape` as a ratchet.

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
