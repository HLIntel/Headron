# JSON Operating Card

**Route:** Data interchange, configuration and machine-written records: package manifests, lockfiles, API payloads, benchmark ledgers.

**Native authority:** the program that reads the file; the spec below when they disagree.

**Avoid:** comments, trailing commas, duplicate keys, numbers past 2^53, hand edits to generated records.

**Verify:** parse -> schema validation -> the program that reads it loads it.

**AI learning loop:** read the consumer of the file before editing it; a valid file the consumer rejects is still broken.

**Research:** https://www.json.org/json-en.html · https://json-schema.org/docs
