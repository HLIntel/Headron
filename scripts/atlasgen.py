#!/usr/bin/env python3
"""Every document section and file GENERATED from atlas.yaml, and the writer that repairs them.

A document that restates the source of truth drifts from it silently, and the reader cannot tell a
current copy from a stale one. So each restatement is written between markers by `index --write`,
and `atlas.py check` fails on any difference: the repository's copy of its own rosters is derived,
never maintained.
"""
from __future__ import annotations

import json
import re

import yaml
from atlascore import ROOT, VERSION_SITES, atlas, label_for, read, route_for, route_targets, routes
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
        manifest = f"[tools.yaml]({language}/tools.yaml)" if (base / "tools.yaml").exists() else "none"
        rows.append(f"| `{language}` | [guide]({language}/README.md) | {card} | {manifest} |")
    present = sum((ROOT / "languages" / lang / "tools.yaml").exists() for lang in route_targets())
    return (f"Derived from `atlas.yaml/artifact_routes` — {len(route_targets())} routes, "
            f"{present} tool manifests.\n\n" + "\n".join(rows))


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


def gates_block() -> str:
    profiles = (atlas().get("verification_policy") or {}).get("profiles") or {}
    width = max((len(k) for k in profiles), default=10)
    lines = [f"{k.ljust(width)} -> " + " + ".join(str(g) for g in (v or {}).get("required", []))
             for k, v in profiles.items()]
    return "```text\n" + "\n".join(lines) + "\n```"


