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

    @patch("providers.complete")
    def test_a_non_answer_is_not_scored(self, mock_complete: Any) -> None:
        # transport error on blind, empty reply on headron: both NOT RUN, neither wrong, neither in the denominator
        def fake_complete(provider: str, model: str, prompt: str, timeout: int, max_tokens: int) -> tuple[str, int]:
            if "Rule A:" in prompt:
                return "  ", 0
            raise OSError("reset")

        mock_complete.side_effect = fake_complete
        qs = [{"kind": "hygiene", "task": "h0", "truth": ["yes"], "blind": "ask", "headron": "Rule A:\nask"}]
        res = multimodel_bench.benchmark_single("router", "small", qs, timeout=5)
        self.assertEqual(res["questions"]["h0"], {"blind": "not_run", "headron": "not_run"})
        self.assertEqual(res["overall"]["blind_not_run"], 1)
        self.assertEqual(res["overall"]["headron_not_run"], 1)
        self.assertEqual(res["kinds"]["hygiene"]["blind"]["not_run"], 1)
        coop = multimodel_bench.benchmark_cooperative("router", "small", "router", "code", qs, timeout=5)
        self.assertEqual((coop["correct"], coop["not_run"]), (0, 1))

    def test_discrimination_drops_flat_tasks(self) -> None:
        def lane(model: str, verdicts: dict[str, str]) -> dict[str, Any]:
            return {"provider": "p", "model": model, "questions": {t: {"blind": v} for t, v in verdicts.items()}}

        lanes = [
            lane("a", {"all_pass": "correct", "all_fail": "wrong", "split": "correct", "solo": "correct"}),
            lane("b", {"all_pass": "correct", "all_fail": "wrong", "split": "wrong", "solo": "not_run"}),
            lane("c", {"all_pass": "correct", "all_fail": "not_run", "split": "not_run"}),
        ]
        d = multimodel_bench.discrimination(lanes)
        self.assertEqual(d["flat_pass"], ["all_pass"])
        self.assertEqual(d["flat_fail"], ["all_fail"])
        self.assertEqual(d["discriminating"], ["split"])
        self.assertEqual(d["unmeasured"], ["solo"])
        rank = multimodel_bench.screen_ranking(lanes)
        self.assertEqual([(r["lane"], r["correct"], r["answered"]) for r in rank][0], ("p:a", 1, 1))
        by = {r["lane"]: r for r in rank}
        self.assertEqual((by["p:c"]["answered"], by["p:c"]["not_run"]), (0, 1))

    def test_wilson_interval(self) -> None:
        self.assertEqual(multimodel_bench.wilson(0, 0), (0.0, 1.0))
        lo, hi = multimodel_bench.wilson(8, 10)
        self.assertEqual((lo, hi), (0.49, 0.943))
        self.assertLess(multimodel_bench.wilson(80, 100)[1] - multimodel_bench.wilson(80, 100)[0], hi - lo)

    def test_identity_names_the_served_model(self) -> None:
        import providers

        self.assertEqual(providers.identity("meta-llama/llama-3.3-70b:free", "llama-3.3-70b"), "match")
        self.assertEqual(providers.identity("x/glm-4.5-air:free", "openrouter/auto"), "differs")
        self.assertEqual(providers.identity("x/glm-4.5-air", ""), "unreported")

    def test_canary_failure_is_not_run_with_a_class(self) -> None:
        import urllib.error

        import providers

        err = urllib.error.HTTPError("u", 429, "slow down", {}, None)  # type: ignore[arg-type]
        with (
            patch("providers.endpoint", return_value=("http://x", {})),
            patch("urllib.request.urlopen", side_effect=err),
        ):
            row = providers.canary("groq", "m")
        self.assertEqual(row["status"], "not_run")
        self.assertTrue(row["error"].startswith("transient:"), row)
        spent = urllib.error.HTTPError("u", 402, "", {}, None)  # type: ignore[arg-type]
        with (
            patch("providers.endpoint", return_value=("http://x", {})),
            patch("urllib.request.urlopen", side_effect=spent),
        ):
            self.assertTrue(providers.canary("groq", "m")["error"].startswith("exhausted:"))

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
