# JSON

Status: production.

## Purpose
Data interchange, configuration and machine-written records: package manifests, lockfiles, API payloads, benchmark ledgers.

## State
A JSON file has no comments and no duplicate-key rule; the parser that reads it decides. Schema files are the contract.

## Verify
parse -> schema validation -> the program that reads it loads it.
