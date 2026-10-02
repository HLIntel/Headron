# R

**Status:** production

## Purpose
Statistics, applied data analysis and reproducible reporting, where the model and its diagnostics matter more than the program around them.

## Why this route exists
It fills statistics and the CRAN ecosystem, which no other route in this atlas reached.

## Stack
renv -> styler -> R CMD check -> testthat -> Rprof.

## Common mistakes
- an analysis with no seed, so the number cannot be regenerated
- `install.packages` with no lockfile, so the environment is unrecorded
- growing a data frame inside a loop
- a silently coerced column type changing a result without an error
- reporting a point estimate with no interval and no diagnostic

The avoid list, boundary contract, verify loop and learning loop live in `OPERATING.md` beside this guide.

Official: https://cran.r-project.org/manuals.html
