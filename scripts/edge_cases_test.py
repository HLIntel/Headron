#!/usr/bin/env python3
"""Planted cases for hard invariants and stage enforcers.

Extracted from atlas_test.py to keep that module under the 1000-line code blob cap.
Like cli_test.py, run(module) accepts the running atlas_test module and records directly
into its counted CASES list so all planted edge assertions remain part of the core shard.
"""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from types import ModuleType
from typing import Any, cast
from unittest import mock

import atlasgen
import atlasinv
import cacheinv

ROOT = CASES = case = mutated = atlas = _VERSION = cast(Any, None)


# Built by parts: a string here would be a word in the code, and so would define the name it plants.
STALE_NAME_ROWS = (
    (
        "docs/VERIFY.md",
        lambda s: s + "\nThe `no_such_" + "mechanism` refuses it.\n",
        "",
        "no_orphaned_symbols",
        "no code defines this name",
    ),
    (
        "scripts/port.py",
        lambda s: s + "\n# `orphans.no_such_" + "symbol` refuses it.\n",
        "",
        "no_orphaned_symbols",
        "no code defines this name",
    ),
)


def promoted_invariant_cases() -> None:
    """Each invariant whose enforcement lives in its own check promoted to a planted case."""
    promoted = [  # a check that cannot fail is worse than a declaration: it reads as coverage
        (
            "scripts/hostshape.py",
            "ls_files(Path.cwd())",
            '[*subprocess.run(["git", "ls-files"]).stdout]',
            "parsers_refuse_rather_than_guess",
            "a second path reader that splits on newlines and lists nothing outside git",
        ),
        (
            "scripts/nativetools.py",
            "parse_jsonc(text)",
            r"json.loads(re.sub(r'//[^\n]*', '', text))",
            "parsers_refuse_rather_than_guess",
            "comments stripped by a regex that also eats the URL a string holds",
        ),
        (
            "scripts/atlasindex.py",
            'parsed_python(source, "<index>")',
            "ast.parse(source)",
            "parsers_refuse_rather_than_guess",
            "a private parser that re-parses and fails its own way",
        ),
        (
            "ci/atlas-ci.yml",
            "    timeout-minutes: 14",
            "    # no timeout",
            "explicit_deadlines",
            "a CI job that hangs until GitHub kills it",
        ),
        (
            "ci/polyglot.yml",
            "run: python scripts/exrun.py",
            "run: python -c 'urlopen(url)'; python scripts/exrun.py",
            "explicit_deadlines",
            "one network call with no deadline spending the whole job on a socket",
        ),
        (
            "scripts/exrun.py",
            "urlopen(url, timeout=FETCH_TIMEOUT)",
            "urlopen(url)",
            "explicit_deadlines",
            "one toolchain download with no deadline spending the whole job on a socket",
        ),
        (
            "ci/atlas-ci.yml",
            "          persist-credentials: false\n",
            "",
            "least_privilege",
            "a checkout that leaves the job's token in .git/config for every later step",
        ),
        (
            ".github/CODEOWNERS",
            "\n* @",
            "\n# no default owner @",
            "auditable_changes",
            "new paths landing with no reviewer",
        ),
        (
            ".github/pull_request_template.md",
            "## Verification",
            "## Vibes",
            "goal_acceptance_is_explicit",
            "a PR that never states what would prove the goal met",
        ),
        (
            "docs/VERSIONING.md",
            f"\n{_VERSION} ",
            f"\n {_VERSION} ",
            "rollback_high_impact",
            "a released version with no changelog line to revert to",
        ),
        (
            "languages/python/tools.yaml",
            "  avoid_by_default:\n  - duplicate_linters\n  - unbounded_async_tasks",
            "  avoid_by_default: []",
            "tool_surfaces_are_bounded",
            "a manifest that names nothing to avoid, so the surface is everything",
        ),
        (
            ".vscode/mcp.json.example",
            '"semgrep": {',
            '"exfiltrator": {',
            "mcp_is_task_scoped",
            "shipping an MCP server no published profile names",
        ),
        (
            "docs/patterns/BOUNDARY-BREAKAGE.md",
            "timeout",
            "deadline",
            "production_boundaries_are_contracts",
            "a boundary doc that never mentions timeouts",
            -1,
        ),
        (
            "config/github-labels.json",
            '"namespaces"',
            '"namespaces"  ,,',
            "schema_first",
            "a machine-read file that no longer parses",
        ),
        (
            "ci/atlas-ci.yml",
            "name: Atlas CI",
            "name: Atlas CI\n# .vscode",
            "ide_is_not_enforcement",
            "a CI gate depending on an editor configuration",
        ),
        (
            "docs/systems/POLYGLOT-ENGINEERING.md",
            lambda s: re.sub(r"(?i)boundary", "frontier", s),
            "",
            "polyglot_boundaries_are_contracts",
            "a polyglot system doc with no boundary declared",
        ),
        (
            "atlas.yaml",
            "    blocker:",
            "    non_blocker:",
            "warnings_are_classified",
            "verification policy missing blocker severity",
        ),
        (
            "atlas.yaml",
            "      required: [formatter, compiler_or_typechecker, unit_tests]",
            "      req_gates: [formatter, compiler_or_typechecker, unit_tests]",
            "task_verification_is_explicit",
            "a verification profile with no required list",
        ),
        (
            "atlas.yaml",
            "    authority: the forge's languages API",
            "    author: the forge's languages API",
            "readings_name_their_cache",
            "staleness discipline entry missing authority",
        ),
        (
            "ci/atlas-ci.yml",
            "runs-on: ubuntu-24.04",
            "runs-on: ubuntu-latest",
            "immutable_first",
            "a CI job running on a moving -latest image",
        ),
        (
            "ci/atlas-ci.yml",
            "atlas_test.py",
            "atlas_mock.py",
            "independent_verification",
            "CI does not run the harness test, so verification is local only",
        ),
        (
            "atlas.yaml",
            "\nmodel_routes:\n",
            "\ndisabled_model_routes:\n",
            "model_choice_is_task_scoped",
            "atlas.yaml/model_routes is empty",
        ),
        (
            "atlas.yaml",
            f"version: {_VERSION}",
            "version: 0.0.1",
            "atlas_consistency",
            "atlas.yaml version and VERSION disagree",
        ),
        (
            "CONTRIBUTING.md",
            lambda s: s + f"\n{atlasgen._begin('language-index')}\n",
            "",
            "one_source_of_truth",
            "generated block 'language-index' also appears in CONTRIBUTING.md",
        ),
        (
            "atlas.yaml",
            "orphan_exemptions:\n",
            'orphan_exemptions:\n  dummy_symbol: ""\n',
            "no_orphaned_symbols",
            "orphan_exemptions/dummy_symbol names no reason",
        ),
        *STALE_NAME_ROWS,
        (
            "atlas.yaml",
            "  baseline_rule:",
            "  no_baseline_rule:",
            "new_violations_cannot_hide_in_baseline",
            "verification_policy.baseline_rule is not declared",
        ),
    ]
    for row in promoted:
        rel_path, find, repl, invariant, kills = row[:5]
        count = row[5] if len(row) > 5 else 1
        with mutated(
            rel_path,
            lambda s, f=find, r=repl, c=count: (
                f(s) if callable(f) else (s.replace(f, r, c) if c > 0 else s.replace(f, r))
            ),
        ):
            case(f"{invariant} FAILS when its property is broken", kills, True, invariant, by=f"inv:{invariant}")


