#!/usr/bin/env python3
"""Mutation tests for the state-to-action pipeline.

Each case asserts the pipeline state machine behaves correctly. The case count
is asserted at the end.

    python scripts/pipeline_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pipeline  # noqa: E402

CASES: list[tuple[str, str]] = []


def case(name: str, kills: str) -> None:
    CASES.append((name, kills))
    print(f"  ok    {name}")


def main() -> int:
    """Run all pipeline cases and assert the count."""

    # 1. Clean change reaches EXIT.
    record = pipeline.run_pipeline("source_change", ["README.md"])
    if record.state != "exit":
        raise SystemExit(f"FAIL clean pipeline\n  expected exit, got {record.state}")
    case("clean change reaches EXIT state", "a pipeline that halts a clean change")

    # 2. Forbidden path reaches SANDBOX_REVIEW.
    record = pipeline.run_pipeline("source_change", ["scripts/atlas.py"])
    if record.state != "sandbox_review":
        raise SystemExit(f"FAIL forbidden pipeline\n  expected sandbox_review, got {record.state}")
    case("forbidden path reaches SANDBOX_REVIEW state", "a pipeline that allows a forbidden path change")

    # 3. Pipeline record has history.
    record = pipeline.run_pipeline("source_change", ["README.md"])
    if not record.history:
        raise SystemExit("FAIL history")
    case("pipeline record carries state history", "a pipeline that loses its state history")

    # 4. Pipeline record has verdicts.
    record = pipeline.run_pipeline("source_change", ["README.md"])
    if not record.verdicts:
        raise SystemExit("FAIL verdicts")
    case("pipeline record carries verdict vector", "a pipeline that drops verdicts")

    # 5. Pipeline record has artifact.
    record = pipeline.run_pipeline("source_change", ["README.md"])
    if record.artifact != "source_change":
        raise SystemExit(f"FAIL artifact\n  expected source_change, got {record.artifact!r}")
    case("pipeline record carries change class artifact", "a pipeline that loses the change class")

    # 6. External dependency reaches HALT.
    record = pipeline.run_pipeline(
        "source_change", ["README.md"], {"files": ["README.md"], "dependency_scope": "external"}
    )
    if record.state != "halt":
        raise SystemExit(f"FAIL external dep\n  expected halt, got {record.state}")
    case("external dependency reaches HALT state", "a pipeline that allows an external dependency change")

    # 7. Large AST delta reaches SANDBOX_REVIEW.
    record = pipeline.run_pipeline("source_change", ["README.md"], {"files": ["README.md"], "ast_delta": 15})
    if record.state != "sandbox_review":
        raise SystemExit(f"FAIL large AST\n  expected sandbox_review, got {record.state}")
    case("large AST delta reaches SANDBOX_REVIEW state", "a pipeline that allows a large structural change")

    # 8. PipelineState enum values are correct.
    ps = pipeline.PipelineState
    if ps.INGEST.value != "ingest" or ps.EXIT.value != "exit":
        raise SystemExit("FAIL PipelineState enum")
    case("PipelineState enum values are correct", "an enum whose values do not match the declared states")

    # 9. PipelineRecord dataclass fields exist.
    rec = pipeline.PipelineRecord(state="test")
    if not hasattr(rec, "verdicts") or not hasattr(rec, "history"):
        raise SystemExit("FAIL PipelineRecord fields")
    case("PipelineRecord has all required fields", "a record missing verdicts or history")

    # 10. Fast-track change reaches EXIT without verify.
    record = pipeline.run_pipeline("nonexistent_class", ["README.md"])
    if record.state != "exit":
        raise SystemExit(f"FAIL fast-track\n  expected exit, got {record.state}")
    case("unknown change class reaches EXIT (fast-track)", "a pipeline that requires verification for an unknown class")

    # 11. History contains ingest.
    record = pipeline.run_pipeline("source_change", ["README.md"])
    if "ingest" not in record.history:
        raise SystemExit("FAIL history ingest")
    case("pipeline history contains INGEST", "a pipeline that skips the ingest stage")

    # 12. History contains exit.
    record = pipeline.run_pipeline("source_change", ["README.md"])
    if "exit" not in record.history:
        raise SystemExit("FAIL history exit")
    case("pipeline history contains EXIT", "a pipeline that skips the exit stage")

    # 13. Sandbox review history contains sandbox_review.
    record = pipeline.run_pipeline("source_change", ["scripts/atlas.py"])
    if "sandbox_review" not in record.history:
        raise SystemExit("FAIL history sandbox")
    case("sandbox review history contains SANDBOX_REVIEW", "a pipeline that loses the sandbox state")

    # 14. Halt history contains halt.
    record = pipeline.run_pipeline(
        "source_change", ["README.md"], {"files": ["README.md"], "dependency_scope": "external"}
    )
    if "halt" not in record.history:
        raise SystemExit("FAIL history halt")
    case("halt history contains HALT", "a pipeline that loses the halt state")

    # 15. A declared process exposes its first executable step.
    execution = pipeline.advance_process("implementation")
    if execution.status != "ready" or execution.next_action != "route":
        raise SystemExit(f"FAIL process start: {execution}")
    case("declared process exposes its next step", "a process that starts without a checkpoint")

    # 16. A checkpoint advances in declaration order.
    execution = pipeline.advance_process("implementation", completed_steps=("route", "scope"))
    if execution.current_step != "retrieve" or execution.checkpoint != 2:
        raise SystemExit(f"FAIL process checkpoint: {execution}")
    case("process resumes from a verified checkpoint", "a resumed process that repeats or skips a step")

    # 17. Invalid checkpoints refuse rather than infer progress.
    execution = pipeline.advance_process("implementation", completed_steps=("retrieve",))
    if execution.status != "halted" or execution.reason != "invalid_checkpoint":
        raise SystemExit(f"FAIL invalid checkpoint: {execution}")
    case("invalid process checkpoints are refused", "a partial checkpoint that silently skips scope")

    # 18. Stop conditions have precedence over escalation.
    execution = pipeline.advance_process("security", observations={"secret_detected": True, "approval_required": True})
    if execution.status != "stopped" or execution.reason != "secret_detected":
        raise SystemExit(f"FAIL process stop condition: {execution}")
    case("process stop conditions are deterministic", "an unsafe process that escalates instead of stopping")

    # 19. Escalation is explicit and resumable.
    execution = pipeline.advance_process("implementation", observations={"approval_required": True})
    if execution.status != "escalated" or execution.reason != "approval_required":
        raise SystemExit(f"FAIL process escalation: {execution}")
    case("process escalation is explicit", "a process that continues past required approval")

    # 20. Completion requires every declared artifact.
    full = (
        "route",
        "scope",
        "retrieve",
        "plan",
        "edit",
        "fast_verify",
        "full_verify",
        "diff_audit",
        "accept",
        "record",
    )
    execution = pipeline.advance_process("implementation", completed_steps=full)
    if execution.status != "blocked" or not execution.reason.startswith("missing_artifacts:"):
        raise SystemExit(f"FAIL missing artifacts: {execution}")
    case("process acceptance requires declared artifacts", "a process that accepts without its outputs")

    # 21. A complete process with outputs is accepted.
    outputs = {name: {"present": True} for name in ("diff", "gate_results", "audit_stream")}
    execution = pipeline.advance_process("implementation", completed_steps=full, artifacts=outputs)
    if execution.status != "accepted":
        raise SystemExit(f"FAIL process acceptance: {execution}")
    case("complete process with outputs is accepted", "a process that refuses a complete result")

    expected = 21
    if len(CASES) != expected:
        raise SystemExit(f"FAIL case count: {len(CASES)} cases, expected {expected}")
    print(f"\n{len(CASES)}/{expected} cases passed")
    return 0


def run(module: ModuleType) -> None:
    """Run in the counted contract suite only after all local cases pass."""
    from testgroups import run_counted

    run_counted(module, CASES, main)


if __name__ == "__main__":
    raise SystemExit(main())
