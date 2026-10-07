# Programming and agent research — laws, principles, and what this atlas took from them — part 3 of 3

[Index](../ENGINEERING-RESEARCH.md)

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
  directly. This atlas routes both kinds, and [languages/ATLAS.md](../../languages/ATLAS.md) records
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
- **A system-design pattern catalogue as a rule source** — the System Design Primer
  (https://github.com/donnemartin/system-design-primer, CC BY 4.0). Read in full and scored
  *already exists · refuted · worth building*; nothing was built, because every pattern it teaches
  already has a mechanism here. Availability in sequence: the blocking shell hooks were timed, the
  interpreter start dominates each one and they run concurrently, so a chain costs its slowest hook,
  not their sum. Backoff with decorrelated jitter that yields to a server's `Retry-After`: the
  resilience module. Write-behind's loss window: pushed is not landed. Refresh-ahead and eventual
  consistency: the staleness walk and the handoff drift check. Denormalised read copies: generated
  blocks with a check that fails on drift. The safe and idempotent verb table: the MCP tool
  annotations. The "Disadvantages" line under every pattern: `does_not_prove` and `closed_by`. Its
  latency and powers-of-two tables are refused: typed figures from another decade's hardware, which
  rule 1 forbids. **One input carried forward:** a partitioned suite balances shards by measured
  per-case wall time, longest first, never by case count — the slowest shard sets the wall. It
  waits on the sharding item's own control run.
- **The opencode agent harness, read for its agent-loop mechanisms.** One adopted: its snapshot
  store keeps work aside without a shared stack, which showed that the shell guard's advice to set
  edits aside on the stash stack was itself a hazard, since every worktree shares that stack and a
  sibling session can pop it. The guard reasons now name a WIP commit or a ref-free stash object.
  Already here: retry with decorrelated jitter, output truncation with a bounded spill directory,
  permission last-match ordering, compaction pruning, subagent deny inheritance. Refuted by
  measurement: a repeated-identical-call breaker (no qualifying run in a fortnight of transcripts,
  with a planted run caught as the control) and a post-edit parse hook (parse errors after an edit
  were rare and the next call already caught most). Not applicable: fuzzy edit matching and its
  disproportionate-match guard, since the edit route here matches exactly. Needs an instrument
  before it is a proposal: a glossary of terms to avoid. Its interface layer was judged as compact,
  functional and fast, and yielded nothing new: tool output collapsing, a context-share readout
  and per-gate one-line verdicts already exist on the surfaces here, and paced streaming and
  transcript caps answer a chat surface this repository does not have.
