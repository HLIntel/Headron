# Claude Code Adapter

Map persistent project constraints to concise project instructions, procedures to Skills, deterministic enforcement to hooks, external capabilities to MCP, and context isolation to subagents.

Keep always-loaded context small. Put deep reference/procedures into on-demand Skills. Use subagents when broad exploration would fill the primary context.

Model instructions are not a security boundary; use deterministic hooks/policy for hard blocks. Side-effecting Skills should normally require explicit invocation or approval.

Official: https://code.claude.com/docs/en/features-overview
Memory: https://code.claude.com/docs/en/memory