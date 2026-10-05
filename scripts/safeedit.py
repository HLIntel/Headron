#!/usr/bin/env python3
"""Edits that cannot fail silently: an anchor that must match once, and a write that is read back.

WHY (2.27.0). Three records were lost in one session with zero errors. A test's restore erased a
concurrent edit; the next insert was anchored on the erased record, so `str.replace` did nothing and
the one after that lost its anchor too. Then a key-set check caught an edit that dropped a key line
and re-parented fourteen children under the new key while the file still parsed. Each primitive
here refuses one of those shapes, and every scripted edit to this tree goes through them.

WHY IT DOES NOT SHIP. Nothing a consumer runs edits this repository's files; the harness that does
is development-only, and a primitive with no shipped caller would be weight in every install.
"""
from __future__ import annotations

from pathlib import Path

from atlascore import portable_yaml, strict_yaml


def replace_once(text: str, old: str, new: str, where: str) -> str:
    """`str.replace` that REFUSES unless `old` occurs exactly once.

    A plain replace with no match returns its input unchanged and says nothing. MEASURED at 2.27.0,
    and it COMPOUNDED: three failure-mode entries were each anchored on the entry written just
    before it; the first was erased by a concurrent restore, so the second's anchor was gone and
    its insert did nothing, which removed the third's anchor in turn. Three records lost, zero
    errors. Twice-matching is refused too — an edit that lands in the first of two places is a
    guess about which one was meant.
    """
    found = text.count(old)
    if found != 1:
        raise ValueError(f"{where}: the anchor occurs {found} times, not once — REFUSING an edit "
                         f"that would {'do nothing' if not found else 'guess which match was meant'}: "
                         f"{old[:70]!r}")
    return text.replace(old, new, 1)

def suite_holds_worktree() -> bool:
    """Is ANOTHER process's mutating suite planting defects in this worktree right now?

    WHY (3.9.0). An audit agent told to read only ran atlas_test, which plants defects in tracked files
    and restores them, while this session was editing the same files. The suite's own lock stopped a
    second suite, and nothing stopped an editor: an edit landing inside a plant window is erased by the
    restore, or restores a planted defect. The lock is the one the suite holds; its own process may write.
    """
    import fcntl  # noqa: PLC0415
    import os  # noqa: PLC0415
    import subprocess  # noqa: PLC0415
    where = subprocess.run(["git", "rev-parse", "--git-path", "atlas-test.lock"], capture_output=True,  # noqa: S607
                           text=True, check=False, timeout=600, cwd=Path(__file__).resolve().parent).stdout.strip()
    lock = Path(where) if Path(where).is_absolute() else Path(__file__).resolve().parent / where
    if not where or not lock.exists() or os.environ.get("THEA_SUITE_PID") == str(os.getpid()):
        return False
    with open(lock) as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle, fcntl.LOCK_UN)
    return False


def _git_path(name: str) -> Path:
    import subprocess  # noqa: PLC0415
    here = Path(__file__).resolve().parent
    where = subprocess.run(["git", "rev-parse", "--git-path", name], capture_output=True, text=True,  # noqa: S607
                           check=False, timeout=600, cwd=here).stdout.strip()
    return Path(where) if Path(where).is_absolute() else here / where


def plant_journal() -> Path:
    """Where a planted suite records each file BEFORE it plants a defect (3.13.0).

    WHY. A reviewer's timeout killed atlas_test mid-case; the restore lives in a `finally` a killed
    process never reaches, so the tree kept `runtime_dependencies: 4`, and the next verify reported the
    plant as the repository's own drift. The journal outlives the process: backup and planted bytes per
    file, deleted after a clean restore, so a leftover is detectable and reversible."""
    return _git_path("atlas-test-plants")


def plant_leftovers(root: Path | None = None) -> list[Path]:
    """Journal entries no running suite owns — plants a killed run left in the tree."""
    import os  # noqa: PLC0415
    journal = plant_journal()
    if not journal.is_dir() or os.environ.get("THEA_SUITE_PID") == str(os.getpid()) or suite_holds_worktree():
        return []
    # ONLY A FILE THAT STILL DIFFERS FROM ITS PRE-PLANT COPY: an entry whose file was restored is stale
    # bookkeeping, not a defect in the tree, and failing on it would fail a correct tree.
    root = root or Path(__file__).resolve().parent.parent

    def still_planted(backup: Path) -> bool:
        target = root / backup.name[: -len(".backup")].replace("%2F", "/")
        return not target.exists() or target.read_bytes() != backup.read_bytes()
    return sorted(b for b in journal.glob("*.backup") if still_planted(b))


def restore_leftovers(root: Path) -> list[str]:
    """Put back every file a killed suite left planted — only where it still holds the planted bytes."""
    report = []
    journal = plant_journal()
    for stale in (journal.glob("*.backup") if journal.is_dir() else []):
        if stale not in plant_leftovers(root):
            stale.unlink()
            stale.with_suffix(".planted").unlink(missing_ok=True)
    for backup in plant_leftovers(root):
        rel = backup.name[: -len(".backup")].replace("%2F", "/")
        planted, target = backup.with_suffix(".planted"), root / rel
        if target.exists() and planted.exists() and target.read_bytes() != planted.read_bytes():
            report.append(f"{rel}: changed since the plant — left alone; the pre-plant copy is {backup}")
            continue
        target.write_bytes(backup.read_bytes())
        backup.unlink()
        planted.unlink(missing_ok=True)
        report.append(f"{rel}: restored")
    return report


