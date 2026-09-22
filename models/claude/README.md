# Claude Code Adapter

Map repository controls to Claude Code's native surfaces rather than duplicating the whole repository into one instruction file.

## Map
- durable project behavior -> concise project instructions
- procedures/reference -> Skills
- deterministic enforcement -> hooks
- external tools -> MCP
- parallel/context isolation -> subagents
- bundled distribution -> plugins

## Efficiency
Use path-relevant guidance, Skills, focused retrieval, and subagents for broad exploration. Keep always-loaded text small.

## Agent safety
Model instructions are not a hard sandbox. Use hooks/policy for deterministic restrictions and explicit approval for destructive side effects.

Official: https://code.claude.com/docs/en/features-overview