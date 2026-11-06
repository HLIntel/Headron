"""Exercise example runner verdicts for unconfigured launchers and real failures."""

import base64
import hashlib
import io
import subprocess
import tarfile
import tempfile
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import exrun


def _integrity(blob: bytes) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(blob).digest()).decode()


def _tarball(name: str) -> bytes:
    held = io.BytesIO()
    with tarfile.open(fileobj=held, mode="w:gz") as archive:
        info = tarfile.TarInfo(f"tool-1/{name}")
        info.size = 2
        info.mode = 0o755
        archive.addfile(info, io.BytesIO(b"hi"))
    return held.getvalue()


def _pinned_toolchain_cases(module: ModuleType) -> None:
    tar, bare = _tarball("tool"), b"binary"
    runners = {
        "archive": {"official": {"url": "https://x/a", "integrity": _integrity(tar)}},
        "bare": {"official": {"url": "https://x/b", "integrity": _integrity(bare), "binary": "lint"}},
        "brewed": {"brew": "other"},
    }
    served = {"https://x/a": tar, "https://x/b": bare}
    with tempfile.TemporaryDirectory() as tmp, patch.object(exrun.sys, "platform", "darwin"):
        store, fetched = Path(tmp) / "store", []

        def fetch(url: str) -> bytes:
            fetched.append(url)
            return served[url]

        with patch.object(exrun.platform, "machine", return_value="arm64"), patch.object(exrun, "_fetch", fetch):
            first = exrun.install_official(runners, store)
            again = exrun.install_official(runners, store)
            downloads = len(fetched)
            bare_runs = (Path(first[1]) / "lint").stat().st_mode & 0o111 != 0
            served["https://x/a"] = b"swapped upstream"
            kept = sorted(path.name for path in store.iterdir())
            wrong = Path(tmp) / "wrong"
            try:
                exrun.install_official({"archive": runners["archive"]}, wrong)
                refused = False
            except ValueError:
                refused = True
            left_nothing = not wrong.exists()
        with patch.object(exrun.platform, "machine", return_value="x86_64"):
            elsewhere = exrun.install_official(runners, Path(tmp) / "other")
    cases = (
        (
            "a pinned toolchain is unpacked or marked runnable, then reused with no second download",
            "a reinstall on every run, or a bare release that lands without its execute bit",
            Path(first[0]).name == "tool-1" and bare_runs and first == again and downloads == 2 and len(kept) == 2,
        ),
        (
            "bytes that differ from the digest in atlas.yaml are refused and nothing is left behind",
            "a toolchain installed from whatever the release URL served today",
            refused and left_nothing,
        ),
        (
            "a machine the pins were not built for installs nothing, so its examples skip as absent",
            "a macOS binary installed where it cannot run, read as a failed example",
            elsewhere == [],
        ),
    )
    for name, kills, ok in cases:
        if not ok:
            raise SystemExit(f"FAIL {name}\n  kills: {kills}")
        module.CASES.append((name, kills))
        print(f"  ok    {name}")


def _yaml_runner_cases(module: ModuleType) -> None:
    steps = exrun.atlas()["example_runners"]["yaml"]["steps"]
    with tempfile.TemporaryDirectory() as tmp:
        good, doubled = Path(tmp) / "good.yaml", Path(tmp) / "doubled.yaml"
        good.write_text("a: 1\n", encoding="utf-8")
        doubled.write_text("a: 1\na: 2\n", encoding="utf-8")
        verdicts = exrun.run_one(good, steps)[0], exrun.run_one(doubled, steps)[0]
    name, kills = (
        "the YAML example runner passes a clean file and refuses a duplicate key",
        "a parser that keeps the last key",
    )
    if verdicts != ("PASS", "FAIL"):
        raise SystemExit(f"FAIL {name}: {verdicts}\n  kills: {kills}")
    module.CASES.append((name, kills))
    print(f"  ok    {name}")


def run(module: ModuleType) -> None:
    _pinned_toolchain_cases(module)
    _yaml_runner_cases(module)
    path = module.ROOT / "examples/lean4/bounded.lean"
    for command, error, expected in (
        ("lean", "error: no default toolchain configured. run elan default stable", "SKIP"),
        ("lean", "error: invalid theorem", "FAIL"),
        ("other", "error: no default toolchain configured.", "FAIL"),
    ):
        result = subprocess.CompletedProcess([command], 1, "", error)
        with (
            patch.object(exrun.shutil, "which", return_value="/installed"),
            patch.object(exrun.subprocess, "run", return_value=result),
        ):
            verdict, _ = exrun.run_one(path, [[command]])
        if verdict != expected:
            raise SystemExit(f"example launcher: {command} {error!r} -> {verdict}, expected {expected}")
    module.CASES.append(
        (
            "an unconfigured Lean launcher skips while a compiler failure is refused",
            "a launcher mistaken for a compiler",
        )
    )
