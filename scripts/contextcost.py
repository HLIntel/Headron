#!/usr/bin/env python3
"""What this repository HANDS OVER before it is asked anything — measured, and ratcheted.

WHY (2.10.0). Measured on this tree: 159 markdown files, 45% of the bytes. That number alone is
rhetoric in both directions. 78 of those files are language packs no session opens until a route
names one, so "45% prose" describes a library, not a blob — and at the same time nothing here
measured the part that actually costs a reader anything, which is what a runtime loads with no
route resolved and no question asked. An entry path can grow a page at a time while every other
count in this contract stays green.

SO THE INSTRUMENT MEASURES THE ENTRY, NOT THE TREE. Two paths are declared in
`atlas.yaml/context_policy/entry_paths` — what an agent runtime loads automatically, and what a
person opens first — each with a byte budget set to its own measured size. The budget is a
RATCHET: it may fall and never rise, so the only way to add to an entry document is to take
something out of it, and `atlas.py check` refuses a raise rather than leaving it to review.

WHAT IT DOES NOT PROVE: that the bytes on the entry path are the RIGHT bytes. A small entry
document that sends every reader to the wrong place costs more than a large one that routes
correctly, and no byte count can see the difference. That is what the router's own evidence line
and a human reviewer are for.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from atlascore import ROOT, atlas, parsed_python, read, route_for, route_targets, tracked


def tokens(size: int) -> int:
    """The ONE bytes-to-tokens estimate. Two formulas for one number disagreed by a token at 2.28.0
    — the printer floored, a README guard rounded — and each was right by its own lights."""
    return max(size, 0) // 4


def paths() -> dict:
    return ((atlas().get("context_policy") or {}).get("entry_paths")) or {}


def _size(rel_path: object) -> int:
    """Bytes a runtime LOADS for this file: the file plus every `@path` it imports, one level, as Claude
    Code expands them. Measuring the file alone would price CLAUDE.md at its import line."""
    path = ROOT / str(rel_path)
    if not path.exists():
        return -1
    imports = (
        [
            ln[1:].strip()
            for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if ln.startswith("@") and (ROOT / ln[1:].strip()).is_file()
        ]
        if path.suffix == ".md"
        else []
    )
    return path.stat().st_size + sum((ROOT / i).stat().st_size for i in imports)


def loaded_size(rel_path: object) -> int:
    return _size(rel_path)


def measure() -> dict[str, dict]:
    """Per declared entry path: its files, their sizes, the total and the budget it is held to."""
    report: dict[str, dict] = {}
    for name, spec in paths().items():
        always = [(str(f), _size(f)) for f in (spec or {}).get("files") or []]
        options = [(str(f), _size(f)) for f in (spec or {}).get("alternatives") or []]
        # `worst_alternative` costs the LARGEST option, not their sum: a runtime reads the one
        # convention it knows. `sum` is for a path where every file really is opened.
        worst = max((size for _, size in options), default=0)
        rows = always + [(f"{f} (one of {len(options)} conventions)", size) for f, size in options]
        report[name] = {
            "files": rows,
            "measure": str((spec or {}).get("measure") or "sum"),
            "bytes": sum(size for _, size in always if size > 0)
            + (
                worst
                if str((spec or {}).get("measure")) == "worst_alternative"
                else sum(size for _, size in options if size > 0)
            ),
            "budget": int((spec or {}).get("budget_bytes") or 0),
            "slack": int((spec or {}).get("slack_bytes") or 0),
            "raised_for": str((spec or {}).get("raised_for") or ""),
            "why": str((spec or {}).get("why") or ""),
        }
    return report


def lazy_bytes() -> tuple[int, int]:
    """Everything reachable ONLY after a route, so the entry cost has something to be read against."""
    entry = {
        str(f)
        for spec in paths().values()
        for f in ((spec or {}).get("files") or []) + ((spec or {}).get("alternatives") or [])
    }
    total = count = 0
    for path in tracked():
        if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".md":
            continue
        if path.resolve().relative_to(ROOT.resolve()).as_posix() in entry:
            continue
        total += path.stat().st_size
        count += 1
    return total, count


def footprint() -> dict:
    """What an install of the harness weighs: its own modules, and how many things it drags in."""
    declared = ((atlas().get("context_policy") or {}).get("install_footprint")) or {}
    # ONLY WHAT SHIPS. Counting every script made this grow whenever an instrument was added,
    # which measured the repository's verification rather than the consumer's install.
    shipped = set(
        re.findall(r'"([a-z_][a-z0-9_]*)"', re.search(r"py-modules = \[(.*?)\]", read("pyproject.toml"), re.S).group(1))
    )
    modules = sorted(p for p in (ROOT / "scripts").glob("*.py") if p.stem in shipped)
    requirements = [line.split("#", 1)[0].strip() for line in read("scripts/requirements.txt").splitlines()]
    return {
        "modules": len(modules),
        "development_only": len(list((ROOT / "scripts").glob("*.py"))) - len(modules),
        "bytes": sum(p.stat().st_size for p in modules),
        "dependencies": len([r for r in requirements if r]),
        "declared": declared,
    }


def _largest_parts(row: dict) -> str:
    """Name what to cut: the biggest ## sections of the files on this path, so a breach is a one-step fix."""
    parts = []
    for name, _ in row.get("files") or []:
        path = ROOT / str(name).split(" (", 1)[0]
        if path.suffix == ".md" and path.is_file():
            for section in path.read_text(encoding="utf-8").split("\n## ")[1:]:
                parts.append((len(section.encode()), f"{path.name} ## {section.splitlines()[0][:40]}"))
    return ", ".join(f"{label} {size} B" for size, label in sorted(parts, reverse=True)[:3]) or "no sections"


