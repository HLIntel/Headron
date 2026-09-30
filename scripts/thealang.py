#!/usr/bin/env python3
"""The surface notation: a `.thea` program compiles to the task contract this repository enforces.

WHY (3.36.0). Every field an agent task needs — intent, identity, scope, capabilities, effects,
budget, proof obligations, provenance, result — has been declared in `tools/agent-task.schema.json`
since 2.9.0 and refused against by the verdicts in `agentpolicy`. What was missing was a
notation a person writes: contracts were hand-written JSON, so the language was fully specified and
had no surface. This is that surface and nothing else.

IT IS A FRONT END, NEVER A SECOND REPRESENTATION. It emits the schema's own record, so there is one
system with two routes and the fork is at the last step. The oracle is the reference contract
`tools/agent-task.example.json`: `tools/agent-task.example.thea` must compile to it field for field,
so the notation cannot drift from the contract without this check failing. There is no second
validator either — `agentpolicy.contract_errors` judges what this emits.

THE ROUND TRIP IS PART OF THE PARSE. `a_round_trip_that_drops_what_the_format_allowed` is already a
measured shape in this tree, and a notation is where it lands: a key the reader accepts and the
printer forgets reads afterwards as a contract that never named it. So `parse(render(x)) == x` is
asserted for every tracked program, not only for the example.

IT REFUSES RATHER THAN GUESSING. An unknown key, a repeated key, an unclosed block, a bare word
where a quoted string belongs, and a DERIVED field typed by hand are each an error carrying its line
number. `schema` and `atlas_version` cannot be written at all: they come from the schema and from
VERSION, because a value typed into a source is a second declaration of it.

WHAT IT DOES NOT PROVE: that a compiled contract is a GOOD one, or that anything ran it. The five
verdicts decide the first and `agentrun.py` is the only caller that does the second. This turns a
notation into a record; every control downstream of the record is unchanged.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from atlascore import ROOT, atlas, rel, tracked

# The surface's whole vocabulary, declared once. A key absent from these tables is REFUSED rather
# than carried through, so a typo cannot become a field nothing reads.
SCALARS: dict[str, str] = {
    "objective": "objective",
    "target": "target",
    "route": "route",
    "profile": "task_profile",
    "change": "change_class",
    "status": "status",
    "base": "base_commit",
    "model": "model",
    "agent": "agent_role",
}
QUOTED = frozenset({"objective"})
VERB_BLOCKS: dict[str, dict[str, str]] = {
    "scope": {"allow": "allowed_paths", "forbid": "forbidden_paths"},
    "commands": {"allow": "allowed_commands"},
}
WORD_BLOCKS: dict[str, str] = {
    "uses": "uses",
    "skills": "skills",
    "prove": "required_gates",
    "accept": "acceptance.required_checks",
    "risk": "risk_modifiers",
    "approval": "approval_required",
    "watch": "watch",
}
# A block that takes BOTH kinds of line: `network denied` is a setting, `deploy` is an effect the
# task may exercise. The dispatch is deterministic — a head the pair table names takes a value, and
# anything else must be a bare word the effect roster declares — so nothing here picks a winner.
MIXED_BLOCKS: dict[str, str] = {"effects": "effects"}
PAIR_BLOCKS: dict[str, dict[str, str]] = {
    "effects": {"network": "network", "side_effects": "acceptance.side_effects"},
    "budget": {name: f"budgets.{name}" for name in
               ("tool_calls", "wall_clock_seconds", "files_changed", "lines_changed",
                "retries", "output_bytes")},
    # The ceiling handed DOWN. Same axes as `budget`, read from that table rather than repeated, so
    # a new budget axis cannot exist on one side of a delegation and not the other.
    "delegate": {},
}
PAIR_BLOCKS["delegate"] = {name: f"delegate_budget.{name}" for name in
                           ("tool_calls", "wall_clock_seconds", "files_changed", "lines_changed",
                            "retries", "output_bytes")}
# ABSENT IS NOT ZERO, so these are never left out: an omitted list and an empty one read the same
# from outside, and one of them means nobody decided. The notation omits the block; the record does
# not omit the key.
ALWAYS_PRESENT = ("risk_modifiers", "required_gates", "allowed_paths", "forbidden_paths",
                  "allowed_commands", "approval_required", "effects")
DERIVED = ("schema", "atlas_version")
KEY_ORDER = ("schema", "task_id", "atlas_version", "objective", "target", "route", "task_profile",
             "model", "agent_role", "uses", "skills", "change_class", "risk_modifiers", "required_gates", "allowed_paths", "forbidden_paths",
             "allowed_commands", "effects", "network", "budgets", "delegate_budget",
             "approval_required", "base_commit",
             "acceptance", "status")


class TheaSyntaxError(ValueError):
    """A refusal with a line number. Never a repaired program."""


def _uncommented(line: str) -> str:
    """Drop a trailing `#` comment while tracking string state.

    A regex for the delimiter deletes the rest of any line that merely CONTAINS it — including a `#`
    inside an objective — and the friendly outcome is a parse error while the unfriendly one is a
    value silently truncated (`parser_discipline/comments_are_not_a_regex`).
    """
    out: list[str] = []
    in_string = False
    escaped = False
    for char in line:
        if escaped:
            out.append(char)
            escaped = False
            continue
        if char == "\\" and in_string:
            out.append(char)
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
        elif char == "#" and not in_string:
            break
        out.append(char)
    if in_string:
        raise TheaSyntaxError("unterminated string")
    return "".join(out).strip()


def _value(key: str, text: str, lineno: int) -> str:
    """One scalar value: quoted where the vocabulary says quoted, bare where it says bare."""
    if key in QUOTED:
        if len(text) < 2 or not text.startswith('"') or not text.endswith('"'):
            raise TheaSyntaxError(f"line {lineno}: '{key}' takes a quoted string")
        return json.loads(text)
    if text.startswith('"'):
        raise TheaSyntaxError(f"line {lineno}: '{key}' takes a bare word, not a quoted string")
    if not text or " " in text:
        raise TheaSyntaxError(f"line {lineno}: '{key}' takes exactly one bare word")
    return text


def _put(raw: dict, path: str, value: object, lineno: int) -> None:
    """Record one field. A second declaration of a scalar is a COLLISION, never the later winner —
    the shape `atlascore.StrictLoader` already refuses for mappings, at the surface."""
    if path in raw and not isinstance(raw[path], list):
        raise TheaSyntaxError(f"line {lineno}: '{path}' is declared twice — refusing to pick a winner")
    if isinstance(raw.get(path), list):
        raw[path].append(value)
    elif isinstance(value, list):
        raw[path] = list(value)
    else:
        raw[path] = value


def _body_line(block: str, text: str, lineno: int, raw: dict) -> None:
    """One line inside a block, dispatched on the block's own kind."""
    head, _, tail = text.partition(" ")
    tail = tail.strip()
    if block in VERB_BLOCKS:
        verbs = VERB_BLOCKS[block]
        if head not in verbs:
            raise TheaSyntaxError(f"line {lineno}: '{block}' has no verb '{head}' "
                                  f"(expected one of {', '.join(sorted(verbs))})")
        raw.setdefault(verbs[head], []).append(tail or _missing(head, lineno))
        return
    if block in WORD_BLOCKS:
        if tail:
            raise TheaSyntaxError(f"line {lineno}: '{block}' takes one name per line, got '{text}'")
        raw.setdefault(WORD_BLOCKS[block], []).append(head)
        return
    pairs = PAIR_BLOCKS[block]
    if head not in pairs:
        bare = MIXED_BLOCKS.get(block)
        if bare and not tail:
            raw.setdefault(bare, []).append(head)
            return
        raise TheaSyntaxError(f"line {lineno}: '{block}' has no key '{head}' "
                              f"(expected one of {', '.join(sorted(pairs))}, or a bare effect name)")
    # THE TYPE COMES FROM THE SCHEMA, NOT FROM THE BLOCK'S NAME. The first version read
    # `block == "budget"`, so the moment a SECOND block of integers existed (`delegate`) its values
    # compiled as strings and six schema violations arrived at once. Branching on a name is
    # branching on a rendering (code-quality §3), in the one file that exists to stop that.
    parsed = int(tail) if pairs[head] in integer_paths() else _value(head, tail, lineno)
    _put(raw, pairs[head], parsed, lineno)


