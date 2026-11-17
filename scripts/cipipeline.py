#!/usr/bin/env python3
"""Headron's CI, declared in Python: every job, its steps, what it needs, and how long each may run.

NATIVE, NOT A REPLAY. No GitHub-hosted runner checks a pull request, and no workflow file is translated:
`headron ci` (scripts/cilocal.py) runs these jobs on this machine, each in a clean worktree of one commit,
and posts the `local-ci` commit status the default-branch ruleset requires only when every CONTRACT job
answered ok. Each step is a microprogram: a command, a timeout_s, the tools it needs, and a MicroResult
(ok / unknown / refused / error, with a next step on every non-ok). A step that cannot run here (no tool,
or an action only a hosted runner holds) answers unknown with what to do, never a passing skip.

The `why` text on a job or step is the history its YAML comments carried; keep it when editing a command.

A step's command runs under `bash -euo pipefail -c` from the job's worktree. It reads three variables:
  HEADRON_CI_TEMP       this unit's own scratch directory (gone after the run)
  HEADRON_CI_ARTIFACTS  one directory every unit of a run shares (how edge-coverage reads the shards' ledgers)
  HEADRON_CI_SHARD      the shard this unit runs, for a job that declares `shards` (else empty)

proves: the declared jobs form a DAG over declared names, every step has a positive timeout within its job's budget
does_not_prove: that a step's command checks what its name says; that is the step's own instrument
closed_by: cilocal_test.py, which plants a cycle, an undeclared need, an over-budget step and a $ in an env value
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from micrograph import Node
from micrograph import problems as graph_problems

# THE REQUIRED VERDICT: `local-ci` is posted only when all four answered ok on one commit. `fast` gates
# `mutation`, `mutation` gates `edge-coverage`; `exercises` needs nothing, so it runs beside them.
CONTRACT = ("fast", "mutation", "edge-coverage", "exercises")


@dataclass(frozen=True)
class Step:
    name: str
    run: str
    timeout_s: float
    env: dict[str, str] = field(default_factory=dict)
    # Executables the command needs on PATH; a missing one answers unknown before the command starts.
    tools: tuple[str, ...] = ()
    cwd: str = ""
    # Set when no local run can do this step (a hosted runner's credential): it answers unknown with this reason.
    unavailable: str = ""
    why: str = ""


@dataclass(frozen=True)
class Job:
    name: str
    pipeline: str
    budget_s: float
    steps: tuple[Step, ...]
    needs: tuple[str, ...] = ()
    # One unit per shard, each in its own worktree with HEADRON_CI_SHARD set; empty = one unit.
    shards: tuple[str, ...] = ()
    why: str = ""

    def units(self) -> tuple[str, ...]:
        return tuple(f"{self.name}:{shard}" for shard in self.shards) or (self.name,)


# THE TOOLCHAIN PINS, CHECKED, NEVER INSTALLED: a run must not change the machine. A host whose tool is not the
# pinned one answers refused with the version it found, so a green is never a different toolchain's green.
PYTHON = Step(
    "Check Python 3.13",
    "python -c 'import sys; v = sys.version_info[:2]; sys.exit(0 if v == (3, 13) else f\"python {v} is not the pinned 3.13\")'",
    timeout_s=30,
    tools=("python",),
)
UV = Step(
    "Check uv 0.12.21",
    'for tool in uv uvx; do "$tool" --version | grep -q "^$tool 0\\.12\\.21\\b" || { "$tool" --version; echo "$tool is not the pinned 0.12.21" >&2; exit 1; }; done',
    timeout_s=30,
    tools=("uv", "uvx"),
)
# ONE INSTALL, BY HASH, LINKED. Every job installs the lock through uv: it refuses a line with no hash
# (--require-hashes) and links each package out of its cache (clonefile on APFS), never unpacking it again.
# MEASURED at contract 3.63.0, same lock, same packages: stdlib venv + pip 5.6 s on a quiet machine and ~28 s under a
# land's load, per unit; uv venv + uv pip 0.8 s. .github/ci-local.sh makes the unit's venv with uv as well.
LOCK = "scripts/requirements.lock.txt"


def install(name: str = "Install harness dependency", *locks: str, timeout_s: float) -> Step:
    """The hash-locked install of LOCK plus `locks` into the unit's venv; with no uv it answers unknown."""
    files = " ".join(f"-r {lock}" for lock in (LOCK, *locks))
    return Step(name, f"uv pip install --quiet --require-hashes {files}", timeout_s=timeout_s, tools=("uv",))


