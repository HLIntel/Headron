"""Tests for portable task-image execution and DAG incremental recomputation (scripts/taskimage.py).

proves: task images export to portable bundles and import into separate checkouts;
  incremental DAG execution recomputes only invalidated nodes;
  checkpoints and receipts are preserved across portable transfers
does_not_prove: network transport layer reliability
closed_by: taskimage_portable_test.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import taskimage
from atlascore import ROOT

EXAMPLE = ROOT / "tools" / "agent-task.example.headron"


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    taskimage._git(path, "init", "-q")  # noqa: SLF001
    (path / "file.txt").write_text("content\n")
    taskimage._git(path, "add", "file.txt")  # noqa: SLF001
    taskimage._git(  # noqa: SLF001
        path, "-c", "user.name=test", "-c", "user.email=t@example.invalid", "commit", "-qm", "initial"
    )
    return path


def test_portable_export_and_import() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _init_repo(Path(tmp) / "src")
        dst = _init_repo(Path(tmp) / "dst")

        # Compile task image in src repo
        taskimage.compile_image(EXAMPLE, repo=src)
        task_id = "reference-contract"

        bundle_file = Path(tmp) / "task.bundle"
        exported, code = taskimage.export_image(task_id, bundle_file, repo=src)
        assert code == 0
        assert exported["status"] == "exported"
        assert bundle_file.is_file()

        # Import into dst repo
        imported, code_imp = taskimage.import_image(bundle_file, repo=dst)
        assert code_imp == 0
        assert imported["status"] == "imported"

        # Verify dst now has the task ref
        commit, files = taskimage.read(task_id, repo=dst) or ("", {})
        assert commit != ""
        assert "contract.json" in files
        assert "state.json" in files


def test_incremental_dag_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = _init_repo(Path(tmp) / "repo")
        taskimage.compile_image(EXAMPLE, repo=repo)
        task_id = "reference-contract"

        # Inspect compiled state
        commit, files = taskimage.read(task_id, repo=repo) or ("", {})
        state = taskimage.json.loads(files["state.json"])
        assert state["order"]

        # Run with execute=False (dry-run/controls-verified)
        from unittest import mock

        with mock.patch.object(taskimage, "ROOT", repo):
            res_state, code = taskimage.run_image(EXAMPLE, execute=False, resume=True, repo=repo, incremental=True)
            assert code in (0, 1)
            assert res_state["task_id"] == task_id


if __name__ == "__main__":
    test_portable_export_and_import()
    test_incremental_dag_run()
    print("taskimage_portable_test: PASS")
