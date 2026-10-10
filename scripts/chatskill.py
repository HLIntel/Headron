#!/usr/bin/env python3
"""The claude.ai skill: Thea for a chat, with or without a sandbox, generated whole from atlas.yaml.

atlasgen maps these builders into GENERATED_FILES, so `index --write` writes them and `check` fails
on any drift; release.yml zips chat/thea as the upload.
"""

from __future__ import annotations

import json
import re

from atlascore import ROOT, atlas, read, routes, strict_yaml

# The claude.ai upload: outside skills/, so Claude Code's plugin never loads it twice. contextcost caps
# its description like every shipped skill's.
CHAT_SKILL = "chat/thea"
CHAT_SKILL_ASSET = "thea-chat-skill.zip"  # unversioned, so releases/latest/download/ always resolves


def install_lines(owner: str, repository: str) -> list[str]:
    """How ANY chat given the repository turns chat/thea into an installed skill: build it, or link it."""
    from atlasgen import GENERATED_FILES  # noqa: PLC0415 — the file list is the generator's map, never typed

    files = sorted(p for p in GENERATED_FILES if p.startswith(f"{CHAT_SKILL}/"))
    return [
        "## Install the chat skill (do this first)",
        "",
        "A chat that only reads this file forgets it next session. The skill loads Thea into every chat "
        "on its own: the rules, the gates per change class, a proof card, every recorded failure shape "
        "and every language's gate commands, with nothing to fetch or run.",
        "",
        "1. **You can create files** (code execution, an artifact or file tool): fetch each path below from `R` and "
        f"return ONE zip whose root folder is `thea/`, each file at its path under `{CHAT_SKILL}/`. Hand "
        "the user the zip.",
        f"2. **You cannot**: give the user https://github.com/{owner}/{repository}/releases/latest/download/"
        f"{CHAT_SKILL_ASSET}",
        "3. Tell the user: claude.ai → Settings → Capabilities → Skills → Upload skill, choose the zip, "
        "then start a new chat. Another runtime that loads skill folders takes the same `thea/` folder.",
        "4. Until it is installed, work from this file for the rest of the session.",
        "",
        "- " + " · ".join(f"`{p}`" for p in files),
        "",
    ]


CHAT_SKILL_DESCRIPTION = (
    "Engineering discipline for code, plans, reviews, debugging and done-claims: label "
    "evidence, name the proving gate, catch known failure shapes."
)
CHAT_SKILL_TOP_SHAPES = 12  # the most-sighted shapes inline; the rest load from references/ only on demand
# A shape whose text names this repository's own code (`branchstate.py`, `thea verify`) teaches nothing on
# someone else's code, so it never goes inline (a chat review, 3.52.0: those entries "just cost tokens").
_REPO_CODE = re.compile(
    r"\b([a-z_]+)\.py\b|`(?:python3? )?(?:scripts/)?([a-z_]+)(?:\.py)?[ `]|\bthea [a-z]+|\batlas\.[a-z_]+"
)