GO = Step(
    "Check Go against examples/go/go.mod",
    (
        "want=$(sed -n 's/^go //p' examples/go/go.mod)\n"
        "have=$(go env GOVERSION)\n"
        'python - "$want" "${have#go}" <<\'EOF\'\n'
        "import sys\n"
        'want, have = ([int(p) for p in v.split(".")] for v in sys.argv[1:3])\n'
        'sys.exit(0 if have >= want else f"go {sys.argv[2]} is older than go.mod\'s {sys.argv[1]}")\n'
        "EOF\n"
    ),
    timeout_s=30,
    tools=("go", "python"),
)


JOBS: tuple[Job, ...] = (
    Job(
        "fast",
        pipeline="atlas",
        budget_s=480,
        why=(
            "CHEAP PREFLIGHT, THEN THE MUTATION SUITE, ONE REQUIRED VERDICT. `fast` gates `mutation`, so a "
            "formatting-only correction never pays for the mutation budget. `exercises` depends on nothing but "
            "the checkout, so it runs beside `fast` rather than before `mutation`: it was chained in front of the "
            "longest job and measured 131s of critical path (main, run 40030035505: mutation started 2m13s after "
            "fast finished, and the gap was exercises alone). `local-ci` (the required status) is posted only "
            "when all four answered ok on one commit; these steps are the commands, nothing translates them."
        ),
        steps=(
            Step(
                "Check repository surface",
                ("test -f docs/GITHUB-FINALIZATION.md\ntest -f docs/wiki/TOOL-ORCHESTRATION.md\n"),
                timeout_s=480,
            ),
            Step("Check patch hygiene", "git diff --check", timeout_s=480),
            Step(
                "Install the pinned secret scanner",
                (
                    "set -euo pipefail\n"
                    'case "$(uname -sm)" in\n'
                    "  'Linux x86_64') platform=linux_x64; digest=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb ;;\n"
                    "  'Linux aarch64') platform=linux_arm64; digest=e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080 ;;\n"
                    "  'Darwin x86_64') platform=darwin_x64; digest=dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709 ;;\n"
                    "  'Darwin arm64') platform=darwin_arm64; digest=b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5 ;;\n"
                    "  *) echo 'unsupported scanner platform' >&2; exit 1 ;;\n"
                    "esac\n"
                    'curl -sSfL -o "${HEADRON_CI_TEMP}/gitleaks.tgz" "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_${platform}.tar.gz"\n'
                    "if command -v sha256sum >/dev/null; then checksum='sha256sum'; else checksum='shasum -a 256'; fi\n"
                    'echo "${digest}  ${HEADRON_CI_TEMP}/gitleaks.tgz" | $checksum -c -\n'
                    'tar -xzf "${HEADRON_CI_TEMP}/gitleaks.tgz" -C "${HEADRON_CI_TEMP}" gitleaks\n'
                ),
                timeout_s=480,
                why=(
                    "FIRST, ON THE BARE CHECKOUT (done_set: secret_scan): after the build steps the directory also holds "
                    "downloaded dependencies and build output, which are not this repository's content."
                ),
            ),
            Step(
                "Scan the tree for secrets",
                ('export PATH="${HEADRON_CI_TEMP}:${PATH}"\ngitleaks dir --no-banner --redact .\n'),
                timeout_s=480,
            ),
            PYTHON,
            install(timeout_s=480),
            Step(
                "Check for personal data and secrets",
                (
                    "python scripts/privacy_guard.py --tree\n"
                    "python scripts/privacy_guard.py --range\n"
                    "python scripts/privacy_guard_test.py\n"
                ),
                timeout_s=480,
                why=(
                    "--require-hashes makes the install deterministic: pip refuses anything whose bytes do not match the "
                    "lock, so a compromised or re-uploaded artifact fails the build rather than entering it. Refuses "
                    "personal emails, home paths, names, identities and key shapes in the tree and in every commit above "
                    "origin/main. The CI secret scan does not cover identity or the personal denylist. After the "
                    "dependency install: the guard reads the tracked set through atlascore, which needs yaml."
                ),
            ),
            Step(
                "Check compact agent context before the long mutation suite",
                "python scripts/cli_test.py --brief-smoke",
                timeout_s=480,
            ),
            Step("Check CI and the done set name the same gates", "python scripts/cidrift.py check", timeout_s=480),
            UV,
            Step(
                "Check the pinned linter",
                "uvx --from ruff==0.16.8 ruff --version",
                timeout_s=480,
                why=("Use the same pinned executable in CI and in local replay."),
            ),
            Step("Lint the harness", "uvx --from ruff==0.16.8 ruff check .", timeout_s=480),
            Step(
                "Check the harness is formatted",
                (
                    "uvx --from ruff==0.16.8 ruff format --check . || {\n"
                    "  uvx --from ruff==0.16.8 ruff format --diff .\n"
                    "  exit 1\n"
                    "}\n"
                ),
                timeout_s=480,
            ),
            Step("Type-check the harness against its baseline", "uvx basedpyright@1.40.2", timeout_s=480),
            Step(
                "Run the artifacts pytest cases",
                "uvx --from pytest==8.3.5 --with-requirements scripts/requirements.lock.txt pytest -q -p no:cacheprovider scripts/artifacts_test.py scripts/datakit_test.py scripts/formula_test.py scripts/multimodel_bench_test.py",
                timeout_s=480,
                why=(
                    "THE ARTIFACTS PYTEST CASES, RUN BY THE PINNED RUNNER (done_set: artifacts_tests). Bare python cannot "
                    "call the tmp_path cases, so this is the one place they run on a pull request."
                ),
            ),
            Step(
                "Lint the workflows",
                "uvx --from actionlint-py==1.7.7.23 actionlint .github/workflows/*.yml",
                timeout_s=480,
                why=(
                    "WORKFLOWS, RUN ON THE PULL REQUEST (the secret scan runs first, on the bare checkout) (done_set: "
                    "secret_scan, workflow_lint, workflow_audit)."
                ),
            ),
            Step("Audit the workflows for security", "uvx zizmor@1.14.2 --offline .", timeout_s=480),
            Step("Run repository harness", "python scripts/atlas.py check", timeout_s=480),
        ),
    ),
    Job(
        "mutation",
        pipeline="atlas",
        budget_s=840,
        needs=("fast",),
        # SLOWEST SHARD FIRST: ready units start in declared order, and at width 3 the third shard waits for
        # exercises' seat. Measured at contract 3.63.0: guards-1 112s, core 111s, guards-0 63s (cilocal_test pins it).
        shards=("guards-1", "core", "guards-0"),
        steps=(
            PYTHON,
            install(timeout_s=840),
            Step(
                "Mutation-test the harness itself",
                'ATLAS_SHARD="$HEADRON_CI_SHARD" python scripts/atlas_test.py',
                timeout_s=840,
                why=(
                    "--require-hashes makes the install deterministic: pip refuses anything whose bytes do not match the "
                    "lock, so a compromised or re-uploaded artifact fails the build rather than entering it. FIRST OF THE "
                    "LONG WORK, and deliberately (3.34.0). The compact context check (Fast checks) is cheap and catches a "
                    "broken packet before this step spends its mutation budget. This step is the longest by far, and "
                    "running it last gave it only what the earlier steps left of `timeout-minutes` — MEASURED: the job "
                    "reached it at 2m12s, the suite ran 8m05s, and the 10-minute budget cancelled it mid-run on two "
                    "separate pull requests. Nothing below it is a prerequisite, so moving it first hands it the whole "
                    "budget without raising the cap or weakening a required check."
                ),
            ),
            Step(
                "Keep this shard's edge ledger",
                'cp "$(git rev-parse --git-path headron-edges.json)" "$HEADRON_CI_ARTIFACTS/edges-${HEADRON_CI_SHARD}.json"',
                timeout_s=840,
                why=(
                    "THIS SHARD'S EDGE LEDGER, for the edge-coverage job. A shard sees only its own cases, so the "
                    "unnamed-enforcer ceiling is judged there over the union of all ledgers, never once per shard."
                ),
            ),
        ),
    ),
    Job(
        "edge-coverage",
        pipeline="atlas",
        budget_s=240,
        needs=("mutation",),
        why=(
            "THE EDGE CEILING, OVER ALL SHARDS: the unnamed-enforcer count is a property of the union of the "
            "shards' cases, so this job merges their ledgers and fails above the ceiling. `contract` requires it."
        ),
        steps=(
            PYTHON,
            install(timeout_s=240),
            Step(
                "Judge the union of the shards",
                'python scripts/edges.py --merge "$HEADRON_CI_ARTIFACTS/edges-core.json" "$HEADRON_CI_ARTIFACTS/edges-guards-0.json" "$HEADRON_CI_ARTIFACTS/edges-guards-1.json"',
                timeout_s=240,
            ),
        ),
    ),
    Job(
        "exercises",
        pipeline="atlas",
        budget_s=600,
        steps=(
            PYTHON,
            install(timeout_s=600),
            Step(
                "Exercise directory routing (a language guide must route to its own pack)",
                "python scripts/atlas.py route languages/python/README.md",
                timeout_s=600,
                why=(
                    "--require-hashes makes the install deterministic: pip refuses anything whose bytes do not match the "
                    "lock, so a compromised or re-uploaded artifact fails the build rather than entering it."
                ),
            ),
            Step("Exercise code routing", "python scripts/atlas.py route scripts/atlas.py", timeout_s=600),
            Step(
                "Exercise task planning",
                "python scripts/atlas.py plan scripts/atlas.py --task implementation",
                timeout_s=600,
            ),
            Step("Exercise the mastery loop", "python scripts/atlas.py learn rust", timeout_s=600),
            Step("Refuse duplicate structures and code blobs", "python scripts/astshape.py", timeout_s=600),
            Step("Exercise every example the runner can build", "python scripts/exrun.py --jobs 4", timeout_s=600),
            GO,
            Step(
                "Fuzz the bounded pool",
                "go test -run '^$' -fuzz FuzzPool -fuzztime 30s .",
                timeout_s=600,
                cwd="examples/go",
            ),
            Step(
                "Run every fuzz target's corpus",
                'for target in fuzz/fuzz_*.py; do python "$target" || exit 1; done',
                timeout_s=600,
            ),
            Step("Report which paths have not been re-examined lately", "python scripts/freshness.py", timeout_s=600),
            Step(
                "Report what the repository hands over before a route", "python scripts/contextcost.py", timeout_s=600
            ),
            Step("Hold every Markdown file to its class", "python scripts/mdshape.py", timeout_s=600),
            Step(
                "Run the enforcement rung Headron ships, on Headron itself",
                "python scripts/enforce.py check --tracked",
                timeout_s=600,
            ),
            Step("Build and verify the retrieval index", "python scripts/atlasindex.py check", timeout_s=600),
            Step("Measure whether the atlas actually helps", "python scripts/bench.py", timeout_s=600),
            Step("Prove the agent controls refuse what they claim to", "python scripts/agent_test.py", timeout_s=600),
            Step("Run the reference task contract under the policy", "python scripts/agentrun.py", timeout_s=600),
            Step("Report hard-invariant ownership", "python scripts/atlas.py invariants", timeout_s=600),
        ),
    ),
    Job(
        "install",
        pipeline="atlas",
        budget_s=480,
        why=(
            "THE DOCUMENTED INSTALL, EXECUTED (3.52.0). README advertised an index install the index did not "
            "carry, and nothing ran it. This job installs the tree being merged by the command the documents "
            "render from atlas.yaml/install_commands, in a clean home, and judges `headron doctor` by exit code."
        ),
        steps=(
            PYTHON,
            UV,
            install(timeout_s=480),
            Step(
                "Run every documented install command in a clean home",
                "python scripts/cli_test.py --install",
                timeout_s=480,
            ),
        ),
    ),
    Job(
        "receipt",
        pipeline="atlas",
        budget_s=300,
        why=(
            "PROOF OF CHANGE (3.48.0). A pull request that names its contract in its body (`Headron-Contract: "
            "path/to/task.headron`) has its DIFF, base..head, judged against that contract's scope, and the "
            "outcome — contract hash, base, head — attested, so the check mark is a signed claim about this exact "
            "change rather than a badge. No line, no claim: it says so and passes."
        ),
        steps=(
            PYTHON,
            install(timeout_s=300),
            Step(
                "Judge the diff against the contract the pull request names",
                (
                    "BODY=$(gh pr view --json body -q .body)\n"
                    "BASE_SHA=$(gh pr view --json baseRefOid -q .baseRefOid)\n"
                    "p=$(printf '%s\\n' \"$BODY\" | sed -n 's/^Headron-Contract:[[:space:]]*\\([^[:space:]]*\\).*$/\\1/p' | head -n 1)\n"
                    'if [ -z "$p" ]; then\n'
                    '  echo "no Headron-Contract line: scope NOT checked, nothing attested"\n'
                    "  exit 0\n"
                    "fi\n"
                    'case "$p" in *..*) echo "refused: $p traverses"; exit 1;; esac\n'
                    "printf '%s' \"$p\" | grep -Eq '^[A-Za-z0-9_./-]+\\.headron$' || { echo \"refused: $p is not a .headron path\"; exit 1; }\n"
                    'git fetch --quiet --depth=1 origin "$BASE_SHA"\n'
                    'HEADRON_BASE="$BASE_SHA" python scripts/agentrun.py --json "$p" > receipt.json\n'
                ),
                timeout_s=300,
                tools=("gh",),
            ),
            Step(
                "Attest the receipt",
                "",
                timeout_s=30,
                unavailable=(
                    "attest-build-provenance signs with a GitHub-hosted OIDC token, which no local run holds; "
                    "receipt.json is judged but NOT attested"
                ),
            ),
        ),
    ),
    Job(
        "examples",
        pipeline="polyglot",
        budget_s=2700,
        steps=(
            PYTHON,
            install(timeout_s=2700),
            Step(
                "Install the declared toolchains",
                "brew bundle check --file=Brewfile",
                timeout_s=2700,
                env={"HOMEBREW_NO_AUTO_UPDATE": "1"},
                tools=("brew",),
                why="CHECKS, NEVER INSTALLS: a run must not change the machine. A missing toolchain fails with `brew bundle --file=Brewfile` as the next step.",
            ),
            Step(
                "Run every example",
                'python scripts/exrun.py --official "$HOME/.cache/headron/toolchains" --jobs 4',
                timeout_s=2700,
            ),
        ),
    ),
    Job(
        "fuzz",
        pipeline="fuzz",
        budget_s=1200,
        shards=("fuzz_manifest_entry", "fuzz_jsonc"),
        steps=(
            PYTHON,
            install("Install the harness and atheris, by hash", "fuzz/requirements.lock.txt", timeout_s=1200),
            Step(
                "Fuzz the target for ten minutes",
                (
                    'crashes="$HEADRON_CI_ARTIFACTS/crashes-$HEADRON_CI_SHARD"\n'
                    'mkdir -p "$crashes"\n'
                    'python "fuzz/$HEADRON_CI_SHARD.py" -max_total_time=600 -artifact_prefix="$crashes/"\n'
                ),
                timeout_s=1200,
            ),
        ),
    ),
)


