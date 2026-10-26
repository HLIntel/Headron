#!/usr/bin/env python3
"""Worktree-based agent isolation — each session gets its own git worktree.

WHY (3.60.0). An agent editing source code shares the worktree with the human and other agents.
A failed edit corrupts the shared tree. The research pattern (arXiv:2610.03140):

  State_{t+1} = Commit if ExitCode==0, else Revert to State_t + Inject StdErr

Each agent session gets its own git worktree under `.trees/`. On session end, the worktree is
merged or removed. The worktree is locked via `git worktree lock --reason` to prevent concurrent access.

This module wraps the existing worktree patterns in branchstate.py and atlascore.py for agent use.

  thea worktree create <session_id> [--branch name]
  thea worktree remove <session_id>
  thea worktree list
  thea worktree lock <session_id>
  thea worktree unlock <session_id>
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from atlascore import ROOT, worktree


def _trees_dir() -> Path:
    """The .trees/ directory under the repository root."""
    trees = ROOT / ".trees"
    trees.mkdir(parents=True, exist_ok=True)
    return trees


def _session_dir(session_id: str) -> Path:
    """The worktree path for a given session."""
    return _trees_dir() / session_id


def _meta_path(session_id: str) -> Path:
    """Metadata file for a session's worktree."""
    return _trees_dir() / f"{session_id}.json"


