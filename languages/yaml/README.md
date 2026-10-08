# YAML

Status: production.

## Purpose
Human-edited configuration: CI workflows, manifests, contracts, deployment descriptors.

## State
Indentation is structure. Duplicate keys are silently last-wins in common loaders; anchors and implicit types (yes, 0123, 1e3) change meaning.

## Verify
parse -> lint -> schema validation -> the program that reads it loads it.
