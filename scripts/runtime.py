#!/usr/bin/env python3
"""Which agent runtime produced a change — resolved once, recorded on every verification.

WHY (3.56.0). Agent scoring is the highest-value future feature: pass rate per runtime. A verification
that does not name its agent cannot feed that scoreboard. Before this module, hooks defaulted an
absent THEA_AGENT to `claude-code`, which credited Claude for Cursor, Codex, Hermes and CI alike.

RESOLUTION ORDER (declared inputs only — declcheck refuses an undeclared read):
  1. THEA_AGENT when set (authority; adapters and launchers set it)
  2. Declared host signals: CLAUDE_CODE_SESSION_ID, HERMES_HOME, GITHUB_BASE_REF / THEA_BASE in CI
  3. `unknown` — never a silent default to one vendor

CURSOR FAMILY. Grok Bot and other Cursor-hosted engines share Cursor's entry file and hook surface;
`family` is `cursor` for those ids so a dashboard can roll them up without inventing a second adapter.

WHAT IT DOES NOT PROVE: that the agent told the truth about its name. It records what the environment
claims, so a future scoreboard has a field to read.
"""

from __future__ import annotations

import os
import re

# Ids a dashboard and a check-run can group. Aliases normalize launcher spellings onto runtime_entry ids.
FAMILIES = {
    "claude": "claude",
    "claude-code": "claude",
    "openai_codex": "openai_codex",
    "codex": "openai_codex",
    "cursor": "cursor",
    "grok-bot": "cursor",
    "cursor-grok": "cursor",
    "grok": "cursor",
    "opencode": "opencode",
    "hermes": "hermes",
    "github_actions": "github_actions",
    "vscode": "vscode",
    "chat": "chat",
    "theaos": "theaos",
    "unknown": "unknown",
}

_ALIAS = re.compile(r"[^a-z0-9]+")


def normalize(name: str | None) -> str:
    """A stable agent id: lower-case, hyphenated, empty becomes unknown."""
    raw = _ALIAS.sub("-", (name or "").strip().lower()).strip("-")
    return raw or "unknown"


def family_of(agent_id: str) -> str:
    """The runtime family an agent id rolls up into; unknown ids keep their own name as family."""
    key = normalize(agent_id)
    if key in FAMILIES:
        return FAMILIES[key]
    # cursor-hosted engines often look like cursor-<engine>
    if key.startswith("cursor-") or key.endswith("-cursor"):
        return "cursor"
    return key


def _from_signals() -> tuple[str, str] | None:
    """Infer from declared host signals only. Returns (agent_id, source) or None."""
    if os.environ.get("CLAUDE_CODE_SESSION_ID"):
        return "claude-code", "CLAUDE_CODE_SESSION_ID"
    if os.environ.get("HERMES_HOME"):
        return "hermes", "HERMES_HOME"
    if os.environ.get("GITHUB_BASE_REF"):
        return "github_actions", "GITHUB_BASE_REF"
    return None


def resolve(explicit: str | None = None) -> dict:
    """The agent attribution record every verification and field event should carry.

    `explicit` wins (CLI / contract field). Otherwise THEA_AGENT, then host signals, then unknown.
    """
    if explicit and str(explicit).strip():
        agent = normalize(explicit)
        source = "explicit"
    elif os.environ.get("THEA_AGENT"):
        agent = normalize(os.environ.get("THEA_AGENT"))
        source = "THEA_AGENT"
    elif found := _from_signals():
        agent, source = found
    else:
        agent, source = "unknown", "absent"
    return {"agent": agent, "runtime": family_of(agent), "family": family_of(agent), "source": source}


if __name__ == "__main__":
    import json
    import sys

    if {"-h", "--help"} & set(sys.argv[1:]):
        print((__doc__ or sys.argv[0]).strip())
        raise SystemExit(0)
    print(json.dumps(resolve(sys.argv[1] if len(sys.argv) > 1 else None), indent=2, sort_keys=True))
