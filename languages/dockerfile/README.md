# Dockerfile

Status: production.

## Purpose
Container image builds: base image, build stages, runtime user, entrypoint.

## State
Every instruction is a layer. Order decides cache reuse; a secret written in a layer stays in the image.

## Verify
lint -> build -> run the image's health check.
