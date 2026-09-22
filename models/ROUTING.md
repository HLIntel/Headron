# Dynamic Model Routing

Choose a model/tool/context bundle from task requirements.

## Router inputs
- task complexity
- codebase/context size
- tool requirements
- latency budget
- cost budget
- data sensitivity
- side-effect risk
- verification requirements
- local/self-hosted availability

## Routing
```text
task -> classify -> scope context -> select model -> select tools -> select isolation -> execute -> verify -> record
```

## Roles
| Role | Use |
|---|---|
| scout | fast navigation/search |
| planner | strong reasoning with low mutation |
| coder | implementation and tool use |
| verifier | tests/security/independent review |
| benchmarker | profiling and workload measurement |
| release | deterministic packaging and validation |

## Fallback
Fallback chains are finite. Specify attempts, total deadline, provider failure classes, and maximum cost.

## Multi-model workflow
`planner -> coder -> tester -> security verifier -> reviewer`
Pass compact structured results rather than full transcripts.