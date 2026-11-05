#!/usr/bin/env python3
"""The GitHub App's wire and queue shapes, as types only: nothing imports this at run time."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class Job(TypedDict):
    """What a webhook asks to have graded. Everything here came from the event; `owner` is the HEAD's, never the base's."""

    repo: str
    clone_url: str
    head_sha: str
    base_sha: str | None  # None for a push with no PR: a full verify, no diff
    pr: int | None
    installation_id: int
    owner: str
    event: str
    delivery: str


class QueuedJob(Job):
    """A job on disk. `enqueue` writes `id`; the rest arrive as the record moves between pending, running and done."""

    id: str
    attempts: NotRequired[int]
    queued_at: NotRequired[float]
    not_before: NotRequired[float]
    last_error: NotRequired[str]
    finalize: NotRequired[str]
    result: NotRequired[dict]
    done_at: NotRequired[float]
    check_run_id: NotRequired[int]


class CheckOutput(TypedDict):
    title: str
    summary: str
    text: str


class CheckRunBody(TypedDict):
    """POST /repos/{repo}/check-runs."""

    name: str
    head_sha: str | None
    status: str
    conclusion: str
    output: CheckOutput
