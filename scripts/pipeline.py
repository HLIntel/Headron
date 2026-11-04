#!/usr/bin/env python3
"""State-to-action pipeline — finite state machine: INGEST → CLASSIFY → VERIFY → EXIT.

Driven by verdict types from decide.py and reflex.py. Produces a structured pipeline
record: {state, verdicts, artifact, next}. Cycle detection refuses a transition loop.

proves: a change moves through the pipeline as a deterministic state machine
does_not_prove: that the gates pass — only that the transitions are valid
closed_by: pipeline_test.py, which plants cycles and asserts refusal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from decide import transition as decide_transition
from processpolicy import process_record


class PipelineState(Enum):
    """Pipeline states for the finite state machine."""

    INGEST = "ingest"
    CLASSIFY = "classify"
    VERIFY = "verify"
    EXIT = "exit"
    HALT = "halt"
    SANDBOX_REVIEW = "sandbox_review"


@dataclass
class PipelineRecord:
    """Structured record of a pipeline run."""

    state: str
    verdicts: dict[str, str] = field(default_factory=dict)
    artifact: str = ""
    next_state: str = ""
    history: list[str] = field(default_factory=list)


@dataclass
class ProcessExecution:
    """A resumable, side-effect-free execution checkpoint for one declared process."""

    process: str
    status: str
    completed_steps: list[str] = field(default_factory=list)
    current_step: str = ""
    next_action: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)
    checkpoint: int = 0
    reason: str = ""


def advance_process(
    process: str,
    *,
    completed_steps: list[str] | tuple[str, ...] = (),
    observations: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
) -> ProcessExecution:
    """Advance a declared process by one deterministic step.

    This is the Phase 1 execution seam: it owns process ordering, stopping and escalation
    decisions, while callers own the side effects of the returned ``next_action``. A
    checkpoint is valid input for the next call, so a resumed worker never infers progress
    from a partially written workspace.
    """
    observations = observations or {}
    supplied_artifacts = dict(artifacts or {})
    try:
        spec = process_record(process)
    except (KeyError, TypeError, ValueError):
        return ProcessExecution(process=str(process), status="halted", reason="unknown_process")

    if spec["process"] != str(process) or not spec["sequence"]:
        return ProcessExecution(process=str(process), status="halted", reason="unknown_process")
    sequence = [str(row["step"]) for row in spec["sequence"]]
    completed = list(dict.fromkeys(str(step) for step in completed_steps))
    invalid = [step for step in completed if step not in sequence]
    if invalid or completed != sequence[: len(completed)]:
        return ProcessExecution(
            process=process,
            status="halted",
            completed_steps=completed,
            artifacts=supplied_artifacts,
            checkpoint=len(completed),
            reason="invalid_checkpoint",
        )

    for condition in spec["stop_when"]:
        if observations.get(condition) is True:
            return ProcessExecution(
                process=process,
                status="stopped",
                completed_steps=completed,
                artifacts=supplied_artifacts,
                checkpoint=len(completed),
                reason=condition,
            )
    for condition in spec["escalate_when"]:
        if observations.get(condition) is True:
            return ProcessExecution(
                process=process,
                status="escalated",
                completed_steps=completed,
                artifacts=supplied_artifacts,
                checkpoint=len(completed),
                reason=condition,
            )

    if len(completed) == len(sequence):
        missing = [name for name in spec["artifacts"] if name not in supplied_artifacts]
        if missing:
            return ProcessExecution(
                process=process,
                status="blocked",
                completed_steps=completed,
                artifacts=supplied_artifacts,
                checkpoint=len(completed),
                reason="missing_artifacts:" + ",".join(missing),
            )
        return ProcessExecution(
            process=process,
            status="accepted",
            completed_steps=completed,
            artifacts=supplied_artifacts,
            checkpoint=len(completed),
            reason="acceptance_ready",
        )

    next_step = sequence[len(completed)]
    return ProcessExecution(
        process=process,
        status="ready",
        completed_steps=completed,
        current_step=next_step,
        next_action=next_step,
        artifacts=supplied_artifacts,
        checkpoint=len(completed),
    )


def run_pipeline(change_class: str, files: list[str], diff_metadata: dict[str, Any] | None = None) -> PipelineRecord:
    """Run the full pipeline: INGEST → CLASSIFY → VERIFY → EXIT.

    Returns a PipelineRecord with the final state and verdicts.
    Cycle detection refuses a transition that would create a loop.

    proves: a change moves through the pipeline as a deterministic state machine
    does_not_prove: that the gates pass — only that the transitions are valid
    closed_by: pipeline_test.py, which plants cycles and asserts refusal
    """
    from reflex import classify_change, classify_diff  # noqa: PLC0415

    record = PipelineRecord(state="ingest", artifact=change_class)
    visited: list[str] = []

    # INGEST stage
    visited.append("ingest")
    if diff_metadata is None:
        diff_metadata = {"files": files}
    verdicts = classify_diff(diff_metadata)
    record.verdicts = verdicts

    # Determine verdict from reflex classification
    change_verdict = classify_change(change_class, files, diff_metadata)

    # CLASSIFY stage
    next_state = decide_transition("ingest", str(change_verdict.value))
    if next_state == "halt":
        record.state = "halt"
        record.next_state = "halt"
        record.history = visited + ["halt"]
        return record
    if next_state == "sandbox_review":
        record.state = "sandbox_review"
        record.next_state = "sandbox_review"
        record.history = visited + ["sandbox_review"]
        return record
    if next_state == "exit":
        record.state = "exit"
        record.next_state = "exit"
        record.history = visited + ["exit"]
        return record

    visited.append("classify")

    # Check for cycle
    if "classify" in visited[:-1]:
        record.state = "halt"
        record.next_state = "cycle_detected"
        record.history = visited + ["cycle_detected"]
        return record

    # VERIFY stage
    next_state = decide_transition("classify", str(change_verdict.value))
    if next_state == "halt":
        record.state = "halt"
        record.next_state = "halt"
        record.history = visited + ["halt"]
        return record
    if next_state == "sandbox_review":
        record.state = "sandbox_review"
        record.next_state = "sandbox_review"
        record.history = visited + ["sandbox_review"]
        return record
    if next_state == "exit":
        record.state = "exit"
        record.next_state = "exit"
        record.history = visited + ["exit"]
        return record

    visited.append("verify")

    # Final transition
    next_state = decide_transition("verify", str(change_verdict.value))
    if next_state == "halt":
        record.state = "halt"
        record.next_state = "halt"
        record.history = visited + ["halt"]
        return record
    if next_state == "sandbox_review":
        record.state = "sandbox_review"
        record.next_state = "sandbox_review"
        record.history = visited + ["sandbox_review"]
        return record

    record.state = "exit"
    record.next_state = "exit"
    record.history = visited + ["exit"]
    return record
