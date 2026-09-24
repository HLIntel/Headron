#!/usr/bin/env python3
"""packprobe — how many of each language pack's DECLARED tools actually resolve on this machine.

WHY THIS EXISTS (2026-09-24). `atlas.py check` proves STRUCTURE: cards 29/29, manifests 29/29,
labels 29/29. Nothing proved that a declared tool EXISTS. A pack naming `cargo-mutants` in its
authority block is a rendering of intent; whether the binary resolves is the identity, and the two
had never been compared. An external review put it as "many skeletons, few proven packs" — this
file is the instrument that turns that opinion into a number.

IT IS A REPORTER, NOT A GATE, AND THAT IS DELIBERATE. Most of these toolchains SHOULD be absent
here: nobody needs `uiua`, `hare` and `carbon` installed on one Mac. A guard that fails on that
fires on correct code and gets silenced, so this prints COVERAGE beside the count instead of a
verdict (shipping-and-parity: every gate prints its coverage beside its refusal count).

BLIND SPOTS, PRINTED EVERY RUN so a high number is never read as more than it is:
  - Resolvable means `command -v` finds a name on THIS machine's PATH. It does not run the tool,
    check its version, or prove the pack was ever exercised against it.
  - A tool absent here may be present on another machine. ABSENT IS NOT WRONG.
  - Alternation (`samply_or_perf`) counts as resolved when EITHER side resolves; that is generous
    on purpose, because the pack declared a choice, not a requirement.
"""
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Names that are documentation or policy words, never binaries.
SKIP_PREFIX = ("http://", "https://")
NOT_A_TOOL = {"non_blocking", "blocking", "compile_failure", "test_failure", "clippy_failure"}


def tool_names(node):
    """Every leaf string under a tools.yaml node, minus URLs and policy words."""
    out = []
    if isinstance(node, dict):
        for v in node.values():
            out += tool_names(v)
    elif isinstance(node, list):
        for v in node:
            out += tool_names(v)
    elif isinstance(node, str):
        s = node.strip()
        if s and not s.startswith(SKIP_PREFIX) and s not in NOT_A_TOOL and "_failure" not in s:
            out.append(s)
    return out


def binary_shaped(name):
    """Is this declared string even a name `command -v` could find?

    §10 — AN INSTRUMENT IS WRONG IN ITS SCOPE LONG BEFORE IT IS WRONG IN ITS MATH. The first
    version of this file counted every leaf string, so `none`, `schema_or_abi`, `EXPLAIN ANALYZE`,
    `BEAM (Erlang/OTP)` and `host toolchain tests under wasmtime` all entered the denominator and
    the coverage figure came out at 9% — a number manufactured by its own selection rule. Prose is
    EXCLUDED from the denominator and the excluded count is PRINTED, because a rejection rate that
    is computed and never shown biases the result invisibly while looking rigorous.
    """
    s = str(name).strip()
    if not s or s.lower() in {"none", "n/a", "schema_or_abi"}:
        return False
    for alt in s.replace("+", "_or_").split("_or_"):
        alt = alt.strip()
        # a binary name has no spaces, no parentheses and no path separators
        if alt and " " not in alt and "(" not in alt and "/" not in alt:
            return True
    return False


def resolves(name):
    """A declared name resolves when any of its alternatives is on PATH."""
    for alt in str(name).replace("+", "_or_").split("_or_"):
        alt = alt.strip().replace("_", "-")
        if alt and shutil.which(alt):
            return True
    return False


def main():
    try:
        import yaml
    except ImportError:
        print("packprobe: PyYAML not installed — REFUSING rather than reporting a number it did not measure")
        return 2

    packs = sorted(p for p in (ROOT / "languages").iterdir() if p.is_dir())
    rows, declared_t, resolved_t, prose_t, umbrella = [], 0, 0, 0, []
    for p in packs:
        ty = p / "tools.yaml"
        if not ty.exists():
            # A domain umbrella (quantum) legitimately has no tools.yaml — it is not a skeleton.
            sub = [d for d in p.iterdir() if d.is_dir()]
            umbrella.append((p.name, len(sub)))
            continue
        doc = yaml.safe_load(ty.read_text()) or {}
        raw = sorted(set(tool_names(doc.get("authority", {})) + tool_names(doc.get("profiles", {}))))
        names = [n for n in raw if binary_shaped(n)]
        prose = len(raw) - len(names)
        hit = [n for n in names if resolves(n)]
        rows.append((p.name, len(names), len(hit), sorted(set(names) - set(hit)), prose))
        declared_t += len(names); resolved_t += len(hit); prose_t += prose

    print(f"packprobe — {len(rows)} pack(s) with a tools.yaml, {len(umbrella)} domain umbrella(s)\n")
    print(f"{'PACK':<14}{'BINARIES':>9}{'RESOLVE':>8}{'COVER':>7}{'PROSE':>7}   MISSING HERE")
    for name, d, r, miss, pr in sorted(rows, key=lambda x: (x[2] / x[1] if x[1] else 0)):
        pct = f"{100*r//d}%" if d else "—"
        print(f"{name:<14}{d:>9}{r:>8}{pct:>7}{pr:>7}   {', '.join(miss[:4])}{' …' if len(miss) > 4 else ''}")
    for name, n in umbrella:
        print(f"{name:<14}{'—':>9}{'—':>8}{'—':>7}{'—':>7}   domain umbrella over {n} sub-pack(s), no tools.yaml by design")

    cov = f"{100*resolved_t//declared_t}%" if declared_t else "—"
    print(f"\nCOVERAGE {resolved_t}/{declared_t} BINARY-SHAPED declared tools resolve here ({cov})")
    print(f"  EXCLUDED {prose_t} prose entries from the denominator (none, schema_or_abi, `EXPLAIN")
    print("  ANALYZE`, `BEAM (Erlang/OTP)` …). Printed, not hidden: a rejection rate that is")
    print("  computed and never shown biases the result while looking rigorous.")
    print("  This is a REPORT, not a verdict. Exit is 0 unless the probe itself could not run.")
    print("  BLIND SPOT: `command -v` finds a NAME. It does not run the tool, check its version, or")
    print("  prove any pack was ever exercised against it. A tool absent here may be present")
    print("  elsewhere — ABSENT IS NOT WRONG. Alternation counts as resolved if either side does.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
