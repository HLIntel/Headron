#!/usr/bin/env python3
"""Every document section and file GENERATED from atlas.yaml, and the writer that repairs them.

A document that restates the source of truth drifts from it silently, and the reader cannot tell a
current copy from a stale one. So each restatement is written between markers by `index --write`,
and `atlas.py check` fails on any difference: the repository's copy of its own rosters is derived,
never maintained.
"""
from __future__ import annotations

import functools
import json
import re
from collections.abc import Callable
from pathlib import Path

import chatskill
import dirscope
import textguard
from atlascore import ROOT, atlas, label_for, read, rel, route_for, route_targets, routes, strict_yaml, tracked
from packmanifest import MANIFEST_SCHEMA, declared_entries, manifest_schema


# Generated blocks: every place a document restates atlas.yaml is written FROM
# atlas.yaml between these markers, and check() fails on drift.
def _begin(name: str) -> str:
    return f"<!-- BEGIN generated: {name} (python scripts/atlas.py index --write) -->"


def _end(name: str) -> str:
    return f"<!-- END generated: {name} -->"


def language_index_block() -> str:
    rows = ["| route | guide | operating card | tool manifest |", "|---|---|---|---|"]
    # An umbrella pack (quantum/) has no extension of its own but owns routed children;
    # it is indexed beside them so the guide-reachability check sees it.
    umbrellas = sorted({t.rsplit("/", 1)[0] for t in route_targets() if "/" in t})
    for language in umbrellas + route_targets():
        base = ROOT / "languages" / language
        card = f"[card]({language}/OPERATING.md)" if (base / "OPERATING.md").exists() else "missing"
        manifest = "`tools.yaml`" if (base / "tools.yaml").exists() else "none"  # beside the card
        rows.append(f"| `{language}` | [guide]({language}/README.md) | {card} | {manifest} |")
    present = sum((ROOT / "languages" / lang / "tools.yaml").exists() for lang in route_targets())
    return (f"Derived from `atlas.yaml/artifact_routes` — {len(route_targets())} routes + {len(umbrellas)} "
            f"umbrella, {present} tool manifests.\n\n" + "\n".join(rows))


def manifest_contract_block() -> str:
    """The required manifest shape, rendered FROM tools/tools.schema.json."""
    schema = manifest_schema()
    props = schema["properties"]
    auth = props["authority"]["required"]
    prof = props["profiles"]["required"]
    pol = props["policy"]["required"]
    # READ, NEVER TYPED. This line said `schema: 1` after the format moved to 2, inside a block
    # whose own prose promises it cannot drift — so the canonical skeleton produced a manifest
    # `atlas.py check` rejects. A generator that hardcodes a value it could read is a document
    # with extra steps.
    lines = [f"schema: {props['schema']['const']}",
             "language: <the pack directory's own name>", "provenance:"]
    lines += [f"  {k}:" for k in props["provenance"]["required"]]
    lines.append("authority:")
    lines += [f"  {role}:" + ("  # https URL" if role in ("docs", "research") else "  # entry")
              for role in auth]
    lines.append("profiles:")
    lines += [f"  {task}: []" for task in prof]
    lines.append("policy:")
    lines += [f"  {key}:" for key in pol]
    lines.append("notes:                     # optional: prose, keyed by the role it qualifies")
    kinds = manifest_schema()["$defs"]["entry"]["x-kinds"]
    table = ["", "Every entry is one of these kinds, and the kind is declared, never inferred:", "",
             "| kind | written as | means |", "|---|---|---|"]
    # A literal pipe inside a Markdown cell ends the cell, so it is escaped on the way out.
    def cell(text: str) -> str:
        return str(text).replace("|", "\\|")
    table += [f"| `{kind}` | `{cell(spec['example'])}` | {cell(spec['means'])} |" for kind, spec in kinds.items()]
    return (f"Derived from `{MANIFEST_SCHEMA}` — {len(schema['required'])} required top-level keys, "
            f"{len(auth)} authority roles, {len(prof)} task profiles, {len(kinds)} entry kinds.\n\n"
            "```yaml\n" + "\n".join(lines) + "\n```\n" + "\n".join(table))


def precedence_block() -> str:
    items = (atlas().get("routing_policy") or {}).get("precedence") or []
    return "```text\n" + "\n    -> ".join(str(i) for i in items) + "\n```"


def lanes_block() -> str:
    pattern = str((atlas().get("branch_policy") or {}).get("language_lane_pattern", "lang/<language>/<topic>"))
    rows = ["| Route | Label | Branch namespace |", "|---|---|---|"]
    for language in route_targets():
        lane = pattern.replace("<language>", language).replace("<topic>", "*")
        rows.append(f"| `{language}` | `{label_for(language)}` | `{lane}` |")
    return "Derived from `atlas.yaml/artifact_routes` + `branch_policy.language_lane_pattern`.\n\n" + "\n".join(rows)


BUILD_RULES = (
    ("No count typed into prose.", "Generate it, or name the instrument that prints it."),
    ("No calendar date.", "Stamp a claim with its contract version; only an external project's own date-shaped "
     "version (`atlas.yaml/external_versions`) is exempt."),
    ("No tool name in prose.", "Tools live in `languages/<route>/tools.yaml`; documents name *gates*."),
    ("Refuse rather than invent.", "`none` is a real answer; a parser that picks a winner on ambiguous input is "
     "worse than one that errors."),
    ("Every limit names its closer.", "All {instruments} instruments carry `proves`, `does_not_prove` and "
     "`closed_by`; an empty closer fails."),
    ("Never raise a cap to fit your code.", "`code_shape` and `context_policy` ratchets only fall: split the "
     "function or shrink the entry path."),
    ("A change ends when the artifact parses.", "Every tracked source and JSON file must parse; that check runs first."),
    ("A control with no enforcer is refused.", "Controls, sandbox rows and gates each name their deciding function "
     "(`atlas.yaml/agent_policy`)."),
)
# The verbs llms.txt lists, in the order an agent reaches for them; usage and help come from the parser.
LLMS_VERBS = ("port", "route", "gate", "do", "plan", "shell", "why", "failures", "landed", "check", "verify", "doctor", "commands")


def _rule_lines(instruments: int) -> list[str]:
    import textwrap  # noqa: PLC0415

    return [ln for i, (title, detail) in enumerate(BUILD_RULES, 1) for ln in textwrap.wrap(
        f"{i}. **{title}** {detail.format(instruments=instruments)}", width=101, subsequent_indent="   ",
        break_long_words=False, break_on_hyphens=False)]


