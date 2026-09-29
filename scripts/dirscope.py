#!/usr/bin/env python3
"""Directory scopes: what a PLACE in this repository is, what a change here must prove, and the
traps already met in it.

WHY (3.36.0). Routing had two axes and needed three. `thea route scripts/doctor.py` answers with a
language, a guide, a card and a manifest; `thea route scripts` answered `route: null,
resolved_by: none`. Every `.thea` program names `allowed_paths`, so every task already works in
terms of PLACES, and no place declared anything — the third axis was used everywhere and stated
nowhere.

AND THE LEDGER WAS GLOBAL WHEN THE TRAPS ARE LOCAL. `agent_failure_modes` records shapes actually
committed here, and an agent editing one directory had to read all of them or none of them. A trap
named where it bites is a trap that gets read; a list of every trap in the repository is a document.

NOTHING HERE IS NEW PROSE. `proves` names gates `verification_policy/done_set` already declares,
`never` names paths, and `traps` names keys of `agent_failure_modes` — each resolved against its own
roster, so a scope that drifts from the tree fails the build rather than rotting quietly. Only `is`
is free text, and it is one sentence.

IT IS LOAD-BEARING, NOT DOCUMENTATION. `contract_scope_errors` refuses a task contract whose
`allowed_paths` reach a scoped directory without carrying that scope's proofs and its forbidden
paths, and `thealang.program_from_plan` fills both in — so a declared scope changes what a program
is allowed to be, which is the difference between a control and a README.

WHAT IT DOES NOT PROVE: that a scope is WISE, or that its trap list is complete. It proves every
name in it resolves, that every top-level directory has one, and that a contract working in a place
carries what that place declares.
"""
from __future__ import annotations

import sys

from atlascore import ROOT, atlas, known_labels


def scopes() -> dict:
    """atlas.yaml/directory_scopes — the one roster of what a place is."""
    return atlas().get("directory_scopes") or {}


def tree_directories() -> list[str]:
    """Every top-level directory, FROM THE TREE. Derived rather than listed, so a directory added
    beside these fails loudly until it is scoped, instead of being silently unscoped."""
    # DOT-DIRECTORIES COUNT WHEN THEY ARE TRACKED, and leaving them out was a real hole: `.github`,
    # `.githooks`, `.vscode` and `.agent` are where the ENFORCEMENT lives, and `thea route
    # .vscode/tasks.json` answered with nothing at all. A cache directory is not tracked and so is not
    # counted — the git index decides, not a name.
    from atlascore import rel as _rel  # noqa: PLC0415
    from atlascore import tracked
    rel = _rel
    plain = {p.name for p in ROOT.iterdir()
             if p.is_dir() and not p.name.startswith(".") and p.name != "__pycache__"}
    dotted = {rel(p).split("/", 1)[0] for p in tracked()
              if rel(p).startswith(".") and "/" in rel(p)}
    return sorted(plain | dotted)


def _reaches(allow: str, prefix: str) -> bool:
    """Does an allowed path touch this prefix — as it, inside it, or containing it?"""
    allow, prefix = allow.rstrip("/"), prefix.rstrip("/")
    return allow == prefix or prefix.startswith(allow + "/") or allow.startswith(prefix + "/")


def scope_for(path_value: str) -> tuple[str, dict]:
    """The DEEPEST declared scope containing this path, or ('', {}).

    Deepest rather than first: `languages/python` is more specific than `languages`, and a router
    that returned the shallower one would answer with the less useful of two true answers.
    """
    candidate, row = "", {}
    cleaned = str(path_value).strip("/")
    for name, spec in scopes().items():
        if (cleaned == name or cleaned.startswith(name + "/")) and len(name) > len(candidate):
            candidate, row = name, spec or {}
    return candidate, row


def scope_record(path_value: str) -> dict | None:
    """The place a path works in, as the record `thea route` embeds. None when nothing covers it —
    an absent scope and an empty one are not the same answer, and only one of them is a finding."""
    name, row = scope_for(path_value)
    if not name:
        return None
    return {"name": name,
            "is": str(row.get("is") or ""),
            "label": str(row.get("label") or ""),
            "proves": [str(g) for g in row.get("proves") or []],
            "never": [str(p) for p in row.get("never") or []],
            "traps": [str(t) for t in row.get("traps") or []],
            "reference": f"{name}/THEA.md"}


def declaration_errors() -> list[str]:
    """Every name in every scope resolves, and every directory in the tree has a scope.

    Both halves earned: a roster whose rows point at nothing is the shape this repository refuses
    six times over, and a roster that does not measure itself against the tree narrows silently the
    moment a directory is added beside it (code-quality §8).
    """
    errors: list[str] = []
    declared = scopes()
    gates = {str(g.get("id")) for g in (atlas().get("verification_policy") or {}).get("done_set") or []}
    traps = set(atlas().get("agent_failure_modes") or {})
    for name, row in declared.items():
        row = row or {}
        if not (ROOT / name).is_dir():
            errors.append(f"directory_scopes/{name} names a directory that does not exist")
        if not str(row.get("is") or "").strip():
            errors.append(f"directory_scopes/{name} says nothing about what the place IS — a scope "
                          "with no subject is a gate list wearing a directory name")
        for gate in row.get("proves") or []:
            if str(gate) not in gates:
                errors.append(f"directory_scopes/{name}/proves names '{gate}', which "
                              "verification_policy/done_set does not declare")
        for trap in row.get("traps") or []:
            if str(trap) not in traps:
                errors.append(f"directory_scopes/{name}/traps names '{trap}', which "
                              "agent_failure_modes does not record — a trap nobody can look up")
        for path_value in row.get("never") or []:
            if not (ROOT / str(path_value)).exists():
                errors.append(f"directory_scopes/{name}/never names {path_value}, which is not in "
                              "this tree — a forbidden path that does not exist forbids nothing")
        label = str(row.get("label") or "")
        if label and label not in known_labels():
            errors.append(f"directory_scopes/{name}/label '{label}' is not in the label catalog — "
                          "a label a program emits and no repository carries files nothing")
        if not label:
            errors.append(f"directory_scopes/{name} carries no label, so a change here cannot be "
                          "filed under the place it was made")
    for directory in tree_directories():
        if directory not in declared:
            errors.append(f"{directory}/ is in the tree and no directory_scopes entry covers it — "
                          "an unscoped place answers 'none' to every question asked about it")
    return errors