def footprint_errors() -> list[str]:
    """One dependency, bounded bytes, and no slack left lying around for the next import."""
    state = footprint()
    declared = state["declared"]
    errors: list[str] = []
    if not declared:
        return [
            "context_policy/install_footprint is not declared, so the CLI's weight is bounded "
            "by nothing and arrives one convenient import at a time"
        ]
    if state["dependencies"] != int(declared.get("runtime_dependencies") or -1):
        errors.append(
            f"the harness declares {declared.get('runtime_dependencies')} runtime "
            f"dependency/ies and scripts/requirements.txt names {state['dependencies']}"
        )
    ceiling, slack = int(declared.get("module_bytes") or 0), int(declared.get("slack_bytes") or 0)
    if not str(declared.get("raised_for") or "").strip():
        errors.append(
            "context_policy/install_footprint names nothing in raised_for — a ceiling "
            "that can move without saying what moved it is not a ratchet, it is a number"
        )
    if state["bytes"] > ceiling:
        errors.append(
            f"the harness is {state['bytes']} bytes against a ceiling of {ceiling} — the "
            "ratchet only falls; split something out or point at it instead of shipping it"
        )
    elif ceiling - state["bytes"] > slack:
        errors.append(
            f"the harness measures {state['bytes']} against a ceiling of {ceiling}, "
            f"{ceiling - state['bytes']} bytes of slack over the declared {slack} — lower "
            "the ceiling, or the next import is absorbed rather than refused"
        )
    return errors


def example_coverage() -> tuple[list[str], list[str]]:
    """(routes that ship something runnable, routes that ship nothing). Both, always."""
    with_example: set[str] = set()
    for path in (p for p in tracked() if p.relative_to(ROOT).parts[:1] == ("examples",)):
        if path.is_file():
            route = route_for(str(path))
            if route:
                with_example.add(route)
    return sorted(with_example), sorted(set(route_targets()) - with_example)


def _ratchet_errors(name: str, measured: list[str], ceiling: object, why: object) -> list[str]:
    """A count that may only fall, held EXACTLY: above the line is refused, below it is a stale line."""
    if ceiling is None:
        return [f"context_policy/{name} is not declared, so a clean pass can cover what nobody counted"]
    if not str(why or "").strip():
        return [f"context_policy/{name} states no reason, which makes it a number rather than an obligation"]
    if len(measured) > int(ceiling):
        return [
            f"{len(measured)} {name} against a declared {ceiling} — the ratchet only falls: "
            + ", ".join(measured)[:300]
        ]
    if len(measured) < int(ceiling):
        return [
            f"{len(measured)} {name} against a stale declaration of {ceiling} — lower it, so the "
            "next one added is refused rather than absorbed"
        ]
    return []