def _verb_lines() -> list[str]:
    from commands import command_table  # noqa: PLC0415

    table, actions = command_table(), "|".join(atlas().get("pack_actions") or {})

    def usage(verb: str) -> str:
        args = [a for a in table[verb]["arguments"] if not a.option_strings]
        return " ".join([verb, *(f"[<{a.dest}>]" if a.nargs in ("?", "*") else f"<{a.dest}>" for a in args)])

    return [f"- `{usage(v)}`: {table[v]['help']}" + (f"; action: {actions}" if v == "do" else "") for v in LLMS_VERBS]


def agent_entrypoint(flavour: str) -> str:
    """The instructions an agent runtime loads automatically, in the convention it expects.

    THREE CONVENTIONS, ONE DECLARATION. Claude Code reads CLAUDE.md, Codex and opencode read
    AGENTS.md, and the llms.txt convention is its own file — so a repository that wants to be
    usable by all three either maintains three documents that drift, or generates them. This
    generated one was the missing piece: before it, a session opening this repository was given
    NOTHING automatically and had to find MODEL.md by luck, in a tree whose whole point is that
    you ask it where to go instead of reading it.

    AGENTS.md used to be REFUSED by the contract — "stale root AGENTS.md exists; MODEL.md is
    canonical" — which served the right goal (no second hand-maintained source) with the wrong
    mechanism. Generation serves that goal and the convention at once.
    """
    version = read("VERSION").strip()
    gates = list(((atlas().get("verification_policy") or {}).get("profiles") or {}))
    instruments = list(atlas().get("instruments") or {})
    claude = flavour == "claude"
    title = "CLAUDE.md" if claude else "AGENTS.md"
    lines = [
        f"# {title} — {(atlas().get('identity') or {}).get('project_name', 'Thea')}, contract v{version}",
        "",
        "**GENERATED by `python scripts/atlas.py index --write`; `atlas.py check` fails on any hand",
        "edit.** It comes from `atlas.yaml`, `VERSION` and the tree: change the declaration, not this file.",
        "",
        "## Ask, do not read",
        "",
        "**Never read this repository breadth-first.** Ask where to go, then load only what the answer names.",
        "",
        __import__("port").plug_line("claude" if claude else "agents"),
        "",
        "```bash",
        "python scripts/atlas.py gate  <path> <gate>    # ONE command: cheapest answer, most accurate",
        "python scripts/atlas.py plan  <path> --task <task> --change <class> [--modifier <m>] --json",
        "python scripts/atlas.py check                  # exit code IS the verdict; doctor: can it run here",
        "```",
        "",
        f"Asked to *{', '.join(atlas()['intents'])}* this repository? `llms.txt` → *When asked to*.",
        "Directed into a role? `thea role`. Picking up interrupted work? `thea resume`. `--json` records",
        "are frozen in `tools/atlas-output.schema.json`: depend on those ids.",
        "",
        "## Rules that fail the build",
        "",
        *_rule_lines(len(instruments)),
        "",
        "## Mistakes made here before, by an agent",
        "",
        "Each RECURRED here: once is a bug, twice a rule. Learn the shapes; they return in other files.",
        "",
        _recurring_mistakes(),
        "",
        "## Before you claim a change is done",
        "",
        "Pick the change class (" + ", ".join(f"`{gate}`" for gate in gates) + ") and satisfy its",
        "gates, then verify **on the exit code**, never on output:",
        "",
        "```bash",
        "python scripts/verify.py    # PASS / FAIL / NOT RUN per gate; exit 0 only if every gate passed",
        "```",
        "",
        "It runs `verification_policy/done_set`: " + ", ".join(
            f"`{g['id']}`" for g in (atlas().get("verification_policy") or {}).get("done_set") or []) + ".",
        "",
        "Both suites plant a real defect per rule and assert their own case counts: new rule, new planted",
        "defect. Land with `python scripts/branchstate.py --land`; a bare push of a lane is refused.",
        "",
        "## Where to put what",
        "",
        "Repeated fact: `atlas.yaml` plus a generated block. Language tool: its pack's `tools.yaml`. New",
        "rule: its own `*_errors()` and planted defect. Example: `examples/`, and it must run."
    ]
    if claude:
        lines += [
            "",
            "## Claude Code specifics",
            "",
            "- Deterministic rules belong in hooks, not instructions: instructions are not a sandbox.",
            "- Adapter: [models/claude/README.md](models/claude/README.md).",
        ]
    else:
        lines += [
            "",
            "## Runtime notes",
            "",
            "- One body for every runtime: CLAUDE.md imports this file, Hermes reads `.agent/bootstrap.json`,",
            "  a bare model `llms.txt`. Each runtime's adapter: `models/<runtime>/README.md`; roster: [MODEL.md](MODEL.md).",
        ]
    return "\n".join(lines) + "\n"


def claude_md() -> str:
    """AGENTS.md by import, not copy (3.10.0): Claude Code expands `@path`; contextcost counts it."""
    full = agent_entrypoint("claude")
    own = full[full.index("## Claude Code specifics"):]
    return f"<!-- GENERATED by `atlas.py index --write`; edit atlas.yaml, not this file. -->\n@AGENTS.md\n\n{own}"


def agents_md() -> str:
    return agent_entrypoint("agents")


