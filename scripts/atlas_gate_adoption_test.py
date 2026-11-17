"""Gate adoption regression cases."""

import os
import tempfile
from pathlib import Path


def gate_adoption_cases(CASES: list) -> None:
    """A formatter runs only where the repository adopted it; a tool never reads a dialect it cannot parse.
    MEASURED AT 3.62.0 on 8 public repositories: 31 of 58 FAIL rows were an unadopted formatter, and `jq` on
    a commented devcontainer.json and hadolint on `RUN <<EOF` failed files that were correct."""
    from atlas_landing_test import _placed

    fmt = {
        "no config: prettier proves nothing": ({"a.ts": "x\n"}, "a.ts", ["prettier", "--check"], "prettier"),
        "config in a subfolder adopts it there": (
            {"web/.prettierrc": "{}", "web/a.ts": ""},
            "web/a.ts",
            ["prettier", "--check"],
            None,
        ),
        "package.json naming it adopts it": (
            {"package.json": '{"devDependencies": {"prettier": "3"}}', "a.ts": ""},
            "a.ts",
            ["prettier", "--check"],
            None,
        ),
        "a dependency that only contains the name is not it": (
            {"package.json": '{"x": "eslint-config-prettier"}', "a.ts": ""},
            "a.ts",
            ["prettier", "--check"],
            "prettier",
        ),
        ".editorconfig alone is no adoption": (
            {".editorconfig": "[*.sh]\nindent_size = 2\n", "a.sh": ""},
            "a.sh",
            ["shfmt", "-d"],
            "shfmt",
        ),
        "an .editorconfig key only shfmt reads adopts shfmt": (
            {".editorconfig": "[*.sh]\nswitch_case_indent = true\n", "a.sh": ""},
            "a.sh",
            ["shfmt", "-d"],
            None,
        ),
        "a shfmt key adopts no other formatter": (
            {".editorconfig": "[*.sh]\nswitch_case_indent = true\n", "a.ts": ""},
            "a.ts",
            ["prettier", "--check"],
            "prettier",
        ),
        "a workflow naming it adopts it": (
            {".github/workflows/ci.yml": "run: shfmt -d .\n", "a.sh": ""},
            "a.sh",
            ["shfmt", "-d"],
            None,
        ),
        "[tool.ruff] adopts ruff format": (
            {"pyproject.toml": "[tool.ruff]\nline-length = 99\n", "a.py": ""},
            "a.py",
            ["ruff", "format", "--check"],
            None,
        ),
        "a toolchain's own formatter always runs": ({"a.rs": ""}, "a.rs", ["rustfmt", "--check"], None),
    }
    for name, (files, target, argv, why) in fmt.items():
        placed = _placed(files, target, "formatter", argv)
        if (why is None) != ("why" not in placed) or why and why not in placed["why"]:
            raise SystemExit(f"FAIL formatter adoption, {name}: {placed}")
    if "no repository" not in _placed({"a.ts": ""}, "a.ts", "formatter", ["prettier", "--check"], repo=False).get(
        "why", ""
    ):
        raise SystemExit("FAIL a file in no repository was handed to a repository's chosen formatter")
    import gateplace  # noqa: PLC0415

    here = Path.cwd()
    with tempfile.TemporaryDirectory() as outside:  # `headron check` from an install: no repository at the cwd
        os.chdir(outside)
        try:
            off_tree = gateplace.placement("scripts/doctor.py", "formatter", ["ruff", "format", "--check"])
        finally:
            os.chdir(here)
    if "why" in off_tree:
        raise SystemExit(f"FAIL a tree-relative path read from outside the tree lost its repository: {off_tree}")
    dialects = {
        "a commented JSON file is JSONC": ("x.json", '{\n  // note\n  "a": 1,\n}\n', ["jq", "empty"], "JSONC"),
        "strict JSON still runs jq": ("x.json", '{"a": 1}\n', ["jq", "empty"], None),
        "JSON broken in every reader still runs jq": ("x.json", '{"a": \n', ["jq", "empty"], None),
        "a RUN heredoc is not for hadolint": (
            "Dockerfile",
            "FROM alpine\nRUN <<EOF\necho hi\nEOF\n",
            ["hadolint", "--failure-threshold", "error"],
            "heredoc",
        ),
        "a here-string is no heredoc": (
            "Dockerfile",
            "FROM alpine\nRUN cat <<<'hi'\n",
            ["hadolint", "--failure-threshold", "error"],
            None,
        ),
    }
    for name, (target, body, argv, why) in dialects.items():
        placed = _placed({target: body}, target, "compiler_or_typechecker", argv)
        if (why is None) != ("why" not in placed) or why and why not in placed["why"]:
            raise SystemExit(f"FAIL dialect, {name}: {placed}")
    CASES.append(
        (
            f"a formatter runs only where the repository adopts it ({len(fmt) + 1} trees)",
            "prettier, shfmt, taplo or ruff reporting FAIL on a repository that never chose that style",
        )
    )
    CASES.append(
        (
            f"jq skips only JSONC and hadolint only a heredoc; a file broken everywhere still runs ({len(dialects)} files)",
            "a gate reporting FAIL on a dialect its tool cannot read, or a broken file hidden as unreadable",
        )
    )
    print("  ok    a formatter runs only where adopted, and a tool never reads a dialect it cannot parse")