def edge_enforcer_cases() -> None:
    """Plant defects to prove edges for stage enforcers that are not wrapped invariants."""
    with mutated(".gitattributes", lambda s: s.replace("AGENTS.md linguist-generated=true", "AGENTS.md # no-gen", 1)):
        case(
            "generated_attribute_errors FAILS when property broken",
            "a generated file not marked in .gitattributes",
            True,
            "does not mark 'AGENTS.md' as linguist-generated",
            by="contextcost.generated_attribute_errors",
        )
    with mutated(
        "atlas.yaml",
        lambda s: s.replace(
            "means: the delegate ran an instrument in THIS tree and reports its verdict", 'means: ""', 1
        ),
    ):
        case(
            "return_label_errors FAILS when property broken",
            "a delegation return label with empty means",
            True,
            "leaves 'means' empty",
            by="declcheck.return_label_errors",
        )
    with mutated("atlas.yaml", lambda s: s.replace("    owner: the pack author", '    owner: ""', 1)):
        case(
            "claim_errors FAILS when property broken",
            "a tool claim with empty owner",
            True,
            "tool_claims/declared declares no owner",
            by="agentpolicy.claim_errors",
        )
    with mutated(
        "languages/python/tools.yaml", lambda s: s.replace("  benchmark: pytest", "  benchmark: lib:somelib", 1)
    ):
        case(
            "runner_errors FAILS when property broken",
            "a runner driver that is not a command",
            True,
            "which is not a command either",
            by="agentpolicy.runner_errors",
        )


