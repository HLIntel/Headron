# R

**Status:** production

## Purpose
Statistics, applied data analysis and reproducible reporting, where the model and its diagnostics matter more than the program around them.

## Why this route exists
It fills statistics and the CRAN ecosystem, which no other route in this atlas reached. A language earns a route here only by contributing a distinct guarantee,
runtime property, ecosystem or performance characteristic — not by being popular.

## Stack
renv -> styler -> R CMD check -> testthat -> Rprof.

## Common mistakes
- an analysis with no seed, so the number cannot be regenerated
- `install.packages` with no lockfile, so the environment is unrecorded
- growing a data frame inside a loop
- a silently coerced column type changing a result without an error
- reporting a point estimate with no interval and no diagnostic

## AI directive
`attach()`, `setwd()` in a script, `t`/`f` instead of `true`/`false`, growing a data frame in a loop, an analysis with no seed and no session record — check for these before generating code, and state the
boundary contract (a data contract at the edge — column names, types, units and missingness stated, because a silently coerced column is the most common defect in this language) before writing the logic that crosses it.

## Verify
`renv::restore()` → `styler` → `testthat` → `R CMD check` on anything shipped as a package

## Learn into
read the data contract → reproduce one figure → change one assumption on purpose → re-check the diagnostics, never only the point estimate

Official: https://cran.r-project.org/manuals.html