def llms_txt() -> str:
    """llms.txt — the machine-readable entry point, in the convention agents already look for.

    WHY A GENERATED FILE AND NOT A HAND-WRITTEN ONE: an index an agent reads is a roster, and a
    roster maintained by hand narrows silently the first time something is added beside it. Every
    line below is derived from atlas.yaml, the CLI parser and files confirmed to exist, so this
    file cannot name a document or a verb the repository does not have. check() fails on any drift.
    It is the worst-case runtime entry, so every line is an answer: verbs, records, rules, routes.
    """
    def link(path: str, note: str) -> str:
        return f"- [{path}]({path}): {note}" if (ROOT / path).exists() else ""

    hooks = " · ".join(f"{when} `{run}`" for when, run in (__import__("port").spec().get("hooks") or {}).items())
    ident = atlas()["identity"]
    lines = [
        f"# {ident['project_name']} by {ident['display_name']} (contract v{read('VERSION').strip()})",
        "",
        "> Rules and build checks for AI coding agents: for any file, which commands prove a change there.",
        "",
        "<!-- GENERATED from atlas.yaml by `atlas.py index --write`; do not edit. -->",
        "",
        "**First reply:** work under Thea for the session, do one thing from it now, file any gap in it with "
        "the report verb, then ask for their file or task. No shell: [CHAT.md](CHAT.md), skill first.",
        "",
        "## Verbs",
        "",
        "`thea <verb>` installed, `python scripts/atlas.py <verb>` in a clone, read-only over MCP (`thea-mcp`). "
        "Exit code is the verdict; `--json` records are frozen in `tools/atlas-output.schema.json`.",
        "",
        *_verb_lines(),
        "",
        f"Hooks: {hooks}.",
        "",
        "## Records",
        "",
        "- `.agent/bootstrap.json`: this entry as one record · `.agent/facts.json`: every published figure",
        "- `AGENTS.md`/`CLAUDE.md`: agent runtimes · `CHAT.md`: a chat with no shell",
        "",
        "## Rules that fail the build",
        "",
        " · ".join(f"{i} {title.rstrip('.')}" for i, (title, _) in enumerate(BUILD_RULES, 1)) + ". Detail: AGENTS.md.",
        "",
        f"## When asked to {', '.join(atlas()['intents'])}",
        "",
        *(f"- **{verb}**: {spec['agent']}." for verb, spec in atlas()["intents"].items()),
        "",
        "## Packs",
        "",
        # ONE LINE STATES WHAT EVERY PACK LINE REPEATED (2.28.0): links cost ~40 B a pack on the paid
        # surface; `check` proves every pack has its guide, card and manifest, so the convention holds.
        "`languages/<pack>/`: `README.md` guide · `OPERATING.md` card · `tools.yaml` commands. "
        "`route <file>` names the pack; read it first.",
        "",
        " · ".join(route_targets()),
        "",
        "## Files",
        "",
    ]
    lines += [ln for ln in (
        link("MODEL.md", "the operating model; read it after `gate`, when a route names it"),
        link("atlas.yaml", "single source of truth: routes, invariants, gates, profiles, policy"),
        link("docs/INDEX.md", "every document"),
        link("docs/VERIFY.md", "the verification ladder"),
        link("docs/ENGINEERING-CONCEPTS.md", "why each rule exists, paired with its mechanism"),
        link("docs/VERSIONING.md", "one line per version, the only changelog"),
        link("SECURITY.md", "security policy and measured platform controls"),
        link("LICENSE", "MIT"),
    ) if ln]
    return "\n".join(lines) + "\n"


def instruments_block() -> str:
    """The instrument roster, rendered FROM atlas.yaml/instruments.

    Every limit names its closer, because that is what atlas.yaml enforces. A table of limits
    with no closers is a list of excuses that ages into a list of defects.
    """
    # TWO COLUMNS, NOT FOUR. The `closed_by` field is the load-bearing one and it is ENFORCED —
    # check() refuses an instrument that leaves it empty — so restating all 20 closers here spent
    # ~4 KB of the landing page re-rendering something a machine already guarantees. The limit
    # stays where it is checked; the page names it and says where to read it.
    rows = ["| instrument | proves | does not prove |", "|---|---|---|"]
    for name, spec in (atlas().get("instruments") or {}).items():
        def cell(key: str, limit: int) -> str:
            text = " ".join(str(spec.get(key, "")).split()).replace("|", "\\|")
            return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"
        rows.append(f"| `{name}` | {cell('proves', 130)} | {cell('does_not_prove', 110)} |")
    return ("Derived from `atlas.yaml/instruments`. Run them; do not read a number about them from "
            "this page. **Every one also declares `closed_by`** — what covers the limit in column "
            "three — and `check` refuses an instrument that leaves it empty. A generated block is "
            "read wherever it is placed, so this NAMES `atlas.yaml/instruments` rather than "
            "linking it: a relative link is correct only for the document it was written in, and "
            "moving this block off the landing page broke exactly that.\n\n" + "\n".join(rows))


def measured_block() -> str:
    from abtest import measured_block as _measured  # noqa: PLC0415 — the A/B owns its evidence's rendering
    return _measured()


def runtime_entry_block() -> str:
    """What each runtime loads by itself, measured. Bounded by runtimes, which arrive rarely — unlike a
    roster that grows by a row per pack, this one earns its place on the ratcheted landing page."""
    from contextcost import loaded_size, tokens
    rows = ["| runtime | loads by itself | ~tokens |", "|---|---|---|"]
    for entry in atlas().get("runtime_entry") or []:
        name, loads = entry["runtime"], entry["loads"]
        cost = tokens(max(loaded_size(loads), 0))
        rows.append(f"| {'**' + name + '**' if name == 'Claude Code' else name} | `{loads}` | {cost:,} |")
    return "\n".join(rows) + "\n\nMeasured from each file on every build."


def facts_block() -> str:
    """Every count this page would otherwise state in prose, derived on every run.

    A number typed into a document is stale the moment the tree moves, and the reader cannot see
    that it moved. So no count is typed anywhere in the documents: each one is computed here and
    `atlas.py check` fails when the rendered block differs from the tree.

    FIVE COUNTS ARE NOT ROWS HERE, and that is the point rather than an omission:
    the `glance` block prints both counts at the top of the same page, so a row for each was the
    same fact twice inside ONE budgeted entry path. It was cut when the sixth agent control pushed
    that path 8 bytes over its ratchet — and the cheapest cut is duplication, never wordsmithing,
    because a byte shaved off a sentence comes back with the next instrument. Extensions and routes
    went the same way at 3.38.0, to pay for the agreement-edge count, which is the one figure that
    says whether the other counts are BACKED: a roster is a claim, an edge is a claim with a file
    behind it.
    """
    f = repository_figures()
    rows = [
        ("contract version", read("VERSION").strip(),
         f"`VERSION`, asserted at a declared line in {f['version_sites']} other files"),
        ("tool manifests", f["tool_manifests"], f"`languages/<route>/tools.yaml`, validated against `{MANIFEST_SCHEMA}`"),
        ("declared tool entries", f["tool_entries"], "distinct entries per manifest, summed; `packprobe.py` classifies every one"),
        ("entry kinds", f["entry_kinds"], f"`{MANIFEST_SCHEMA}` `$defs.entry.x-kinds`"),
        ("change classes (verification profiles)", f["gate_classes"], "`atlas.yaml/verification_policy/profiles`"),
        ("task profiles", f["task_profiles"], "`atlas.yaml/task_profiles`"),
        ("python files in the harness", f["harness_py"], "`scripts/*.py`, every one held by the " + " · ".join(
            f"`{g['id']}`" for g in (atlas().get("verification_policy") or {}).get("done_set") or []
            if g["id"] in ("lint", "format", "typecheck")) + " gates"),
    ]
    # BULLETS, NOT A TABLE (3.1.0): a three-column table scrolled sideways on a phone; each fact still
    # names its source on its own line. NUMBER FIRST (3.53.0): mid-sentence figures gave the eye no
    # column to scan, so every row leads with its bold value, as the glance line does.
    return "\n".join(f"- **{value}** {label} — {source}" for label, value, source in rows)


