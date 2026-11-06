#!/usr/bin/env python3
"""exrun — run every example this machine can, and say why it skipped the rest.

WHY THIS EXISTS (v2.2.0). The examples were documentation that happened to be code: one imported a
package that was never installed, so it could not run at all, and nothing noticed. An example
nobody executes is a skeleton — the exact thing this repository refuses in language packs, sitting
in the directory a reader copies from.

It holds NO roster of its own. Every file under examples/ is routed with this repository's own
router, and the recipe is looked up by route in atlas.yaml/example_runners. A file that does not
route, or whose route declares no runner, is REPORTED as unexercised rather than quietly passed
over: those two look identical in a summary and mean opposite things.

  python scripts/exrun.py            # PASS / FAIL / SKIP with the reason, exit 1 on any FAIL
  python scripts/exrun.py --json     # the same as a record

SCOPE: an example that PASSES proves its own assertions held on this machine with this toolchain.
It does not prove the pack's other declarations, which is `packprobe.py --mode smoke`, and it says
nothing about a toolchain that is absent — ABSENT IS NOT WRONG.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import atomicfile  # noqa: E402
import resilience  # noqa: E402
from atlascore import atlas, rel, route_for, tracked  # noqa: E402

STEP_TIMEOUT = 120
FETCH_TIMEOUT = 300
SKIP_SUFFIXES = {".json", ".md", ".txt", ".lock", ".mod", ".sum"}


def examples() -> list[Path]:
    return sorted(
        p
        for p in tracked()
        if p.relative_to(ROOT).parts[:1] == ("examples",)  # the tree, not the disk
        and p.is_file()
        and p.suffix.lower() not in SKIP_SUFFIXES
        and not p.name.endswith(".d.ts")
    )


def run_one(path: Path, steps: list[list[str]]) -> tuple[str, str]:
    """(verdict, detail) for one example: PASS, FAIL or SKIP with the reason.

    Every step runs BESIDE THE FILE, not at the repository root, because a module-aware toolchain
    needs its own manifest in scope — `go vet .` cannot see examples/go/go.mod from anywhere else.
    Paths are substituted absolute, so the working directory changes nothing for the others.
    """
    if not steps:
        return "FAIL", "the runner declares no steps, so nothing ran"
    done = subprocess.CompletedProcess([], 0, "", "")  # never read: `steps` is non-empty past the guard
    with tempfile.TemporaryDirectory() as work:
        out = str(Path(work) / "example.bin")
        for step in steps:
            argv = [
                word.replace("{file}", str(path)).replace("{out}", out).replace("{scripts}", str(ROOT / "scripts"))
                for word in step
            ]
            if not shutil.which(argv[0]) and not argv[0].startswith("/"):
                return "SKIP", f"{argv[0]} is not on PATH — absent is not wrong"
            try:
                # NO INHERITED STDIN (3.57.0): `futhark run` reads its entry point's arguments from stdin,
                # so under a parent holding a terminal or pipe open it waited out STEP_TIMEOUT and FAILED.
                done = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=STEP_TIMEOUT,
                    cwd=path.parent,
                    check=False,
                    stdin=subprocess.DEVNULL,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                return "FAIL", f"{exc.__class__.__name__} running {' '.join(argv[:2])}"
            if done.returncode != 0:
                if argv[0] == "lean" and done.stderr.startswith("error: no default toolchain configured."):
                    return "SKIP", "Lean launcher has no default toolchain — absent is not wrong"
                tail = (done.stderr or done.stdout).strip().splitlines()
                return "FAIL", f"exit {done.returncode} from {argv[0]}: {tail[-1][:120] if tail else 'no output'}"
        said = (done.stdout or "").strip().splitlines()
        return "PASS", (said[-1][:96] if said else "exited 0 and printed nothing")


def _fetch(url: str) -> bytes:
    def read() -> bytes:
        with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT) as answer:  # noqa: S310 — https rows pinned in atlas.yaml
            return answer.read()

    return resilience.call(read, attempts=3, base=1.0, cap=10.0, deadline=FETCH_TIMEOUT)


def install_official(runners: dict, store: Path) -> list[str]:
    """The directories to put on PATH for every toolchain a runner pins by digest, installing what is not there yet.

    Only a release whose bytes match the digest in atlas.yaml is ever kept, and it lands by rename, so an interrupted
    install leaves nothing a later run could mistake for it. A directory named for the digest is therefore reused
    without another download. A mismatch raises: refusing the toolchain is not the same as lacking it.
    """
    if (sys.platform, platform.machine()) != ("darwin", "arm64"):
        return []  # each pin is one macOS arm64 build; elsewhere these examples SKIP as absent
    directories = []
    for name, spec in sorted(runners.items()):
        pin = (spec or {}).get("official")
        if not pin:
            continue
        expected = base64.b64decode(pin["integrity"].removeprefix("sha256-")).hex()
        home = store / f"{name}-{expected[:16]}"
        if not home.is_dir():
            blob = _fetch(pin["url"])
            if hashlib.sha256(blob).hexdigest() != expected:
                raise ValueError(f"{name}: {pin['url']} does not match the digest in atlas.yaml")
            store.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=store) as work:
                unpacked = Path(work) / "toolchain"
                unpacked.mkdir()
                if binary := pin.get("binary"):
                    (unpacked / binary).write_bytes(blob)
                    (unpacked / binary).chmod(0o755)
                else:
                    with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
                        archive.extractall(unpacked, filter="data")
                atomicfile.move(unpacked, home)
        tops = [path for path in home.iterdir() if path.is_dir()]
        directories.append(str(tops[0] if len(tops) == 1 else home))
    return directories


def brewfile() -> str:
    """Brewfile: every toolchain an example declares with `brew:`, so `brew bundle` installs exactly
    what `exrun.py` needs. GENERATED, because a hand-kept install list narrows silently the first
    time a runner is added beside it; and `brew bundle check` is then a real gate, not a hope."""
    formulae = sorted(
        {
            str(spec["brew"])
            for spec in (atlas().get("example_runners") or {}).values()
            if isinstance(spec, dict) and spec.get("brew")
        }
    )
    head = [
        "# GENERATED from atlas.yaml/example_runners by `python scripts/atlas.py index --write`. Do not edit.",
        "# brew bundle            installs every toolchain an example needs",
        "# brew bundle check      exit code says whether this machine has them all",
        "",
    ]
    return "\n".join(head + [f'brew "{f}"' for f in formulae]) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="exrun.py", description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--json", action="store_true", help="emit the run as a record")
    parser.add_argument("--jobs", type=int, default=1, help="independent examples to run at once (default: 1)")
    parser.add_argument(
        "--official", metavar="DIR", help="install the digest-pinned toolchains here first and use them"
    )
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")

    runners = atlas().get("example_runners") or {}
    if args.official:
        try:
            pinned = install_official(runners, Path(args.official))
        except (OSError, ValueError, tarfile.TarError) as exc:
            print(f"exrun: a pinned toolchain was refused: {exc}", file=sys.stderr)
            return 2
        os.environ["PATH"] = os.pathsep.join([*pinned, os.environ.get("PATH", os.defpath)])
    rows: list[dict] = []
    work: list[tuple[Path, str, list[list[str]]]] = []
    seen_dirs: set[Path] = set()
    for path in examples():
        route = route_for(str(path))
        if route is None:
            rows.append(
                {
                    "file": rel(path),
                    "route": None,
                    "verdict": "SKIP",
                    "detail": "not a routed artifact, so no toolchain claims it",
                }
            )
            continue
        recipe = runners.get(route)
        if recipe and recipe.get("per") == "directory":
            # ONE RUN PER DIRECTORY. A module-scoped toolchain vets, tests and runs the whole
            # package, so running it once per file in that package would report the same work
            # several times and hide which file was the subject.
            if path.parent in seen_dirs:
                continue
            seen_dirs.add(path.parent)
        if not recipe:
            rows.append(
                {
                    "file": rel(path),
                    "route": route,
                    "verdict": "UNEXERCISED",
                    "detail": f"atlas.yaml/example_runners declares no recipe for {route}",
                }
            )
            continue
        work.append((path, route, recipe["steps"]))

    # Every run owns its temporary output and executes beside its example. Parallelism therefore
    # shortens independent compiler/runtime starts without sharing artifacts. map preserves routed
    # order, so JSON records and human output remain deterministic.
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda item: run_one(item[0], item[2]), work))
    rows.extend(
        {"file": rel(path), "route": route, "verdict": verdict, "detail": detail}
        for (path, route, _), (verdict, detail) in zip(work, results, strict=True)
    )
    rows.sort(key=lambda row: row["file"])

    counts = {v: sum(1 for r in rows if r["verdict"] == v) for v in ("PASS", "FAIL", "SKIP", "UNEXERCISED")}
    if args.json:
        print(json.dumps({"schema": 1, "command": "exrun", "rows": rows, "counts": counts}, indent=2))
        return 1 if counts["FAIL"] or counts["UNEXERCISED"] else 0

    width = max(len(r["file"]) for r in rows)
    for row in rows:
        print(f"{row['verdict']:<12}{row['file'].ljust(width)}  {row['detail']}")
    print(
        f"\n{counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped, "
        f"{counts['UNEXERCISED']} routed with no runner declared, {len(rows)} reported"
        + (f" ({len(seen_dirs)} directory-scoped, so a package counts once)" if seen_dirs else "")
    )
    from contextcost import example_coverage as _coverage

    covered, without = _coverage()
    print(
        f"COVERAGE: {len(covered)} of {len(covered) + len(without)} routes ship a runnable "
        f"example; {len(without)} ship none, so a clean pass above covers {len(covered)} packs "
        f"and says nothing about the rest: {', '.join(without)}"
    )
    print("SCOPE: a PASS proves this example's own assertions held here. Toolchain coverage per pack")
    print("       is `packprobe.py --mode smoke`; an absent toolchain is a fact about the machine.")
    # A ROUTED EXAMPLE NOBODY RUNS IS A FAILURE, NOT A FOOTNOTE: an unexercised config printed its row
    # and the gate still exited 0, so the cloudflare example went unrun with every check green.
    return 1 if counts["FAIL"] or counts["UNEXERCISED"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
