# Programming and agent research — laws, principles, and what this atlas took from them — part 2 of 3

[Index](../ENGINEERING-RESEARCH.md)

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
kaizen. Already load-bearing in [ENGINEERING-CONCEPTS](../../docs/ENGINEERING-CONCEPTS.md); noted here
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
