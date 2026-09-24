#!/usr/bin/env python3
"""The language tool manifest contract — ONE reader for tools/tools.schema.json.

WHY THIS IS ITS OWN MODULE (1.3.0). Three things need to understand a manifest: the contract
harness (does it conform?), packprobe (what can PATH answer for?), and PACK-TOOLS-SPEC.md (what
must an author write?). Before this file they would have needed three copies of the same
required-field rosters and the same entry grammar, and two copies of a roster agree only until one
of them is edited. The schema declares it once; this module is the only code that reads the
schema, and everything else reads this module.

WHY THE VALIDATOR IS WRITTEN OUT HERE rather than delegated to `jsonschema`: the harness has one
runtime dependency (PyYAML) and is expected to run in a bare checkout. The risk in a hand-written
validator is not that it is wrong — it is that it SILENTLY IGNORES a keyword and prints a clean
pass over a constraint nobody checked. So `_check` REFUSES on any keyword it does not implement
(`schema keyword not implemented`), which turns that failure mode from invisible into loud. The
implementation is cross-checked against `jsonschema` 4.26.0 by
`python scripts/atlas_test.py`, which skips that one case, by name, when the library is absent.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import yaml

# Each module locates the repository from its own file; nothing is copied between them.
ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = "tools/tools.schema.json"

# Keywords this validator implements. A schema using anything else is a REFUSAL, never a skip.
IMPLEMENTED = {
    "$ref", "$schema", "$id", "$defs", "title", "description", "x-kinds",
    "type", "const", "enum", "pattern", "minLength", "minItems",
    "required", "properties", "additionalProperties", "propertyNames", "items", "oneOf",
}
JSON_TYPES = {
    "object": dict, "array": list, "string": str, "integer": int,
    "number": (int, float), "boolean": bool, "null": type(None),
}


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def manifest_schema() -> dict:
    """tools/tools.schema.json — the one declaration of what a tools.yaml may contain."""
    data = json.loads(_read(MANIFEST_SCHEMA))
    if not isinstance(data, dict) or "$defs" not in data:
        raise SystemExit(f"{MANIFEST_SCHEMA} did not parse to a schema")
    return data


@lru_cache(maxsize=4)
def manifest_pattern(name: str) -> re.Pattern[str]:
    return re.compile(manifest_schema()["$defs"][name]["pattern"])


def reset_caches() -> None:
    """Forget the parsed schema.

    A CACHED SOURCE OF TRUTH MAKES A PLANTED DEFECT INVISIBLE. The mutation test that edits
    tools/tools.schema.json passed while changing nothing, because this module had already read
    the file and held it: the harness was checking the old bytes and printing a clean pass. Any
    test or tool that edits the schema on disk calls this, and so does the contract's own runner.
    """
    manifest_schema.cache_clear()
    manifest_pattern.cache_clear()


def _resolve(ref: str, root: dict) -> dict:
    node: object = root
    for part in ref.lstrip("#/").split("/"):
        node = node[part]  # type: ignore[index]
    if not isinstance(node, dict):
        raise SystemExit(f"{MANIFEST_SCHEMA}: $ref {ref} does not point at a schema")
    return node


def _check(value: object, schema: dict, root: dict, where: str) -> list[str]:
    """Every violation of `schema` by `value`, each named with the field that holds it."""
    if "$ref" in schema:
        return _check(value, _resolve(schema["$ref"], root), root, where)
    unknown = set(schema) - IMPLEMENTED
    if unknown:
        # A validator that skips a keyword prints a clean pass over an unchecked constraint.
        return [f"{where}: schema keyword not implemented by this harness: {', '.join(sorted(unknown))}"]

    out: list[str] = []
    if "type" in schema:
        expected = JSON_TYPES[schema["type"]]
        # bool is an int in Python; a JSON integer field must not accept true.
        if isinstance(value, bool) is not (schema["type"] == "boolean") or not isinstance(value, expected):
            return [f"{where}: expected {schema['type']}, got {type(value).__name__}"]
    if "const" in schema and value != schema["const"]:
        out.append(f"{where}: must be {schema['const']!r}, is {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{where}: {value!r} is not one of {schema['enum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            out.append(f"{where}: {value!r} does not match the declared form")
        if "minLength" in schema and len(value) < schema["minLength"]:
            out.append(f"{where}: shorter than the declared minimum of {schema['minLength']}")
    if "oneOf" in schema:
        matches = [s for s in schema["oneOf"] if not _check(value, s, root, where)]
        if len(matches) != 1:
            # The message names the FORM, not the arithmetic: "matches 0 of 2 alternatives" tells a
            # manifest author nothing about what to write instead.
            out.append(f"{where}: {value!r} does not match the declared form "
                       f"({len(matches)} of {len(schema['oneOf'])} alternatives matched)")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            out.append(f"{where}: {len(value)} item(s), declared minimum {schema['minItems']}")
        if "items" in schema:
            for i, item in enumerate(value):
                out += _check(item, schema["items"], root, f"{where}[{i}]")
    if isinstance(value, dict):
        out += [f"{where}: missing '{k}'" for k in schema.get("required", []) if k not in value]
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        names = schema.get("propertyNames")
        for key, item in value.items():
            if names is not None:
                out += _check(key, names, root, f"{where} key {key!r}")
            if key in props:
                out += _check(item, props[key], root, f"{where}.{key}")
            elif extra is False:
                out.append(f"{where}: undeclared key '{key}'")
            elif isinstance(extra, dict):
                out += _check(item, extra, root, f"{where}.{key}")
    return out


def entry_kind(value: str) -> str:
    """The DECLARED kind of a manifest entry: command, lib, builtin, concept or none.

    The kind used to be INFERRED from punctuation: an entry with a space or a parenthesis was
    assumed to be prose and dropped from every measurement, which is how 49% of the declared
    surface became unevaluable while the packs still read as complete. The grammar in
    tools/tools.schema.json makes the kind the author's declaration instead of a guess.
    """
    text = str(value).strip()
    kinds = manifest_schema()["$defs"]["entry"]["x-kinds"]
    if text == kinds["none"]["marker"]:
        return "none"
    for kind, spec in kinds.items():
        marker = spec["marker"]
        if marker.endswith(":") and text.startswith(marker):
            return kind
    return "command"


def entry_binaries(value: str) -> list[str]:
    """PATH names a `command` entry may resolve to; empty for every other kind."""
    if entry_kind(value) != "command":
        return []
    return [alt for alt in str(value).strip().split(" ", 1)[0].split("|") if alt]


def entry_commands(value: str) -> list[list[str]]:
    """One argv prefix per declared alternative, so a probe can RUN what it resolved.

    Subcommands are kept deliberately: `command -v cargo` answers for `cargo mutants` only in the
    sense that cargo exists, and running `cargo mutants --version` is what answers for the
    subcommand. EVERY alternative is returned, because returning only the first made the runner
    report `gdb|lldb` unavailable on a machine where the resolver had found lldb — two instruments
    disagreeing about one entry is worse than either being silent.
    """
    if entry_kind(value) != "command":
        return []
    words = str(value).strip().split()
    return [[binary, *words[1:]] for binary in words[0].split("|")]


def manifest_entries(data: dict) -> list[tuple[str, str]]:
    """(field, entry) for every declared entry in a manifest, URLs and policy words aside."""
    out: list[tuple[str, str]] = []
    urls = ("docs", "research")
    for role, value in (data.get("authority") or {}).items():
        if role in urls:
            continue
        for item in value if isinstance(value, list) else [value]:
            out.append((f"authority.{role}", str(item)))
    for group in ("profiles", "policy"):
        for key, value in (data.get(group) or {}).items():
            if group == "policy" and key not in ("default_tools", "optional_tools"):
                continue
            for item in value or []:
                out.append((f"{group}.{key}", str(item)))
    return out


def declared_entries(data: dict) -> list[str]:
    """The DISTINCT declared entries of one manifest, sorted.

    ONE DECLARATION OF ONE NUMBER. packprobe counted distinct entries per pack while the README's
    generated facts counted every position — 276 against 884 for the same words, which is worse
    than either being absent, because a reader cannot tell which instrument is lying. A role and a
    profile naming the same tool is one declared tool.
    """
    return sorted({entry for _, entry in manifest_entries(data)})


def manifest_errors(language: str) -> list[str]:
    """Every way a manifest deviates from tools/tools.schema.json, named with its field.

    SHAPE, NOT EXISTENCE, NOT TRUTH — and the other two are owned, not left open:
    `packprobe.py` answers whether a declared command exists and runs, and `provenance.basis`
    states, per pack, what has not been confirmed against a real toolchain.
    """
    path = ROOT / "languages" / language / "tools.yaml"
    name = f"languages/{language}/tools.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"manifest not YAML: {name} ({exc.__class__.__name__})"]
    if not isinstance(data, dict):
        return [f"manifest not a mapping: {name}"]

    schema = manifest_schema()
    out: list[str] = []
    # The two wordings the mutation tests look for are kept explicit, because a planted defect
    # must produce a message a reader recognises, not only a non-zero exit.
    out += [f"manifest missing key '{k}': {name}" for k in schema["required"] if k not in data]
    policy = data.get("policy")
    if isinstance(policy, dict):
        out += [f"manifest policy missing '{k}': {name}"
                for k in schema["properties"]["policy"]["required"] if k not in policy]
    if str(data.get("language")) != language.split("/")[-1]:
        out.append(f"manifest identity mismatch: {name} language={data.get('language')!r}")
    # Everything else the schema declares, enforced generically. Nothing is skipped: a keyword
    # this validator does not implement is reported as a failure of the harness.
    out += [f"manifest {problem.lstrip('.')}: {name}" for problem in _check(data, schema, schema, "")]
    return sorted(dict.fromkeys(out))