def repository_figures() -> dict:
    """The repository-facts counts as data: the README block renders them and `.agent/facts.json` carries them."""
    manifests = list((ROOT / "languages").rglob("tools.yaml"))
    entries = sum(
        len(declared_entries(strict_yaml(m.read_text(encoding="utf-8"), str(m)) or {})) for m in manifests
    )
    return {
        "version_sites": len(atlas().get("version_sites") or {}),
        "tool_manifests": len({m.parent.name for m in manifests}),
        "tool_entries": entries,
        "entry_kinds": len(manifest_schema()["$defs"]["entry"]["x-kinds"]),
        "gate_classes": len((atlas().get("verification_policy") or {}).get("profiles") or {}),
        "task_profiles": len(atlas().get("task_profiles") or {}),
        "harness_py": len(list((ROOT / "scripts").glob("*.py"))),
    }


def language_roster_block() -> str:
    """Every route as one compact line — the count is the length of this list, never a typed number."""
    rows = []
    for target in route_targets():
        extensions = sorted(ext for ext, route in routes().items() if route == target)
        rows.append(f"`{target}`" + (f" ({' '.join(extensions)})" if extensions else ""))
    return (f"{len(rows)} routes, each with a guide, an operating card and a tool manifest — "
            "the full table with links is in `languages/README.md`.\n\n"
            + " · ".join(rows))


def route_table_block() -> str:
    """Extension -> route -> the pack that answers, from atlas.yaml.

    The hand-written version of this table named a "native authority" per row — `Pyright` where the
    pack declares `basedpyright`, `.NET SDK` where it declares `dotnet` — and omitted six routes
    entirely. A route's authority is its manifest; this table's job is to say which manifest.
    """
    by_route: dict[str, list[str]] = {}
    for extension, route in sorted(routes().items()):
        by_route.setdefault(route, []).append(extension)
    rows = ["| artifact | route |", "|---|---|"]
    for route in route_targets():
        rows.append(f"| {' '.join(f'`{e}`' for e in by_route.get(route, []))} | `{route}` |")
    # Each pack's links live once, in languages/README.md: 72 copies here doubled the link count.
    return ("Derived from `atlas.yaml/artifact_routes`. The authority is each route's `tools.yaml`, linked\n"
            "with its card in the [language index](../languages/README.md#language-index).\n\n"
            + "\n".join(rows))


def _profile_table(section: str, column: str, preamble: str) -> str:
    """One renderer for both profile tables.

    FOUND BY astshape, IN CODE WRITTEN MINUTES EARLIER: `task_profile_block` and
    `tool_profile_block` had the same canonical AST — erase the names and they were one function
    rendering a mapping of name to list as a two-column table. The tool's advice was "import one,
    delete the rest", and this is that, with the difference passed in rather than copied.
    """
    rows = [f"| {section.rstrip('s').replace('_', ' ')} | {column} |", "|---|---|"]
    for name, entries in (atlas().get(section) or {}).items():
        rows.append(f"| `{name}` | " + " · ".join(f"`{entry}`" for entry in entries or []) + " |")
    return f"{preamble}\n\n" + "\n".join(rows)


def task_profile_block() -> str:
    """Every task profile and what it activates, from atlas.yaml."""
    return _profile_table(
        "task_profiles", "what it activates",
        "Derived from `atlas.yaml/task_profiles`, resolved for one artifact by\n"
        "`python scripts/atlas.py plan <path> --task <name>`.")


def tool_profile_block() -> str:
    """Every tool profile, from atlas.yaml — the smallest set a task may activate."""
    return _profile_table(
        "tool_profiles", "tools",
        "Derived from `atlas.yaml/tool_profiles`. Use the smallest profile that satisfies the task;\n"
        "native compiler, LSP, debugger, test and profiler output stays authoritative.")


def runtime_block() -> str:
    """Runtimes and what each is routed for, from atlas.yaml — not a hand list in MODEL.md."""
    routes_by_runtime: dict[str, list[str]] = {}
    for task, runtimes in (atlas().get("model_routes") or {}).items():
        for runtime in runtimes or []:
            routes_by_runtime.setdefault(str(runtime), []).append(str(task))
    roles = atlas().get("runtime_roles") or {}
    declared_adapter = {str(e.get("id")): str(e.get("adapter")) for e in atlas().get("runtime_entry") or []}
    rows = ["| runtime | routed for | declared role | adapter |", "|---|---|---|---|"]
    for runtime in sorted(set(routes_by_runtime) | set(roles)):
        tasks = " · ".join(f"`{t}`" for t in sorted(routes_by_runtime.get(runtime, []))) or "—"
        role = f"`{roles[runtime]}`" if runtime in roles else "—"
        # ONE MAPPING: the adapter comes from runtime_entry, the declaration the entry-cost table reads
        # too. Guessing it from the folder name was a second, silent mapping, and it left Codex
        # (`openai_codex`, folder `openai`) with no adapter link at all.
        path = declared_adapter.get(runtime) or f"models/{runtime}/README.md"
        adapter = f"[{Path(path).parent.as_posix()}]({path})" if (ROOT / path).exists() else "—"
        rows.append(f"| `{runtime}` | {tasks} | {role} | {adapter} |")
    # A hand-written roster here once named seven runtimes and omitted the two verification ones.
    return "Derived from `atlas.yaml/model_routes` and `runtime_roles`.\n\n" + "\n".join(rows)


def severity_block() -> str:
    """The severity classes and the baseline rule, from atlas.yaml."""
    policy = atlas().get("verification_policy") or {}
    rows = ["| class | effect on a merge |", "|---|---|"]
    rows += [f"| `{k}` | `{v}` |" for k, v in (policy.get("severity") or {}).items()]
    rule = str(policy.get("baseline_rule", "")).strip()
    return ("Derived from `atlas.yaml/verification_policy`.\n\n" + "\n".join(rows)
            + (f"\n\n**Baseline rule:** `{rule}`. A pack may declare `policy.warnings: blocking` in its own\n"
               "manifest, which is the one thing that changes the answer for that route." if rule else ""))


def canonical_flow_block() -> str:
    """The canonical layer order, from atlas.yaml/default_flow."""
    steps = [s.strip() for s in str(atlas().get("default_flow", "")).split("->") if s.strip()]
    return ("Derived from `atlas.yaml/default_flow` — the order a reader, an agent or an instrument\n"
            "should consult these in.\n\n"
            + "\n".join(f"{i}. `{step}`" for i, step in enumerate(steps, 1)))


