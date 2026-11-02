# OpenSSF — Scorecard and Best Practices

Part of [CERTIFICATION](CERTIFICATION.md).

## OpenSSF Scorecard, check by check

Floors are declared once and rendered here:

<!-- BEGIN generated: scorecard-floors (python scripts/atlas.py index --write) -->
Derived from `config/github-controls.json`: 18 checks carry a floor, and the
aggregate floor is 7.7. `python scripts/ghaudit.py` prints the live value beside each
one and reports every check below its floor — this page states no measurement.

| check | floor |
|---|---|
| `Binary-Artifacts` | 10 |
| `Branch-Protection` | 4 |
| `CI-Tests` | 10 |
| `CII-Best-Practices` | 0 |
| `Code-Review` | 0 |
| `Contributors` | 3 |
| `Dangerous-Workflow` | 10 |
| `Dependency-Update-Tool` | 10 |
| `Fuzzing` | 10 |
| `License` | 10 |
| `Maintained` | 0 |
| `Packaging` | 10 |
| `Pinned-Dependencies` | 10 |
| `SAST` | 10 |
| `Security-Policy` | 10 |
| `Signed-Releases` | 10 |
| `Token-Permissions` | 10 |
| `Vulnerabilities` | 10 |
<!-- END generated: scorecard-floors -->

## Read the evidence

The floors are targets, not live scores. [The control declaration](../config/github-controls.json)
records the expected repository settings, the per-check floors and historical observations.
Run its audit to compare those declarations with the current repository state; a historical
observation is not evidence of a current setting or score.

The declaration names the expected required status context. The release workflow contains an
index-publishing job, conditional on repository configuration; its presence alone does not prove
a package was published. See [verification](VERIFY.md) for what the local gates prove.

## Best Practices criteria

[Certification](CERTIFICATION.md) contains the generated criteria and evidence table. Keep the
criteria there rather than maintaining a second copy on this page. Its entries describe the
declared evidence, not an independent certification or a current hosted-service measurement.
