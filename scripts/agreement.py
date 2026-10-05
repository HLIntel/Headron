#!/usr/bin/env python3
"""The agreement graph: which file implements which declaration, and what a diff puts at risk.

WHY (3.37.0). Every roster here pointed ONE WAY. `INVARIANT_CHECKS` maps an invariant to the function
that enforces it, `agent_policy/controls` maps a control to its decider, `instruments` maps a name to
a script, `agent_failure_modes` maps a shape to what refuses it, `language_mechanisms` maps a
mechanism to where it was taken. Not one of them could answer the question a reader actually asks
before editing: WHAT DOES THIS FILE ANSWER FOR? So a change landed against declarations nobody
listed, and the only way to find out was to break something.

IT IS DERIVED, NEVER TYPED. Every edge comes from a roster that already exists — a check function's
own `__code__.co_filename`, a control's `enforced_by`, an instrument's `script`. A hand-written index
would be `a_derived_roster_written_out_by_hand`, which is in this repository's ledger because it was
committed here.

WHAT AGREEMENT LEVEL THIS IS, STATED SO IT IS NOT READ AS MORE. This is naming and wiring: it proves
a declaration resolves to a file and that a file answers for what it claims. It does NOT run an
adapter, so it cannot prove two runtimes BEHAVE the same. Conformance here is Level 1-2 — schema and
wiring — and the level above it needs a runtime this repository deliberately does not have.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys

from atlascore import ROOT, atlas, rel


def _file_of(reference: str) -> str:
    """The file a `module.function` reference lives in, or '' — resolved through the import system
    rather than by guessing a path, so a function that MOVED is followed rather than lost.

    IT UNWRAPS FIRST, AND THAT WAS MEASURED. The first version read `__code__.co_filename` straight,
    which for anything behind `@contextlib.contextmanager` is contextlib's own file — outside this
    tree — so three declarations pointing at `atlas_test.mutated` were reported as resolving to
    NOTHING. A guard built to find holes reported a hole it had made itself, which is
    `a_probe_that_reports_absent_what_it_could_not_reach` with the tell this repository already
    records: every miscall in one direction, never a false PRESENT.

    AND THE FALLBACK IS THE DEFINING MODULE, not silence: a callable whose code object sits outside
    the tree still belongs to the module that exported it.
    """
    import importlib
    import inspect
    import re

    # A REFERENCE OR NOTHING, DECIDED BEFORE THE IMPORT SYSTEM IS ASKED. `enforced_by` is MIXED in
    # two rosters — some rows name a callable, some describe a practice — and an empty string reached
    # importlib, which raises ValueError rather than ImportError, so this crashed on input another
    # roster owns. That is `a_guard_that_crashes_on_another_guards_input`, met for the second time in
    # this session; the shape is the same and so is the fix: decide what this function OWNS first.
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", str(reference).strip()):
        return ""
    module_name, _, attribute = str(reference).strip().partition(".")
    try:
        module = importlib.import_module(module_name)
    except (ImportError, ValueError):
        return ""
    target = inspect.unwrap(getattr(module, attribute, None)) if getattr(module, attribute, None) else None
    # A FALLBACK LOOP THAT RETURNS ON AN EMPTY CANDIDATE IS NOT A FALLBACK. The first version did,
    # so anything without a `__code__` — `Verdict` is a NamedTuple, not a function — returned ''
    # from the first arm and never reached the module that defines it. Skip an empty candidate;
    # only a resolved one returns.
    for source in (getattr(getattr(target, "__code__", None), "co_filename", ""), getattr(module, "__file__", "")):
        if not source:
            continue
        try:
            return rel(type(ROOT)(source))
        except ValueError:
            continue
    return ""


def _invariant_edges() -> list[tuple[str, str, str]]:
    """(file, kind, id) for every hard invariant, from the check table itself."""
    import atlasinv

    edges = []
    for name, check in atlasinv.INVARIANT_CHECKS.items():
        where = getattr(getattr(check, "__code__", None), "co_filename", "")
        try:
            edges.append((rel(type(ROOT)(where)), "invariant", name))
        except ValueError:
            continue
    return edges


def _declaration_edges() -> list[tuple[str, str, str]]:
    """(file, kind, id) for controls, effects, instruments, failure modes and mechanisms."""
    data = atlas()
    edges: list[tuple[str, str, str]] = []
    policy = data.get("agent_policy") or {}
    for name, row in (policy.get("controls") or {}).items():
        edges.append((_file_of(str((row or {}).get("enforced_by"))), "control", name))
    for name, row in (policy.get("effect_classes") or {}).items():
        edges.append((_file_of(str((row or {}).get("refused_by"))), "effect", name))
    for name, row in (data.get("instruments") or {}).items():
        edges.append((str((row or {}).get("script") or ""), "instrument", name))
    for name, row in (data.get("agent_failure_modes") or {}).items():
        for reference in (row or {}).get("enforced_by") or []:
            target = str(reference)
            edges.append((target if "/" in target else _file_of(target), "failure_mode", name))
    # PARSER DISCIPLINE AND BRANCH POLICY NAME THEIR ENFORCERS TOO, and were outside this graph
    # only because nobody read them. `enforced_by` in those rosters is MIXED — some rows name a
    # callable, some describe a practice a person follows — so a row is an edge when it RESOLVES and
    # is left alone when it does not. Refusing the prose rows would fire on correct content; reading
    # them as references would invent edges that point nowhere. Both are declared shapes here.
    # A ROW IS A MAPPING OR IT IS NOT THIS FUNCTION'S BUSINESS. branch_policy mixes mappings with
    # plain scalars, and assuming otherwise crashed here — the THIRD time in this session that a
    # reader assumed the shape of a roster it does not own. Once is a bug and twice is a rule; the
    # rule is that every roster read here is filtered to the shape it is read for, first.
    for section in ("parser_discipline", "branch_policy"):
        for name, row in (data.get(section) or {}).items():
            if not isinstance(row, dict):
                continue
            # THE BARE REFERENCE, NOT THE SENTENCE. `enforced_by` in these two rosters is prose
            # that BEGINS with a reference, and parsing a reference out of a sentence is branching
            # on a rendering. `enforced_by_ref` is the declared identity; declcheck keeps the two
            # in step so the sentence cannot drift away from the function it names.
            where = _file_of(str(row.get("enforced_by_ref") or ""))
            if where:
                edges.append((where, section, name))
    # A POINTER ON A SECTION, NOT ONLY ON A ROW. Found by scanning the atlas rather than by
    # remembering: `worktree_policy.reported_by` was declared and wired to nothing, because every
    # reader here walked ROWS and no section-level pointer had ever existed before. One roster with
    # one such field is one edge; the point is that the next one is now read without being noticed.
    for section, spec in data.items():
        if not isinstance(spec, dict):
            continue
        for field in ("reported_by", "enforced_by", "measured_by", "refused_by", "decided_by"):
            where = _file_of(str(spec.get(field) or ""))
            if where:
                edges.append((where, "declaration", f"{section}.{field}"))
    for name, row in (data.get("language_mechanisms") or {}).items():
        target = str((row or {}).get("as") or "")
        if (row or {}).get("status") == "harvested" and not target.startswith("atlas.yaml/"):
            edges.append((target if "/" in target else _file_of(target), "mechanism", name))
    return edges


def index() -> dict[str, list[dict]]:
    """file -> everything it answers for. THE REVERSE OF EVERY ROSTER, computed rather than kept."""
    graph: dict[str, list[dict]] = {}
    for where, kind, name in _invariant_edges() + _declaration_edges():
        if not where:
            continue
        graph.setdefault(where, []).append({"kind": kind, "id": name})
    return {k: sorted(v, key=lambda row: (row["kind"], row["id"])) for k, v in sorted(graph.items())}


def unanswered() -> list[str]:
    """Declarations whose implementation resolved to NO file. Printed beside the edge count, because
    a graph with a hole and a graph with none print the same number of edges otherwise."""
    return sorted({f"{kind}/{name}" for where, kind, name in _invariant_edges() + _declaration_edges() if not where})


def changed_files(base: str = "origin/main") -> list[str]:
    """What this branch changed, for impact. Falls back to the working tree when the base is absent —
    and says which it used, because a diff against nothing is an empty diff that looks like a clean one."""
    for argv in ([f"{base}...HEAD"], ["HEAD"]):
        try:
            out = subprocess.run(
                ["git", "diff", "--name-only", *argv], cwd=ROOT, check=True, capture_output=True, timeout=120
            ).stdout.decode()
            return sorted(line for line in out.splitlines() if line.strip())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return []


def impact(paths: list[str]) -> dict:
    """What a set of changed files answers for, and therefore what a reviewer must re-establish."""
    graph = index()
    touched = {p: graph.get(p, []) for p in paths}
    kinds: dict[str, set] = {}
    for rows in touched.values():
        for row in rows:
            kinds.setdefault(row["kind"], set()).add(row["id"])
    return {
        "schema": 1,
        "command": "impact",
        "files": len(paths),
        "answered_for": {k: sorted(v) for k, v in sorted(kinds.items())},
        "files_with_no_declaration": sorted(p for p, rows in touched.items() if not rows),
    }


def _digest(value: object) -> str:
    """16 hex of the CANONICAL form: a drift detector, not a signature, and short enough that no
    secret scanner reads it as a 64-hex key."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]