def landed_states_block() -> str:
    """The landing states as a state diagram, from atlas.yaml/branch_policy/landed_states (3.50.0).

    MERMAID WHERE THE SHAPE IS A GRAPH, and only generated: a state machine reads at a glance as edges
    and costs fewer bytes than the prose that walks it; a flat roster stays a table, which a diff reads.
    """
    states = list(atlas()["branch_policy"]["landed_states"])
    edges = "\n".join(f"  {a} --> {b}" for a, b in zip(["[*]", *states], [*states, "[*]"], strict=True))
    return ("Derived from `atlas.yaml/branch_policy/landed_states`; `branchstate.py --land` reads each one back.\n\n"
            "```mermaid\nstateDiagram-v2\n" + edges + "\n```")


def best_practices_block() -> str:
    """The OpenSSF Best Practices answer sheet, rendered from data.

    Every evidence path is emitted as a Markdown link, so the contract's link checker validates it:
    an answer citing a file that does not exist fails the build rather than a reviewer.
    """
    sheet = json.loads(read("config/openssf-best-practices.json"))
    rows = ["| criterion | answer | evidence |", "|---|---|---|"]
    for item in sheet["criteria"]:
        path = item["evidence"]
        # The link is written FROM docs/CERTIFICATION.md: a sibling in docs/ drops that segment,
        # anything else climbs one. Emitting the repository-relative path unchanged produced
        # docs/docs/VERIFY.md, which the contract's link checker refused — as it should.
        target = path[len("docs/"):] if path.startswith("docs/") else f"../{path}"
        rows.append(f"| `{item['id']}` | {item['answer']} | [{path}]({target}) — {item['note']} |")
    return (f"Derived from `config/openssf-best-practices.json` — {len(sheet['criteria'])} criteria at the "
            f"**{sheet['level']}** level, each with the file that answers it. Registration at "
            f"{sheet['registry']} is a sign-in and a paste.\n\n" + "\n".join(rows))


def scorecard_floors_block() -> str:
    """Every declared Scorecard floor, from config/github-controls.json.

    The floors were hand-copied into CERTIFICATION.md, which is the one thing that can disagree
    with a ratchet — the page's own argument is that the floors live in the declaration and only
    move up. A second copy could move down without anybody noticing.
    """
    card = json.loads(read("config/github-controls.json")).get("scorecard") or {}
    floors = card.get("check_floors") or {}
    rows = ["| check | floor |", "|---|---|"]
    rows += [f"| `{name}` | {floor} |" for name, floor in sorted(floors.items())]
    return (f"Derived from `config/github-controls.json`: {len(floors)} checks carry a floor, and the\n"
            "aggregate floor is "
            f"{card.get('minimum', '—')}. `python scripts/ghaudit.py` prints the live value beside each\n"
            "one and reports every check below its floor — this page states no measurement.\n\n"
            + "\n".join(rows))


def gate_detail_block() -> str:
    """Every change class with what it requires, and every tier, from atlas.yaml.

    VERIFY.md used to name tools — `pyright`, `staticcheck`, `npm test` — none of which matched the
    manifests that own those roles, and it covered four routes while being the canonical
    verification document for all of them. Naming a tool in prose is how that happens: the roster
    lives in each pack's tools.yaml, so this block names the GATE and never the tool.
    """
    policy = atlas().get("verification_policy") or {}
    rows = ["| change class | what it requires |", "|---|---|"]
    for name, spec in (policy.get("profiles") or {}).items():
        required = " · ".join(f"`{step}`" for step in (spec or {}).get("required", []))
        rows.append(f"| `{name}` | {required} |")
    tiers = ["", "Tiers, cheapest sufficient first — each includes the one before it:", "",
             "| tier | adds |", "|---|---|"]
    tiers += [f"| `{name}` | " + " · ".join(f"`{s}`" for s in (steps or [])) + " |"
              for name, steps in (policy.get("tiers") or {}).items()]
    severity = ["", "Severity, and what each one does to a merge:", "", "| class | effect |", "|---|---|"]
    severity += [f"| `{k}` | `{v}` |" for k, v in (policy.get("severity") or {}).items()]
    return ("Derived from `atlas.yaml/verification_policy`. The gate names a REQUIREMENT; the tool that\n"
            "satisfies it is declared per route in `languages/<route>/tools.yaml`, which is the only\n"
            "place a tool name lives.\n\n" + "\n".join(rows + tiers + severity))


def build_order_block() -> str:
    """The declared order of work, rendered from atlas.yaml so the document cannot disagree."""
    steps = atlas().get("build_order") or []
    rows = ["| # | step | gate that judges it |", "|---|---|---|"]
    rows += [f"| {i} | `{s.get('step')}` | `{s.get('gate')}` |" for i, s in enumerate(steps, 1)]
    rule = str(atlas().get("build_order_rule", "")).strip()
    return "\n".join(rows) + (f"\n\n**{rule[0].upper() + rule[1:]}.**" if rule else "")


def examples_block() -> str:
    """Every example, routed and with its runner — the hand-written table had gone stale at 6 of 11."""
    runners = atlas().get("example_runners") or {}
    rows = ["| example | route | how it runs |", "|---|---|---|"]
    # exrun's roster, never a second one: a table that picked its own files listed 4 exrun never runs.
    from exrun import examples  # noqa: PLC0415
    for path in examples():
        name = path.relative_to(ROOT).as_posix()
        route = route_for(str(path))
        recipe = (runners.get(route) or {}).get("steps") if route else None
        how = f"`{' '.join(recipe[0]).replace('{file}', name)}`" if recipe else "not routed to a runner"
        rows.append(f"| `{name}` | `{route or '—'}` | {how} |")  # a link repeated the path the command names
    return ("Derived from the tree and `atlas.yaml/example_runners`. Every row is executed by\n"
            "`python scripts/exrun.py`, which CI runs before the contract.\n\n" + "\n".join(rows))


