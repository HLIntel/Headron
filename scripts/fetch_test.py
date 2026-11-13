#!/usr/bin/env python3
"""Regression cases for a bare index install: it fetches its own release atlas, sha256-checked, or refuses.

urlopen is replaced, never reached: each case serves planted bytes, and a missing URL is a network error.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType


def _release(version: str, shipped: str | None = None, extra: str | None = None) -> bytes:
    """A release tarball shaped like `git archive --prefix=headron-software-v<version>/`, built in memory."""
    import tarfile

    top = f"headron-software-v{version}/"
    files = {top + "VERSION": f"{shipped or version}\n", top + "atlas.yaml": "version: planted\n"}
    if extra:
        files[extra] = "planted\n"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, text in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(text.encode())
            tar.addfile(info, io.BytesIO(text.encode()))
    return buf.getvalue()


def _fetch_problems() -> list[str]:
    """A bare index install fetches exactly its own release, verified; every other shape is refused."""
    import hashlib
    from unittest import mock

    import atlas_cli

    version, name = "9.9.9", "headron-v9.9.9.tar.gz"
    url = f"{atlas_cli.RELEASES}/v{version}/{name}"
    calls: list[str] = []

    def served(blob: bytes, digest: str | None = None) -> dict[str, bytes]:
        return {url: blob, url + ".sha256": f"{digest or hashlib.sha256(blob).hexdigest()}  {name}\n".encode()}

    def outcome(files: dict[str, bytes] | None, env: dict[str, str] | None = None) -> str:
        """'ok <dir>' or 'refused <message>', from a fresh cache with urlopen answering only `files`."""

        def urlopen(target: str, timeout: float | None = None):
            calls.append(target)
            if files is None or target not in files:
                raise OSError("network is unreachable (planted)")
            return contextlib.nullcontext(io.BytesIO(files[target]))

        with (
            tempfile.TemporaryDirectory() as cache,
            mock.patch.dict(os.environ, {"XDG_CACHE_HOME": cache, **(env or {})}),
            mock.patch("urllib" + ".request.urlopen", urlopen),  # assembled: this harness imports no network
        ):
            try:
                got = atlas_cli.fetch_atlas(version)
            except atlas_cli.FetchError as exc:
                left = list(Path(cache).rglob("atlas.yaml"))
                return f"refused {exc}" + (f" BUT LEFT {left}" if left else "")
            again = len(calls)
            atlas_cli.fetch_atlas(version)  # the second call must be served by the marked cache
            cached = "" if len(calls) == again else " BUT DOWNLOADED TWICE"
            return f"ok {got.relative_to(cache)}{cached}" if (got / atlas_cli.MARKER).is_file() else f"UNMARKED {got}"

    good = _release(version)
    problems = []
    planted = {  # case -> (served files, what the verdict must contain)
        "the verified release": (served(good), "ok headron/atlas-9.9.9"),
        "a planted bad checksum": (served(good, "0" * 64), "refused headron-v9.9.9.tar.gz: sha256 is not"),
        "no network": (None, "refused cannot download"),
        "a sha256 file naming another file": (
            {url: good, url + ".sha256": b"%s  other.tar.gz\n" % b"a" * 64},
            "refused headron-v9.9.9.tar.gz: sha256 is not",
        ),
        "a sha256 file naming it twice": (
            {url: good, url + ".sha256": served(good)[url + ".sha256"] + f"{'b' * 64}  {name}\n".encode()},
            "refused headron-v9.9.9.tar.gz: sha256 is not",
        ),
        "another version inside the tarball": (
            served(_release(version, shipped="9.9.8")),
            "not one tree of contract 9.9.9",
        ),
        "a path that climbs out": (
            served(_release(version, extra="headron-software-v9.9.9/../../evil")),
            "could not be unpacked",
        ),
    }
    for label, (files, want) in planted.items():
        said = outcome(files)
        if want not in said or "BUT" in said:
            problems.append(f"{label}: {said[:200]}")
    problems += _lock_problems(atlas_cli, version, served(good), calls)
    with (
        tempfile.TemporaryDirectory() as away,
        contextlib.chdir(away),
        mock.patch.object(atlas_cli, "__file__", str(Path(away, "lib", "site", "atlas_cli.py"))),
        mock.patch.dict(os.environ, {"HEADRON_NO_FETCH": "1"}),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        for var in ("HEADRON_ROOT", "CODE_DEVELOPMENT_ROOT"):
            os.environ.pop(var, None)
        before = len(calls)
        root, rule = atlas_cli._resolved(["doctor"])
        if len(calls) != before or "HEADRON_NO_FETCH" not in (rule or ""):
            problems.append(f"HEADRON_NO_FETCH=1 still fetched or was not named: {rule}")
    return problems


def _lock_problems(atlas_cli: ModuleType, version: str, files: dict[str, bytes], calls: list[str]) -> list[str]:
    """A fetched tree is read-only, and an edited, added or removed file refuses the next run; bytecode lands outside."""
    import stat
    from unittest import mock

    def tampered(how: Callable[[Path], object]) -> str:
        with (
            tempfile.TemporaryDirectory() as cache,
            mock.patch.dict(os.environ, {"XDG_CACHE_HOME": cache}),
            mock.patch("urllib" + ".request.urlopen", lambda u, timeout=None: io.BytesIO(files[u])),
        ):
            tree = atlas_cli.fetch_atlas(version)
            how(tree)
            try:
                atlas_cli.fetch_atlas(version)
            except atlas_cli.FetchError as exc:
                return str(exc)
            return "served"

    def edit(tree: Path) -> None:
        (tree / "atlas.yaml").chmod(0o644)
        (tree / "atlas.yaml").write_text("version: edited\n")

    problems = []
    cases = {
        "an untouched tree": (lambda tree: None, "served"),
        "an edited file": (edit, "atlas.yaml changed after download"),
        "an added file": (lambda t: (t / "planted.py").write_text("x\n"), "planted.py changed after download"),
        "a removed file": (lambda t: (t / "VERSION").unlink(), "VERSION changed after download"),
        "a writable file": (
            lambda t: problems.extend(
                f"{p.name} is writable" for p in t.rglob("*") if p.is_file() and p.stat().st_mode & stat.S_IWUSR
            ),
            "served",
        ),
    }
    for label, (how, want) in cases.items():
        said = tampered(how)
        if want not in said:
            problems.append(f"{label}: {said[:200]}")
    with (
        tempfile.TemporaryDirectory() as cache,
        mock.patch.dict(os.environ, {"XDG_CACHE_HOME": cache, "PYTHONPYCACHEPREFIX": ""}),
        mock.patch.object(atlas_cli, "resolve_root", lambda argv, cwd: (Path(cache, "none"), atlas_cli.INSTALLED_FROM)),
        mock.patch("importlib.metadata.version", lambda name: version),
        mock.patch("urllib" + ".request.urlopen", lambda u, timeout=None: io.BytesIO(files[u])),
        mock.patch.object(atlas_cli.sys, "pycache_prefix", None),
    ):
        os.environ.pop("HEADRON_NO_FETCH", None)
        root, _ = atlas_cli._resolved(["doctor"])
        prefix = Path(os.environ["PYTHONPYCACHEPREFIX"] or root)
        if root is None or root in [prefix, *prefix.parents] or atlas_cli.sys.pycache_prefix != str(prefix):
            problems.append(f"bytecode for the fetched tree is written inside it: {prefix}")
    return problems


def _handshake_problems() -> list[str]:
    """`headron-mcp` with a HEADRON_ROOT holding no atlas: exit 2 AND one JSON-RPC error reply to initialize."""
    with tempfile.TemporaryDirectory() as empty:
        env = {**os.environ, "HEADRON_ROOT": empty, "HEADRON_NO_FETCH": "1"}
        ask = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "initialize", "params": {}}) + "\n"
        code = "import sys; sys.path.insert(0, 'scripts'); import atlas_cli; sys.exit(atlas_cli.mcp_main())"
        root = Path(__file__).resolve().parents[1]
        run = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            env=env,
            input=ask,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        try:
            reply = json.loads(run.stdout)
        except ValueError:
            return [f"no JSON-RPC reply to initialize: rc={run.returncode} stdout={run.stdout[:160]!r}"]
        message, problems = str((reply.get("error") or {}).get("message", "")), []
        if run.returncode != 2 or reply.get("id") != 7 or "result" in reply:
            problems.append(f"want rc=2 and an error for id 7: rc={run.returncode} reply={reply!r}"[:240])
        if str(Path(empty).resolve()) not in message or "HEADRON_ROOT" not in message:
            problems.append(f"the error does not name the root and the fix: {message[:200]!r}")
        if "no atlas with scripts/headron_mcp.py" not in run.stderr:
            problems.append("the refusal no longer reaches stderr")
        return problems


def _client_pin_problems() -> list[str]:
    """`headron-mcp` started at `/` reads the pin in HEADRON_CLIENT_DIR's project, never the launch directory's (3.63.0)."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp, "project")
        (project / "elsewhere").mkdir(parents=True)  # a pinned root with no atlas: refused BY NAME if the pin is read
        (project / ".atlas.yaml").write_text("atlas:\n  root: elsewhere\n", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k not in ("HEADRON_ROOT", "CODE_DEVELOPMENT_ROOT")}
        env |= {"HEADRON_CLIENT_DIR": str(project), "HEADRON_NO_FETCH": "1"}
        scripts = str(Path(__file__).resolve().parent)
        code = f"import sys; sys.path.insert(0, {scripts!r}); import atlas_cli; sys.exit(atlas_cli.mcp_main())"
        ask = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n"
        run = subprocess.run(
            [sys.executable, "-c", code],
            cwd="/",
            env=env,
            input=ask,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    if run.returncode != 2 or "root declared in .atlas.yaml" not in run.stdout:
        return [f"started at / it skipped the project's pin: rc={run.returncode} stdout={run.stdout[-200:]!r}"]
    return []


def _pinned_root_problems() -> list[str]:
    """A `.atlas.yaml` root runs only as the top of its own git checkout, at its `ref` when one is pinned (3.64.0)."""
    from unittest import mock

    import atlas_cli

    def git(where: Path, *args: str) -> str:
        cmd = ["git", "-C", str(where), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        cmd += ["-c", "commit.gpgsign=false", *args]
        return subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60).stdout.strip()

    def verdict(project: Path, pin: str, env: dict[str, str]) -> str:
        (project / ".atlas.yaml").write_text(f"atlas:\n{pin}", encoding="utf-8")
        with mock.patch.dict(os.environ, env):
            try:
                return "ran " + atlas_cli.resolve_root([], project)[0].name
            except atlas_cli.ConfigError as exc:
                return f"refused {exc}"

    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        project, atlas = Path(tmp, "project"), Path(tmp, "atlas")
        for repo in (project, atlas):
            (repo / "scripts").mkdir(parents=True)
            git(repo, "init", "-q")
            git(repo, "commit", "-q", "--no-verify", "--allow-empty", "-m", "first")
        old = git(atlas, "rev-parse", "HEAD")
        git(atlas, "commit", "-q", "--no-verify", "--allow-empty", "-m", "second")
        (project / "vendor" / "headron").mkdir(parents=True)
        own, copied = "the top of its own git checkout", "  root: vendor/headron\n"
        cases = {  # label -> (pin, verdict must contain)
            "a tree copied into the project": (copied, own),
            "a directory outside any checkout": ("  root: ../nowhere\n", own),
            "its own checkout at another ref": (f"  root: ../atlas\n  ref: {old[:7]}\n", "at its pinned ref"),
            "a ref that names nothing": ("  root: ../atlas\n  ref: v0.0.0-none\n", "at its pinned ref"),
            "its own checkout at its ref": (
                f"  root: ../atlas\n  ref: {git(atlas, 'rev-parse', 'HEAD')}\n",
                "ran atlas",
            ),
            "its own checkout, no ref": ("  root: ../atlas\n", "ran atlas"),
        }
        Path(tmp, "nowhere").mkdir()
        bare = {k: v for k, v in os.environ.items() if k not in ("HEADRON_ROOT", "CODE_DEVELOPMENT_ROOT")}
        with mock.patch.dict(os.environ, bare, clear=True):
            for hook in ({}, {"GIT_DIR": str(project / ".git"), "GIT_WORK_TREE": str(project)}):
                for label, (pin, want) in cases.items():
                    said = verdict(project, pin, hook)
                    if want not in said:
                        problems.append(f"{label}{' under a hook GIT_DIR' if hook else ''}: {said[:200]}")
    return problems


def run(module: ModuleType) -> None:
    found = _fetch_problems()
    if found:
        raise SystemExit("FAIL release fetch: " + "; ".join(found))
    module.CASES.append(
        (
            "a bare install fetches its own release, sha256-verified; a bad checksum, no network, another "
            "version, a misnamed or doubled digest, a climbing path and HEADRON_NO_FETCH each refuse; the tree is "
            "read-only, keeps bytecode outside, and an edited, added or removed file refuses the next run",
            "an index install that runs an unverified, different-version or since-edited atlas, or none at all",
        )
    )
    print("  ok    release fetch: the verified release is cached once; every planted defect refuses")
    if found := _handshake_problems():
        raise SystemExit("FAIL headron-mcp on a bad root does not answer initialize: " + "; ".join(found))
    module.CASES.append(
        (
            "headron-mcp on a root it cannot serve answers initialize with a JSON-RPC error naming the root",
            "a server that prints its refusal on stderr and exits, so the client shows only 'Connection closed'",
        )
    )
    print("  ok    headron-mcp on a bad root answers initialize with an error naming the root and the fix")
    if found := _client_pin_problems():
        raise SystemExit("FAIL headron-mcp resolves its atlas from the launch directory: " + "; ".join(found))
    module.CASES.append(
        (
            "headron-mcp started outside the project reads the pin in HEADRON_CLIENT_DIR's .atlas.yaml",
            "a server Cursor starts at / that skips the project's pin and silently serves the installed atlas",
        )
    )
    print("  ok    headron-mcp reads the client project's pin wherever it is started")
    if found := _pinned_root_problems():
        raise SystemExit("FAIL a pinned atlas root runs without being its own checkout at its ref: " + "; ".join(found))
    module.CASES.append(
        (
            "an .atlas.yaml root runs only as the top of its own git checkout, at its pinned ref, even under a "
            "hook's GIT_DIR; a copied tree, a non-checkout, another ref and a ref naming nothing each refuse",
            "a cloned project whose .atlas.yaml points at a tree it ships, so the approved MCP entry runs its code",
        )
    )
    print("  ok    a pinned atlas root runs only as its own checkout at its pinned ref")
