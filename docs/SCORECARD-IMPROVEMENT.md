# OpenSSF Scorecard

**Repository contract: v3.61.0**

Scorecard is an external signal, not proof that a repository is secure. Its results and the
repository's settings can change independently of this page.

- [Certification](CERTIFICATION.md) explains the checks, their limits, and possible improvements.
- [GitHub controls](../config/github-controls.json) declares the intended settings and score floors.
- [GitHub finalization](GITHUB-FINALIZATION.md) explains how to compare those declarations with
  live settings and distinguish configured controls from enforcement.

The audit reads the public Scorecard result when available and reports an unavailable result as
unknown. Inspect the current ruleset and its complete parameters before changing it: an incomplete
replacement can remove required checks or other controls.