def _missing(verb: str, lineno: int) -> str:
    raise TheaSyntaxError(f"line {lineno}: '{verb}' names nothing")


def integer_paths() -> frozenset[str]:
    """Every contract path the SCHEMA declares as an integer, `$ref`s resolved.

    One declaration of what a number is: add an integer field to the schema and the notation parses
    it as one, with nothing here to remember.
    """
    schema = json.loads((ROOT / "tools" / "agent-task.schema.json").read_text(encoding="utf-8"))
    defs = schema.get("$defs") or {}

    def kind(spec: dict) -> str:
        ref = str(spec.get("$ref") or "")
        if ref.startswith("#/$defs/"):
            spec = defs.get(ref.split("/")[-1]) or {}
        return str(spec.get("type") or "")

    return frozenset(f"{name}.{leaf}"
                     for name, prop in (schema.get("properties") or {}).items()
                     for leaf, sub in ((prop.get("properties") or {}) if isinstance(prop, dict) else {}).items()
                     if kind(sub) == "integer")


def _schema_const() -> int:
    """The `schema` value, READ FROM THE SCHEMA. Typing it here would be its second declaration."""
    schema = json.loads((ROOT / "tools" / "agent-task.schema.json").read_text(encoding="utf-8"))
    return int(schema["properties"]["schema"]["const"])


