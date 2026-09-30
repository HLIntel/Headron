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

## Parts

- [Part 1](engineering-research/01-i-laws-about-systems-and.md): I. Laws about systems and the people who build them · II. Laws about limits — what no amount of engineering removes · III. Principles about structure · IV. Principles about effort and evidence · V. Practice — discipline with no single origin, and no invented one
- [Part 2](engineering-research/02-vi-reviewed-benchmarks-and-primary.md): VI. Reviewed benchmarks and primary sources, 2026 · VIII. Systems built outside the Anglophone tooling default · IX. Typed decision engines — reviewed rather than harvested · IX-b. A three-way harvest, judged rather than absorbed · X. Curated lists — a source, never a dependency
- [Part 3](engineering-research/03-xi-computation-per-unit-of.md): XI. Computation per unit of hardware, and the discipline compression needs · VII. What was read and NOT adopted
