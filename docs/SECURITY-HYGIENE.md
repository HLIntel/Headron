# Security hygiene — the instruments, not a tool list

This page was a roster of fifteen tools, two of which this repository has never used, framed as
things to "study" — several of which have since been implemented and measured per check. A roster
that names what you do not run, beside a document that measures what you do, is the duplication
this repository refuses.

**What is actually enforced, and by what:**

| concern | mechanism | instrument |
|---|---|---|
| secrets never enter the tree | the absolute rule in [SECURITY.md](../SECURITY.md); secret scanning with push protection | `ghaudit.py` · a contract check that fails on a tracked `.env` |
| dependency vulnerabilities | Dependabot security updates; Dependency Review required for merge | the required `Dependency Review` check |
| dependency determinism | a hash-pinned lock installed with `--require-hashes` | `atlas.py check` asserts the pin sits inside the declared range |
| licence contamination | `deny-licenses` on Dependency Review | the same required check |
| static analysis | CodeQL default setup, two contexts required for merge | `ghaudit.py` compares the required-check list |
| supply-chain posture | OpenSSF Scorecard, with a floor **per check** | `ghaudit.py`, which reports any check below its floor |
| workflow privilege | every workflow starts from `contents: read`; no privileged triggers | the `least_privilege` hard invariant |
| action provenance | every action pinned to a commit SHA | [docs/CERTIFICATION.md](CERTIFICATION.md) records the measured defect this closed |

Per-check detail, what would raise each score, and what is structural rather than fixable:
[docs/CERTIFICATION.md](CERTIFICATION.md). Platform state is declared in
[config/github-controls.json](../config/github-controls.json) and compared by `ghaudit.py` — never
typed into prose, because prose cannot be compared by a machine.
