#!/usr/bin/env python3
"""The installable entry point: resolve WHICH atlas, then run the contract's own CLI against it.

WHY A SEPARATE MODULE (2.11.0). `atlascore` resolves the repository root at IMPORT time, which is
right for a checkout and wrong for an installed copy — site-packages is not an atlas. A flag
cannot fix that from inside `atlas.py`, because by the time argparse sees it the root is already
decided. So this module resolves the root FIRST, exports it, and only then imports the harness.

IT PRINTS WHICH RULE RESOLVED THE ROOT, for the same reason the router prints which rule resolved
a route: an explicit `--atlas-root` and a lucky fall-through to the directory this file happens to
sit in are the same answer with very different trust, and a consumer that cannot tell them apart
will eventually run yesterday's policy against today's tree and never know.

A CONSUMER PINS A REF, NEVER `main`. `.atlas.yaml` carries the pin so it is reviewed in the
consuming repository's own diff rather than passed on a command line nobody reads twice.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

CONSUMER_CONFIG = ".atlas.yaml"


def _config(start: Path) -> tuple[dict, Path | None]:
    """The nearest .atlas.yaml at or above `start`. No parser dependency: three keys, read plainly.

    PyYAML is the harness's one runtime dependency and it is not guaranteed to be importable
    before the harness is installed. This reads the handful of scalar keys a consumer config may
    carry and REFUSES anything more complicated rather than half-parsing YAML.
    """
    for directory in [start, *start.parents]:
        path = directory / CONSUMER_CONFIG
        if not path.exists():
            continue
        found: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue
            key, _, value = stripped.partition(":")
            value = value.strip().strip("'\"")
            if value:
                found[key.strip()] = value
        return found, path
    return {}, None


def resolve_root(argv: list[str], cwd: Path) -> tuple[Path, str]:
    """The atlas this invocation runs against, and the rule that decided it. In declared order."""
    if "--atlas-root" in argv:
        return Path(argv[argv.index("--atlas-root") + 1]).expanduser().resolve(), "explicit --atlas-root"
    for var in ("THEA_ROOT", "CODE_DEVELOPMENT_ROOT"):  # the second is the pre-3.0 name, still honoured
        if os.environ.get(var):
            return Path(os.environ[var]).resolve(), f"{var} in the environment"
    config, where = _config(cwd)
    if config.get("root"):
        base = (where.parent / config["root"]).resolve()
        return base, f"root declared in {where.name} (ref {config.get('ref', 'unpinned')})"
    return Path(__file__).resolve().parents[1], "the checkout this entry point was installed from"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root, rule = resolve_root(argv, Path.cwd())
    if "--atlas-root" in argv:
        index = argv.index("--atlas-root")
        del argv[index:index + 2]
    if not (root / "atlas.yaml").exists():
        print(f"no atlas at {root} (resolved by: {rule})", file=sys.stderr)
        print("point at a checkout with --atlas-root, THEA_ROOT, or a pinned "
              f"`root:` in {CONSUMER_CONFIG}", file=sys.stderr)
        return 2
    os.environ["THEA_ROOT"] = os.environ["CODE_DEVELOPMENT_ROOT"] = str(root)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if "--where" in argv:
        print(f"atlas root: {root}")
        print(f"resolved by: {rule}")
        # AN AGENT HANDED ONLY AN INSTALL MUST STILL FIND WHERE TO START. The entry is a file in the
        # resolved atlas, never a copy in the wheel, so it is printed from the root just resolved.
        print(f"agent entry: {root / '.agent' / 'bootstrap.json'}  (then: atlas gate <file> <gate>)")
        return 0
    import atlas  # noqa: PLC0415 — deliberate: the root must be exported before this import
    return atlas.main(argv or ["check"])


if __name__ == "__main__":
    sys.exit(main())
