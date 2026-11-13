# `benchmarks/` — what this place is

recorded measurements, and the PLANTED bug tasks an agent benchmark asks a model to fix

## A change here proves

- `contract`

## Traps already met here (ledger: `headron failures`)

- **a_mutation_harness_scored_over_zero_runs** — a perfect score. At 2.27.0 a zsh `$S:scripts` (`:s` is a substitution modifier) failed before any test ran and scored 5 of 5 mutants KILLED; fixed, the suite's own sys.path insert shadowed every mutant and scored 6 of 6 SURVIVED over the real module. At 3.62.0 mutants run under `python -I` scored KILLED because the child could not import the mutated module, not because a case failed
  - do: run an unmutated control first and count a mutant killed only when the assertion written for it fails, never by a non-zero exit
- **a_tie_that_was_an_artifact_of_the_question_set** — the strongest possible result — equal accuracy at a third of the cost. At 2.26.0, over two question kinds, routed and whole_tree tied at 98.5%; a third kind at 2.27.0 separated them, 96.8% against 97.5%, and the honest claim became a trade rather than a free lunch
- **a_non_answer_scored_as_wrong** — a large, clean improvement
  - do: judge an answer by the fields it must carry; a 200 or an exit 0 with an empty payload is unanswered, and a zero or false stays a value
- **a_bad_result_captioned_and_passed** — an honest report — the number is true, and the defect behind it ships

Declared in `atlas.yaml/directory_scopes/benchmarks`; `headron route benchmarks` prints it as a record.