@contextlib.contextmanager
def _listed_as_tracked(reader: ModuleType, name: str):
    """A real file `reader` sees as tracked, with the Git index untouched: other suites share that index."""
    path = ROOT / name
    path.write_text("planted\n", encoding="utf-8")
    listed = reader.tracked()
    try:
        with mock.patch.object(reader, "tracked", lambda: [*listed, path]):
            yield
    finally:
        path.unlink()


def named_enforcer_cases() -> None:
    """The last enforcers no case named. Each plant trips one alone, so UNNAMED_ENFORCER_CEILING stays at zero."""
    import commands  # noqa: PLC0415

    with _listed_as_tracked(atlas, ".env.planted"):
        case(
            "tracked_file_errors FAILS on a tracked environment file",
            "a secrets file committed with nothing to refuse it",
            True,
            "tracked environment/secret file: .env.planted",
            by="tracked_file_errors",
        )
    with _listed_as_tracked(atlasinv, "planted_stream.jsonl"):
        case(
            "no_unbounded_growth FAILS on a tracked append-only stream",
            "a log committed to the repository that grows on every run",
            True,
            "an append-only stream is tracked",
            by="inv:no_unbounded_growth",
        )
    with mutated("scripts/port.py", lambda s: s + "\n" * 1001):
        case(
            "code_blobs_are_bounded FAILS on a code file over the line cap",
            "a module growing past the cap that every split is meant to hold",
            True,
            "code file over MAX_CODE_LINES",
            by="inv:code_blobs_are_bounded",
        )
    with mock.patch.object(atlasinv, "ORPHAN_ROOTS", (*atlasinv.ORPHAN_ROOTS, "planted_root")):
        case(
            "durable_artifacts_are_reachable_or_declared FAILS on a declared root that is gone",
            "an orphan scan over a directory that no longer exists, reading as clean",
            True,
            "a declared documentation root is missing: planted_root",
            by="inv:durable_artifacts_are_reachable_or_declared",
        )
    with mock.patch.object(atlas, "REQUIRED_WIKI", (*atlas.REQUIRED_WIKI, "docs/wiki/planted-page.md")):
        case(
            "required_path_errors FAILS on a required path that is gone",
            "a file the contract depends on deleted with no refusal",
            True,
            "missing required path: docs/wiki/planted-page.md",
            by="required_path_errors",
        )
    with mutated("scripts/port.py", lambda s: s + "\n# sub." + "_choices_actions\n"):  # split: the scan reads this file
        case(
            "argparse_reader_errors FAILS when the tree reads argparse privates",
            "a private read copied outside commands.py, where a stdlib change breaks it",
            True,
            "reads argparse internals",
            by="commands.argparse_reader_errors",
        )
    parser, sub = commands._built_parser()  # a private tree: build_parser's cached one is shared with every reader
    sub.add_parser("planted", help="")
    with mock.patch.object(commands, "build_parser", lambda: (parser, sub)):
        case(
            "cli_errors FAILS on a command with no help line",
            "a command `headron commands` lists as a bare name",
            True,
            "command 'planted' has no help line",
            by="commands.cli_errors",
        )