def lock_record() -> dict:
    """The contract state, one digest per declaration, so a consumer can tell WHICH part moved.

    IT IS A STATEMENT OF STATE, NOT OF CORRECTNESS. Two trees with the same lock agree about what the
    contract IS; whether either one passes its gates is what `verify` answers.

    WHY PER SECTION, OF PARSED DATA (3.49.0). It hashed atlas.yaml's BYTES: every comment and ledger
    edit moved its one line, so the lock said "changed" on every commit and could never say what —
    and nothing read it. Sections come from the file itself, never a list typed here; a comment-only
    edit no longer moves it. Its reader is `lock_drift`, which doctor and the land refresh use.
    """
    data = atlas()
    schemas = {
        rel(p): json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "tools").glob("*.schema.json"))
    }
    return {
        "schema": 2,
        "contract": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "sections": {name: _digest(value) for name, value in data.items()},
        "schemas": {name: _digest(value) for name, value in schemas.items()},
    }


def lock_file() -> str:
    return json.dumps(lock_record(), indent=2, sort_keys=True) + "\n"


def lock_drift(theirs: dict, ours: dict | None = None) -> list[str]:
    """Every declaration whose digest differs between two locks — `section/<name>`, `schema/<path>`.
    A lock in an older shape is ONE finding, never a silent empty diff."""
    ours = ours or lock_record()
    if theirs.get("schema") != ours.get("schema"):
        return [f"lock schema {theirs.get('schema')} != {ours.get('schema')}"]
    return [
        f"{kind.rstrip('s')}/{name}"
        for kind in ("sections", "schemas")
        for name in sorted(set(theirs.get(kind) or {}) | set(ours.get(kind) or {}))
        if (theirs.get(kind) or {}).get(name) != (ours.get(kind) or {}).get(name)
    ]


