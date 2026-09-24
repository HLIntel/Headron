#!/usr/bin/env python3
"""packprobe — how many of each language pack's DECLARED commands resolve on this machine.

WHY THIS EXISTS (2026-09-24). `atlas.py check` proves STRUCTURE: cards 29/29, manifests 29/29,
labels 29/29. Nothing proved that a declared tool EXISTS. A pack naming `cargo-mutants` in its
authority block is a rendering of intent; whether the binary resolves is the identity, and the two
had never been compared.

IT IS A REPORTER, NOT A GATE, AND THAT IS DELIBERATE. Most of these toolchains SHOULD be absent
here: nobody needs `uiua`, `hare` and `carbon` installed on one Mac. A guard that fails on that
fires on correct code and gets silenced, so this prints COVERAGE beside the count instead of a
verdict.

WHAT CHANGED AT 1.3.0 — THE DENOMINATOR IS NOW DECLARED, NOT GUESSED. The previous version
inferred which entries were even probeable by looking at punctuation: anything with a space, a
parenthesis or a slash was assumed to be prose and dropped. That rule excluded 127 of 260 entries
(49%) — including `go test`, `zig fmt` and `cargo clippy`, which PATH can answer for perfectly
well — and a selection rule correlated with the quantity being measured manufactures the result
rather than adding noise to it. Every entry now declares its own kind under the grammar in
tools/tools.schema.json, this file reads that grammar through scripts/packmanifest.py, and the
four non-PATH kinds are counted and printed instead of silently leaving the denominator.

WHAT EACH MODE ANSWERS, AND WHAT IT LEAVES TO THE NEXT ONE:
  --mode resolve  `command -v` finds the FIRST WORD of a command entry on THIS machine's PATH.
                  It says nothing about a subcommand: `cargo mutants` resolves on cargo alone.
  --mode version  RUNS each resolved entry with a version flag, so a subcommand answers for
  --mode smoke    itself, and prints what it said. This is the resolve-mode limit, closed.

SCOPE, NOT A GAP — stated so a low number is not read as a defect:
  - A tool absent here may be present on another machine. ABSENT IS NOT WRONG, and no developer
    is expected to hold 29 toolchains: coverage is printed beside the count, never as a verdict.
  - Alternation (`lldb|gdb`) counts as resolved when EITHER side resolves, because the pack
    declared a choice, not a requirement; both are tried before it is called missing.
  - `lib:`, `builtin:` and `concept:` entries are real declarations that PATH cannot answer for.
    They are counted and printed by kind, never folded into coverage.
  - Whether a pack was exercised END TO END is a codespace's answer (.devcontainer/README.md)
    plus that pack's provenance; this file does not claim it.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from packmanifest import declared_entries, entry_binaries, entry_commands, entry_kind  # noqa: E402

# How a command is asked to identify itself, in order. The first that exits 0 is the answer.
VERSION_FLAGS = ("--version", "-V", "version")
RUN_TIMEOUT = 10


def resolves(entry: str) -> bool:
    """A command entry resolves when any of its declared alternatives is on PATH."""
    return any(shutil.which(name) for name in entry_binaries(entry))


def executes(entry: str) -> tuple[bool, str]:
    """RUN the declared command and let it identify itself: (exited 0, what it said).

    THIS IS THE BLIND SPOT `--mode resolve` LEAVES OPEN, CLOSED. `command -v cargo` answers for
    `cargo mutants` only in the sense that cargo exists; running `cargo mutants --version` is what
    answers for the subcommand. Nothing here is mutated, written or networked: a version flag is
    the one argument a CLI is expected to answer without side effects, and the timeout is bounded.
    """
    tried = [argv for argv in entry_commands(entry) if shutil.which(argv[0])]
    if not tried:
        return False, "not on PATH"
    for argv in tried:
        for flag in VERSION_FLAGS:
            try:
                done = subprocess.run([*argv, flag], capture_output=True, text=True,
                                      timeout=RUN_TIMEOUT, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                return False, f"{exc.__class__.__name__} on `{' '.join(argv)} {flag}`"
            if done.returncode == 0:
                said = (done.stdout or done.stderr).strip().splitlines()
                return True, (said[0][:60] if said else "exited 0 and said nothing")
    return False, f"`{' '.join(tried[0])}` is installed but answered no version flag"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="packprobe.py", description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=("resolve", "version", "smoke"), default="resolve",
                        help="resolve: PATH only (fast). version: run each resolved command's "
                             "version flag. smoke: the same, and count the ones that exit 0.")
    args = parser.parse_args(argv)
    try:
        import yaml
    except ImportError:
        print("packprobe: PyYAML not installed — REFUSING rather than reporting a number it did not measure")
        return 2

    # THE ROSTER IS THE TREE, NOT THE TOP LEVEL. This walked `languages/*/tools.yaml` only, so the
    # nested quantum/qsharp pack — a real pack with a real manifest — was never probed and its
    # entries left the denominator without a word. `rglob` is the tree; a one-level listing was a
    # rendering of it that happened to agree until a pack was nested.
    packs = sorted((ROOT / "languages").rglob("tools.yaml"))
    umbrella = [(d.name, len([s for s in d.iterdir() if s.is_dir()]))
                for d in sorted((ROOT / "languages").iterdir())
                if d.is_dir() and not (d / "tools.yaml").exists()]
    rows = []
    totals = {"declared": 0, "command": 0, "resolved": 0, "ran": 0,
              "lib": 0, "builtin": 0, "concept": 0, "none": 0}
    for manifest in packs:
        pack_name = manifest.parent.relative_to(ROOT / "languages").as_posix()
        doc = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        entries = declared_entries(doc)
        kinds = {k: 0 for k in ("command", "lib", "builtin", "concept", "none")}
        commands, hit, ran, said = [], [], [], {}
        for entry in entries:
            kind = entry_kind(entry)
            kinds[kind] += 1
            if kind != "command":
                continue
            commands.append(entry)
            if resolves(entry):
                hit.append(entry)
                if args.mode in ("version", "smoke"):
                    ok, what = executes(entry)
                    said[entry] = what
                    if ok:
                        ran.append(entry)
        rows.append((pack_name, len(entries), len(commands), len(hit),
                     sorted(set(commands) - set(hit)), kinds, ran, said))
        totals["declared"] += len(entries)
        totals["command"] += len(commands)
        totals["resolved"] += len(hit)
        totals["ran"] += len(ran)
        for kind in ("lib", "builtin", "concept", "none"):
            totals[kind] += kinds[kind]

    print(f"packprobe — {len(rows)} pack(s) with a tools.yaml, {len(umbrella)} domain umbrella(s)\n")
    ran_col = "RAN" if args.mode in ("version", "smoke") else ""
    print(f"{'PACK':<16}{'DECLARED':>9}{'COMMANDS':>9}{'RESOLVE':>8}{ran_col:>5}{'COVER':>7}   MISSING HERE")
    for name, declared, commands, resolved, missing, _, ran, _said in sorted(
            rows, key=lambda r: (r[3] / r[2] if r[2] else 0)):
        cover = f"{100 * resolved // commands}%" if commands else "—"
        ran_cell = f"{len(ran)}" if ran_col else ""
        print(f"{name:<16}{declared:>9}{commands:>9}{resolved:>8}{ran_cell:>5}{cover:>7}   "
              f"{', '.join(missing[:4])}{' …' if len(missing) > 4 else ''}")
    for name, subs in umbrella:
        print(f"{name:<16}{'—':>9}{'—':>9}{'—':>8}{'':>5}{'—':>7}   domain umbrella over {subs} "
              "sub-pack(s), no tools.yaml by design")
    if args.mode in ("version", "smoke"):
        print("\nWHAT EACH RESOLVED COMMAND SAID WHEN RUN:")
        for name, _d, _c, _r, _m, _k, _ran, said in sorted(rows):
            for entry, what in sorted(said.items()):
                print(f"  {name:<16} {entry:<28} {what}")

    cover = f"{100 * totals['resolved'] // totals['command']}%" if totals["command"] else "—"
    print(f"\nCOVERAGE {totals['resolved']}/{totals['command']} declared COMMANDS resolve here ({cover})")
    print(f"  DECLARED {totals['declared']} entries in total, every one classified by the grammar in")
    print("  tools/tools.schema.json — nothing is dropped for looking like prose:")
    print(f"    command {totals['command']}  ·  lib {totals['lib']}  ·  builtin {totals['builtin']}"
          f"  ·  concept {totals['concept']}  ·  none {totals['none']}")
    print("  The last four are declarations PATH cannot answer for, so they are reported by kind")
    print("  and never counted as coverage. `none` is a real answer: no established tool exists.")
    if args.mode in ("version", "smoke"):
        print(f"  EXECUTED {totals['ran']}/{totals['resolved']} resolved commands answered a version flag")
        print("  ({}), so those are confirmed to RUN here, not merely to be on PATH.".format(
            ", ".join(VERSION_FLAGS)))
    else:
        print("  `--mode resolve` asks PATH only. `--mode smoke` RUNS each resolved command's version")
        print("  flag, which is what answers for a subcommand: `command -v cargo` says nothing about")
        print("  whether `cargo mutants` exists.")
    print("  This is a REPORT, not a verdict. Exit is 0 unless the probe itself could not run.")
    print("  SCOPE, not a gap: a tool absent here may be present on another machine — ABSENT IS NOT")
    print("  WRONG, and no pack is expected to resolve fully on any one developer's box. Alternation")
    print("  counts as resolved if either side does, because the pack declared a choice.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