def example_coverage_errors() -> list[str]:
    """Uncovered routes, and the SURFACE itself, may only fall. A pack that ships nothing runnable is
    DECLARED, not proven; a route or instrument added is breadth the contract froze (3.48.0)."""
    policy = atlas().get("context_policy") or {}
    declared, surface = policy.get("example_coverage") or {}, policy.get("surface") or {}
    _, without = example_coverage()
    return (
        _ratchet_errors(
            "routes_without_example", without, declared.get("routes_without_example"), declared.get("why_not_zero")
        )
        + _ratchet_errors("routes", sorted(route_targets()), surface.get("routes"), surface.get("why_frozen"))
        + _ratchet_errors(
            "instruments",
            sorted(atlas().get("instruments") or {}),
            surface.get("instruments"),
            surface.get("why_frozen"),
        )
    )


def wheel_import_errors() -> list[str]:
    """No SHIPPED module imports a harness module at its top level, or the wheel does not import at all.

    3.7.0: the wheel ships only the launcher, and the harness exists only once the launcher has
    resolved an atlas and put ITS scripts/ on the path. A top-level `import atlas` in the launcher
    would bind to whatever `atlas` happens to be importable first — the failure is invisible from a
    checkout, where scripts/ is already beside it, and appears only for the consumer.
    """
    import ast as _ast

    shipped = set(
        re.findall(r'"([a-z_][a-z0-9_]*)"', re.search(r"py-modules = \[(.*?)\]", read("pyproject.toml"), re.S).group(1))
    )
    harness = {p.stem for p in (ROOT / "scripts").glob("*.py")}
    errors: list[str] = []
    for name in sorted(shipped):
        source = ROOT / "scripts" / f"{name}.py"
        if not source.exists():
            errors.append(
                f"pyproject ships {name}, and scripts/{name}.py does not exist — the wheel would "
                "install a module that is not there, and an import check over nothing passes"
            )
            continue
        if (parsed := parsed_python(source.read_text(encoding="utf-8"), str(source))) is None:
            # A FILE THAT DOES NOT PARSE IS ALREADY SOMEBODY ELSE'S FINDING: check() asserts every
            # tracked source compiles, first; this guard crashing on it once took the contract down.
            continue
        for node in parsed.body:  # TOP LEVEL ONLY: an import inside main() runs after the root is resolved
            imported = (
                [a.name for a in node.names]
                if isinstance(node, _ast.Import)
                else [node.module]
                if isinstance(node, _ast.ImportFrom) and node.module
                else []
            )
            for target in imported:
                if str(target).split(".")[0] in harness - shipped:
                    errors.append(
                        f"shipped module '{name}' imports harness module '{target}' at top level — "
                        "in an install that binds before the atlas is resolved, or not at all"
                    )
    return errors


def generated_attribute_errors() -> list[str]:
    """Every generated file is MARKED generated in .gitattributes, so the two rosters cannot drift.

    Not cosmetic: a generated file read as hand-written is reviewed line by line, and counted as
    source it misreports what the repository is made of — which is how a routing table with a
    contract came to be published as 61% documentation.

    It lives HERE rather than beside the language-bar instrument because that instrument is
    development-only and this check belongs to the contract, which ships. The wheel-import guard
    refused the other arrangement, which is the guard working.
    """
    lines = [line.strip() for line in read(".gitattributes").splitlines() if line.strip() and not line.startswith("#")]
    marked = {line.split()[0] for line in lines if "linguist-generated=true" in line}
    return [
        f".gitattributes does not mark '{name}' as linguist-generated, and atlas.yaml declares "
        "it generated — read as hand-written it is reviewed line by line, and counted as "
        "source it misreports what this repository is made of"
        for name in (atlas().get("generated_files") or [])
        if str(name) not in marked
    ]