def write_verified(path: Path, text: str) -> None:
    """Write, then READ IT BACK. A write that did not land is the quietest failure there is.
    REFUSED while another process's mutating suite holds the worktree: its restore would erase this."""
    if suite_holds_worktree():
        raise OSError(f"{path}: a mutating suite (atlas_test) holds this worktree — REFUSING an edit its "
                      "restore would erase; wait for it, or run audits with THEA_READ_ONLY=1")
    path.write_text(text, encoding="utf-8")
    if path.read_text(encoding="utf-8") != text:
        raise OSError(f"{path}: the bytes read back differ from the bytes written — another "
                      "writer, a full disk or a filesystem that lied; the edit did NOT land")

def write_yaml_verified(path: Path, text: str, added: set[str] = frozenset(),
                        removed: set[str] = frozenset()) -> None:
    """Write YAML, then prove the top-level key set moved EXACTLY as intended — no more.

    Checking only that a new key exists is too weak. MEASURED at 2.27.0: an insert anchored on
    `language_selection:` dropped that key line, its fourteen children were silently re-parented
    under the new key, the file still parsed, and the new-key assertion passed. The contract caught
    it one layer later. The whole key set is the identity; one key is a rendering of it.
    """
    before = set(strict_yaml(path.read_text(encoding="utf-8"), str(path)) or {})
    after = set(strict_yaml(text, str(path)) or {})
    want = (before | set(added)) - set(removed)
    if after != want:
        raise ValueError(f"{path}: top-level keys moved beyond intent — unexpectedly gained "
                         f"{sorted(after - want)}, lost {sorted(want - after)}; nothing written")
    write_verified(path, text)


def yaml_value(text: str) -> str:
    """A YAML value that reads back as exactly `text` — generated, never hand-quoted.

    WHY (3.3.0). Hand-quoting failed three ways in one session: a colon ended a plain value, an
    apostrophe closed a single-quoted one, and an unquoted comma split a flow value, silently
    truncating six declarations. The emitter knows YAML's rules; the round trip below proves it.
    """
    import yaml

    # SAFE UNDER BOTH PARSERS (3.50.0). strict_yaml uses libyaml when it is installed and pure Python when
    # not, and the two disagree: libyaml reads `{v: é?no}` and the pure parser refuses it. A value proven
    # on one parser was a file that loads on the author's machine and breaks on the next one.
    def reads_back(out: str) -> bool:  # SAFE IN BOTH PLACES: a plain value and inside a {flow} mapping
        try:
            return all(read(f"k: {out}").get("k") == text and read(f"k: {{v: {out}}}").get("k") == {"v": text}
                       for read in (lambda doc: strict_yaml(doc, "yaml_value"),
                                    lambda doc: portable_yaml(doc, "yaml_value")))
        except (ValueError, yaml.YAMLError):  # a candidate that does not even parse is simply rejected
            return False
    for style in (None, "'", '"'):  # plain when it is safe, else single quotes, else double
        out = yaml.safe_dump(text, default_style=style, width=10**9, allow_unicode=True).strip()
        out = out.removesuffix("...").strip()
        if reads_back(out):
            return out
    raise ValueError(f"yaml_value: no quoting of {text!r} reads back exactly")


def add_entry(path: Path, section: str, name: str, pairs: list[str]) -> None:
    """Append `name` to a top-level mapping, every value GENERATED by yaml_value, then read the entry back.

    WHY (3.49.0). A ledger entry typed by hand put an apostrophe inside single quotes and the whole file
    stopped parsing — the 3.3.0 failure again, because quoting was a tool nobody had to go through.
    `k=v` is a string, `k=7` an integer, `k=[a,b]` a flow list; the read-back is the proof, not the parse.
    """
    def value(v: str) -> object:
        return [x.strip() for x in v[1:-1].split(",") if x.strip()] if v.startswith("[") else int(v) if v.isdigit() else v
    fields = {k: value(v) for k, v in (p.split("=", 1) for p in pairs)}
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    end = next((i for i in range(lines.index(f"{section}:\n") + 1, len(lines)) if lines[i][:1] not in " \n#"), len(lines))
    while lines[end - 1][:1] in "#\n":  # a comment block above the next key belongs to that key
        end -= 1
    emit = lambda v: "[" + ", ".join(map(yaml_value, v)) + "]" if isinstance(v, list) else str(v) if isinstance(v, int) else yaml_value(v)  # noqa: E731
    text = "".join(lines[:end] + [f"  {name}:\n"] + [f"    {k}: {emit(v)}\n" for k, v in fields.items()] + lines[end:])
    if (strict_yaml(text, str(path)).get(section) or {}).get(name) != fields:
        raise ValueError(f"{path}: {section}/{name} does not read back as written; nothing written")
    write_yaml_verified(path, text)


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["quote"] and len(sys.argv) == 3:
        print(yaml_value(sys.argv[2]))
    elif sys.argv[1:2] == ["entry"] and len(sys.argv) > 4:
        add_entry(Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5:])
    else:
        raise SystemExit("usage: safeedit.py quote '<text>' | entry <file.yaml> <section> <name> k=v...   — values generated, read back")