def packages_block() -> str:
    """What this repository declares as a package, and what it depends on."""
    pyproject = read("pyproject.toml")

    def field(key: str) -> str:
        match = re.search(rf'^{key}\s*=\s*"([^"]+)"', pyproject, re.M)
        return match.group(1) if match else "(not declared)"

    requirements = [ln.strip() for ln in read("scripts/requirements.txt").splitlines() if ln.strip()]
    rows = [
        ("harness package", f"`{field('name')}`", "declared in `pyproject.toml`; released to the index once `PYPI_PUBLISH` is on"),
        ("python required", f"`{field('requires-python')}`", "`pyproject.toml`"),
        ("runtime dependency", ", ".join(f"`{r}`" for r in requirements),
         "`scripts/requirements.txt`, mirrored in `pyproject.toml`"),
        ("what CI actually installs", "`scripts/requirements.lock.txt`",
         "hash-pinned and installed with `--require-hashes`; the contract asserts the pin sits "
         "inside the range above"),
        ("quality extra", "`ruff`", "`pyproject.toml` `[project.optional-dependencies]`"),
        ("language toolchains", "declared per pack, installed by nobody here",
         "`languages/<route>/tools.yaml`; run `python scripts/packprobe.py --mode smoke`"),
    ]
    out = ["| package surface | value | where it is declared |", "|---|---|---|"]
    out += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    return ("The atlas is not a library you install. One Python dependency runs the harness; every\n"
            "language toolchain is declared by a pack and installed by the machine that needs it.\n\n"
            + "\n".join(out))


def topics_block() -> str:
    """Repository topics, from the declared file — the live list is ghaudit.py's answer."""
    declared = json.loads(read("config/github-controls.json"))
    topics = declared.get("topics") or []
    return ("Declared in `config/github-controls.json` and asserted against the live repository by\n"
            "`python scripts/ghaudit.py` — this page states the declaration, the instrument states\n"
            "the fact.\n\n" + " · ".join(f"`{t}`" for t in topics))


def agent_bootstrap() -> str:
    """.agent/bootstrap.json — the smallest thing an agent needs before it reads anything at all.

    WHY A RECORD AND NOT A PAGE. CLAUDE.md, AGENTS.md and llms.txt are generated and consistent and
    they are still PROSE: a runtime that loads one is reading policy at the moment it has the least
    context for it, and a reader arriving at this tree sees documents before it sees the contract
    that makes them true. This file is what a machine parses instead — the commands, the schema it
    must emit, and the one sentence that is not safe to leave implicit — with everything else
    reachable from a route it has already resolved.
    """
    data = atlas()
    policy = data.get("agent_policy") or {}
    record = {
        "schema": 1,
        "project": (atlas().get("identity") or {}).get("project_name"),
        "atlas_version": read("VERSION").strip(),
        "read_nothing_first": "port first, then load only what it names",
        "commands": {
            "port": "python scripts/atlas.py port <path> --frame agent --json",
            "gate": "python scripts/atlas.py gate <path> <gate> --json",
            "plan": "python scripts/atlas.py plan <path> --task <task> --change <class> --json",
            "check": "python scripts/atlas.py check",
            "doctor": "python scripts/atlas.py doctor --json",
            "policy": "python scripts/agentpolicy.py <contract>",
            "run": "python scripts/agentrun.py <contract> --json",
            "installed": "atlas --atlas-root <checkout> port <path> --json; `atlas --where` names the atlas",
        },
        "intents": "/".join(data.get("intents") or {}) + ": llms.txt, When asked to",
        "hooks": dict((data.get("port") or {}).get("hooks") or {}),
        "output_schema": "tools/atlas-output.schema.json",
        # EVERY RUNTIME READS THIS RECORD, so the rename lives here rather than in one editor's
        # notes: opencode, hermes, cursor and any future session get the same answer about
        # who owns this tree and what is staged.
        "identity": {
            "owner": (data.get("identity") or {}).get("owner"),
            "repository": (data.get("identity") or {}).get("repository"),
            "rename_staged": (((data.get("identity") or {}).get("successor")) or {}).get("owner"),
            "rename_applied": (((data.get("identity") or {}).get("successor")) or {}).get("applied"),
            "rule": "display renames; what RESOLVES does not — identity/published_interfaces",
        },
        "processes": sorted(data.get("processes") or {}),
        "task_contract_schema": policy.get("schema"),
        "reference_contract": policy.get("reference_contract"),
        "controls": sorted(policy.get("controls") or {}),
        "change_classes": sorted((data.get("verification_policy") or {}).get("profiles") or {}),
        "task_profiles": sorted(data.get("task_profiles") or {}),
        "forbidden_context": list((data.get("context_policy") or {}).get("forbidden_default") or []),
        "failure_modes": "thea failures --for <path>: mistakes made here, each with its tell and refusal; thea successes: the moves",
        "not_a_security_boundary": (
            "the runner refuses what it is asked about; an agent that does not ask is bounded by "
            "the host, per atlas.yaml/agent_policy/sandbox_requirements"),
        "verify_on": "the exit code, never a line of output",
    }
    return json.dumps(record, indent=2, sort_keys=False) + "\n"


# path -> generator. A GENERATED FILE is written whole by `index --write`; check() fails on
# drift exactly as it does for a generated block inside a document.
def brewfile() -> str:
    from exrun import brewfile as _brewfile  # noqa: PLC0415 — the example runner owns its toolchains
    return _brewfile()