def mcp_schema_tax(tool_lists: dict[str, list]) -> dict:
    """Per-server tokens for a TOOL SCHEMA, which is a per-turn tax and was not counted here.

    THE BLIND SPOT THIS CLOSES. Until 3.34.0 this instrument counted exactly one per-turn tax -- a
    shipped skill's DESCRIPTION -- and said so. An MCP tool schema is the same kind of cost and a much
    larger one: it is handed over on EVERY request by any client without deferred tool loading, and
    nothing bounded it. MEASURED at contract 3.34.0 against six servers by driving `tools/list` and counting
    bytes: 30,853 tokens of schema on ONE agent, of which a machine-maintenance server contributed
    11,569 and a web-scraping server 10,670 -- on a CODING agent that called neither. The leanest
    server measured spent 464 B/tool; the fattest 1,653 B/tool for the same number of tools.

    WHY IT MISSED IT: scope, not arithmetic. It measured FILES on the entry path, and a tool schema
    never appears in a file -- it arrives over a protocol at runtime. An instrument is wrong in its
    scope long before it is wrong in its math, and the reading it produced was correct about documents
    while the larger bill sat outside its window.

    TAKES THE TOOL LISTS AS AN ARGUMENT. This repository cannot spawn a consumer's servers, and must
    not try: the roster is theirs, the credentials are theirs, and a probe that reaches out would make
    a measurement depend on a network. The caller drives `tools/list` and passes what came back.
    """
    per = {name: len(json.dumps(tools)) for name, tools in sorted(tool_lists.items())}
    total = sum(per.values())
    return {
        "servers": len(per),
        "bytes": total,
        "tokens": tokens(total),
        "per_server": {
            name: {"bytes": b, "tokens": tokens(b), "tools": len(tool_lists[name])} for name, b in per.items()
        },
        "worst": max(per, key=per.get) if per else None,
    }


def mcp_tax_errors(tool_lists: dict[str, list], cap_tokens: int | None = None) -> list[str]:
    """Refuse a server whose schema exceeds the declared per-server band. A ratchet, like the others.

    `cap_tokens` defaults to atlas.yaml/context_policy/mcp_server_tokens. A cap of 0 or absent is
    itself the finding: nothing would bound a cost paid on every request.
    """
    if cap_tokens is None:
        cap_tokens = int(((atlas().get("context_policy") or {}).get("mcp_server_tokens") or 0))
    if not cap_tokens:
        return [
            "atlas.yaml/context_policy declares no mcp_server_tokens — an MCP tool schema is paid on "
            "EVERY request by a client without deferred tool loading, and nothing would bound it"
        ]
    report = mcp_schema_tax(tool_lists)
    errors = []
    for name, row in sorted(report["per_server"].items()):
        if row["tokens"] > cap_tokens:
            errors.append(
                f"mcp server {name!r} hands over {row['tokens']:,} tokens of schema for {row['tools']} tools, "
                f"over the declared {cap_tokens:,} — paid on every request. Split it into a smaller subset "
                f"for the agents that call it, or shorten its descriptions and input schemas"
            )
    return errors


def skill_cost_errors() -> list[str]:
    """A shipped skill's DESCRIPTION is a per-TURN tax, and the only thing here that is (3.24.0).

    An entry path is paid once a session; a skill's body is lazy, but its description is loaded into every
    request of every session that installs the skill. This repository ships `skills/` and a consumer
    symlinks it, so a description lengthened here is paid by them forever — and found only in THEIR budget,
    which is where it was found. A ratchet, like every other budget: it may fall and never rise.
    """
    import re  # noqa: PLC0415

    cap = int(((atlas().get("context_policy") or {}).get("skill_description_bytes") or 0))
    if not cap:
        return [
            "atlas.yaml/context_policy declares no skill_description_bytes — a shipped skill's description "
            "is paid on every request of every session that installs it, and nothing would bound it"
        ]
    errors = []
    for path in sorted([*(ROOT / "skills").glob("*/SKILL.md"), *(ROOT / "chat").glob("*/SKILL.md")]):
        found = re.search(r"^description:\s*(.+)$", path.read_text(encoding="utf-8"), re.M)
        if not found:
            errors.append(f"{path.relative_to(ROOT)} declares no description: a skill nothing can route to")
            continue
        size = len(found.group(1).strip().encode())
        if size > cap:
            errors.append(
                f"{path.relative_to(ROOT)} description is {size} bytes against a cap of {cap} — "
                "it is paid on EVERY request of every session that installs this skill; cut it, "
                "keeping every trigger word, or move the detail into the body, which is lazy"
            )
    return errors


