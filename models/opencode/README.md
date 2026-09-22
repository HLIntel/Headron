# OpenCode Adapter

Provider-flexible terminal coding surface.

## Architecture
`OpenCode -> router -> provider endpoint -> tools/MCP -> repository`

Keep provider details out of application logic. Use the shared LLM provider schema.

## Efficiency
Use terminal-native repo navigation and focused commands. Reserve broad agentic tools for tasks that actually need them.

## Safety
Dedicated worktree, bounded command execution, dependency review, and independent verification for broad changes.