def cache_invariant_case() -> None:
    """A force-added hidden cache must be caught through the real Git index."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        subprocess.run(["git", "init", "--quiet"], cwd=root, check=True, timeout=30)
        (root / ".gitignore").write_text(".ruff_cache/\n")
        source = root / "src" / "build"
        source.mkdir(parents=True)
        (source / "algorithm.py").write_text("value = 1\n")
        subprocess.run(["git", "add", "src/build/algorithm.py"], cwd=root, check=True, timeout=30)
        cache = root / ".ruff_cache"
        cache.mkdir()
        (cache / "entry").write_text("cache")
        previous = cacheinv.ROOT
        try:
            cacheinv.ROOT = root
            assert cacheinv._inv_no_repo_caches() is None, "legitimate source or ignored cache was refused"
            subprocess.run(["git", "add", "-f", ".ruff_cache/entry"], cwd=root, check=True, timeout=30)
            case(
                "no_repo_caches catches a staged hidden cache",
                "a force-added ignored cache",
                True,
                "cache artifact in repository: .ruff_cache/entry",
                by="inv:no_repo_caches",
            )
        finally:
            cacheinv.ROOT = previous


def shared_read_cases() -> None:
    """text_of holds a file's text against its stat, so what it must never do is answer from before a write."""
    import atlascore  # noqa: PLC0415
    import resilience  # noqa: PLC0415

    moved_past = time.time_ns() + 50_000_000
    settled = atlascore._SETTLED_NS
    with tempfile.TemporaryDirectory() as scratch:
        target = Path(scratch) / "held.txt"
        target.write_text("first", encoding="utf-8")
        assert atlascore.text_of(target) == "first"
        assert (str(target), "strict") not in atlascore._TEXTS, "a file written just now was held"
        target.write_text("other", encoding="utf-8")
        assert atlascore.text_of(target) == "other", "a same-size rewrite answered from before it"
        try:
            atlascore._SETTLED_NS = -(10**18)  # everything counts as settled, so the key alone must catch the write
            held = target.stat()
            assert atlascore.text_of(target) == "other"
            assert (str(target), "strict") in atlascore._TEXTS, "a settled file was not held"
            resilience.wait_until(lambda: time.time_ns() > moved_past, timeout=2, interval=0.01)
            target.write_text("third", encoding="utf-8")
            os.utime(target, ns=(held.st_atime_ns, held.st_mtime_ns))  # same size, same mtime: only ctime moved
            assert atlascore.text_of(target) == "third", "a rewrite with its mtime set back answered from before it"
            bad = Path(scratch) / "bad.txt"
            bad.write_bytes(b"\xff")
            assert atlascore.text_of(bad, errors="replace") == "\ufffd"
            try:
                atlascore.text_of(bad)
            except UnicodeDecodeError:
                pass
            else:
                raise AssertionError("a strict read took the lenient read's answer")
        finally:
            atlascore._SETTLED_NS = settled
    CASES.append(("text_of never answers from before a write", "a held answer outliving the write that replaced it"))
    print("  ok    text_of never answers from before a write")