def _assemble(raw: dict, task_id: str) -> dict:
    """The flat fields, placed into the contract the schema declares."""
    contract: dict = {"schema": _schema_const(), "task_id": task_id,
                      "atlas_version": (ROOT / "VERSION").read_text(encoding="utf-8").strip()}
    acceptance: dict = {}
    budgets: dict = {}
    delegate_budget: dict = {}
    for path, value in raw.items():
        head, _, leaf = path.partition(".")
        target = {"acceptance": acceptance, "budgets": budgets,
                  "delegate_budget": delegate_budget}.get(head)
        if target is None:
            contract[path] = value
        else:
            target[leaf] = value
    for key in ALWAYS_PRESENT:
        contract.setdefault(key, [])
    if "required_checks" not in acceptance:
        acceptance["required_checks"] = []
    contract["budgets"] = budgets
    if delegate_budget:
        contract["delegate_budget"] = delegate_budget
    contract["acceptance"] = acceptance
    ordered = {k: contract[k] for k in KEY_ORDER if k in contract}
    ordered.update({k: v for k, v in contract.items() if k not in ordered})
    return ordered


def parse(text: str, filename: str = "<surface>") -> dict:
    """A `.thea` program to a task contract, or a refusal naming the line."""
    raw: dict = {}
    task_id: str | None = None
    block: str | None = None
    for lineno, source in enumerate(text.splitlines(), start=1):
        try:
            line = _uncommented(source)
        except TheaSyntaxError as exc:
            raise TheaSyntaxError(f"{filename} line {lineno}: {exc}") from None
        if not line:
            continue
        try:
            task_id, block = _statement(line, lineno, raw, task_id, block)
        except TheaSyntaxError as exc:
            raise TheaSyntaxError(f"{filename}: {exc}" if str(exc).startswith("line")
                                  else f"{filename} line {lineno}: {exc}") from None
    if block is not None:
        raise TheaSyntaxError(f"{filename}: block '{block}' is never closed")
    if task_id is None:
        raise TheaSyntaxError(f"{filename}: no `task <id> {{` header")
    return _assemble(raw, task_id)