def adapter_conformance_errors() -> list[str]:
    """Every runtime adapter names only commands this CLI actually has.

    THE SHAPE THIS CLOSES is already in the ledger: `a_named_mechanism_that_does_not_exist`. Eight
    adapters tell eight runtimes how to reach this atlas, and nothing checked that what they tell
    them to run exists — so a command renamed here keeps being advertised there, and the runtime
    that follows the adapter gets a usage error instead of an answer.

    ONLY BACKTICKED MENTIONS COUNT, deliberately. `thea` appears in prose all over these documents,
    and a check that read every occurrence would fire on correct content — which is how a guard gets
    switched off. A command is written in backticks here; that is the declared form, so that is what
    is read.

    IT IS LEVEL 1-2 AGREEMENT — naming and wiring. It cannot prove two runtimes BEHAVE alike, because
    proving that means running them, and this repository deliberately runs no runtime.
    """
    import re

    from commands import build_parser, instruments_on_path

    _, sub = build_parser()
    known = set(sub.choices) | set(instruments_on_path())
    errors: list[str] = []
    adapters = sorted(p for p in (ROOT / "models").iterdir() if p.is_dir() and (p / "README.md").is_file())
    for adapter in adapters:
        text = (adapter / "README.md").read_text(encoding="utf-8", errors="replace")
        for named in sorted(set(re.findall(r"`thea ([a-z][a-z0-9-]*)", text))):
            if named not in known:
                errors.append(
                    f"{rel(adapter / 'README.md')} tells its runtime to run `thea {named}`, "
                    "which this CLI does not have — an adapter advertising a command that "
                    "was renamed or never existed hands its runtime a usage error"
                )
    if not adapters:
        errors.append(
            "models/ carries no runtime adapter with a README — the conformance check "
            "resolved to nothing, which reads exactly like a clean pass"
        )
    return errors


