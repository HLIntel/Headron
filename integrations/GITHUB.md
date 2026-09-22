# GitHub Engineering

GitHub is a programmable development control plane.

## Surface selection
- local state -> Git
- interactive repository work -> `gh`
- deterministic automation -> REST/API
- multi-resource querying -> GraphQL
- service integration -> GitHub App
- CI/CD -> Actions
- event ingress -> Webhooks
- AI capability -> MCP
- policy enforcement -> rulesets/branch/environment protections

## AI coding
A model should receive only the GitHub capabilities needed for the task.

Example capability bands:
`read -> branch -> commit -> PR -> merge -> release/admin`

Do not bundle merge/release/admin into an ordinary coding tool.

## Repository policy
Executable policy belongs in GitHub rulesets, branch protection, Actions permissions, protected environments, CODEOWNERS/review requirements, and security scanning rather than only in prose.

## API hygiene
Bound pagination, cache stable non-sensitive metadata, handle rate limits, and do not put tokens in source or model context.

## Actions
Prefer minimal workflow permissions. Separate build/test from deployment and release privileges.

## GitHub MCP
Treat MCP GitHub actions as privileged capabilities. Narrow the imported tool surface and review side effects.

Official: https://docs.github.com/ and https://cli.github.com/manual/