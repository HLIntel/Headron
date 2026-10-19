<!-- AGENTS: do not read this page breadth-first. Plug in: `python scripts/atlas.py port <file>`,
     or parse .agent/bootstrap.json — one record back. -->
<!-- mcp-name: io.github.HeartlandIntel/thea -->
<p align="center">
  <img src="docs/assets/theaos-engineering-intelligence-banner.png"
       alt="TheaOS — engineering intelligence for the agentic era" width="1200">
</p>

<p align="center">
  <a href="https://github.com/HLIntel/thea-software/actions/workflows/atlas-ci.yml"><img
     src="https://github.com/HLIntel/thea-software/actions/workflows/atlas-ci.yml/badge.svg?branch=main"
     alt="Atlas CI"></a>
  <a href="https://github.com/HLIntel/thea-software/releases/latest"><img
     src="https://img.shields.io/github/v/tag/HLIntel/thea-software?label=contract"
     alt="contract version"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/HLIntel/thea-software"><img
     src="https://api.securityscorecards.dev/projects/github.com/HLIntel/thea-software/badge"
     alt="OpenSSF Scorecard"></a>
  <a href="https://pypi.org/project/thea-software/"><img
     src="https://img.shields.io/pypi/v/thea-software?label=PyPI"
     alt="PyPI version"></a>
  <a href="https://pypi.org/project/thea-software/"><img
     src="https://img.shields.io/pypi/pyversions/thea-software"
     alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
</p>

<!-- BEGIN generated: headline (python scripts/atlas.py index --write) -->

**Measured:** the commands that prove a change, build-enforced ([evidence](#what-it-measurably-buys)). Agents: [llms.txt](llms.txt); chats: [CHAT.md](CHAT.md).

<!-- END generated: headline -->

**Start:** [install/use](#quickstart) · [agents](llms.txt) · [chat](CHAT.md) · [adapters](models/README.md)

## What it does

Thea turns repository policy into executable verification. [`atlas.yaml`](atlas.yaml) tells agents
what proves each file's change; CLI, MCP, hooks, CI and adapters enforce it. Gates report `PASS`,
`FAIL` or `NOT RUN` — missing tools never become green.