def public_facts() -> str:
    """.agent/facts.json — every public figure as a key (3.54.0). The site and TheaOS read this,
    never a regex over README prose: a block that moved pages broke that silently."""
    from abtest import measured_figures  # noqa: PLC0415
    from knowledge import glance_figures  # noqa: PLC0415

    facts = {"version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(), **glance_figures(), **measured_figures(), **repository_figures()}
    return json.dumps({"schema": 1, "facts": facts}, indent=2, sort_keys=True) + "\n"


GENERATED_FILES: dict[str, Callable[[], str]] = {
    ".agent/facts.json": public_facts,
    "Brewfile": brewfile,
    "llms.txt": llms_txt,
    "CHAT.md": chatskill.chat_md,
    f"{chatskill.CHAT_SKILL}/SKILL.md": chatskill.chat_skill,
    f"{chatskill.CHAT_SKILL}/references/routes.md": chatskill.chat_skill_routes,
    f"{chatskill.CHAT_SKILL}/references/failures.md": chatskill.chat_skill_failures,
    f"{chatskill.CHAT_SKILL}/references/shapes.md": chatskill.chat_skill_shapes,
    f"{chatskill.CHAT_SKILL}/references/moves.md": chatskill.chat_skill_moves,
    ".agent/bootstrap.json": agent_bootstrap,
    "CLAUDE.md": claude_md,
    "AGENTS.md": agents_md,
    "agreement.lock": lambda: __import__("agreement").lock_file(),
}
# THE PER-DIRECTORY READS, DERIVED FROM directory_scopes RATHER THAN LISTED BESIDE IT. Typing these
# into GENERATED_FILES or into atlas.yaml/generated_files would be a second declaration of the scope
# roster, free to disagree with it — `a_derived_roster_written_out_by_hand`, already committed here.
GENERATED_FILES.update({
    reference_path: functools.partial(dirscope.reference, reference_path.split("/", 1)[0])
    for reference_path in sorted(dirscope.generated_references())
})


# name -> (files that carry the block, generator). check() asserts every one.
BLOCKS: dict[str, tuple[tuple[str, ...], Callable[[], str]]] = {
    "language-index": (("languages/README.md",), language_index_block),
    "routing-precedence": (("wiki/CODE-ROUTING.md",), precedence_block),
    "manifest-contract": (("languages/PACK-TOOLS-SPEC.md",), manifest_contract_block),
    # README ONLY: in both README and MODEL.md, which sit on one entry path, every reader paid for the
    # same table twice. duplicate_prose_errors now refuses that shape.
    "language-lanes": (("wiki/LANGUAGE-LANES.md",), lanes_block),
    # NOT README: this roster grows by one row per instrument, and the landing page is on a
    # ratcheted entry path. A table whose length is a function of how many instruments exist
    # has no place in a document handed to every reader before they have asked anything.
    "instruments": (("docs/INSTRUMENTS.md",), instruments_block),
    "agreement-edges": (("docs/CERTIFICATION.md",), lambda: __import__("agreement").edges_block()),
    "repository-facts": (("README.md",), facts_block),
    "runtime-entry": (("models/README.md",), runtime_entry_block),
    "measured-benefits": (("README.md",), measured_block),
    **{k: (("README.md",), lambda f=f: f()) for k, f in __import__("knowledge").README_BLOCKS.items()},
    **{k: ((p,), lambda f=f: f()) for k, (p, f) in __import__("knowledge").ELSEWHERE_BLOCKS.items()},
    # NOT README: a roster that grows by a row per pack, on a ratcheted landing page. It
    # belongs on the page whose job is choosing a language.
    "language-roster": (("languages/ATLAS.md",), language_roster_block),
    "thea-surface": (("docs/THEA-LANGUAGE.md",), lambda: __import__("thealang").surface_reference()),
    "thea-places": (("docs/THEA-LANGUAGE.md",), dirscope.places_block),
    "mechanism-harvest": (("docs/LANGUAGE-SPEC.md",), lambda: __import__("declcheck").mechanism_block()),
    # NOT README: another roster that grows by a row per package, on a ratcheted entry path.
    "packages": (("docs/PACKAGE-CATALOG.md",), packages_block),
    "examples-index": (("examples/README.md",), examples_block),
    "build-order": (("systems/BACKEND-ARCHITECTURE.md",), build_order_block),
    "gate-detail": (("docs/VERIFY.md",), gate_detail_block),
    "scorecard-floors": (("docs/OPENSSF.md",), scorecard_floors_block),
    "best-practices": (("docs/CERTIFICATION.md",), best_practices_block),
    "route-table": (("wiki/CODE-ROUTING.md",), route_table_block),
    "task-profiles": (("wiki/CODE-ROUTING.md",), task_profile_block),
    "tool-profiles": (("wiki/CODE-ROUTING.md",), tool_profile_block),
    "severity": (("MODEL.md",), severity_block),
    "runtimes": (("MODEL.md",), runtime_block),
    "canonical-flow": (("docs/CONSISTENCY.md",), canonical_flow_block),
    "landed-states": (("wiki/BRANCH-WORKTREES.md",), landed_states_block),
    "topics": (("ABOUT.md",), topics_block),
    # BOTH DOCUMENTS, ONE DECLARATION: the command CI executes is the command a reader pastes.
    "install": (("README.md", "docs/CONSUMING.md"), lambda: __import__("installcheck").install_block()),
}


def document_errors() -> list[str]:
    """The document rules that live beside the generator, so the SHIPPED harness pays one call for all."""
    checks = (generated_file_errors, relative_link_errors, current_version_errors, typed_size_errors,
              textguard.hidden_unicode_errors, textguard.confusable_command_errors,
              missing_path_errors)
    return [error for check in checks for error in check()]



def missing_path_errors() -> list[str]:
    """Every repository path a document names in backticks exists.

    FOUND AT 2.30.0: atlas.yaml sent toolchain installs to "the scheduled polyglot workflow", and no
    such workflow existed — a mechanism named in prose, read as covered, implemented nowhere. Links
    were checked; backticked paths were not. A path outside this tree is written `<your repo>/...`.
    """
    from atlascore import tracked  # noqa: PLC0415
    names = {rel(p) for p in tracked()}
    # SEGMENTS SPLIT ON "/", which no segment may contain, so matching is linear. The first version nested
    # a quantified group over a class holding ".", and CodeQL flagged exponential backtracking (2.30.0).
    pattern = re.compile(r"`([\w.-]+(?:/[\w.-]+)+)`")
    kinds = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".txt", ".sh", ".jsonc"}
    errors: list[str] = []
    for path in tracked():
        if path.suffix.lower() not in {".md", ".yaml", ".txt"} or not path.is_file():
            continue
        for m in pattern.finditer(path.read_text(encoding="utf-8", errors="replace")):
            target = m.group(1)
            if Path(target).suffix not in kinds:
                continue
            if target not in names and not (path.parent / target).exists() and not (ROOT / target).exists():
                errors.append(f"{rel(path)} names `{target}`, which does not exist")
    return errors


def typed_size_errors() -> list[str]:
    """A size or token cost typed into an entry document, outside a generated block, fails.

    FOUND AT 2.29.0: README said "184 KiB installed" while the instrument measured 189 — rule 1 of
    this repository ("no count typed into prose"), broken on its own landing page, because nothing
    checked that shape. Sizes are the numbers most certain to move, so they are held first; the
    entry documents are the ones every reader is handed, so they are swept first.
    """
    pattern = re.compile(r"\b\d[\d,.]*\s?(KiB|MiB|GiB|KB|MB|GB|tokens?)\b")
    errors: list[str] = []
    for path in ("README.md", "MODEL.md", "ABOUT.md", "docs/INDEX.md"):
        text = re.sub(r"<!-- BEGIN generated.*?<!-- END generated[^>]*-->", "", read(path), flags=re.S)
        errors += [f"{path}: a size typed into prose ({m.group(0)!r}) — generate it or name the instrument"
                   for m in pattern.finditer(text)]
    return errors