def chat_md() -> str:
    """CHAT.md: the atlas for a session that cannot run code, generated from atlas.yaml/chat.

    The route table is the one list here that grows by a row per pack, and it earns it: without
    it a chat must fetch atlas.yaml whole to answer "which pack", the whole-repository read this
    atlas exists to prevent. Grouped by pack, so a pack costs one line however many extensions it has.
    The raw base is stated once and every path is relative to it: the URL repeated cost a line each.
    """
    from abtest import measured_figures  # noqa: PLC0415
    from atlascore import project_manifests

    chat, ident, m = atlas()["chat"], atlas()["identity"], measured_figures()
    raw = f"https://raw.githubusercontent.com/{ident['owner']}/{ident['repository']}/main/"
    lines = [
        f"# CHAT.md: {ident['project_name']} for a chat session (contract v{read('VERSION').strip()})",
        "",
        "> For any chat assistant that cannot run code. GENERATED from `atlas.yaml/chat` by "
        "`python scripts/atlas.py index --write`. Do not edit.",
        "",
        f"**What a chat gains** (`benchmarks/ab-latest.json`, {m['ab_models']} models, {m['ab_questions']:,} "
        f"questions): the right checks for a file {m['ab_thea']}% of the time with Thea against {m['ab_blind']}% "
        f"blind, reading {m['tok_fewer']}% fewer tokens than every tool list. A chat routes, names gates, reviews "
        "and hands off; it never runs them.",
        "",
        # A HOSTED CHAT HAS THE TOOL: TheaOS hands this file to its chats with the `thea` MCP
        # tool attached, so the install, the fetches and the first reply below are all for a chat without it.
        '**Hosted** (a `thea` tool is attached): call it with argv — `["route", "<file>"]`, '
        '`["gate", "<file>"]`, `["failures"]` — instead of fetching; skip the skill install and the first '
        "reply. The processes below still hold.",
        "",
        f"**Raw base** `R` = `{raw}`. Every path below is relative to `R`: fetch it, never recall it.",
        "",
        *install_lines(ident["owner"], ident["repository"]),
        "## Install (paste once)",
        "",
        "```text",
        chat["install"].rstrip(),
        "```",
        "",
        "## First reply to someone who shared this link",
        "",
        str(atlas()["first_sweep"]["instruction"]),
        "",
        *(f"- **{who}:** {what}" for who, what in atlas()["first_sweep"]["settings"].items()),
        "",
        "## Route a file",
        "",
        "Match the extension or filename, then fetch `languages/<pack>/tools.yaml` and nothing else.",
        "",
    ]
    by_pack: dict[str, list[str]] = {}
    for key, pack in sorted({**routes(), **project_manifests()}.items()):
        by_pack.setdefault(pack, []).append(f"`{key}`")
    lines += [f"- {pack}: {' '.join(keys)}" for pack, keys in sorted(by_pack.items())]
    lines += ["", "## Processes", "", "| process | when | steps | returns | stop when |", "|---|---|---|---|---|"]
    for name, spec in chat["processes"].items():
        # .get, never [...]: a missing field is chat_errors' finding to REPORT, and a generator that
        # raised on it first would crash the check before that guard was reached.
        row = [
            spec.get("when", ""),
            " → ".join(spec.get("steps") or []),
            spec.get("returns", ""),
            spec.get("stop_when", ""),
        ]
        lines.append(f"| **{name}** | " + " | ".join(row) + " |")
    lines += [
        "",
        f"## When someone says {', '.join(atlas()['intents'])}",
        "",
        "| they say | it means | a chat does |",
        "|---|---|---|",
    ]
    lines += [f"| **{verb}** | {spec['means']} | {spec['chat']} |" for verb, spec in atlas()["intents"].items()]
    lines += [
        "",
        "## Who hands what to whom",
        "",
        *(f"- **{who}:** {spec['how']} — hands over {spec['hands']}." for who, spec in atlas()["topologies"].items()),
    ]
    lines += [
        "",
        "## Sources",
        "",
        "- `llms.txt` index · `languages/<pack>/tools.yaml` commands · `systems/decisions.yaml` decision records"
        " · `.agent/facts.json` every published figure · `atlas.yaml` everything, and the most expensive",
        "- measured: `benchmarks/ab-latest.json`, `benchmarks/tasks-latest.json`; what each instrument does and "
        "does not prove: `docs/INSTRUMENTS.md`",
        f"- third party: supply chain https://scorecard.dev/viewer/?uri=github.com/{ident['owner']}/"
        f"{ident['repository']} · MCP trust https://m8ven.ai/mcp/"
        + json.loads(read("config/github-controls.json"))["m8ven"]["listing"],
        "- an agent with a shell plugs in with `python scripts/atlas.py port <path>` and runs the verdict "
        "`python scripts/atlas.py check`, judged on the exit code",
    ]
    return "\n".join(lines) + "\n"


