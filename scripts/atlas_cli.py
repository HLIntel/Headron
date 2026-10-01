#!/usr/bin/env python3
"""The installable entry point: resolve WHICH atlas, then run the contract's own CLI against it.

A SEPARATE MODULE (2.11.0) because `atlascore` fixes the root at IMPORT time: this resolves it first,
exports it, then imports the harness. IT PRINTS THE RULE THAT DECIDED THE ROOT: an explicit flag and
a lucky fall-through are the same answer with very different trust. A CONSUMER PINS A REF, NEVER
`main`, in `.atlas.yaml`, so the pin is reviewed in its own diff.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

CONSUMER_CONFIG = ".atlas.yaml"
FLAG = "--atlas-root"
# REFUSE RATHER THAN INVENT (3.47.0): a key not known by name is refused at its file:line.
SECTIONS, PIN = ("atlas", "stack_tiers", "markdown_policy"), ("ref", "root", "task", "change_class", "process")


class ConfigError(ValueError):
    """A root flag or consumer config this entry point refuses to guess about."""


def _keys(path: Path, node, what: str, allowed=()) -> dict:
    if not isinstance(node, yaml.MappingNode):
        raise ConfigError(f"{path}:{node.start_mark.line + 1}: {what} must be a mapping")
    out = {}
    for key, value in node.value:
        name, line = key.value, key.start_mark.line + 1
        if not isinstance(name, str) or name in out or allowed and name not in allowed:
            raise ConfigError(f"{path}:{line}: bad or repeated key {name!r} in {what}; allowed: {allowed}")
        out[name] = value
    return out


def _pin(path: Path) -> dict[str, str]:
    """The `atlas:` mapping of one config file, every key checked by name."""
    try:
        doc = yaml.compose(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        raise ConfigError(f"{path}:{mark.line + 1 if mark else 1}: not parseable YAML") from None
    sections = _keys(path, doc, CONSUMER_CONFIG, SECTIONS) if doc else {}
    pins = {name: _keys(path, node, name) for name, node in sections.items()}.get("atlas", {})
    for name, value in pins.items():
        if name not in PIN or value.tag != "tag:yaml.org,2002:str" or not value.value.strip():
            raise ConfigError(f"{path}:{value.start_mark.line + 1}: atlas.{name}: want a string in {PIN}")
    return {name: value.value for name, value in pins.items()}


def _config(start: Path) -> tuple[dict, Path | None]:
    """The pin of the nearest .atlas.yaml at or above `start`; ConfigError on any doubt."""
    for path in (d / CONSUMER_CONFIG for d in [start, *start.parents]):
        if path.exists():
            return _pin(path), path
    return {}, None


def root_flag(argv: list[str]) -> tuple[str | None, int, int]:
    """(value, index, width) of the root flag, or (None, -1, 0); refused with no value (3.47.0)."""
    hits = [i for i, arg in enumerate(argv) if arg == FLAG or arg.startswith(FLAG + "=")]
    if not hits:
        return None, -1, 0
    i, eq = hits[0], argv[hits[0]] != FLAG
    value = argv[i].partition("=")[2] if eq else (argv[i + 1 :] or [""])[0]
    if len(hits) > 1 or not value.strip() or value.startswith("-") and not eq:
        raise ConfigError(f"{FLAG} needs one directory, given once; got {value!r}")
    return value, i, 1 if eq else 2


def resolve_root(argv: list[str], cwd: Path) -> tuple[Path, str]:
    """The atlas this invocation runs against, and the rule that decided it. In declared order."""
    value = root_flag(argv)[0]
    if value is not None:
        return Path(value).expanduser().resolve(), f"explicit {FLAG}"
    for var in ("THEA_ROOT", "CODE_DEVELOPMENT_ROOT"):  # the second is the pre-3.0 name, still honoured
        if os.environ.get(var):
            return Path(os.environ[var]).resolve(), f"{var} in the environment"
    config, where = _config(cwd)
    if config.get("root"):
        base = (where.parent / config["root"]).resolve()
        return base, f"root declared in {where.name} (ref {config.get('ref', 'unpinned')})"
    return Path(__file__).resolve().parents[1], "the checkout this entry point was installed from"


def _resolved(argv: list[str]) -> tuple:
    try:
        return resolve_root(argv, Path.cwd())
    except ConfigError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return None, None


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root, rule = _resolved(argv)
    if root is None:
        return 2
    _, index, width = root_flag(argv)
    del argv[index : index + width]
    if not (root / "atlas.yaml").exists():
        print(f"no atlas at {root} (resolved by: {rule})", file=sys.stderr)
        print(f"point at a checkout with {FLAG}, THEA_ROOT, or `atlas: root:` in {CONSUMER_CONFIG}", file=sys.stderr)
        return 2
    os.environ["THEA_ROOT"] = os.environ["CODE_DEVELOPMENT_ROOT"] = str(root)
    # THE HARNESS COMES FROM THE ATLAS, NEVER THE WHEEL (3.7.0): a bundled copy is a second implementation.
    harness = root / "scripts"
    if not (harness / "atlas.py").exists():
        print(f"{root} has an atlas.yaml and no scripts/atlas.py — not a Thea checkout", file=sys.stderr)
        return 2
    sys.path.insert(0, str(harness))
    if "--where" in argv:
        print(f"atlas root: {root}")
        print(f"resolved by: {rule}")
        # An agent handed only an install must still find where to start: the resolved atlas's entry.
        print(f"agent entry: {root / '.agent' / 'bootstrap.json'}  (then: thea gate <file>)")
        return 0
    import atlas  # noqa: PLC0415 — deliberate: the root must be exported before this import

    return atlas.main(argv or ["check"])


def mcp_main() -> int:
    """`thea-mcp`: the same root resolution, then serve the resolved atlas's MCP route on stdio."""
    argv = sys.argv[1:]
    if "--where" in argv:
        return main(argv)
    root, rule = _resolved(argv)
    if root is None:
        return 2
    if not (root / "scripts" / "thea_mcp.py").exists():
        print(f"no Thea MCP server at {root} (resolved by: {rule})", file=sys.stderr)
        return 2
    os.environ["THEA_ROOT"] = os.environ["CODE_DEVELOPMENT_ROOT"] = str(root)
    sys.path.insert(0, str(root / "scripts"))
    import thea_mcp  # noqa: PLC0415 — deliberate: the root must be exported before this import

    return thea_mcp.serve()


if __name__ == "__main__":
    sys.exit(main())