def current_version_errors() -> list[str]:
    """A typed "contract vX.Y.Z" names the CURRENT contract unless a stamp word says it is history.

    FOUND AT 2.28.0: the README's navigation line read `contract v2.26.0` two releases after the
    tree moved, beside a badge that served the right one. `check` passed: its version-site rule asks
    only whether the version appears ANYWHERE in the file, and this page's generated A/B stamp said
    2.28.0 — a rendering satisfied it while the claim beside it was stale. A
    claim measured AT a version ("at contract v1.0.0", "since contract v…") is history and passes.
    """
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    pattern = re.compile(r"(\w+\s+)?contract v(\d+\.\d+\.\d+)")
    errors: list[str] = []
    for path in tracked():
        if path.suffix.lower() not in {".md", ".txt"} or path.is_symlink() or not path.exists():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for found in pattern.finditer(line):
                stamp = (found.group(1) or "").strip().lower()
                if found.group(2) != version and stamp not in {"at", "since", "from", "before", "until"}:
                    errors.append(f"{rel(path)}:{number} names contract v{found.group(2)} as current; VERSION is "
                                  f"{version} — link the version badge, or stamp it 'at contract v…' if it is history")
    return errors




def relative_link_errors() -> list[str]:
    """A generated block may not carry a RELATIVE link. Caught twice; that makes it a rule.

    A generated block is rendered into whichever file registers it, and a relative link is correct
    only for the document it was WRITTEN in. Moving the instruments table to docs/ broke its link
    to atlas.yaml; moving the language roster to languages/ broke its link to languages/README.md.
    Both were caught by the link checker AFTER the move, which is late — the block is the thing
    that is portable, so the constraint belongs on the block.

    Absolute URLs and bare anchors are fine: neither depends on where the block lands. The remedy
    is to NAME the file in backticks instead, which reads the same everywhere.
    """
    errors: list[str] = []
    pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for name, (files, render) in BLOCKS.items():
        # ONE HOME IS FINE. A relative link in a block registered in exactly one file is correct
        # for that file, and the link checker already proves it resolves. THE FIRST VERSION OF
        # THIS GUARD REFUSED THOSE TOO and stripped 76 working links out of the tree before the
        # count showed it — a guard that fires on correct work does not get fixed, it gets
        # silenced, and this one was actively removing navigation to satisfy itself.
        if len(files) < 2:
            continue
        for target in pattern.findall(render()):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            errors.append(f"generated block '{name}' is registered in {len(files)} files and "
                          f"contains the relative link '{target}', which cannot be correct for all "
                          "of them — name the file in backticks instead")
    return errors


def generated_file_errors() -> list[str]:
    """The generator's map and atlas.yaml/generated_files must name exactly the same files."""
    # The scope reads are DECLARED by `directory_scopes`, one level up, so they are declared here too
    # rather than repeated in `generated_files` where the two copies could disagree.
    declared = {str(p) for p in atlas().get("generated_files") or []} | dirscope.generated_references()
    built = set(GENERATED_FILES)
    return ([f"atlas.yaml/generated_files names '{p}', which no generator writes" for p in sorted(declared - built)]
            + [f"a generator writes '{p}', which atlas.yaml/generated_files does not declare — the "
               "policy reads the declaration, so an undeclared generated file is writable by a task "
               "contract and silently reverted by the next index --write"
               for p in sorted(built - declared)])


def rendered(name: str) -> str:
    return f"{_begin(name)}\n{BLOCKS[name][1]()}\n{_end(name)}"


# THE MISTAKES LIST IS BOUNDED IN BYTES, because it sits in the most expensive text this repository
# has: the entry every runtime loads every session. It grew one line per recurring shape and pushed
# that entry over its ratchet at 2.27.0 — an unbounded list on a paid surface. Most-sighted first;
# the rest are named by count and reachable where they live.
MISTAKES_BUDGET_BYTES = 460  # lowered at 3.19.0 to pay for the role/resume line: `thea failures` lists all


def _recurring_mistakes() -> str:
    modes = [(int((spec or {}).get("sightings") or 0), name, str((spec or {}).get("looks_like")))
             for name, spec in (atlas().get("agent_failure_modes") or {}).items()]
    recurring = sorted((m for m in modes if m[0] > 1), key=lambda m: (-m[0], m[1]))
    shown, used = [], 0
    for _, name, looks in recurring:
        line = f"- `{name}` — {looks}"
        if used + len(line) + 1 > MISTAKES_BUDGET_BYTES:
            break
        shown.append(line)
        used += len(line) + 1
    rest = len(modes) - len(shown)
    return "\n".join(shown + [f"- …and {rest} more: `thea failures`"] if rest else shown)


def _write_generated_files(write: bool) -> int:
    wrote = 0
    for rel_path, generator in GENERATED_FILES.items():
        (ROOT / rel_path).parent.mkdir(parents=True, exist_ok=True)
        path = ROOT / rel_path
        text = generator()
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if write and text != current:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {rel_path} (generated file)")
            wrote += 1
        elif not write:
            print(f"--- {rel_path} (generated file, {len(text.splitlines())} lines)")
    return wrote


def _write_blocks(write: bool) -> tuple[int, int]:
    missing = wrote = 0
    for name, (files, _) in BLOCKS.items():
        block = rendered(name)
        for rel_path in files:
            path = ROOT / rel_path
            text = path.read_text(encoding="utf-8")
            if _begin(name) not in text or _end(name) not in text:
                print(f"markers missing for {name} in {rel_path}")
                missing += 1
                continue
            pre, rest = text.split(_begin(name), 1)
            _, post = rest.split(_end(name), 1)
            new = pre + block + post
            if write and new != text:
                path.write_text(new, encoding="utf-8")
                print(f"wrote {name} -> {rel_path}")
                wrote += 1
            elif not write:
                print(f"--- {name} -> {rel_path}\n{block}")
    return missing, wrote


def index(write: bool) -> int:
    """Regenerate every generated file, THEN every block. Markers must already exist.

    FILES FIRST (2.28.0): runtime-entry measures CLAUDE.md, AGENTS.md and llms.txt. BLOCKS UNTIL STILL
    (3.49.0): measured-benefits sizes lazy docs whose blocks are written after it, so one pass left
    README a build behind and `check` red after a clean `index --write`. FILES TOO (3.53.0):
    `.agent/facts.json` sizes files the blocks write, so it was the one left a pass behind.
    """
    missing = 0
    for _ in range(3):
        wrote = _write_generated_files(write)
        missing, blocks = _write_blocks(write)
        if not (wrote or blocks):
            break
    print(f"generated blocks: {len(BLOCKS)} ({sum(len(f) for f, _ in BLOCKS.values())} sites), "
          f"{len(GENERATED_FILES)} generated file(s), {missing} missing markers")
    return 1 if missing else 0
