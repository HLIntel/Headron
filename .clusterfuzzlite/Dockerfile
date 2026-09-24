# ClusterFuzzLite build image for the manifest-grammar fuzz target.
#
# The base image supplies atheris and the libFuzzer toolchain; everything this target needs beyond
# that is the repository itself and PyYAML — the same single dependency the harness declares,
# installed from the hash-pinned lock so the fuzzing image cannot drift from the tested tree.
FROM gcr.io/oss-fuzz-base/base-builder-python:v1

RUN python3 -m pip install --no-cache-dir --upgrade pip
COPY . $SRC/code-development
WORKDIR $SRC/code-development
RUN python3 -m pip install --no-cache-dir --require-hashes -r scripts/requirements.lock.txt
COPY .clusterfuzzlite/build.sh $SRC/build.sh
