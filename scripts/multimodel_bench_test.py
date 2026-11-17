#!/usr/bin/env python3
"""Tests for multi-model benchmark evaluation and collaborative matrix.

proves: multi-model matrix computation, cooperative ensemble auditing, and markdown reporting
does_not_prove: live vendor response rates or token latencies
closed_by: python scripts/multimodel_bench_test.py
"""

from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import patch

import multimodel_bench


class TestMultiModelBench(unittest.TestCase):
    def test_parse_model_spec(self) -> None:
        self.assertEqual(multimodel_bench.parse_model_spec("router:small"), ("router", "small"))
        self.assertEqual(multimodel_bench.parse_model_spec("code"), ("router", "code"))
        self.assertEqual(
            multimodel_bench.parse_model_spec("google-ai-studio:gemini-2.0-flash"),
            ("google-ai-studio", "gemini-2.0-flash"),
        )

    def test_select_questions(self) -> None:
        qs = multimodel_bench.select_questions(["hygiene", "plan"], sample_diagnose=2)
        kinds = {q["kind"] for q in qs}
        self.assertEqual(kinds, {"hygiene", "plan"})
        self.assertEqual(len(qs), 17)

        qs_diag = multimodel_bench.select_questions(["diagnose"], sample_diagnose=3)
        self.assertEqual(len(qs_diag), 3)

    @patch("providers.complete")
    def test_benchmark_single(self, mock_complete: Any) -> None:
        # Mock responses: blind fails, headron succeeds
        def fake_complete(provider: str, model: str, prompt: str, timeout: int, max_tokens: int) -> tuple[str, int]:
            if "Rule A:" in prompt or "Change classes" in prompt:
                return "yes", 150
            return "maybe", 120

        mock_complete.side_effect = fake_complete
        qs = [{"kind": "hygiene", "task": "h0", "truth": ["yes"], "blind": "ask", "headron": "Rule A:\nask"}]
        res = multimodel_bench.benchmark_single("router", "small", qs, timeout=5)
        self.assertEqual(res["provider"], "router")
        self.assertEqual(res["model"], "small")
        self.assertEqual(res["overall"]["total"], 1)
        self.assertEqual(res["overall"]["blind_correct"], 0)
        self.assertEqual(res["overall"]["headron_correct"], 1)

    @patch("providers.complete")
    def test_benchmark_cooperative(self, mock_complete: Any) -> None:
        # Lead gives wrong answer, peer audits and corrects it
        calls: list[tuple[str, str]] = []

        def fake_complete(provider: str, model: str, prompt: str, timeout: int, max_tokens: int) -> tuple[str, int]:
            calls.append((provider, model))
            if "teammate drafted this answer" in prompt:
                return "yes", 80
            return "no", 60

        mock_complete.side_effect = fake_complete
        qs = [{"kind": "hygiene", "task": "h0", "truth": ["yes"], "blind": "ask", "headron": "Rule A:\nask"}]
        res = multimodel_bench.benchmark_cooperative("router", "small", "router", "code", qs, timeout=5)
        self.assertEqual(res["correct"], 1)
        self.assertEqual(res["total"], 1)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], ("router", "small"))
        self.assertEqual(calls[1], ("router", "code"))

    def test_format_matrix_markdown(self) -> None:
        benchmarks = [
            {
                "provider": "router",
                "model": "small",
                "overall": {
                    "blind_correct": 5,
                    "headron_correct": 10,
                    "total": 10,
                    "blind_tokens": 1200,
                    "headron_tokens": 1800,
                },
                "kinds": {
                    "hygiene": {
                        "blind": {"correct": 5, "asked": 10, "tokens": 1200, "latency_s": 1.5},
                        "headron": {"correct": 10, "asked": 10, "tokens": 1800, "latency_s": 2.0},
                    }
                },
            }
        ]
        coop = {
            "lead": "router:small",
            "peer": "router:code",
            "correct": 10,
            "total": 10,
            "tokens": 2400,
            "latency_s": 2.5,
        }
        md = multimodel_bench.format_matrix_markdown(benchmarks, coop)
        self.assertIn("`router:small`", md)
        self.assertIn("50.0%", md)
        self.assertIn("100.0%", md)
        self.assertIn("+50.0%", md)
        self.assertIn("`cooperative:router:small+router:code`", md)


if __name__ == "__main__":
    unittest.main()
