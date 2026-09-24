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
    rows = ["| instrument | proves | does not prove | closed by |", "|---|---|---|---|"]
    for name, spec in (atlas().get("instruments") or {}).items():
        def cell(key: str) -> str:
            return " ".join(str(spec.get(key, "")).split()).replace("|", "\\|")
        rows.append(f"| `{name}` | {cell('proves')} | {cell('does_not_prove')} | {cell('closed_by')} |")
    return ("Derived from `atlas.yaml/instruments`. Run them; do not read a number about them "
            "from this page.\n\n" + "\n".join(rows))


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


# path -> generator. A GENERATED FILE is written whole by `index --write`; check() fails on
# drift exactly as it does for a generated block inside a document.
GENERATED_FILES: dict[str, object] = {"llms.txt": llms_txt}


# name -> (files that carry the block, generator). check() asserts every one.
BLOCKS: dict[str, tuple[tuple[str, ...], object]] = {
    "language-index": (("languages/README.md",), language_index_block),
    "routing-precedence": (("wiki/CODE-ROUTING.md",), precedence_block),
    "manifest-contract": (("languages/PACK-TOOLS-SPEC.md",), manifest_contract_block),
    "verification-gates": (("README.md", "MODEL.md"), gates_block),
    "language-lanes": (("wiki/LANGUAGE-LANES.md",), lanes_block),
    "instruments": (("README.md",), instruments_block),
    "repository-facts": (("README.md",), facts_block),
    "language-roster": (("README.md",), language_roster_block),
    "packages": (("README.md",), packages_block),
    "examples-index": (("examples/README.md",), examples_block),
    "build-order": (("systems/BACKEND-ARCHITECTURE.md",), build_order_block),
    "gate-detail": (("docs/VERIFY.md",), gate_detail_block),
    "scorecard-floors": (("docs/CERTIFICATION.md",), scorecard_floors_block),
    "best-practices": (("docs/CERTIFICATION.md",), best_practices_block),
    "topics": (("README.md",), topics_block),
}


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
