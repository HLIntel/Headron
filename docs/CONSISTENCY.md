# Repository Consistency

Code-Development has multiple entry points for models, humans, and tools. Agreement is checked rather than assumed.

## Canonical layers
- MODEL.md: behavioral/control contract
- VERSION: contract version
- atlas.yaml: machine routing
- docs/INDEX.md: human routing
- language README: language-specific detail
- model adapter: runtime translation

## Checker
scripts/check_contract.py validates version agreement, required files, alias symlinks, artifact route coverage, and model-adapter references.

## Future checks
Markdown link resolution, full Atlas target validation, duplicate canonical instructions, provider schema validation, secret-pattern scanning, and language-guide completeness.