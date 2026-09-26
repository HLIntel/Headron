#!/usr/bin/env python3
"""native_agent_tools_are_kept: Thea is ADDED to an agent runtime's layer and never removes a tool from it.

Split out of atlasinv.py (3.8.0) so that file stays under its line cap; the declaration it reads is
atlas.yaml/native_agent_tools, and atlasinv registers this check as a hard invariant.
"""
from __future__ import annotations

import json
import re
import subprocess
import tomllib

from atlascore import ROOT, atlas, tracked


def _disabling(node, keys: set[str], trail: str = "", values: frozenset | set = frozenset()) -> list[str]:
    """Every place a parsed tool configuration turns a tool OFF: a disabling key with a value, a tools map
    set false, or a leaf whose VALUE denies (opencode's `permission: {bash: deny}` puts it in the value)."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{trail}.{key}" if trail else str(key)
            if key in keys and value or isinstance(value, str) and value in values:
                found.append(here)
            elif key == "tools" and isinstance(value, dict):
                found += [f"{here}.{name}" for name, on in value.items() if on is False]
            found += _disabling(value, keys, here, values)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            found += _disabling(item, keys, f"{trail}[{i}]", values)
    return found


def parse_config(rel: str, text: str):
    """TOML or JSON, and JSON WITH COMMENTS: Zed and opencode accept `//`, and skipping a file that does not
    parse as plain JSON would report nothing on a file it never read."""
    if rel.endswith(".toml"):
        return tomllib.loads(text)
    return json.loads(re.sub(r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/', lambda m: m.group(1) or "", text, flags=re.S))


def _hooks_path() -> str:
    out = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=ROOT, capture_output=True,  # noqa: S607
                         text=True, check=False, timeout=600).stdout.strip()
    return str((ROOT / out).resolve().relative_to(ROOT.resolve())) if out and (ROOT / out).resolve().is_relative_to(ROOT.resolve()) else out


def native_agent_tool_errors() -> list[str]:
    """native_agent_tools_are_kept — Thea is added to a runtime's layer and never removes a tool from it.

    WHY (3.8.0). An install that denies a runtime's own shell or edit tool, or a checked-in settings file
    that switches one off, turns "Thea adapts to the agent" into "the agent adapts to Thea" — and the loss
    is SILENT, because the agent still starts and simply cannot do what it did yesterday. The roster is
    derived from runtime_entry, so a runtime added there without a declaration here fails.
    """
    spec = atlas().get("native_agent_tools") or {}
    runtimes = spec.get("runtimes") or {}
    reach, keys = set(spec.get("reaches_through") or []), set(spec.get("disabling_keys") or [])
    values = set(spec.get("denying_values") or [])
    errors: list[str] = []
    entries = {str(e.get("id")): e for e in atlas().get("runtime_entry") or []}
    errors += [f"native_agent_tools declares nothing for runtime {i}: whether it keeps its tools is unsaid"
               for i in sorted(set(entries) - set(runtimes))]
    errors += [f"native_agent_tools declares {i}, which runtime_entry does not name" for i in sorted(set(runtimes) - set(entries))]
    configs: set[str] = set()
    for rid, r in sorted(runtimes.items()):
        r = r or {}
        paths, via = list(r.get("tool_config") or []), list(r.get("thea_via") or [])
        configs |= set(paths)
        if not paths and not str(r.get("none_because") or "").strip():
            errors.append(f"native_agent_tools/{rid} names no tool configuration and no none_because")
        errors += [f"native_agent_tools/{rid} reaches it through {v}, which reaches_through does not declare"
                   for v in via if v not in reach]
        adapter = ROOT / str((entries.get(rid) or {}).get("adapter"))
        if via and adapter.is_file():
            section = re.search(r"## Native tools stay\n(.*?)(?=\n## |\Z)", adapter.read_text(encoding="utf-8"), re.S)
            if not section or not section.group(1).strip():
                errors.append(f"{adapter.relative_to(ROOT)} has no 'Native tools stay' section: the adapter never says "
                              "this runtime keeps its own tools")
    hooks = _hooks_path()
    for written in [w.replace("git_hooks", hooks, 1) for w in spec.get("install_writes") or []]:
        # A runtime's configuration DIRECTORY is its own, not only the named file: .claude/ is Claude Code's.
        clash = [c for c in configs if written == c or ("/" in c and written.startswith(c.rsplit("/", 1)[0] + "/"))]
        errors += [f"an install writes {written}, inside a runtime's tool configuration {c}" for c in clash]
    for rel in sorted(configs & {str(p.relative_to(ROOT)) for p in tracked()}):
        text = (ROOT / rel).read_text(encoding="utf-8")
        try:
            parsed = parse_config(rel, text)
        except ValueError:
            continue  # a file that does not parse is check()'s first finding, never this one's crash
        errors += [f"{rel} disables a native tool at {where}: Thea adds to a runtime, it never subtracts"
                   for where in _disabling(parsed, keys, "", values)]
    return errors

