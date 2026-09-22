# Programming and Agent Research Notes — 2026

Reviewed for the Atlas on 2026-09-22.

Repository context:
- ContextBench: https://arxiv.org/abs/2602.05892
- Agent Retrieval Bench: https://arxiv.org/abs/2607.24882
- CodeNib: https://arxiv.org/html/2607.25431

Adopt: measure useful context retrieval and exploration cost instead of dumping whole repositories into agent context.

Multilingual agents:
- SWE-PolyBench: https://arxiv.org/abs/2504.08703
- Multi-SWE-bench: https://arxiv.org/abs/2504.02605

Adopt: language-diverse evaluation with language-specific verification.

Heterogeneous systems:
- Backline: https://arxiv.org/abs/2609.09270
- CASS: https://arxiv.org/abs/2505.16968

Adopt: make execution placement and data movement explicit; verify generated accelerator code with compilation and execution.

MCP/IDE:
- VS Code MCP: https://code.visualstudio.com/docs/agent-customization/mcp-servers
- GitHub MCP Server: https://github.com/github/github-mcp-server
- Serena: https://github.com/oraios/serena
- Playwright MCP: https://github.com/microsoft/playwright-mcp
- Context7: https://github.com/upstash/context7
- DBHub: https://github.com/bytebase/dbhub
- Semgrep MCP: https://github.com/semgrep/semgrep/tree/develop/cli/src/semgrep/mcp

Adopt: capability profiles rather than loading every MCP.