def generated_references() -> set[str]:
    """The per-directory reads, DERIVED from the scopes rather than listed beside them.

    `a_derived_roster_written_out_by_hand` is a shape already committed here: the moment this set
    is typed into `generated_files` it is a second declaration of `directory_scopes`, free to
    disagree with it. It is computed in one place and read by the generator, by the equality check
    and by `never_writable`, so no contract can hand-edit a page the build rewrites.
    """
    return {f"{name}/THEA.md" for name in scopes()}


def labels_for(contract: dict) -> list[str]:
    """The labels a program carries: its route, and the place every allowed path works in.

    Only labels the catalog already declares, and NOTHING inferred. A change class or a risk
    modifier could each be mapped to a `kind/` or `risk/` row by guessing, and a guessed label is
    the one a reader trusts and nobody set — so those are left out until a mapping is declared.
    """
    known = known_labels()
    found = set()
    route = str(contract.get("route") or "")
    if route and f"lang/{route}" in known:
        found.add(f"lang/{route}")
    for allow in contract.get("allowed_paths") or []:
        label = str((scope_for(str(allow))[1] or {}).get("label") or "")
        if label in known:
            found.add(label)
    return sorted(found)


def contract_scope_errors(contract: dict) -> list[str]:
    """A contract working in a place carries what that place declares. THIS is the reader.

    Without it a scope is a document, and a document nothing reads is the arm this repository
    refuses everywhere else: built, measured, and never wired.
    """
    errors: list[str] = []
    checks = {str(c) for c in (contract.get("acceptance") or {}).get("required_checks") or []}
    forbidden = [str(p) for p in contract.get("forbidden_paths") or []]
    for allow in (str(a) for a in contract.get("allowed_paths") or []):
        name, row = scope_for(allow)
        if not name:
            continue
        for gate in (row or {}).get("proves") or []:
            if str(gate) not in checks:
                errors.append(f"contract.allowed_paths {allow!r} works in '{name}', which requires "
                              f"'{gate}' — acceptance.required_checks does not name it")
        for prefix in (row or {}).get("never") or []:
            if _reaches(allow, str(prefix)) and not any(_reaches(f, str(prefix)) for f in forbidden):
                errors.append(f"contract.allowed_paths {allow!r} reaches {prefix!r}, which '{name}' "
                              "declares must never be written, and forbidden_paths does not cover it")
    return errors


def reference(name: str) -> str:
    """The generated per-directory read — the whole point being that it is GENERATED.

    A hand-written README per directory is N documents no gate can tell are wrong, which is why the
    obvious version of this idea is refused here. Every line below is composed from rosters that
    already exist, so drift is a failed build rather than a stale page.
    """
    row = scopes().get(name) or {}
    modes = atlas().get("agent_failure_modes") or {}
    out = [f"# `{name}/` — what this place is", "", str(row.get("is") or ""), ""]
    out += ["## A change here proves", ""]
    out += [f"- `{gate}`" for gate in row.get("proves") or []] or ["- nothing beyond the repository floor"]
    if row.get("never"):
        out += ["", "## Never written by any task contract", ""]
        out += [f"- `{path_value}`" for path_value in row["never"]]
    out += ["", "## Traps already met here", "",
            "Each one was committed in this repository at least once. `thea failures` has the full ledger.", ""]
    for trap in row.get("traps") or []:
        out.append(f"- **{trap}** — {str((modes.get(trap) or {}).get('looks_like') or '').strip()}")
    out += ["", f"Declared in `atlas.yaml/directory_scopes/{name}`; `thea route {name}` prints it as a record."]
    return "\n".join(out) + "\n"


def places_block() -> str:
    """Every place, linked. This exists so the per-directory reads are REACHED rather than exempted:
    an orphan rule answered with an exemption list is a rule answered by switching it off, and the
    exemption would itself be a derived roster written out by hand."""
    rows = ["| place | label | proves | traps |", "|---|---|---|---|"]
    for name, row in sorted(scopes().items()):
        row = row or {}
        rows.append(f"| [`{name}/`](../{name}/THEA.md) | `{row.get('label')}` | "
                    f"{', '.join(f'`{g}`' for g in row.get('proves') or [])} | "
                    f"{len(row.get('traps') or [])} |")
    return "\n".join(rows)


def main(argv: list[str]) -> int:
    if argv:
        import json
        record = scope_record(argv[0])
        print(json.dumps(record, indent=2) if record else
              f"no directory_scopes entry contains {argv[0]}")
        return 0 if record else 1
    problems = declaration_errors()
    for problem in problems:
        print(f"  {problem}")
    print(f"directory scopes: {len(scopes())} declared over {len(tree_directories())} directories, "
          f"{len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
