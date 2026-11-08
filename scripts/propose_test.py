#!/usr/bin/env python3
"""Regression cases for `headron propose`: a draft lives outside the tree and is held to the adaptation contract."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
from pathlib import Path
from types import ModuleType
from unittest import mock

REFUTED = (
    "was:\n  statement: s\n  label: INFERRED\n  evidence: [file:style.cfg]\n  provenance: p\n  status: refuted\n"
    "  superseded_by: now\n  dependents: [file:style.cfg]\n"
    "now:\n  statement: s\n  label: CONFIRMED\n  evidence: [file:style.cfg]\n  provenance: p\n  status: holds\n"
)


def _tree(tmp: Path, registry: str) -> Path:
    (tmp / "docs" / "systems").mkdir(parents=True)
    (tmp / "docs" / "systems" / "claims.yaml").write_text(registry, encoding="utf-8")
    (tmp / "style.cfg").write_text("indent = 4\n", encoding="utf-8")
    return tmp


def _files(path: Path) -> list[str]:
    return sorted(str(p.relative_to(path)) for p in path.rglob("*") if p.is_file())


def run(module: ModuleType) -> None:
    import propose

    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        root, home = _tree(base / "tree", REFUTED), base / "home" / "drafts"
        before = _files(root)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            wrote = propose.propose(True, root, home)
        row = json.loads(out.getvalue())
        assert wrote == 1 and row["proposed"] == ["was"], row
        assert _files(root) == before, "a draft was written into the tree"
        draft = home / "revise-was.json"
        spec = json.loads(draft.read_text(encoding="utf-8"))["revise_was"]
        assert spec["rests_on"] == ["now"] and "file:style.cfg" in spec["intervention"], spec
        with contextlib.redirect_stdout(io.StringIO()) as out:
            incomplete = propose.check(str(draft), True, root)
        errors = json.loads(out.getvalue())["errors"]
        assert incomplete == 1 and any("declares no expected_gain" in e for e in errors), errors
        filled = {"revise_was": {**spec, **dict.fromkeys(propose.LEFT_FOR_A_PERSON, "x")}}
        draft.write_text(json.dumps(filled), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            complete = propose.check(str(draft), True, root)
        assert complete == 0, "a draft with every proof field filled was refused"

        inside = root / ".headron" / "drafts"
        with contextlib.redirect_stdout(io.StringIO()) as out:
            refused = propose.propose(True, root, inside)
        assert refused == 2 and "resolves inside" in out.getvalue(), out.getvalue()
        assert _files(root) == before and not inside.exists(), "a refused draft still reached the tree"

        with mock.patch.dict(os.environ, {"HEADRON_READ_ONLY": "1"}), contextlib.redirect_stdout(io.StringIO()) as out:
            read_only = propose.propose(True, root, base / "home-ro")
        assert read_only == 2 and "HEADRON_READ_ONLY" in out.getvalue(), out.getvalue()
        assert not (base / "home-ro").exists(), "the read-only route wrote a draft"

        clean = _tree(base / "clean", REFUTED.replace("status: refuted", "status: holds"))
        with contextlib.redirect_stdout(io.StringIO()):
            nothing = propose.propose(True, clean, base / "home2")
        assert nothing == 0 and not (base / "home2").exists(), "a tree with no refuted claim got a draft"
    module.CASES.append(
        (
            "propose: one draft per refuted claim with dependents, written outside the tree, held to every "
            "adaptation proof field; a drafts directory inside the tree, or a read-only route, is refused and nothing is written",
            "a loop that drafts its own revision into the checkout, where the next commit promotes it",
        )
    )
    print("  ok    propose: drafts outside the tree, held to the adaptation contract; inside is refused")
