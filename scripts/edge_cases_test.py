#!/usr/bin/env python3
"""Planted cases for hard invariants and stage enforcers.

Extracted from atlas_test.py to keep that module under the 1000-line code blob cap.
Like cli_test.py, run(module) accepts the running atlas_test module and records directly
into its counted CASES list so all planted edge assertions remain part of the core shard.
"""

from __future__ import annotations

import re
from typing import Any, cast

import atlasgen

ROOT = CASES = case = mutated = atlas = _VERSION = cast(Any, None)


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
            ".github/workflows/atlas-ci.yml",
            "    timeout-minutes: 14",
            "    # no timeout",
            "explicit_deadlines",
            "a CI job that hangs until GitHub kills it",
        ),
        (
            ".github/workflows/polyglot.yml",
            ", timeout=60)",
            ")",
            "explicit_deadlines",
            "one network call with no deadline spending the whole job on a socket",
        ),
        (
            ".github/workflows/atlas-ci.yml",
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
            ".github/workflows/atlas-ci.yml",
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
            ".github/workflows/atlas-ci.yml",
            "runs-on: ubuntu-24.04",
            "runs-on: ubuntu-latest",
            "immutable_first",
            "a CI job running on a moving -latest image",
        ),
        (
            ".github/workflows/atlas-ci.yml",
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
            "orphan_exemptions: {}",
            'orphan_exemptions:\n  dummy_symbol: ""',
            "no_orphaned_symbols",
            "orphan_exemptions/dummy_symbol names no reason",
        ),
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


def run(module) -> None:
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