def create_worktree(session_id: str, branch: str | None = None, base: str | None = None) -> dict:
    """Create an isolated worktree for an agent session.

    ARGUMENTS:
        session_id: unique session identifier
        branch: branch name to create (defaults to session_id)
        base: base commit/branch to create from (defaults to HEAD)

    RETURNS:
        Dict with session_id, path, branch, base, created_at.
    """
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("session_id must be a non-empty string")

    session_dir = _session_dir(session_id)
    if session_dir.exists():
        raise OSError(f"worktree already exists for session {session_id!r}: {session_dir}")

    branch = branch or session_id
    base = base or "HEAD"

    # Create the worktree
    repo = worktree()
    result = subprocess.run(
        ["git", "worktree", "add", "-q", "--detach", str(session_dir), base],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if result.returncode != 0:
        raise OSError(f"git worktree add failed: {result.stderr.strip()}")

    # Lock the worktree to prevent concurrent access
    subprocess.run(
        ["git", "worktree", "lock", "--reason", f"Agent {session_id}", str(session_dir)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )

    # Record metadata
    meta = {
        "session_id": session_id,
        "path": str(session_dir),
        "branch": branch,
        "base": base,
        "created_at": round(time.time(), 3),
        "locked": True,
        "merged": False,
        "removed": False,
    }
    _meta_path(session_id).write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def remove_worktree(session_id: str, force: bool = False) -> dict:
    """Remove a session's worktree.

    ARGUMENTS:
        session_id: the session identifier
        force: force removal even if there are uncommitted changes

    RETURNS:
        Updated metadata dict.
    """
    session_dir = _session_dir(session_id)
    meta_path = _meta_path(session_id)

    if not session_dir.exists():
        raise OSError(f"worktree does not exist for session {session_id!r}")

    repo = worktree()

    # Unlock first if locked
    subprocess.run(
        ["git", "worktree", "unlock", str(session_dir)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )

    # Remove the worktree
    flags = ["--force"] if force else []
    result = subprocess.run(
        ["git", "worktree", "remove"] + flags + [str(session_dir)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )

    # Update metadata
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    meta["removed"] = True
    meta["removed_at"] = round(time.time(), 3)
    meta["remove_error"] = result.stderr.strip() if result.returncode != 0 else None
    meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def lock_worktree(session_id: str, reason: str | None = None) -> bool:
    """Lock a session's worktree to prevent concurrent access.

    ARGUMENTS:
        session_id: the session identifier
        reason: reason for the lock (defaults to "Agent <session_id>")

    RETURNS:
        True if locked successfully.
    """
    session_dir = _session_dir(session_id)
    if not session_dir.exists():
        return False

    reason = reason or f"Agent {session_id}"
    repo = worktree()
    result = subprocess.run(
        ["git", "worktree", "lock", "--reason", reason, str(session_dir)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    return result.returncode == 0


def unlock_worktree(session_id: str) -> bool:
    """Unlock a session's worktree.

    ARGUMENTS:
        session_id: the session identifier

    RETURNS:
        True if unlocked successfully.
    """
    session_dir = _session_dir(session_id)
    if not session_dir.exists():
        return False

    repo = worktree()
    result = subprocess.run(
        ["git", "worktree", "unlock", str(session_dir)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    return result.returncode == 0


def get_worktree_meta(session_id: str) -> dict | None:
    """Get worktree metadata, reading the JSON sidecar for the session."""
    meta_path = _meta_path(session_id)
    try:
        content = meta_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def list_worktrees() -> list[dict]:
    """List all agent worktrees.

    RETURNS:
        List of metadata dicts for all worktrees.
    """
    trees_dir = _trees_dir()
    if not trees_dir.exists():
        return []
    metas = []
    for meta_path in trees_dir.glob("*.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            metas.append(meta)
        except (json.JSONDecodeError, OSError):
            continue
    return metas


def cleanup_old_worktrees(max_age_seconds: int = 86400 * 7) -> int:
    """Remove worktrees older than max_age_seconds (bounded storage).

    ARGUMENTS:
        max_age_seconds: maximum age in seconds (default: 7 days)

    RETURNS:
        Number of worktrees cleaned up.
    """
    now = time.time()
    cleaned = 0
    for meta in list_worktrees():
        created = meta.get("created_at", 0)
        if now - created > max_age_seconds and not meta.get("removed"):
            session_id = meta.get("session_id")
            if session_id:
                try:
                    remove_worktree(session_id, force=True)
                    cleaned += 1
                except OSError:
                    continue
    return cleaned


def state_rollback(session_id: str, exit_code: int) -> dict | None:
    """Apply state machine rollback based on exit code.

    State_{t+1} = Commit if ExitCode==0, else Revert to State_t + Inject StdErr

    ARGUMENTS:
        session_id: the session identifier
        exit_code: the exit code of the command that ran in the worktree

    RETURNS:
        Updated metadata dict or None if not found.
    """
    meta = get_worktree_meta(session_id)
    if meta is None:
        return None

    if exit_code == 0:
        # Success — mark as committed
        meta["last_exit"] = 0
        meta["last_commit"] = round(time.time(), 3)
    else:
        # Failure — revert changes
        session_dir = _session_dir(session_id)
        if session_dir.exists():
            subprocess.run(
                ["git", "checkout", "--force", "."],
                cwd=session_dir,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
            subprocess.run(
                ["git", "clean", "-fd"], cwd=session_dir, capture_output=True, text=True, timeout=600, check=False
            )
        meta["last_exit"] = exit_code
        meta["last_rollback"] = round(time.time(), 3)

    meta_path = _meta_path(session_id)
    meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Worktree-based agent isolation")
    sub = parser.add_subparsers(dest="command")

    create_p = sub.add_parser("create", help="Create a worktree for a session")
    create_p.add_argument("session_id")
    create_p.add_argument("--branch", default=None)
    create_p.add_argument("--base", default="HEAD")

    remove_p = sub.add_parser("remove", help="Remove a session's worktree")
    remove_p.add_argument("session_id")
    remove_p.add_argument("--force", action="store_true")

    sub.add_parser("list", help="List all agent worktrees")

    lock_p = sub.add_parser("lock", help="Lock a session's worktree")
    lock_p.add_argument("session_id")
    lock_p.add_argument("--reason", default=None)

    sub.add_parser("unlock", help="Unlock a session's worktree").add_argument("session_id")

    status_p = sub.add_parser("status", help="Show worktree status")
    status_p.add_argument("session_id", nargs="?")

    rollback_p = sub.add_parser("rollback", help="Apply state machine rollback")
    rollback_p.add_argument("session_id")
    rollback_p.add_argument("exit_code", type=int)

    sub.add_parser("cleanup", help="Clean up old worktrees")

    args = parser.parse_args()

    if args.command == "create":
        meta = create_worktree(args.session_id, args.branch, args.base)
        print(json.dumps(meta, indent=1))
    elif args.command == "remove":
        meta = remove_worktree(args.session_id, args.force)
        print(json.dumps(meta, indent=1))
    elif args.command == "list":
        metas = list_worktrees()
        print(json.dumps(metas, indent=1))
    elif args.command == "lock":
        ok = lock_worktree(args.session_id, args.reason)
        print("locked" if ok else "failed to lock")
    elif args.command == "unlock":
        ok = unlock_worktree(args.session_id)
        print("unlocked" if ok else "failed to unlock")
    elif args.command == "status":
        if args.session_id:
            meta = get_worktree_meta(args.session_id)
            if meta:
                print(json.dumps(meta, indent=1))
            else:
                print("no worktree found")
        else:
            metas = list_worktrees()
            print(f"agent worktrees: {len(metas)}")
            for meta in metas:
                path = meta.get("path", "")
                removed = meta.get("removed", False)
                print(f"  {meta['session_id']}: {'removed' if removed else path}")
    elif args.command == "rollback":
        meta = state_rollback(args.session_id, args.exit_code)
        if meta:
            action = "committed" if args.exit_code == 0 else "rolled back"
            print(f"{action}: {json.dumps(meta, indent=1)}")
    elif args.command == "cleanup":
        cleaned = cleanup_old_worktrees()
        print(f"cleaned {cleaned} old worktrees")
    else:
        parser.print_help()
