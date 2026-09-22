# OpenCode Adapter

Use OpenCode as a provider-flexible terminal coding surface.

Architecture: `OpenCode -> provider/model router -> endpoint -> tools/MCP -> repository`.

Normalize `provider`, `model`, `base_url`, `auth_env`, `context_budget`, `reasoning_budget`, `timeout`, `retry_budget`, and `tool_policy` so provider switching does not leak into business logic.

Use dedicated worktrees for risky or multi-file changes.