def _statement(line: str, lineno: int, raw: dict, task_id: str | None,
               block: str | None) -> tuple[str | None, str | None]:
    """One non-blank line, in or out of a block. Returns the task id and open block after it."""
    if line == "}":
        return task_id, None if block else _closed_nothing(lineno, task_id)
    if block is not None:
        _body_line(block, line, lineno, raw)
        return task_id, block
    if line.endswith("{"):
        head, _, _ = line[:-1].strip().partition(" ")
        rest = line[:-1].strip()[len(head):].strip()
        if head == "task":
            if task_id is not None:
                raise TheaSyntaxError(f"line {lineno}: a second `task` header — one program, one task")
            return _value("task", rest, lineno), None
        if head not in VERB_BLOCKS and head not in WORD_BLOCKS and head not in PAIR_BLOCKS:
            raise TheaSyntaxError(f"line {lineno}: unknown block '{head}'")
        if rest:
            raise TheaSyntaxError(f"line {lineno}: '{head}' takes no name before its brace")
        return task_id, head
    key, _, tail = line.partition(" ")
    if key in DERIVED:
        raise TheaSyntaxError(f"line {lineno}: '{key}' is DERIVED — from the schema and from VERSION; "
                              "typing it here is a second declaration of the same value")
    if key not in SCALARS:
        raise TheaSyntaxError(f"line {lineno}: unknown key '{key}'")
    if task_id is None:
        raise TheaSyntaxError(f"line {lineno}: '{key}' sits outside any `task` block")
    _put(raw, SCALARS[key], _value(key, tail.strip(), lineno), lineno)
    return task_id, None


def _closed_nothing(lineno: int, task_id: str | None) -> str | None:
    if task_id is None:
        raise TheaSyntaxError(f"line {lineno}: '}}' closes nothing")
    return None


def render(contract: dict) -> str:
    """The contract back as a program. The printer's roster is the PARSER's, inverted — a second
    hand-kept list is how a key gets accepted and then silently dropped."""
    out = [f"task {contract['task_id']} {{"]
    for surface, key in SCALARS.items():
        if key in contract:
            value = json.dumps(contract[key]) if surface in QUOTED else contract[key]
            out.append(f"  {surface} {value}")
    for block, verbs in VERB_BLOCKS.items():
        rows = [f"  {verb} {item}" for verb, key in verbs.items() for item in contract.get(key) or []]
        out += ["", f"  {block} {{", *[f"  {row}" for row in rows], "  }"] if rows else []
    for block, pairs in PAIR_BLOCKS.items():
        rows = [f"    {leaf} {_read(contract, path)}" for leaf, path in pairs.items()
                if _read(contract, path) is not None]
        rows += [f"    {word}" for word in contract.get(MIXED_BLOCKS.get(block) or "") or []]
        out += ["", f"  {block} {{", *rows, "  }"] if rows else []
    for block, path in WORD_BLOCKS.items():
        rows = [f"    {item}" for item in _read(contract, path) or []]
        out += ["", f"  {block} {{", *rows, "  }"] if rows else []
    out.append("}")
    return "\n".join(out) + "\n"


def _read(contract: dict, path: str) -> object:
    head, _, leaf = path.partition(".")
    return (contract.get(head) or {}).get(leaf) if leaf else contract.get(head)


def _label(path: Path) -> str:
    """The name a refusal prints. A LABEL, so it must never be the thing that fails.

    MEASURED while probing a program written outside the checkout: `rel()` raises for any path that
    is not under the repository root, so compiling a consumer's own program — the entire point of a
    portable notation — died in the filename rather than in the parse, and the traceback named
    pathlib. A repository-relative name where one exists, the path as given where one does not.
    """
    try:
        return rel(path)
    except ValueError:
        return str(path)


def compile_path(path: Path) -> dict:
    return parse(path.read_text(encoding="utf-8"), _label(path))


