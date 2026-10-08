#!/usr/bin/env python3
"""Regression cases for a bare index install: it fetches its own release atlas, sha256-checked, or refuses.

urlopen is replaced, never reached: each case serves planted bytes, and a missing URL is a network error.
"""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
from pathlib import Path


def _release(version: str, shipped: str | None = None, extra: str | None = None) -> bytes:
    """A release tarball shaped like `git archive --prefix=thea-software-v<version>/`, built in memory."""
    import tarfile

    top = f"thea-software-v{version}/"
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

    version, name = "9.9.9", "thea-v9.9.9.tar.gz"
    url = f"{atlas_cli.RELEASES}/v{version}/{name}"
    calls: list[str] = []

    def served(blob: bytes, digest: str | None = None) -> dict[str, bytes]:
        return {url: blob, url + ".sha256": f"{digest or hashlib.sha256(blob).hexdigest()}  {name}\n".encode()}

    def outcome(files: dict[str, bytes] | None, env: dict[str, str] | None = None) -> str:
        """'ok <dir>' or 'refused <message>', from a fresh cache with urlopen answering only `files`."""

        def urlopen(target, timeout=None):
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
        "the verified release": (served(good), "ok thea/atlas-9.9.9"),
        "a planted bad checksum": (served(good, "0" * 64), "refused thea-v9.9.9.tar.gz: sha256 is not"),
        "no network": (None, "refused cannot download"),
        "a sha256 file naming another file": (
            {url: good, url + ".sha256": b"%s  other.tar.gz\n" % b"a" * 64},
            "refused thea-v9.9.9.tar.gz: sha256 is not",
        ),
        "a sha256 file naming it twice": (
            {url: good, url + ".sha256": served(good)[url + ".sha256"] + f"{'b' * 64}  {name}\n".encode()},
            "refused thea-v9.9.9.tar.gz: sha256 is not",
        ),
        "another version inside the tarball": (
            served(_release(version, shipped="9.9.8")),
            "not one tree of contract 9.9.9",
        ),
        "a path that climbs out": (
            served(_release(version, extra="thea-software-v9.9.9/../../evil")),
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
        mock.patch.dict(os.environ, {"THEA_NO_FETCH": "1"}),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        for var in ("THEA_ROOT", "CODE_DEVELOPMENT_ROOT"):
            os.environ.pop(var, None)
        before = len(calls)
        root, rule = atlas_cli._resolved(["doctor"])
        if len(calls) != before or "THEA_NO_FETCH" not in (rule or ""):
            problems.append(f"THEA_NO_FETCH=1 still fetched or was not named: {rule}")
    return problems


def _lock_problems(atlas_cli, version: str, files: dict[str, bytes], calls: list[str]) -> list[str]:
    """A fetched tree is read-only, and an edited, added or removed file refuses the next run; bytecode lands outside."""
    import stat
    from unittest import mock

    def tampered(how) -> str:
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
        os.environ.pop("THEA_NO_FETCH", None)
        root, _ = atlas_cli._resolved(["doctor"])
        prefix = Path(os.environ["PYTHONPYCACHEPREFIX"] or root)
        if root is None or root in [prefix, *prefix.parents] or atlas_cli.sys.pycache_prefix != str(prefix):
            problems.append(f"bytecode for the fetched tree is written inside it: {prefix}")
    return problems


def run(module) -> None:
    found = _fetch_problems()
    if found:
        raise SystemExit("FAIL release fetch: " + "; ".join(found))
    module.CASES.append(
        (
            "a bare install fetches its own release, sha256-verified; a bad checksum, no network, another "
            "version, a misnamed or doubled digest, a climbing path and THEA_NO_FETCH each refuse; the tree is "
            "read-only, keeps bytecode outside, and an edited, added or removed file refuses the next run",
            "an index install that runs an unverified, different-version or since-edited atlas, or none at all",
        )
    )
    print("  ok    release fetch: the verified release is cached once; every planted defect refuses")
