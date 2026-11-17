#!/usr/bin/env python3
"""Tests for in-memory micro-code intermediate representation evaluation and telemetry."""

from __future__ import annotations

import microcode
from atlascore import parsed_python


def test_eval_depth() -> None:
    src_flat = "def f():\n    x = 1\n    return x\n"
    tree = parsed_python(src_flat, "<test>")
    assert tree is not None
    assert microcode.eval_max_depth(tree) == 1

    src_nested = """
def outer():
    if True:
        for i in range(5):
            while False:
                try:
                    with open('x') as f:
                        pass
                except Exception:
                    pass
"""
    tree_nest = parsed_python(src_nested, "<test>")
    assert tree_nest is not None
    assert microcode.eval_max_depth(tree_nest) == 6


def test_eval_line_bounds() -> None:
    src = "line1\nline2\nline3\n"
    count, ok = microcode.eval_line_bounds(src, cap=2)
    assert count == 3
    assert not ok

    count, ok = microcode.eval_line_bounds(src, cap=5)
    assert count == 3
    assert ok


def test_eval_structural_fingerprint() -> None:
    src = """
async def fetch(url: str) -> dict:
    return await client.get(url)
"""
    tree = parsed_python(src, "<test>")
    assert tree is not None
    tokens = microcode.eval_structural_fingerprint(tree)
    assert "ast_asyncfunctiondef" in tokens
    assert "sig_async" in tokens
    assert "sig_typed" in tokens
    assert "sig_args_1" in tokens
    assert "call_get" in tokens


def test_run_micro_audit() -> None:
    src = "def add(a, b):\n    return a + b\n"
    result = microcode.run_micro_audit(src, "math.py")
    assert result["verdict"] == "PASS"
    assert result["depth"] == 1
    assert result["latency_us"] > 0.0

    # Test syntax error refusal
    bad_src = "def broken(:"
    bad_result = microcode.run_micro_audit(bad_src, "broken.py")
    assert bad_result["verdict"] == "FAIL"


if __name__ == "__main__":
    test_eval_depth()
    test_eval_line_bounds()
    test_eval_structural_fingerprint()
    test_run_micro_audit()
    print("4/4 microcode tests passed")
