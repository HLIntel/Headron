#!/usr/bin/env python3
"""Regression cases for atlas.yaml/artifact_edges: a plan the model writes is applied by something else."""

from __future__ import annotations


def run(module) -> None:
    """One planted defect per edge rule; each LOOKS complete, which is why each is planted."""
    with module.mutated(
        "atlas.yaml",
        lambda s: s.replace(
            "    applied_by: a deterministic writer that refuses a row the column map cannot type",
            "    applied_by: the model writes the rows directly",
            1,
        ),
    ):
        module.case(
            "an artifact edge applied by the model FAILS",
            "a model that writes a plan and applies it, so the result is graded by the hand that made it",
            True,
            "grades its own work",
            by="knowledge.knowledge_errors",
        )
    with module.mutated(
        "atlas.yaml",
        lambda s: s.replace(
            "    to: [structured]\n    examples: ['records to csv'",
            "    to: [spreadsheet]\n    examples: ['records to csv'",
            1,
        ),
    ):
        module.case(
            "an artifact edge into an undeclared class FAILS",
            "a format added as its own class, so the graph grows a node no retrieval rule covers",
            True,
            "data_classes does not declare",
            by="knowledge.knowledge_errors",
        )