def load_contract(path: Path | str) -> dict:
    """A task contract from either form, dispatched on the SUFFIX — the one place that knows there
    are two forms at all.

    This is what makes the notation shipped rather than checked: `agentrun` and `sandboxgen` take a
    program exactly where they took a contract, and neither one grows its own idea of what a
    `.thea` file is. One system, two routes, and the fork is this function.
    """
    path = Path(path)
    if path.suffix == ".thea":
        return compile_path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def surface_errors() -> list[str]:
    """Every tracked `.thea` program parses, round-trips, validates, and — where a contract of the
    same stem sits beside it — compiles to THAT contract field for field.

    The last clause is the one that matters: it makes the reference contract the oracle, so the
    notation cannot drift from the schema it claims to be a surface for. The count of programs
    travels with the verdict, because refusing 0 of 0 and 0 of many print the same 0.
    """
    import agentpolicy
    errors: list[str] = []
    programs = [p for p in tracked() if p.suffix == ".thea" and p.is_file() and not p.is_symlink()]
    for path in programs:
        try:
            contract = compile_path(path)
        except (TheaSyntaxError, ValueError) as exc:
            errors.append(f"{rel(path)} does not compile: {exc}")
            continue
        # A CHECKER NEVER CRASHES ON WHAT ANOTHER CHECKER OWNS — `a_guard_that_crashes_on_another
        # _guards_input`, met here on the first run: the planting suite breaks atlas.yaml on purpose
        # to prove a DIFFERENT case, and validating against the declaration raised out of this
        # function, so the whole harness died before reaching that case's own assertion. The
        # declaration is somebody else's finding; the parse, the round trip and the oracle below
        # need none of it and still run.
        try:
            errors += [f"{rel(path)}: {problem}" for problem in agentpolicy.contract_errors(contract)]
        except ValueError:
            errors.append(f"{rel(path)}: NOT VALIDATED — the declaration it validates against does "
                          "not load; that is the contract check's finding, not this one's")
        again = parse(render(contract), rel(path))
        if again != contract:
            dropped = sorted(set(contract) ^ set(again)) or ["a value, not a key"]
            errors.append(f"{rel(path)} does not survive its own printer — {', '.join(dropped)}")
        oracle = path.with_suffix(".json")
        if oracle.exists():
            expected = json.loads(oracle.read_text(encoding="utf-8"))
            if agentpolicy.contract_hash(contract) != agentpolicy.contract_hash(expected):
                errors.append(f"{rel(path)} compiles to a contract that is not {rel(oracle)}: "
                              f"{_difference(expected, contract)}")
    if not programs:
        errors.append("no tracked .thea program — the surface has no example, so nothing proves it "
                      "still compiles to the contract")
    return errors


def _difference(expected: dict, got: dict) -> str:
    keys = sorted(set(expected) | set(got))
    return "; ".join(f"{k}: expected {expected.get(k)!r}, got {got.get(k)!r}"
                     for k in keys if expected.get(k) != got.get(k))


