# Repository Consistency

The repository is intentionally multi-layered, so consistency has to be checked rather than assumed.

## Contract surfaces
`MODEL.md`, `VERSION`, `README.md`, `ABOUT.md`, `docs/INDEX.md`, `atlas.yaml`, relevant model adapters, language Atlas, and patterns.

## Checks
The repository checker validates:
- version agreement in primary contract files
- required directories/files
- `languages/ATLAS.md` language paths
- symlink targets for alias docs
- stale root `AGENTS.md` absence

## Design principle
Canonical content lives once. Other surfaces should link, index, or adapt it.

## Future checks to add
- Markdown link resolution
- language status/tag agreement
- package catalog vs language guide coverage
- route target existence
- prompt template front matter
- provider registry schema
- secrets-pattern scans
- duplicate canonical instructions

Run:
```bash
python scripts/check_contract.py
```