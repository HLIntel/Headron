# Quantum

**Quantum is a domain with its own declarations, not another language convention.** The mistake
this page exists to prevent is treating it as "one more language pack": the classical gates would
then pass a quantum change that declared no shot count, no noise model and no baseline, and a
result produced that way is not a measurement.

## What a quantum change must declare, and what must come out of it

Two rosters, both machine-readable in [atlas.yaml](../../atlas.yaml):

| declared BEFORE the run (`task_profiles.quantum`) | produced BY the run (`verification_policy.profiles.quantum_change`) |
|---|---|
| the simulator or backend used | a simulator run |
| the shot count | the shot count, stated with the result |
| the noise model, including "none, ideal simulator" | the noise model it was produced under |
| the qubit budget | a resource estimate |
| a classical baseline to beat | the comparison against that baseline |

**A quantum result quoted without its shots and its noise model is a rendering of a number.**
Re-running it under a different simulator gives a different answer and nothing says so, which is
the silent-break shape this repository is built around.

## Routes, and the rule for what gets one

| artifact | route | why |
|---|---|---|
| `.qs` | [`quantum/qsharp`](qsharp/README.md) | a language with its own compiler and toolchain |
| `.slq` | [`quantum/silq`](silq/README.md) | a research language with its own compiler; almost every other role is honestly `none` |
| Python using Qiskit | the `python` route **plus** the `quantum` task profile | [Qiskit](qiskit/README.md) is an SDK, not a language — see below |

**A language gets a route; an SDK gets a task profile.** Giving Qiskit a language route would have
created a pack whose compiler, formatter, LSP and debugger are all Python's, which reads as
coverage and adds nothing a router can use.

Keep experiment provenance, dependency versions, execution budgets and the classical/quantum
interface contract explicit — the same rule as any other boundary here, with the addition that the
budget is money and queue time on real hardware.
