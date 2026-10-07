#!/usr/bin/env python3
"""The claude.ai skill: Thea for a chat that can run nothing, generated whole from atlas.yaml.

atlasgen maps these builders into GENERATED_FILES, so `index --write` writes them and `check` fails
on any drift; release.yml zips chat/thea as the upload.
"""

from __future__ import annotations

from atlascore import ROOT, atlas, read, routes, strict_yaml

# The claude.ai upload: outside skills/, so Claude Code's plugin never loads it twice. contextcost caps
# its description like every shipped skill's.
CHAT_SKILL = "chat/thea"
CHAT_SKILL_DESCRIPTION = (
    "Engineering discipline for code, plans, reviews, debugging and done-claims: label "
    "evidence, name the proving gate, catch known failure shapes."
)
CHAT_SKILL_TOP_SHAPES = 12  # the most-sighted shapes inline; the rest load from references/ only on demand


def _class_gates(name: str) -> list[str]:
    """A change class's gates with `extends` resolved, parent first, each gate once."""
    spec = atlas()["verification_policy"]["profiles"][name]
    inherited = [g for parent in spec.get("extends") or [] for g in _class_gates(parent)]
    return list(dict.fromkeys(inherited + list(spec.get("required") or [])))


def _pack_gate_command(pack: str, gate: str) -> str:
    """The command that proves one gate in one pack, from its tools.yaml and gate_tools — or `none`."""
    spec, path = atlas().get("gate_tools", {}).get(gate) or {}, f"languages/{pack}/tools.yaml"
    if not (ROOT / path).is_file():  # a planted tree drops packs; the route guard reports that, not this table
        return "none"
    tool = (strict_yaml(read(path), path).get("authority") or {}).get(spec.get("role", ""))
    if not isinstance(tool, str) or tool == "none" or tool.startswith(("lib:", "http")):
        return "none"
    verb = (spec.get("verbs") or {}).get(tool)
    return f"`{' '.join(verb) if verb else tool}`"


def chat_skill() -> str:
    """chat/thea/SKILL.md: Thea for a chat that can run nothing — every rule, gate and lesson INLINE.

    CHAT.md routes a chat to files it must fetch and commands it cannot run, so in a plain chat it
    delivers almost nothing (measured by use, 3.52.0). This carries the content itself: claim labels,
    the gates per change class, the most-sighted failure shapes with their tells, and a proof card the
    answer ends on. The long tail sits in references/, which a skill runtime loads only when asked.
    """
    chat = atlas()["chat"]
    modes = atlas()["agent_failure_modes"]
    top = sorted(modes.items(), key=lambda kv: -int(kv[1].get("sightings") or 0))[:CHAT_SKILL_TOP_SHAPES]
    lines = [
        "---",
        "name: thea",
        f"description: {CHAT_SKILL_DESCRIPTION}",
        "---",
        "",
        f"# Thea in a chat (contract v{read('VERSION').strip()})",
        "",
        "GENERATED from atlas.yaml by `python scripts/atlas.py index --write`. Do not edit.",
        "",
        "Apply to every answer that writes, reviews, plans or debugs code, or claims something works. "
        "You cannot run anything here: your job is to make every claim checkable and to name the run "
        "that would check it.",
        "",
        "## Rules for every answer",
        "",
        "Where a rule says CHAT.md or tools.yaml, read `references/routes.md`: it carries both.",
        "",
        chat["install"].rstrip(),
        "",
        "## End every code or plan answer with a proof card",
        "",
        "```text",
        "CHANGE   what changes, in one line",
        "CLASS    the change class below that it falls in",
        "GATES    each gate for that class, with the command for this language (references/routes.md)",
        "PROVEN   what this chat actually established, each line labelled CONFIRMED / INFERRED",
        "UNPROVEN what still needs a run, and the command that runs it",
        "SHAPES   any failure shape below this answer risks, by id",
        "```",
        "",
        "## Gates per change class",
        "",
        "Pick the narrowest class that covers the change; a change can be in more than one.",
        "",
    ]
    lines += [f"- **{name}**: {', '.join(_class_gates(name))}" for name in atlas()["verification_policy"]["profiles"]]
    lines += ["", "## Processes", ""]
    lines += [
        f"- **{name}** ({spec.get('when', '')}): {' → '.join(spec.get('steps') or [])}. "
        f"Returns {spec.get('returns', '')}. Stop when {spec.get('stop_when', '')}."
        for name, spec in chat["processes"].items()
    ]
    lines += [
        "",
        "## The failure shapes seen most often",
        "",
        "Before you answer, check your own draft against these. Each one was a real, repeated mistake.",
        "",
    ]
    lines += [f"- **{key}**: tell: {spec['tell'].rstrip('.')}. Do instead: {spec['prevented_by']}" for key, spec in top]
    lines += [
        "",
        "## Load only when needed",
        "",
        "- `references/routes.md`: file extension → language pack → the command for each gate",
        f"- `references/failures.md`: every recorded failure shape ({len(modes)}), with its tell and fix",
        f"- `references/moves.md`: every proven move ({len(atlas()['agent_success_patterns'])}), "
        "with when it applies and how to verify it",
        "",
        "## When you or the user get something wrong",
        "",
        "Say so in the same answer, then give a ready-to-paste ledger entry: `id` (snake_case shape "
        "name), `shape`, `looks_like`, `tell`, `prevented_by`. One entry per shape, never per incident.",
    ]
    return "\n".join(lines) + "\n"


def chat_skill_routes() -> str:
    """references/routes.md: every pack's gate commands inlined, so a chat never fetches tools.yaml."""
    from atlascore import project_manifests

    by_pack: dict[str, list[str]] = {}
    for key, pack in sorted({**routes(), **project_manifests()}.items()):
        by_pack.setdefault(pack, []).append(f"`{key}`")
    gates = _class_gates("source_change")
    lines = [
        "# Routes: file → pack → gate commands",
        "",
        "GENERATED from languages/*/tools.yaml. `none` "
        "means no established tool is recorded: say so, never invent one.",
        "",
        "| pack | files | " + " | ".join(gates) + " |",
        "|---" * (len(gates) + 2) + "|",
    ]
    lines += [
        f"| {pack} | {' '.join(keys)} | " + " | ".join(_pack_gate_command(pack, g) for g in gates) + " |"
        for pack, keys in sorted(by_pack.items())
    ]
    return "\n".join(lines) + "\n"


def chat_skill_failures() -> str:
    """references/failures.md: the whole failure ledger, most-sighted first."""
    modes = sorted(atlas()["agent_failure_modes"].items(), key=lambda kv: -int(kv[1].get("sightings") or 0))
    lines = ["# Failure shapes", "", "GENERATED from atlas.yaml/agent_failure_modes, most-sighted first.", ""]
    for key, spec in modes:
        lines += [
            f"## {key}",
            "",
            f"- shape: {spec['shape']}",
            f"- looks like: {spec['looks_like']}",
            f"- tell: {spec['tell']}",
            f"- do instead: {spec['prevented_by']}",
            "",
        ]
    return "\n".join(lines)


def chat_skill_moves() -> str:
    """references/moves.md: every proven move, with the failures it answers."""
    lines = ["# Proven moves", "", "GENERATED from atlas.yaml/agent_success_patterns.", ""]
    for key, spec in atlas()["agent_success_patterns"].items():
        lines += [
            f"## {key}",
            "",
            f"- move: {spec['move']}",
            f"- when: {spec['when']}",
            f"- verify: {spec['verification']}",
            f"- answers: {', '.join(spec.get('pairs') or [])}",
            "",
        ]
    return "\n".join(lines)