def walk_index_cases() -> None:
    """The fast walk and the index by class are only speed: both must give what the slow form gave, in its order."""
    import ast  # noqa: PLC0415
    from collections import deque  # noqa: PLC0415

    import atlascore  # noqa: PLC0415

    def slow_walk(root: ast.AST) -> tuple:
        queue, nodes = deque([root]), []
        while queue:
            nodes.append(queue.popleft())
            queue.extend(ast.iter_child_nodes(nodes[-1]))
        return tuple(nodes)

    kinds = (ast.Call, ast.Constant, ast.Try, ast.FunctionDef, ast.Assign, ast.Import, ast.ImportFrom)
    for name in ("atlascore", "callshape", "plantcheck", "roster"):
        tree = atlascore.parsed_python(atlascore.text_of(ROOT / "scripts" / f"{name}.py"), name)
        assert tree is not None, f"{name} did not parse"
        every = atlascore.walked(tree)
        assert every == slow_walk(tree), f"{name}: the walk left breadth-first child order"
        for kind in kinds:
            filtered = tuple(node for node in every if isinstance(node, kind))
            assert atlascore.nodes_of(tree, kind) == filtered, f"{name}: nodes_of({kind.__name__}) left the filter"
    assert atlascore.nodes_of(ast.parse("x = 1"), ast.Try) == (), "a class a tree lacks answered with nodes"
    CASES.append(
        (
            "walked and nodes_of answer as a queue walk and an isinstance filter do",
            "a walk that drops or reorders nodes",
        )
    )
    print("  ok    walked and nodes_of answer as a queue walk and an isinstance filter do")


def flow_prose_cases() -> None:
    """Both YAML scanners give one answer. The C one was once refused as blind: a style test read neither alike."""
    import yaml  # noqa: PLC0415
    from yamlshape import flow_prose  # noqa: PLC0415

    fast = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    plants = {
        "k: [one two three, tail]": ((1, "one two three"),),
        "k: {a: one two three}": ((1, "one two three"),),
        "# note\n\nk: [[a b c]]": ((3, "a b c"),),
        "k:\r\n  - [a b c, d]": ((2, "a b c"),),
        "k: [a\n  b c, d]": ((1, "a b c"),),
        "k: ['one two three', tail]": (),
        'k: ["one two three", tail]': (),
        "k: one two three": (),
    }
    for text, expected in plants.items():
        assert flow_prose(text, yaml.SafeLoader) == expected, f"the Python scanner misread {text!r}"
        assert flow_prose(text, fast) == expected, f"the C scanner misread {text!r}"
    CASES.append(
        ("flow_prose gives one answer under both YAML scanners", "a fast scanner that reads no plain scalar as plain")
    )
    print("  ok    flow_prose gives one answer under both YAML scanners")


def leak_anchor_cases() -> None:
    """An anchor skips a pattern on a file without it, so a leak the anchor misses would pass as clean."""
    import leaks  # noqa: PLC0415

    # Built from parts: this file is itself in the tree the scan reads.
    samples = {
        "home path": "see /" + "Users/someone/x",
        "email address": "write to a" + "@" + "example.org now",
        "private network address": "host 10" + ".1.2.3 up",
        "internal hostname": "at box" + ".internal now",
        "pricing or plan term": "from $" + "5/seat today",
    }
    assert set(samples) == set(leaks.PATTERNS) == set(leaks.ANCHORS), "a leak kind has no anchor or no planted hit"
    for kind, text in samples.items():
        assert any(found == kind for found, _ in leaks._scan(text, ())), f"the anchors hid a {kind}"
    also = {
        "home path": "/" + "home/someone/x",
        "private network address": "192.168" + ".1.2",
        "pricing or plan term": "Headron " + "Teams",
    }
    for kind, text in also.items():
        assert any(found == kind for found, _ in leaks._scan(text, ())), f"the anchors hid a {kind}: {text}"
    CASES.append(("the leak scan's anchors hide no leak of any kind", "a prefilter that skips a file holding the leak"))
    print("  ok    the leak scan's anchors hide no leak of any kind")


def run(module: ModuleType) -> None:
    global ROOT, CASES, case, mutated, atlas, _VERSION
    ROOT, CASES, case, mutated, atlas, _VERSION = (
        module.ROOT,
        module.CASES,
        module.case,
        module.mutated,
        module.atlas,
        module._VERSION,
    )
    promoted_invariant_cases()
    edge_enforcer_cases()
    named_enforcer_cases()
    cache_invariant_case()
    shared_read_cases()
    walk_index_cases()
    flow_prose_cases()
    leak_anchor_cases()