def task_id_for(target: str) -> str:
    """A stable id from the path the task is about, shaped to the schema's own identifier pattern.

    Derived rather than asked for: an id typed by hand is the field that collides with an existing
    audit stream, and the stream is named after it.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", str(target).lower()).strip("-")[:64]
    return slug if len(slug) >= 3 else f"{slug or 'thea'}-task"


def program_from_plan(record: dict, objective: str) -> str:
    """A starter program from what `thea plan` already resolved — route, profile, change class,
    gates — with the allowances DERIVED from the gate commands and the effects derived from those.

    WHY THIS AND NOT A TEMPLATE. A template is a second declaration of the contract's shape, and it
    goes stale the first time a gate is added. This renders through the same printer every other
    program goes through, so what it emits is re-parseable by construction and carries whatever the
    plan actually resolved rather than whatever a template's author remembered.

    THE OBJECTIVE IS NOT DERIVED, AND IS NOT INVENTED EITHER — the caller supplies it, because it
    is the one field nothing in the tree knows, and a parser that fills in an ambiguous field is
    worse than one that refuses (`parser_discipline/refuse_rather_than_pick_a_winner`).
    """
    import agenteffects
    import agentpolicy
    import dirscope
    import knowledge
    route, target = str(record["route"]), str(record["path"])
    # THE PLACE IS PART OF THE PLAN. A program born without the gates and the forbidden paths its
    # own directory declares would be refused by `contract_scope_errors` the moment anyone compiled
    # it — so it is born carrying them, and the scope is a control rather than a thing to remember.
    scope = dirscope.scope_for(target)[1]
    gates = [str(g) for g in record.get("required_gates") or []]
    commands = sorted({argv[0] for argv in (agentpolicy.gate_command(route, g)[0] for g in gates) if argv})
    return render({
        "schema": _schema_const(),
        "task_id": task_id_for(target),
        "atlas_version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "objective": objective,
        "target": target,
        "route": route,
        "task_profile": str(record["task"]),
        "change_class": str(record["change_class"]),
        "risk_modifiers": [str(m) for m in record.get("risk_modifiers") or []],
        "required_gates": gates,
        "allowed_paths": [target],
        "allowed_commands": commands,
        "effects": sorted(agenteffects.argv_effects(commands)),
        "network": "denied",
        "budgets": dict(agentpolicy.policy().get("default_budgets") or {}),
        "approval_required": [],
        "forbidden_paths": [str(p) for p in scope.get("never") or []],
        "acceptance": {"required_checks": sorted({"contract", *(str(g) for g in scope.get("proves") or [])}),
                       "side_effects": "none"},
        "status": "planned",
        # THE LESSONS TRAVEL WITH THE TASK. What an agent reads before a step is what it checks that
        # step against, so a program is born naming the ledger shapes that share words with its target.
        "watch": [lesson["failure"] for lesson in knowledge.lessons_for(target, 3)],
    })


def labels_for(contract: dict) -> list[str]:
    """The labels a program carries, from the one place that maps a scope to one."""
    import dirscope
    return dirscope.labels_for(contract)


def plan_program(record: dict, objective: str | None, change: str | None) -> tuple[str, str]:
    """(program, refusal) for `thea plan --thea`. Exactly one of the two is ever non-empty.

    Both refusals are the same rule: the notation refuses rather than filling a field in. A
    placeholder objective ships a program that validates and says nothing, which is the shape a
    reader trusts and should not; a program with no change class names no gates, and a contract
    that proves nothing is worse than no contract.
    """
    if not (objective or "").strip():
        return "", ("refused: --thea needs --objective, the one sentence nothing in this tree can "
                    "derive — what would make this task DONE")
    if not change:
        return "", ("refused: --thea needs --change, because a program with no change class names "
                    "no gates and a contract that proves nothing is worse than none")
    return program_from_plan(record, str(objective).strip()), ""


# WHERE EACH ELEMENT IS DECLARED. `--explain` prints this beside the program so a reader can walk
# from any field to the roster that decides it, instead of grepping. A MARK rather than a colour:
# a terminal without colour, a pipe and a log file all read the same, and this repository already
# honours NO_COLOR — so the mark carries the meaning and colour would only repeat it.
#   =  derived from the tree and refused if written by hand
#   :  declared here, resolved against a roster
#   !  binds an approval or a refusal
DECLARED_IN: dict[str, tuple[str, str]] = {
    "schema": ("=", "tools/agent-task.schema.json properties.schema.const"),
    "atlas_version": ("=", "VERSION"),
    "task_id": (":", "the task's own name, and its audit stream"),
    "route": (":", "atlas.yaml/artifact_routes — `thea route <path>`"),
    "task_profile": (":", "atlas.yaml/task_profiles"),
    "change_class": (":", "atlas.yaml/verification_policy/profiles"),
    "risk_modifiers": (":", "atlas.yaml/risk_modifiers"),
    "required_gates": ("=", "derived from change_class and risk_modifiers"),
    "allowed_paths": ("!", "agentpolicy.path_verdict"),
    "forbidden_paths": ("!", "agentpolicy.path_verdict, and the place's own `never`"),
    "allowed_commands": ("!", "agentpolicy.command_verdict"),
    "effects": ("!", "atlas.yaml/agent_policy/effect_classes — agenteffects.effect_verdict"),
    "network": ("!", "agenteffects.effect_verdict"),
    "budgets": ("!", "agentpolicy.budget_verdict, lower of this and default_budgets"),
    "approval_required": ("!", "agentpolicy.approval_verdict"),
    "acceptance": (":", "atlas.yaml/verification_policy/done_set, and the place's own `proves`"),
    "status": ("=", "written by agentrun; `planned` is the only value a runner accepts"),
    "watch": (":", "atlas.yaml/agent_failure_modes — `thea failures --for <target>`"),
}


def explain(contract: dict) -> str:
    """Every element of a program beside the roster that decides it, and the place it works in."""
    import dirscope
    rows = [f"  {mark} {name:<18} {where}" for name, (mark, where) in DECLARED_IN.items()
            if name in contract]
    scope = dirscope.scope_record(str(contract.get("target") or ""))
    lines = ["declared in:", *rows, "",
             f"labels:  {', '.join(labels_for(contract)) or 'none the catalog declares'}"]
    if scope:
        lines += [f"place:   {scope['name']} — {scope['is']}",
                  f"         read {scope['reference']} · {len(scope['traps'])} trap(s) met here"]
    return "\n".join(lines)


def compile_command(path_value: str, as_labels: bool = False, as_explain: bool = False) -> int:
    """`thea compile <file.thea>` — the program as the contract every control already reads.

    It prints the RECORD, never a summary of it: the notation's whole claim is that it produces
    that record and no other, and a rendering of a contract is not a contract. `--explain` adds
    where each element is decided; `--labels` prints only the labels, for a caller filing the work.
    """
    import agentpolicy
    contract = compile_path(Path(path_value))
    if as_labels:
        print("\n".join(labels_for(contract)))
    else:
        print(json.dumps(contract, indent=2, sort_keys=False))
        if as_explain:
            print(explain(contract))
    problems = agentpolicy.contract_errors(contract)
    for problem in problems:
        print(f"- refused: {problem}", file=sys.stderr)
    return 1 if problems else 0


def surface_reference() -> str:
    """Every word the `.thea` parser accepts, READ FROM THE PARSER'S OWN TABLES.

    A grammar written by hand beside a parser is the second declaration of a language, and it goes
    stale on the first keyword either side adds. This reads `thealang`'s vocabulary and the effect
    roster in `atlas.yaml`, so a keyword that exists and is undocumented, or is documented and does
    not exist, is a drifted generated block and `atlas.py check` fails on it.
    """
    effects = ", ".join(f"`{name}`" for name in sorted((atlas().get("agent_policy") or {}).get("effect_classes") or {}))
    rows = [("`task <id> { … }`", "the whole program", "`task_id`")]
    rows += [(f"`{word} <value>`" + (" — quoted" if word in QUOTED else ""), "the task body", f"`{field}`")
             for word, field in SCALARS.items()]
    for name, verbs in VERB_BLOCKS.items():
        for verb, field in verbs.items():
            rows.append((f"`{verb} <path>`", f"`{name} {{ … }}`", f"`{field}`"))
    for name, pairs in PAIR_BLOCKS.items():
        for key, field in pairs.items():
            rows.append((f"`{key} <value>`", f"`{name} {{ … }}`", f"`{field}`"))
        if name in MIXED_BLOCKS:
            rows.append((f"a bare effect: {effects}", f"`{name} {{ … }}`", f"`{MIXED_BLOCKS[name]}`"))
    rows += [("a bare name", f"`{name} {{ … }}`", f"`{field}`") for name, field in WORD_BLOCKS.items()]
    table = ["| write | in | becomes, in the contract |", "|---|---|---|"]
    table += [f"| {write} | {where} | {field} |" for write, where, field in rows]
    derived = ", ".join(f"`{name}`" for name in DERIVED)
    return "\n".join(table) + (
        f"\n\nRefused rather than accepted: {derived} — these are DERIVED, from the schema's own "
        "`const` and from `VERSION`, and writing either one in a program is a second declaration of "
        "a value that already has one. An unknown key, a repeated key, an unclosed block and a bare "
        "word where a quoted string belongs are each refused with the line that holds them.")


def main(argv: list[str]) -> int:
    """`thealang.py <file.thea>` prints the contract; with no argument it checks the tracked set."""
    if argv:
        print(json.dumps(compile_path(Path(argv[0])), indent=2))
        return 0
    problems = surface_errors()
    for problem in problems:
        print(f"  {problem}")
    count = sum(1 for p in tracked() if p.suffix == ".thea")
    print(f"thea surface: {count} program(s), {len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
