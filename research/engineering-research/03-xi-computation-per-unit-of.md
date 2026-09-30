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
