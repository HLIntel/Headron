# Dockerfile Operating Card

**Route:** Container image builds: base image, build stages, runtime user, entrypoint.

**Fast path:** `hadolint --failure-threshold error <file>` → `docker build --check` → build the image the file names.

**Native authority:** the program that reads the file; the spec below when they disagree.

**Avoid:** unpinned base tags, root at runtime, secrets in ARG or ENV, apt without cleanup in the same layer.

**Verify:** lint -> build -> run the image's health check.

**AI learning loop:** read the consumer of the file before editing it; a valid file the consumer rejects is still broken.

**Research:** https://docs.docker.com/reference/dockerfile/ · https://github.com/hadolint/hadolint
