#!/usr/bin/env python3
"""gitobject: every name it computes agrees with real git, in both object formats, on every shape a tree can hold."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from types import ModuleType
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import callshape
import gitobject
import receipt

CLEAN_ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}  # a hook sets these, and they would win
FORMATS = ("sha1", "sha256")


def _git(cwd: Path, *args: str, stdin: bytes = b"") -> str:
    done = subprocess.run(
        ["git", *args], cwd=cwd, input=stdin, capture_output=True, check=True, timeout=60, env=CLEAN_ENV
    )
    return done.stdout.decode().strip()


def _repo(directory: Path, object_format: str) -> Path:
    root = directory / object_format
    root.mkdir()
    _git(root, "init", "-q", f"--object-format={object_format}")
    return root


def _stage(root: Path, name: str, data: bytes) -> str:
    (root / name).write_bytes(data)
    _git(root, "add", "--", name)
    return _git(root, "rev-parse", f":{name}")


def agrees_with_git_case(directory: Path) -> None:
    samples = {
        "empty": b"",
        "text": b"hello\n",
        "nul": b"a\0b\0\n",
        "binary": bytes(range(256)) * 41,
        "crlf": b"one\r\ntwo\r\n",
        "large": b"x" * (3 << 20),  # past one read chunk
    }
    for object_format in FORMATS:
        root = _repo(directory, object_format)
        repo = gitobject.Repo.discover(root)
        if repo.object_format != object_format:
            raise SystemExit(f"FAIL read format {repo.object_format} from a {object_format} repository")
        for name, data in samples.items():
            want = _git(root, "hash-object", "--no-filters", "--stdin", stdin=data)
            (root / name).write_bytes(data)
            if repo.blob_oid(data) != want or repo.path_oid(root / name) != want:
                raise SystemExit(f"FAIL {object_format} {name}: {repo.blob_oid(data)} is not git's {want}")
        os.symlink("no/such/target", root / "link")
        _git(root, "add", "--", "link")
        if repo.path_oid(root / "link") != _git(root, "rev-parse", ":link"):
            raise SystemExit(f"FAIL {object_format} a symlink's blob is its target text")
    print("  ok    bytes, files and symlinks name the same blob git names, in both formats")


def filter_is_named_case(directory: Path) -> None:
    """The documented limit, held true: a file with a text conversion is not its blob, and git says so too."""
    root = _repo(directory, "sha1")
    (root / ".gitattributes").write_text("*.txt text eol=lf\n", encoding="utf-8")
    stored = _stage(root, "a.txt", b"one\r\n")
    unfiltered = gitobject.Repo.discover(root).path_oid(root / "a.txt")
    if stored == unfiltered or unfiltered != _git(root, "hash-object", "--no-filters", "a.txt"):
        raise SystemExit(
            "FAIL path_oid must be the unfiltered name, and differ from the converted blob it did not store"
        )
    print("  ok    a converted file is named unfiltered, the limit the module states")


def index_case(directory: Path) -> None:
    for object_format in FORMATS:
        root = _repo(directory, object_format)
        (root / "dir").mkdir()
        want = {name: _stage(root, name, data) for name, data in {"a": b"1\n", "dir/nested name": b"2\n"}.items()}
        long_name = "n/" * 2100 + "n"  # past the 12-bit length field; only the index holds it, no filesystem would
        want[long_name] = want["a"]
        _git(root, "update-index", "--add", "--cacheinfo", f"100644,{want['a']},{long_name}")
        repo = gitobject.Repo.discover(root)
        if {e.path: e.oid for e in repo.entries()} != want:
            raise SystemExit(f"FAIL {object_format} index read {repo.entries()} want {want}")
        _git(root, "update-index", "--index-version", "3")
        (root / "later").write_bytes(b"4\n")
        _git(root, "add", "--intent-to-add", "--", "later")  # the extended flag: a v3 entry, two bytes longer
        seen = {e.path for e in repo.entries()}
        if seen != {*want, "later"}:
            raise SystemExit(f"FAIL {object_format} extended-flag entry misread: {sorted(seen)[:4]}")
    print("  ok    the index reads the same names git stages, past long names and extended flags")


def refuses_unknown_index_case(directory: Path) -> None:
    root = _repo(directory, "sha1")
    _stage(root, "a", b"1\n")
    repo = gitobject.Repo.discover(root)
    good = repo.index.read_bytes()
    sealed = b"nope" + good[4:-20]
    sealed += hashlib.sha1(
        sealed, usedforsecurity=False
    ).digest()  # whole by its checksum, so only the magic refuses it
    plants = {"checksum": good[:20] + bytes([good[20] ^ 1]) + good[21:], "not an index": sealed}
    for label, raw in plants.items():
        repo.index.write_bytes(raw)
        try:
            repo.entries()
        except gitobject.Unsupported:
            continue
        raise SystemExit(f"FAIL an index with a bad {label} was read as though it were whole")
    repo.index.write_bytes(good)
    _git(root, "update-index", "--index-version", "4")
    try:
        repo.entries()
    except gitobject.Unsupported:
        pass
    else:
        raise SystemExit("FAIL a v4 index was parsed as v2: compressed paths would be read as garbage")
    _git(root, "update-index", "--index-version", "2")
    _git(root, "update-index", "--split-index")
    try:
        repo.entries()
    except gitobject.Unsupported:
        pass
    else:
        raise SystemExit("FAIL a split index keeps its entries elsewhere, and was read as a short list")
    _git(root, "update-index", "--no-split-index")
    _git(
        root,
        "-c",
        "index.skipHash=true",
        "update-index",
        "--add",
        "--cacheinfo",
        f"100644,{_git(root, 'rev-parse', ':a')},b",
    )
    if {e.path for e in repo.entries()} != {"a", "b"}:
        raise SystemExit("FAIL index.skipHash writes zeros on purpose, and that index is whole")
    print("  ok    a damaged index or a shape it cannot read raises Unsupported, never a short list")


def stage_case(directory: Path) -> None:
    root = _repo(directory, "sha1")
    oid = _stage(root, "a", b"1\n")
    _git(
        root, "update-index", "--index-info", stdin=f"0 {'0' * 40}\ta\n100644 {oid} 2\ta\n100644 {oid} 3\ta\n".encode()
    )
    if [(e.path, e.stage) for e in gitobject.Repo.discover(root).entries()] != [("a", 2), ("a", 3)]:
        raise SystemExit("FAIL a conflict's stages were not read")
    print("  ok    a conflict's stages are read")


def verify_staged_case(directory: Path) -> None:
    for object_format in FORMATS:
        root = _repo(directory, object_format)
        keep, damage = _stage(root, "keep", b"keep\n"), _stage(root, "damage", b"damage\n")
        repo = gitobject.Repo.discover(root)
        if repo.verify_staged() != gitobject.Staged(2, [], 0):
            raise SystemExit(f"FAIL {object_format} two whole loose blobs: {repo.verify_staged()}")
        stored = repo.objects / damage[:2] / damage[2:]
        original = stored.read_bytes()
        stored.chmod(0o600)
        wrong = b"blob 7\0tamper\n"
        for label, raw in {
            "other bytes": zlib.compress(wrong),
            "not zlib": b"garbage",
            "truncated": original[: len(original) // 2],
            "no checksum": zlib.compress(b"blob 7\0damage\n")[
                :-4
            ],  # every byte inflates: only the stream's end says so
            "other kind": zlib.compress(b"tree 7\0damage\n"),
            "wrong length": zlib.compress(b"blob 9\0damage\n"),
        }.items():
            stored.write_bytes(raw)
            if repo.verify_staged() != gitobject.Staged(2, ["damage"], 0):
                raise SystemExit(f"FAIL {object_format} {label}: {repo.verify_staged()}")
            if (
                subprocess.run(
                    [sys.executable, gitobject.__file__, "verify-staged"],
                    cwd=root,
                    capture_output=True,
                    check=False,
                    timeout=60,
                    env=CLEAN_ENV,
                ).returncode
                != 1
            ):
                raise SystemExit(f"FAIL {object_format} {label}: the command did not exit 1")
        stored.unlink()
        if repo.verify_staged() != gitobject.Staged(1, [], 1):
            raise SystemExit(
                f"FAIL {object_format} an object not loose must count as unchecked: {repo.verify_staged()}"
            )
        (repo.objects / keep[:2] / keep[2:]).unlink()
    print("  ok    damage in a stored blob is named; an object not read counts as unchecked, never as checked")


def consistent_lie_case(directory: Path) -> None:
    """A stored object whose name is its own hash can still not be the blob it claims: its header says so."""
    root = _repo(directory, "sha1")
    repo = gitobject.Repo.discover(root)
    for label, body in {
        "a tree": b"tree 7\0damage\n",
        "a wrong length": b"blob 9\0damage\n",
        "no header": b"damage\n",
    }.items():
        oid = hashlib.sha1(body, usedforsecurity=False).hexdigest()
        (repo.objects / oid[:2]).mkdir(exist_ok=True)
        (repo.objects / oid[:2] / oid[2:]).write_bytes(zlib.compress(body))
        if repo.loose_matches(oid) is not False:
            raise SystemExit(f"FAIL {label} whose name matches its bytes passed as a blob")
    print("  ok    a self-consistent object that is not a well-formed blob is refused")


def command_case(directory: Path) -> None:
    command = [sys.executable, gitobject.__file__]
    root = _repo(directory, "sha1")
    _stage(root, "a", b"1\n")
    for args, cwd, code in (
        (["verify-staged"], root, 0),
        (["verify-staged"], directory, 2),
        ([], root, 2),
        (["other"], root, 2),
    ):
        done = subprocess.run(
            [*command, *args], cwd=cwd, capture_output=True, text=True, check=False, timeout=60, env=CLEAN_ENV
        )
        if done.returncode != code:
            raise SystemExit(f"FAIL {args} in {cwd.name}: exit {done.returncode}, want {code}: {done.stderr[:120]}")
    print("  ok    the command says pass, damage and cannot-judge with three different exits")


def packed_and_gitlink_case(directory: Path) -> None:
    root = _repo(directory, "sha1")
    _stage(root, "a", b"1\n")
    tree = _git(root, "write-tree")
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    with mock.patch.dict(CLEAN_ENV, env):
        commit = _git(root, "commit-tree", tree, "-m", "x")
    _git(root, "update-ref", "refs/heads/main", commit)
    _git(root, "gc", "-q", "--prune=now")
    repo = gitobject.Repo.discover(root)
    if repo.verify_staged() != gitobject.Staged(0, [], 1):
        raise SystemExit(f"FAIL a packed blob is not checked and must say so: {repo.verify_staged()}")
    _git(root, "update-index", "--add", "--cacheinfo", f"160000,{commit},sub")
    if repo.verify_staged() != gitobject.Staged(0, [], 1):
        raise SystemExit(f"FAIL a gitlink names a commit elsewhere, not a blob here: {repo.verify_staged()}")
    print("  ok    a packed blob is counted unchecked and a gitlink is not a blob")


def discovery_case(directory: Path) -> None:
    root = _repo(directory, "sha256")
    _stage(root, "a", b"1\n")
    _git(root, "update-ref", "HEAD", _commit(root))
    linked = directory / "linked"
    _git(root, "worktree", "add", "-q", "--detach", str(linked))
    nested = linked / "deep"
    nested.mkdir()
    repo = gitobject.Repo.discover(nested)
    if repo.object_format != "sha256" or repo.objects != gitobject.Repo.discover(root).objects:
        raise SystemExit(f"FAIL a linked worktree must read the main repository's config and objects: {repo.objects}")
    other = directory / "other-index"
    environment = {"GIT_INDEX_FILE": str(other), "GIT_OBJECT_DIRECTORY": str(directory / "quarantine")}
    with mock.patch.dict(os.environ, environment):
        moved = gitobject.Repo.discover(root)
    if moved.index != other.resolve() or moved.objects != (directory / "quarantine").resolve():
        raise SystemExit("FAIL a hook's GIT_INDEX_FILE and quarantine directory must win over the default paths")
    pointed = {"GIT_DIR": str(linked / ".git"), "GIT_COMMON_DIR": str(root / ".git")}
    with mock.patch.dict(os.environ, pointed):
        direct = gitobject.Repo.discover(directory)
    if direct.common_dir != (root / ".git").resolve() or direct.object_format != "sha256":
        raise SystemExit("FAIL a hook's GIT_DIR and GIT_COMMON_DIR must win over the directory it runs in")
    other_section = _repo(directory, "sha1")
    (other_section / ".git" / "config").write_text("[other]\n\tobjectformat = sha256\n", encoding="utf-8")
    if gitobject.Repo.discover(other_section).object_format != "sha1":
        raise SystemExit("FAIL only [extensions] names the object format")
    (root / ".git" / "config").write_text("[extensions]\n\tobjectformat = sha999\n", encoding="utf-8")
    try:
        gitobject.Repo.discover(root)
    except gitobject.Unsupported:
        print("  ok    worktrees, a hook's environment and an unknown format are each read as git reads them")
    else:
        raise SystemExit("FAIL an unknown object format was read as SHA-1")


def _commit(root: Path) -> str:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    with mock.patch.dict(CLEAN_ENV, env):
        return _git(root, "commit-tree", _git(root, "write-tree"), "-m", "x")


def object_id_shape_case(_directory: Path) -> None:
    good = ("a" * 40, "0" * 64, "f" * 64)
    bad = ("a" * 39, "a" * 41, "a" * 63, "a" * 65, "A" * 40, "g" * 40, "", None, 40, "a" * 40 + "\n")
    if not all(map(gitobject.is_oid, good)) or any(map(gitobject.is_oid, bad)):
        raise SystemExit("FAIL is_oid must take exactly 40 or 64 lower-case hex")
    # receipt.py runs alone, so it spells this shape itself: the two must give one answer. Null means no base there.
    whole = receipt.build([], base_commit=good[0], policy_digest=None, input_digest="c" * 64)
    for value in filter(lambda given: given is not None, (*good, *bad)):
        refused = "base_commit" in (receipt._shape_error({**whole, "base_commit": value}) or "")
        if refused == gitobject.is_oid(value):
            raise SystemExit(f"FAIL receipt and is_oid disagree on the base commit {value!r}")
    if gitobject.absent("sha256") != "0" * 64 or gitobject.absent("sha1") != "0" * 40:
        raise SystemExit("FAIL absent must be as long as the format's hash")
    print("  ok    an object id is 40 or 64 hex, and an absent one is zeros of its format's length")


def prepush_formats_case(directory: Path) -> None:
    """The hook is shell, so its zero check is planted through real runs in both formats."""
    hook = callshape.ROOT / ".githooks" / "pre-push"
    for object_format in FORMATS:
        root = _repo(directory, object_format)
        _stage(root, "a", b"1\n")
        head, zero = _commit(root), gitobject.absent(object_format)
        for label, line, code, text in (
            ("new lane", f"refs/heads/x {head} refs/heads/x {zero}\n", 1, "bare push"),
            ("delete", f"(delete) {zero} refs/heads/x {head}\n", 0, ""),
        ):
            done = subprocess.run(
                ["sh", str(hook)],
                input=line,
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
                env=CLEAN_ENV,
            )
            if done.returncode != code or text not in done.stderr:
                raise SystemExit(f"FAIL pre-push {object_format} {label}: exit {done.returncode}, {done.stderr[:120]}")
    print("  ok    pre-push reads an absent object in either format")


def guard_case(directory: Path) -> None:
    """object_ids_are_format_agnostic, on planted files: every SHA-1-only shape bites in any scanned place."""
    # Built here so this file's own text plants nothing for a tree-wide scan.
    forty = "[0-9a-f]{" + "40}"
    planted = {
        "scripts/zeros.py": ("ZERO = " + chr(34) + "0" * 40 + chr(34), True),
        "scripts/spelled.py": ("ZERO = '0'" + " * 40", True),
        "scripts/spaced.py": ('ZERO = "0"' + "*40", True),
        "scripts/pattern.py": ("re.fullmatch(r'" + forty + "', sha)", True),
        ".githooks/pre-push": ("zero=" + "0" * 40, True),
        "tools/receipt.schema.json": ('{"pattern": "^' + forty + '$"}', True),
        "fuzz/seed.py": ("ZERO = " + chr(34) + "0" * 40 + chr(34), True),
        "scripts/both.py": ("r'" + forty + "([0-9a-f]{24})?'", False),
        "scripts/both_group.py": ("r'" + forty + "(?:[0-9a-f]{24})?'", False),
        "scripts/owner.py": ('"0" * OID_HEX[fmt]', False),
        "scripts/clip.py": ("text[:" + "40]", False),
        "scripts/planted_test.py": ("ZERO = '0'" + " * 40", False),
        "docs/note.py": ("ZERO = '0'" + " * 40", False),
    }
    for name, (line, _) in planted.items():
        (directory / name).parent.mkdir(exist_ok=True)
        (directory / name).write_text(line + "\n", encoding="utf-8")
    (directory / ".githooks" / "subdir.py").mkdir()  # a directory a glob returns is not a file to read
    with mock.patch.object(callshape, "ROOT", directory):
        errors = callshape.oid_literal_errors()
    hit = {error.split(":")[0] for error in errors}
    want = {name for name, (_, bites) in planted.items() if bites}
    if hit != want:
        raise SystemExit(f"FAIL the guard missed {sorted(want - hit)} and wrongly refused {sorted(hit - want)}")
    if not all(":1 " in error for error in errors):
        raise SystemExit(f"FAIL a finding must name its line: {errors[:2]}")
    print("  ok    a forty-only id is refused in Python, shell and JSON; the two-format shape and the tests are not")


def run(module: ModuleType | None) -> None:
    for case in (
        agrees_with_git_case,
        filter_is_named_case,
        index_case,
        refuses_unknown_index_case,
        verify_staged_case,
        consistent_lie_case,
        stage_case,
        command_case,
        packed_and_gitlink_case,
        discovery_case,
        object_id_shape_case,
        prepush_formats_case,
        guard_case,
    ):
        with (
            tempfile.TemporaryDirectory(prefix="gitobject-") as directory,
            mock.patch.dict(os.environ, CLEAN_ENV, clear=True),
        ):
            case(Path(directory).resolve())
    if module is None:
        return
    # The enforcer's edge: the invariant itself refuses a real scanned file, not only callshape on a planted tree.
    with module.mutated("scripts/gitobject.py", lambda source: source + "ZERO = '0'" + " * 40\n"):
        module.case(
            "a forty-character object id in a scanned file FAILS",
            "an id spelled for SHA-1 only, which refused every new lane in a SHA-256 repository for the wrong reason",
            True,
            "assumes a forty-character object id",
            by="inv:object_ids_are_format_agnostic",
        )


if __name__ == "__main__":
    run(None)
