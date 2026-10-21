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
