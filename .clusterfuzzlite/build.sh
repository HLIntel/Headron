#!/bin/bash -eu
# Compile every fuzz target in fuzz/ into $OUT, the way ClusterFuzzLite expects.
#
# `compile_python_fuzzer` wraps the target with atheris and libFuzzer. The repository is copied
# whole rather than installed, because the harness is not a package — pyproject.toml says so — and
# the target imports it by path exactly as every instrument does.
cd "$SRC/code-development"
for target in fuzz/fuzz_*.py; do
  compile_python_fuzzer "$target"
done
