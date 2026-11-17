# YAML

Status: production.

## Purpose
Human-edited configuration: CI workflows, manifests, contracts, deployment descriptors.

## State
Indentation is structure. Duplicate keys are silently last-wins in common loaders; anchors and implicit types (yes, 0123, 1e3) change meaning.

## Verify
parse -> lint -> schema validation -> the program that reads it loads it.

## Operating card

**Route:** Human-edited configuration: CI workflows, manifests, contracts, deployment descriptors.

**Fast path:** `yamllint <file>` → schema validation (`check-jsonschema`) → the consumer loads it.

**Native authority:** the program that reads the file; the spec below when they disagree.

**Avoid:** duplicate keys, implicit booleans, tabs, unquoted version strings, anchors across documents.

**Verify:** parse -> lint -> schema validation -> the program that reads it loads it.

**AI learning loop:** read the consumer of the file before editing it; a valid file the consumer rejects is still broken.

**Research:** https://yaml.org/spec/1.2.2/ · https://yamllint.readthedocs.io/