def lanes_block() -> str:
    pattern = str((atlas().get("branch_policy") or {}).get("language_lane_pattern", "lang/<language>/<topic>"))
    rows = ["| Route | Label | Branch namespace |", "|---|---|---|"]
    for language in route_targets():
        lane = pattern.replace("<language>", language).replace("<topic>", "*")
        rows.append(f"| `{language}` | `{label_for(language)}` | `{lane}` |")
    return "Derived from `atlas.yaml/artifact_routes` + `branch_policy.language_lane_pattern`.\n\n" + "\n".join(rows)


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
        f"# {title} — Code-Development, contract v{version}",
        "",
        "**GENERATED by `python scripts/atlas.py index --write`. Do not edit — `atlas.py check` fails on",
        "drift.** The facts below come from `atlas.yaml`, `VERSION` and the tree, so this file cannot",
        "disagree with them. To change what it says, change the declaration.",
        "",
        "## Ask, do not read",
        "",
        "**Do not read this repository breadth-first.** It is a routing table with a contract: ask",
        "where to go, then load only what the answer names.",
        "",
        "```bash",
        "python scripts/atlas.py route <path> --json    # pack, card, manifest, label, lane, authority",
        "python scripts/atlas.py plan  <path> --task <task> --change <class> [--modifier <m>] --json",
        "python scripts/atlas.py process <id> --json    # a named process: gates, artifacts, stop/escalate",
        "python scripts/atlas.py check                  # the exit code IS the verdict",
        "python scripts/atlas.py doctor                 # can this machine run the instruments?",
        "```",
        "",
        "`route` says **which precedence rule resolved it and the evidence**, so an explicit match and",
        "a lucky guess do not look alike. The `--json` records are frozen in",
        "`tools/atlas-output.schema.json` — depend on those ids, never on rendered Markdown.",
        "",
        "## Rules that fail the build",
        "",
        "1. **No count typed into prose.** Generate it, or name the instrument that prints it.",
        "2. **No calendar date.** Stamp a claim with the contract version it was measured at; the only",
        "   exception is an external project's own date-shaped version in `atlas.yaml/external_versions`.",
        "3. **No tool name in prose.** A tool belongs in `languages/<route>/tools.yaml`, where an",
        "   instrument can check it. Documents name *gates*, never commands.",
        "4. **Refuse rather than invent.** `none` is a real answer. A parser that picks a winner where",
        "   the input is ambiguous is worse than one that errors.",
        f"5. **Every limit names its closer.** All {len(instruments)} instruments carry `proves`,",
        "   `does_not_prove` and `closed_by`; an empty closer fails the contract.",
        "6. **Do not raise a cap to fit your code.** The caps in `atlas.yaml/code_shape` and the entry",
        "   budgets in `context_policy/entry_paths` are ratchets that only fall. Split the function,",
        "   or take something out of the entry path.",
        "7. **A transformation ends when the artifact parses.** Every tracked source file must compile;",
        "   that check runs first, because nothing below it means anything otherwise.",
        "8. **A control with no enforcer is refused.** Agent controls, sandbox rows and gates each name",
        "   the function that decides them — see `atlas.yaml/agent_policy`.",
        "",
        "## Before you claim a change is done",
        "",
        "Pick the change class and satisfy its gate — " + ", ".join(f"`{gate}`" for gate in gates) + " —",
        "then verify **on the exit code**, never on a line of output:",
        "",
        "```bash",
        "python scripts/atlas.py check && python scripts/atlas_test.py && python scripts/agent_test.py",
        "python scripts/astshape.py && python scripts/exrun.py && python scripts/contextcost.py",
        "ruff check .",
        "```",
        "",
        "`atlas_test.py` and `agent_test.py` plant a real defect for every rule claimed and assert their",
        "own case counts, so a skipped case cannot print a full pass. Add a rule, add its planted defect.",
        "",
        "## Where to put what",
        "",
        "| you are adding | it goes in |",
        "|---|---|",
        "| a fact any document repeats | `atlas.yaml`, then a generated block |",
        "| a tool for a language | that pack's `tools.yaml` |",
        "| a new rule | its own `*_errors()` function, called by `check()` |",
        "| a new process | `atlas.yaml/processes` |",
        "| a platform expectation | `config/github-controls.json` |",
        "| a worked example | `examples/`, self-verifying, run by `exrun.py` |"
    ]
    if claude:
        lines += [
            "",
            "## Claude Code specifics",
            "",
            "- **Skills and subagents over context.** Route first, then load only the pack the route names.",
            "  A whole-repository read is the failure this atlas exists to prevent, and it is listed in",
            "  `atlas.yaml/context_policy/forbidden_default`.",
            "- **Hooks, not instructions, for anything deterministic.** Model instructions are not a",
            "  sandbox; the contract and the ruleset are.",
            "- **The adapter for this runtime is [models/claude/README.md](models/claude/README.md)**, and",
            "  the runtime roster is generated in [MODEL.md](MODEL.md).",
        ]
    else:
        lines += [
            "",
            "## Runtime notes",
            "",
            "- Adapters per runtime live in `models/<runtime>/README.md`; the roster is generated in",
            "  [MODEL.md](MODEL.md) from `atlas.yaml/model_routes` and `runtime_roles`.",
            "- `llms.txt` at the repository root is the same entry point in that convention.",
            "- Consuming this atlas from another repository or a vault:",
            "  [docs/CONSUMING.md](docs/CONSUMING.md).",
        ]
    return "\n".join(lines) + "\n"


def claude_md() -> str:
    return agent_entrypoint("claude")


def agents_md() -> str:
    return agent_entrypoint("agents")


