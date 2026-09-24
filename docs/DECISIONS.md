# Decisions — where they actually live

This page offered an ADR template and a `docs/decisions/` directory. **Neither was ever used, and
meanwhile the real decision record accreted in three other places** — so the pointer described a
system that had been superseded rather than built. A router is what it should have been:

| kind of decision | where it is recorded, with its reason |
|---|---|
| a control this repository expects of GitHub, and why a gap stays open | [config/github-controls.json](../config/github-controls.json) — every `_*_note` field carries the measured cause |
| a Scorecard check we cannot raise, and whether that is owner action or structural | [docs/CERTIFICATION.md](CERTIFICATION.md) |
| a language considered and refused, with the trigger that would change the verdict | [languages/ATLAS.md](../languages/ATLAS.md) |
| a concept adopted, and the mechanism that implements it — or that none does | [docs/ENGINEERING-CONCEPTS.md](ENGINEERING-CONCEPTS.md) |
| what a version changed | [docs/VERSIONING.md](VERSIONING.md), one line per version |
| why an instrument cannot prove something, and who closes it | `atlas.yaml/instruments`, rendered into the README table |

**The rule that replaced the template:** a decision is recorded where the thing it decides lives,
in the field or file a reader is already looking at — not in a parallel directory they have to know
to visit. A rejection is worth as much as an adoption, because it stops the same proposal arriving
twice.
