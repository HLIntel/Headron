#!/usr/bin/env python3
"""What a consuming repository's pull request requires, resolved against a pinned atlas.

WHY IT REPORTS AND DOES NOT VERIFY (2.11.0). This runs inside someone else's repository, where it
knows the diff and knows nothing about the toolchain. A step that ran the caller's gates would be
guessing at commands it cannot see, and a workflow that prints green over gates it did not run is
the exact shape this atlas exists to refuse. So it answers one question — what does THIS change
require? — and names, for every gate it resolved, whether a tool can run it at all.

IT FAILS ON AN UNROUTABLE FILE rather than passing over it. A file the atlas cannot place is a
file whose gates nobody chose, and the useful moment to say so is before the change lands.
"""
from __future__ import annotations

import os
import subprocess
import sys

from agentpolicy import gate_command, process_record, required_gates
from atlascore import atlas, route_for


def changed_paths() -> tuple[list[str], str]:
    """The caller's diff, or the paths it named. Says WHICH, because an empty diff is not no diff."""
    declared = [line.strip() for line in os.environ.get("ATLAS_PATHS", "").splitlines() if line.strip()]
    if declared:
        return declared, "declared by the caller in `paths`"
    base = os.environ.get("GITHUB_BASE_REF") or "origin/HEAD"
    result = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return [], f"git could not diff against {base}: {result.stderr.strip()[:120]}"
    return [line for line in result.stdout.splitlines() if line.strip()], f"the diff against {base}"


def main() -> int:
    task = os.environ.get("ATLAS_TASK") or "implementation"
    change = os.environ.get("ATLAS_CHANGE") or "source_change"
    wanted = os.environ.get("ATLAS_PROCESS") or ""
    paths, how = changed_paths()
    print(f"## Atlas {atlas().get('version')} — required gates\n")
    print(f"Task `{task}`, change class `{change}`. Files: {how}.\n")
    routes: dict[str, list[str]] = {}
    unroutable: list[str] = []
    for path in paths:
        target = route_for(path)
        if target:
            routes.setdefault(target, []).append(path)
        else:
            unroutable.append(path)
    print("| route | files | gate | runnable as |")
    print("|---|---|---|---|")
    gates = required_gates({"change_class": change, "risk_modifiers": []})
    for route, files in sorted(routes.items()):
        for gate in gates:
            argv, why = gate_command(route, gate)
            print(f"| `{route}` | {len(files)} | `{gate}` | " + (f"`{' '.join(argv)}`" if argv else f"not runnable — {why}") + " |")
    if wanted:
        record = process_record(wanted)
        print(f"\n### Process `{wanted}`\n")
        print("Stop when: " + ", ".join(record["stop_when"]))
        print("\nEscalate when: " + ", ".join(record["escalate_when"]))
    if unroutable:
        print(f"\n**{len(unroutable)} file(s) the atlas cannot route**, so no gate was chosen for them:\n")
        for path in sorted(unroutable)[:20]:
            print(f"- `{path}`")
        return 1
    print(f"\n{len(paths)} file(s) over {len(routes)} route(s); every one placed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