def conformance_report() -> dict:
    """Counts beside the verdict: a check over 0 adapters and a check over 8 print the same 0 findings."""
    adapters = sorted(rel(p) for p in (ROOT / "models").iterdir() if p.is_dir() and (p / "README.md").is_file())
    return {"adapters": adapters, "findings": adapter_conformance_errors()}


def agreement_errors() -> list[str]:
    """What `atlas.py check` reads: the graph has no hole, and every adapter names real commands."""
    return [
        f"agreement graph: {name} resolves to no file in this tree — a declaration nothing implements is a claim"
        for name in unanswered()
    ] + adapter_conformance_errors()


def edges_block() -> str:
    """What an edge IS, and how many of each kind exist — generated, so the page cannot disagree
    with the graph or with the count on the landing page."""
    kinds: dict[str, int] = {}
    for rows in index().values():
        for row in rows:
            kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
    total = sum(kinds.values())
    out = [
        "An **edge** is `(file) → (declaration that file answers for)`. It exists when a roster in",
        "`atlas.yaml` names a function, a script or a path and that name resolves to something real.",
        "",
        f"**{total} edges over {len(index())} files.** `agreement_errors` fails the build when any",
        "declaration resolves to none, so coverage is enforced rather than reported.",
        "",
        "| kind | declaration → implementation | edges |",
        "|---|---|---|",
    ]
    means = {
        "invariant": "a hard invariant → the function enforcing it",
        "control": "an agent control → its deciding function",
        "effect": "an effect class → its refuser",
        "instrument": "an instrument → its script",
        "failure_mode": "a recorded mistake → what refuses it now",
        "mechanism": "a harvested language mechanism → where it lives",
        "parser_discipline": "a parsing rule → the reader that enforces it",
        "branch_policy": "a landing rule → the function deciding it",
    }
    out += [f"| `{k}` | {means.get(k, '—')} | {n} |" for k, n in sorted(kinds.items())]
    out += [
        "",
        "**The target is not edge count.** Adding declarations nothing refuses would raise it and",
        "weaken the repository — the unshipped-arm shape at graph scale. The numbers that matter are",
        "COVERAGE (declarations with an implementation, enforced at 100%) and FILES ANSWERING FOR",
        "NOTHING, which is the one that should fall. `thea agreement <file>` answers for one file;",
        "`thea agreement --impact` reads a diff through the same graph.",
    ]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    graph = index()
    if argv and argv[0] == "--conformance":
        print(json.dumps(conformance_report(), indent=2))
        return 1 if conformance_report()["findings"] else 0
    if argv and argv[0] == "--lock":
        print(lock_file(), end="")
        return 0
    if argv and argv[0] == "--impact":
        print(json.dumps(impact(argv[1:] or changed_files()), indent=2))
        return 0
    if argv:
        rows = graph.get(argv[0], [])
        print(json.dumps({"file": argv[0], "answers_for": rows}, indent=2))
        return 0 if rows else 1
    holes = unanswered()
    for hole in holes:
        print(f"  unanswered: {hole}")
    print(
        f"agreement graph: {sum(len(v) for v in graph.values())} edge(s) over {len(graph)} file(s), "
        f"{len(holes)} declaration(s) resolving to no file"
    )
    return 1 if holes else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