def nodes(jobs: Sequence[Job]) -> list[Node]:
    """One graph node per unit; a unit needs EVERY unit of each job its job needs, among `jobs`."""
    names = {job.name for job in jobs}
    units = {job.name: job.units() for job in jobs}
    return [
        Node(unit, tuple(u for need in job.needs if need in names for u in units[need]), job.budget_s)
        for job in jobs
        for unit in job.units()
    ]


def problems(jobs: Sequence[Job] = JOBS) -> list[str]:
    """Every way the declaration is not a runnable DAG of bounded steps; empty when it is."""
    names = [job.name for job in jobs]
    found = [f"job {name!r} declared twice" for name in sorted({n for n in names if names.count(n) > 1})]
    known = set(names)
    for job in jobs:
        found += [f"{job.name} needs undeclared job {need!r}" for need in job.needs if need not in known]
        if not job.steps:
            found.append(f"{job.name} has no steps")
        for step in job.steps:
            if not 0 < step.timeout_s <= job.budget_s:
                found.append(
                    f"{job.name} / {step.name}: timeout_s {step.timeout_s:g} is not within (0, {job.budget_s:g}]"
                )
            # AN ENV VALUE IS LITERAL: nothing expands it. "${HEADRON_CI_SHARD}" here reached the step as those
            # characters, so every mutation shard ran the whole suite; a variable belongs in the command.
            found += [
                f"{job.name} / {step.name}: env {key}={value!r} holds a $; put the variable in the command"
                for key, value in step.env.items()
                if "$" in value
            ]
    if not found:
        found = graph_problems(nodes(jobs))
    return found


def selected(
    names: Sequence[str], pipeline: str = "", jobs: Sequence[Job] = JOBS, contract: Sequence[str] = CONTRACT
) -> list[Job]:
    """Exactly the named jobs, in declared order; none named = the CONTRACT jobs (or one pipeline's jobs).

    A NAMED JOB RUNS ALONE: `ci-local.sh edge-coverage` must not silently pay for fast and three mutation
    shards. Its needs outside the selection are dropped, so it reads whatever the shared store already holds.
    """
    names = list(names) or ([job.name for job in jobs if job.pipeline == pipeline] if pipeline else list(contract))
    declared = [job.name for job in jobs]
    if unknown := [name for name in names if name not in declared]:
        raise SystemExit(f"ci: no job {', '.join(unknown)}; declared: {', '.join(declared)}")
    return [job for job in jobs if job.name in names]
