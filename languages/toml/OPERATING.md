# TOML Operating Card

**Route:** Tool and package configuration: pyproject, Cargo, wrangler, linter settings.

**Native authority:** the program that reads the file; the spec below when they disagree.

**Avoid:** redefined tables, mixed inline and header tables for one key, floats where an integer is meant.

**Verify:** parse -> schema validation -> the tool that owns the file loads it.

**AI learning loop:** read the consumer of the file before editing it; a valid file the consumer rejects is still broken.

**Research:** https://toml.io/en/v1.0.0 · https://taplo.tamasfe.dev/
