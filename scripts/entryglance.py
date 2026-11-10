"""Shared first-glance facts for entry pages and structured metadata.

One block, so README.md, llms.txt, CHAT.md and .agent/bootstrap.json cannot disagree. What code knows
comes from code: the Python floor and dependency names from pyproject.toml, init's files from onboard.
"""

from __future__ import annotations

import re
import tomllib

from atlascore import atlas, read


def glance_facts() -> dict:
    """The first-glance answers, with what code knows rendered from code: a typed list would age."""
    from onboard import WIRING  # noqa: PLC0415

    project = tomllib.loads(read("pyproject.toml"))["project"]
    deps = ", ".join(re.split(r"[\s<>=!~\[;]", d, maxsplit=1)[0] for d in project["dependencies"])
    g = atlas()["glance"]
    return {
        "is": g["is"],
        "is_not": g["is_not"],
        "needs": f"Python {project['requires-python']}, {deps}. {g['needs']}",
        "init_writes": [*WIRING, ".git/hooks/pre-commit"],
        "init_note": g["init"],
        "mind": g["mind"],
    }


def glance_lines() -> list[str]:
    """One block for every entry a person or agent opens first, so no two entries can disagree."""
    g = glance_facts()
    writes = ", ".join(g["init_writes"])  # plain: these are the reader's files, absent from this tree
    return [
        f"- **Is:** {g['is']}",
        f"- **Is not:** {g['is_not']}",
        f"- **`headron init` writes:** {writes}. {g['init_note']}",
        f"- **Mind API:** {g['mind']}",
    ]