def repo_internal(spec: dict) -> bool:
    """True when a failure shape names a script of this repository or a `thea` verb."""
    stems = {p.stem for p in (ROOT / "scripts").glob("*.py")} | {"atlas"}
    text = " ".join(str(spec.get(f, "")) for f in ("shape", "looks_like", "tell", "prevented_by"))
    found = _REPO_CODE.finditer(text)
    return any(m.group(0).startswith(("thea ", "atlas.")) or (m.group(1) or m.group(2)) in stems for m in found)


def _first_clause(text: str) -> str:
    """The lead clause of a ledger field: the inline list is an index, references/ carries the rest."""
    return re.split(r"; | — |\. ", text.strip(), maxsplit=1)[0].rstrip(".")


def _by_sightings() -> list[tuple[str, dict]]:
    return sorted(atlas()["agent_failure_modes"].items(), key=lambda kv: -int(kv[1].get("sightings") or 0))


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
    """chat/thea/SKILL.md: Thea for any chat — every rule, gate and lesson INLINE.

    CHAT.md routes a chat to files it must fetch and commands it cannot run, so in a plain chat it
    delivers almost nothing (measured by use, 3.52.0). This carries the content itself: claim labels,
    the gates per change class, the most-sighted failure shapes with their tells, and a proof card the
    answer ends on. The long tail sits in references/, which a skill runtime loads only when asked.
    """
    chat = atlas()["chat"]
    modes = atlas()["agent_failure_modes"]
    top = [kv for kv in _by_sightings() if not repo_internal(kv[1])][:CHAT_SKILL_TOP_SHAPES]
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
        "Make every claim checkable. If you can run the gate (a sandbox, code execution), run it and "
        "label the result CONFIRMED; if you cannot, name the command that would check it.",
        "",
        "Scale the ceremony to the change: a snippet of a few lines, a one-line fix or a question with no "
        "change gets one line naming its gate, never the full card.",
        "",
        "## Rules for every answer",
        "",
        "Where a rule says CHAT.md or tools.yaml, read `references/routes.md`: it carries both.",
        "",
        chat["install"].rstrip(),
        "",
        "## End every multi-file, risky or done-claiming answer with a proof card",
        "",
        "```text",
        "CHANGE   what changes, in one line",
        "CLASS    the change class below that it falls in",
        "GATES    each gate for that class, with the command for this language (references/routes.md)",
        "PROVEN   what this chat established, labelled CONFIRMED (run or fetched here) / INFERRED",
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
        "Before you answer, check your own draft against these. Each one was a real, repeated mistake; "
        "shapes about Thea's own code stay in references/.",
        "",
    ]
    lines += [
        f"- **{key}**: tell: {_first_clause(spec['tell'])}. Do instead: {_first_clause(spec['prevented_by'])}."
        for key, spec in top
    ]
    lines += [
        "",
        "## Load only when needed",
        "",
        "- `references/routes.md`: file extension → language pack → the command for each gate",
        f"- `references/shapes.md`: one line per recorded failure shape ({len(modes)}): id, scope, tell. "
        "Find the one that fits, then read only its `## <id>` section of `references/failures.md`",
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


def chat_skill_shapes() -> str:
    """references/shapes.md: the index into failures.md, so a chat pulls one entry, never the whole ledger."""
    lines = [
        "# Failure shapes: index",
        "",
        "GENERATED from atlas.yaml/agent_failure_modes. `thea` = about Thea's own code.",
        "",
    ]
    lines += [
        f"- `{key}` ({'thea' if repo_internal(spec) else 'any'}): {_first_clause(spec['tell'])}"
        for key, spec in _by_sightings()
    ]
    return "\n".join(lines) + "\n"


def chat_skill_failures() -> str:
    """references/failures.md: the whole failure ledger, most-sighted first."""
    modes = _by_sightings()
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
