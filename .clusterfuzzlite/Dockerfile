# ClusterFuzzLite build image for the manifest-grammar fuzz target.
#
# The base image supplies atheris and the libFuzzer toolchain; everything this target needs beyond
# that is the repository itself and PyYAML — the same single dependency the harness declares,
# installed from the hash-pinned lock so the fuzzing image cannot drift from the tested tree.
# PINNED BY DIGEST, NOT BY TAG, and the ratchet is why. Adding this file dropped Scorecard's
# Pinned-Dependencies check from 10 to 7 — 'dependency not pinned by hash detected' — while the
# aggregate ROSE from 7.0 to 7.3 in the same scan. A single floor on the total would have called
# that an improvement; the per-check floor caught it in the audit that followed the merge.
# A tag moves; a digest does not. Resolved from the registry at the contract version in VERSION.
FROM gcr.io/oss-fuzz-base/base-builder-python:v1@sha256:1de9e4ac301ddea42b8846480d5e4903580ed5071357c9173a4d26a4af65a6fa

# NO `pip install --upgrade pip`. Scorecard named this line — `pipCommand not pinned by hash`,
# the last unpinned dependency in the tree — and the honest fix is to DELETE THE WRITER: the
# base image ships the pip that OSS-Fuzz tests with, so upgrading it bought nothing and cost
# the one supply-chain guarantee this repository holds everywhere else.
COPY . $SRC/code-development
WORKDIR $SRC/code-development
RUN python3 -m pip install --no-cache-dir --require-hashes -r scripts/requirements.lock.txt
COPY .clusterfuzzlite/build.sh $SRC/build.sh
