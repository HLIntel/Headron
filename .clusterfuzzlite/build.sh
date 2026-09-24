#!/bin/bash -eu
# Compile every fuzz target in fuzz/ into $OUT, the way ClusterFuzzLite expects.
#
# TWO THINGS THE FIRST VERSION GOT WRONG, both found by running it:
#   1. compile_python_fuzzer FREEZES the target with PyInstaller, so a runtime `sys.path.insert`
#      never happens — the modules must be discoverable at BUILD time (--paths, --hidden-import).
#   2. The target reads real repository data (atlas.yaml, the manifest schema, the language tree).
#      A frozen binary has no repository around it, so the data travels in the bundle and
#      atlascore resolves ROOT from PyInstaller's extraction directory.
cd "$SRC/code-development"

for target in fuzz/fuzz_*.py; do
  compile_python_fuzzer "$target" \
    --paths="$SRC/code-development/scripts" \
    --hidden-import=atlascore \
    --hidden-import=packmanifest \
    --hidden-import=yaml \
    --add-data="$SRC/code-development/atlas.yaml:." \
    --add-data="$SRC/code-development/VERSION:." \
    --add-data="$SRC/code-development/tools/tools.schema.json:tools" \
    --add-data="$SRC/code-development/languages:languages" \
    --add-data="$SRC/code-development/config:config"
done