def llms_txt() -> str:
    """llms.txt — the machine-readable entry point, in the convention agents already look for.

    WHY A GENERATED FILE AND NOT A HAND-WRITTEN ONE: an index an agent reads is a roster, and a
    roster maintained by hand narrows silently the first time something is added beside it. Every
    line below is derived from atlas.yaml and from files that were confirmed to exist, so this
    file cannot name a document the repository does not have. check() fails on any drift.
    """
    def link(path: str, note: str) -> str:
        return f"- [{path}]({path}): {note}" if (ROOT / path).exists() else ""

    version = read("VERSION").strip()
    lines = [
        f"# Code-Development — the Engineering Atlas (contract v{version})",
        "",
        "> Route the artifact, verify the change, print every count. A model-aware engineering "
        "atlas for polyglot programming, AI coding agents, Git/GitHub, APIs, MCP connectors, "
        "storage, verification and release control. GENERATED by "
        "`python scripts/atlas.py index --write` from atlas.yaml and the file tree — do not edit.",
        "",
        "## Ask the atlas instead of reading it",
        "",
        "```bash",
        "python scripts/atlas.py route <path>            # language, card, manifest, label, lane, gates",
        "python scripts/atlas.py route <path> --json     # the same answer, machine-readable",
        "python scripts/atlas.py plan <path> --task debugging --json",
        "python scripts/atlas.py check                   # exit code IS the verdict",
        "python scripts/atlas.py doctor                  # can THIS machine run each instrument?",
        "python scripts/packprobe.py --mode smoke        # which declared commands run here",
        "```",
        "",
        "## Control plane",
        "",
    ]
    lines += [ln for ln in (
        link("MODEL.md", "the canonical operating model; read before anything else"),
        link("atlas.yaml", "single source of truth: routes, invariants, gates, profiles, policy"),
        link("docs/INDEX.md", "full document index"),
        link("tools/tools.schema.json", "JSON Schema for every language tool manifest"),
        link("config/github-labels.json", "the label catalog routes resolve against"),
        link("SECURITY.md", "security policy and measured platform controls"),
        link("LICENSE", "MIT"),
    ) if ln]
    lines += ["", "## Language packs", ""]
    for target in route_targets():
        base = f"languages/{target}"
        extras = [name for name, path in (("card", f"{base}/OPERATING.md"), ("manifest", f"{base}/tools.yaml"))
                  if (ROOT / path).exists()]
        lines.append(f"- [{base}/README.md]({base}/README.md): {label_for(target)} · " + " · ".join(extras))
    lines += ["", "## Optional", ""]
    lines += [ln for ln in (
        link("docs/ENGINEERING-CONCEPTS.md", "why each rule here exists, paired with its mechanism"),
        link("docs/VERIFY.md", "the verification ladder"),
        link("docs/VERSIONING.md", "one line per version, the only changelog"),
        link("research/ENGINEERING-RESEARCH.md", "background research"),
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


def facts_block() -> str:
    """Every count this page would otherwise state in prose, derived on every run.

    A number typed into a document is stale the moment the tree moves, and the reader cannot see
    that it moved. So no count is typed anywhere in the documents: each one is computed here and
    `atlas.py check` fails when the rendered block differs from the tree.
    """
    targets = route_targets()
    packs = sorted({p.parent.name for p in (ROOT / "languages").rglob("tools.yaml")})
    schema = manifest_schema()
    entries = kinds = 0
    for manifest in (ROOT / "languages").rglob("tools.yaml"):
        doc = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        entries += len(declared_entries(doc))
    kinds = len(schema["$defs"]["entry"]["x-kinds"])
    rows = [
        ("contract version", read("VERSION").strip(),
         f"`VERSION`, asserted identical in {len(VERSION_SITES)} other files"),
        ("artifact extensions routed", len(routes()), "`atlas.yaml/artifact_routes`"),
        ("language routes", len(targets), "distinct targets of those extensions"),
        ("tool manifests", len(packs), f"`languages/<route>/tools.yaml`, validated against `{MANIFEST_SCHEMA}`"),
        ("declared tool entries", entries, "distinct entries per manifest, summed; `packprobe.py` classifies every one"),
        ("entry kinds", kinds, f"`{MANIFEST_SCHEMA}` `$defs.entry.x-kinds`"),
        ("hard invariants", len(atlas().get("hard_invariants") or []), "each CHECKED or DECLARED, never neither"),
        ("instruments", len(atlas().get("instruments") or {}), "`atlas.yaml/instruments`, each naming its own limits"),
        ("verification gate classes", len(((atlas().get("verification_policy") or {}).get("profiles") or {})), "`atlas.yaml/verification_policy/profiles`"),
        ("task profiles", len(atlas().get("task_profiles") or {}), "`atlas.yaml/task_profiles`"),
        ("python files in the harness", len(sorted((ROOT / "scripts").glob("*.py"))), "`scripts/*.py`, all linted by ruff"),
    ]
    out = ["| fact | value | derived from |", "|---|---|---|"]
    out += [f"| {label} | **{value}** | {source} |" for label, value, source in rows]
    return "\n".join(out)


def language_roster_block() -> str:
    """Every route as one compact line — the count is the length of this list, never a typed number."""
    rows = []
    for target in route_targets():
        extensions = sorted(ext for ext, route in routes().items() if route == target)
        rows.append(f"`{target}` ({' '.join(extensions)})")
    return (f"{len(rows)} routes, each with a guide, an operating card and a tool manifest — "
            "the full table with links is in [languages/README.md](languages/README.md).\n\n"
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
    rows = ["| artifact | route | authority (declared per pack) |", "|---|---|---|"]
    for route in route_targets():
        extensions = " ".join(f"`{e}`" for e in by_route.get(route, []))
        rows.append(f"| {extensions} | `{route}` | "
                    f"[tools.yaml](../languages/{route}/tools.yaml) · "
                    f"[card](../languages/{route}/OPERATING.md) |")
    return ("Derived from `atlas.yaml/artifact_routes`. The authority for a route is its manifest — no\n"
            "tool is named here, because a tool named in prose is a tool nothing can check.\n\n"
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
    rows = ["| runtime | routed for | declared role | adapter |", "|---|---|---|---|"]
    for runtime in sorted(set(routes_by_runtime) | set(roles)):
        tasks = " · ".join(f"`{t}`" for t in sorted(routes_by_runtime.get(runtime, []))) or "—"
        role = f"`{roles[runtime]}`" if runtime in roles else "—"
        adapter = (f"[models/{runtime}](models/{runtime}/README.md)"
                   if (ROOT / "models" / runtime / "README.md").exists() else "—")
        rows.append(f"| `{runtime}` | {tasks} | {role} | {adapter} |")
    return ("Derived from `atlas.yaml/model_routes` and `runtime_roles`. The hand-written version of\n"
            "this roster named seven runtimes in a sentence and omitted the two verification runtimes\n"
            "those declarations name, which is how a roster disagrees with the thing it describes.\n\n"
            + "\n".join(rows))


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
    for path in sorted((ROOT / "examples").rglob("*")):
        if not path.is_file() or path.suffix.lower() in {".md"}:
            continue
        name = path.relative_to(ROOT).as_posix()
        route = route_for(str(path))
        recipe = (runners.get(route) or {}).get("steps") if route else None
        how = f"`{' '.join(recipe[0]).replace('{file}', name)}`" if recipe else "not routed to a runner"
        rows.append(f"| [{name}]({name.replace('examples/', '')}) | `{route or '—'}` | {how} |")
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
        ("harness package", f"`{field('name')}`", "declared in `pyproject.toml`; nothing is published to an index"),
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
        "atlas_version": read("VERSION").strip(),
        "read_nothing_first": "resolve a route, then load only what it names",
        "commands": {
            "route": "python scripts/atlas.py route <path> --json",
            "plan": "python scripts/atlas.py plan <path> --task <task> --change <class> --json",
            "check": "python scripts/atlas.py check",
            "doctor": "python scripts/atlas.py doctor --json",
            "process": "python scripts/atlas.py process <id> --json",
            "policy": "python scripts/agentpolicy.py <contract>",
            "run": "python scripts/agentrun.py <contract> --json",
            "installed": "atlas --atlas-root <checkout> route <path> --json  (`atlas --where` says which atlas)",
        },
        "output_schema": "tools/atlas-output.schema.json",
        "processes": sorted(data.get("processes") or {}),
        "task_contract_schema": policy.get("schema"),
        "reference_contract": policy.get("reference_contract"),
        "controls": sorted(policy.get("controls") or {}),
        "change_classes": sorted((data.get("verification_policy") or {}).get("profiles") or {}),
        "task_profiles": sorted(data.get("task_profiles") or {}),
        "forbidden_context": list((data.get("context_policy") or {}).get("forbidden_default") or []),
        "not_a_security_boundary": (
            "the runner refuses what it is asked about; an agent that does not ask is bounded by "
            "the host, per atlas.yaml/agent_policy/sandbox_requirements"),
        "verify_on": "the exit code, never a line of output",
    }
    return json.dumps(record, indent=2, sort_keys=False) + "\n"


# path -> generator. A GENERATED FILE is written whole by `index --write`; check() fails on
# drift exactly as it does for a generated block inside a document.
GENERATED_FILES: dict[str, object] = {
    "llms.txt": llms_txt,
    ".agent/bootstrap.json": agent_bootstrap,
    "CLAUDE.md": claude_md,
    "AGENTS.md": agents_md,
}


# name -> (files that carry the block, generator). check() asserts every one.
BLOCKS: dict[str, tuple[tuple[str, ...], object]] = {
    "language-index": (("languages/README.md",), language_index_block),
    "routing-precedence": (("wiki/CODE-ROUTING.md",), precedence_block),
    "manifest-contract": (("languages/PACK-TOOLS-SPEC.md",), manifest_contract_block),
    "verification-gates": (("README.md", "MODEL.md"), gates_block),
    "language-lanes": (("wiki/LANGUAGE-LANES.md",), lanes_block),
    # NOT README: this roster grows by one row per instrument, and the landing page is on a
    # ratcheted entry path. A table whose length is a function of how many instruments exist
    # has no place in a document handed to every reader before they have asked anything.
    "instruments": (("docs/CERTIFICATION.md",), instruments_block),
    "repository-facts": (("README.md",), facts_block),
    "language-roster": (("README.md",), language_roster_block),
    # NOT README: another roster that grows by a row per package, on a ratcheted entry path.
    "packages": (("docs/PACKAGE-CATALOG.md",), packages_block),
    "examples-index": (("examples/README.md",), examples_block),
    "build-order": (("systems/BACKEND-ARCHITECTURE.md",), build_order_block),
    "gate-detail": (("docs/VERIFY.md",), gate_detail_block),
    "scorecard-floors": (("docs/CERTIFICATION.md",), scorecard_floors_block),
    "best-practices": (("docs/CERTIFICATION.md",), best_practices_block),
    "route-table": (("wiki/CODE-ROUTING.md",), route_table_block),
    "task-profiles": (("wiki/CODE-ROUTING.md",), task_profile_block),
    "tool-profiles": (("wiki/CODE-ROUTING.md",), tool_profile_block),
    "severity": (("MODEL.md",), severity_block),
    "runtimes": (("MODEL.md",), runtime_block),
    "canonical-flow": (("docs/CONSISTENCY.md",), canonical_flow_block),
    "topics": (("README.md",), topics_block),
}


def generated_file_errors() -> list[str]:
    """The generator's map and atlas.yaml/generated_files must name exactly the same files."""
    declared = {str(p) for p in atlas().get("generated_files") or []}
    built = set(GENERATED_FILES)
    return ([f"atlas.yaml/generated_files names '{p}', which no generator writes" for p in sorted(declared - built)]
            + [f"a generator writes '{p}', which atlas.yaml/generated_files does not declare — the "
               "policy reads the declaration, so an undeclared generated file is writable by a task "
               "contract and silently reverted by the next index --write"
               for p in sorted(built - declared)])


def rendered(name: str) -> str:
    return f"{_begin(name)}\n{BLOCKS[name][1]()}\n{_end(name)}"


def index(write: bool) -> int:
    """Regenerate every registered block. Markers must already exist in the file."""
    missing = 0
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
            elif not write:
                print(f"--- {name} -> {rel_path}\n{block}")
    for rel_path, generator in GENERATED_FILES.items():
        (ROOT / rel_path).parent.mkdir(parents=True, exist_ok=True)
        path = ROOT / rel_path
        text = generator()
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if write and text != current:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {rel_path} (generated file)")
        elif not write:
            print(f"--- {rel_path} (generated file, {len(text.splitlines())} lines)")
    print(f"generated blocks: {len(BLOCKS)} ({sum(len(f) for f, _ in BLOCKS.values())} sites), "
          f"{len(GENERATED_FILES)} generated file(s), {missing} missing markers")
    return 1 if missing else 0
