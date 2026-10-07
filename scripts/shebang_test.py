#!/usr/bin/env python3
"""Regression cases for shebang routing: the interpreter a first line names chooses the route and the gate."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


def shebang_cases(module) -> None:
    """The interpreter a shebang names chooses the route and the gate; the suffix only names a family (3.43.0)."""
    import enforce
    from agentpolicy import gate_resolution
    from atlas import gate_record
    from atlascore import route_for

    body = "for f in *(N); do :; done\n[[ -n $x ]] || { echo no; exit 1 }\n"  # correct zsh, a syntax error to bash
    with tempfile.TemporaryDirectory() as scratch:
        zsh_file, bash_file, bare = Path(scratch) / "z.sh", Path(scratch) / "b.sh", Path(scratch) / "zrun"
        zsh_file.write_text("#!/usr/bin/env zsh\n" + body)
        bash_file.write_text("#!/bin/bash\n" + body)
        bare.write_text("#!/bin/zsh\n" + body)
        gated = {
            f.name: {g: gate_record(str(f), g)["argv"] for g in ("formatter", "compiler_or_typechecker")}
            for f in (zsh_file, bash_file, bare)
        }
        routed = {f.name: route_for(str(f)) for f in (zsh_file, bash_file, bare)}
        zsh_state, bash_state = enforce.check_file(zsh_file)[0], enforce.check_file(bash_file)[0]
        bare_state = enforce.check_file(bare)[0]
    bash_own = gate_resolution("bash", "compiler_or_typechecker")["argv"]
    want = {
        "z.sh": {
            "formatter": ["shfmt", "-ln", "zsh", "-d", str(zsh_file)],
            "compiler_or_typechecker": ["zsh", "-n", str(zsh_file)],
        },
        "zrun": {
            "formatter": ["shfmt", "-ln", "zsh", "-d", str(bare)],
            "compiler_or_typechecker": ["zsh", "-n", str(bare)],
        },
    }
    if gated["z.sh"] != want["z.sh"] or gated["zrun"] != want["zrun"]:
        raise SystemExit(f"FAIL shebang gate: a zsh shebang must choose zsh's gates, got {gated}")
    if gated["b.sh"]["compiler_or_typechecker"] != [*bash_own, str(bash_file)]:
        raise SystemExit(f"FAIL shebang gate: a bash shebang must keep the pack's {bash_own}, got {gated['b.sh']}")
    if routed != {"z.sh": "bash", "b.sh": "bash", "zrun": "bash"}:
        raise SystemExit(f"FAIL shebang route: an extensionless zsh script must route by its shebang, got {routed}")
    if route_for("*" + "\xff" * 400 + "*~~") is not None:  # a name too long to stat routes nowhere, never raises
        raise SystemExit("FAIL shebang route: an unstattable name must route to None")
    if route_for("a\x00b.sh") != "bash":  # a NUL byte cannot be opened; the suffix still names the family
        raise SystemExit("FAIL shebang route: a name with a NUL byte must fall back to its suffix")
    zsh_want = "PASS" if shutil.which("zsh") else "SKIP"  # a runner without zsh says so; it never passes zsh as bash
    if zsh_state != zsh_want or bare_state != zsh_want or bash_state != "FAIL":
        raise SystemExit(f"FAIL shebang: zsh={zsh_state} bare={bare_state} bash={bash_state}")
    module.CASES.append(
        (
            "a `#!/usr/bin/env zsh` .sh file is checked by zsh, and the same text under bash is refused",
            "correct zsh refused by `bash -n` because a suffix was read as the interpreter",
        )
    )
    module.CASES.append(
        (
            "`thea gate` on a zsh-shebang .sh prints `zsh -n` and a zsh-dialect formatter; a bash shebang keeps the pack's",
            "the gate record read the suffix after the enforcement rung had learned the shebang",
        )
    )
    module.CASES.append(
        (
            "an extensionless `#!/bin/zsh` script routes by its shebang and is gated by zsh",
            "a script with no suffix routed nowhere, so no gate reached it",
        )
    )
    print("  ok    a shebang chooses the route and the gate; the suffix only names a family")


def run(module) -> None:
    shebang_cases(module)