def entry_cost_errors() -> list[str]:
    """A budget may only fall, and a path may not name a file the tree does not have."""
    errors: list[str] = []
    if not paths():
        return [
            "atlas.yaml/context_policy declares no entry_paths — the one cost a reader pays "
            "before asking anything would then be measured by nothing"
        ]
    for name, row in measure().items():
        for rel_path, size in row["files"]:
            if size < 0:
                errors.append(f"context_policy/entry_paths/{name} names {rel_path}, which does not exist")
        if not str(row.get("raised_for") or "").strip():
            errors.append(
                f"context_policy/entry_paths/{name} names nothing in raised_for — a "
                "budget that can move without saying what moved it is not a ratchet"
            )
        if not row["budget"]:
            errors.append(
                f"context_policy/entry_paths/{name} declares no budget_bytes — an entry "
                "path with no ceiling grows a page at a time and nothing says so"
            )
        elif row["bytes"] > row["budget"]:
            errors.append(
                f"entry path '{name}' is {row['bytes']} bytes against a budget of "
                f"{row['budget']} — largest parts: {_largest_parts(row)} — the ratchet only falls: take something OUT of the "
                "entry path, or move it behind a route"
            )
        elif row["budget"] - row["bytes"] > row["slack"]:
            errors.append(
                f"entry path '{name}' measures {row['bytes']} against a budget of "
                f"{row['budget']} — {row['budget'] - row['bytes']} bytes of slack, over the "
                f"declared {row['slack']}. Lower the budget to what it now costs, or the "
                "next addition is absorbed by the gap instead of being refused by it"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    report = measure()
    for name, row in report.items():
        print(f"entry path '{name}' [{row['measure']}] — {row['why']}")
        for rel_path, size in row["files"]:
            print(f"  {size:>7} B  ~{tokens(size):>6} tok  {rel_path}")
        print(
            f"  {row['bytes']:>7} B  ~{tokens(row['bytes']):>6} tok  TOTAL — budget {row['budget']}, "
            f"slack {row['budget'] - row['bytes']}/{row['slack']}"
        )
    lazy, files = lazy_bytes()
    handed = sum(r["bytes"] for r in report.values())
    print(f"handed over before a route: {handed} B (~{tokens(handed)} tok)")
    print(
        f"reachable only through a route: {lazy} B across {files} documents — "
        f"{lazy / max(handed, 1):.1f}x the entry path, and none of it is read unasked"
    )
    weight = footprint()
    print(
        f"install footprint: {weight['modules']} modules, {weight['bytes']} B "
        f"(~{weight['bytes'] // 1024} KiB), {weight['dependencies']} runtime dependency/ies, "
        f"{weight['development_only']} harness modules run from the resolved atlas, never shipped — the "
        "policy content is POINTED AT, never shipped, so no install carries a copy that ages"
    )
    covered, without = example_coverage()
    print(
        f"runnable examples: {len(covered)} of {len(route_targets())} routes ship one; "
        f"{len(without)} ship nothing that runs and are DECLARED rather than exercised"
    )
    # MCP SCHEMA TAX. This repository cannot spawn a consumer's servers, so the tool lists arrive as a
    # file: a JSON object {server: [tool, ...]} captured from `tools/list`. Given none, the cost is
    # DECLARED UNMEASURED and printed — never passed over in silence, because an unmeasured per-turn
    # tax and a zero one print the same nothing, and this instrument missed exactly this cost until
    # 3.34.0 by having it outside its window.
    mcp_problems: list[str] = []
    dump = (argv or [None])[0] if argv else None
    if dump and Path(dump).is_file():
        lists = json.loads(Path(dump).read_text(encoding="utf-8"))
        tax = mcp_schema_tax(lists)
        print(
            f"mcp tool schemas: {tax['servers']} server(s), {tax['bytes']} B (~{tax['tokens']} tok) "
            f"handed over on EVERY request; worst = {tax['worst']}"
        )
        for name, row in sorted(tax["per_server"].items(), key=lambda kv: -kv[1]["tokens"]):
            print(f"  {row['bytes']:>7} B  ~{row['tokens']:>6} tok  {row['tools']:>3} tools  {name}")
        mcp_problems = mcp_tax_errors(lists)
    else:
        cap = int(((atlas().get("context_policy") or {}).get("mcp_server_tokens") or 0))
        print(
            f"mcp tool schemas: NOT MEASURED here — pass a tools/list dump as the first argument. "
            f"The declared band is {cap or 'NONE'} tokens per server, paid on every request."
        )

    problems = (
        entry_cost_errors() + footprint_errors() + example_coverage_errors() + wheel_import_errors() + mcp_problems
    )
    for problem in problems:
        print(f"- {problem}")
    print("SCOPE: bytes, not judgement. A short entry document that sends every reader to the")
    print("       wrong place costs more than a long one that routes correctly, and no byte")
    print("       count can tell them apart — the router's evidence line and a reviewer can.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
