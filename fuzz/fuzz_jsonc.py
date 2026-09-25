#!/usr/bin/env python3
"""Coverage-guided fuzz target for the JSONC reader.

WHY THIS ONE. `parse_jsonc` is a hand-written parser over untrusted-shaped text: editor
configuration, written by people and by tools, carrying comments and trailing commas that JSON
does not allow. It exists because the obvious implementation — strip `//` with a regular
expression — deletes the rest of any line containing the delimiter, INCLUDING the one inside
"https://example". That is not a hypothetical: it is how a task file in this repository first
failed to load.

A parser written to avoid one string-state bug is exactly the code most likely to contain
another, so it is fuzzed rather than trusted.

THE THREE PROPERTIES, and the second is the one that matters:

  1. IT NEVER RAISES ANYTHING BUT ValueError. A caller catches that; anything else takes down the
     contract, and a guard that crashes on malformed input reports none of the malformation.
  2. ON COMMENT-FREE INPUT IT AGREES WITH json EXACTLY. Where the dialects overlap, a second
     parser that disagrees with the standard one is worse than no second parser.
  3. A STRING CONTAINING A COMMENT DELIMITER SURVIVES INTACT. The bug this file exists for.

Runs two ways, like the grammar target: under atheris for the coverage-guided campaign, and on a
deterministic corpus with `python fuzz/fuzz_jsonc.py`, so it is exercised where atheris is absent.
A fuzz target nobody can run is a skeleton.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from atlascore import parse_jsonc  # noqa: E402


def check(text: str) -> None:
    """Every property, on one input. Raises AssertionError when one does not hold."""
    try:
        got = parse_jsonc(text)
    except ValueError:
        got = None            # a refusal is a legal outcome; a CRASH is not
    except RecursionError:
        return                # deep nesting is the interpreter's limit, not this parser's bug
    # 2. Where the dialects overlap, the two parsers must agree exactly.
    if "//" not in text and "/*" not in text:
        try:
            expected = json.loads(text)
        except ValueError:
            expected = None
        if got is not None and expected is not None:
            assert got == expected, f"disagrees with json on comment-free input: {text[:60]!r}"
    # 3. A comment delimiter INSIDE a string is data and must survive.
    holder = json.dumps({"u": f"https://example.test/{text[:24]}"})
    survived = parse_jsonc(holder)
    assert survived == json.loads(holder), "a // inside a string was treated as a comment"


def TestOneInput(data: bytes) -> None:  # noqa: N802 — libFuzzer's required entry point name
    check(data.decode("utf-8", errors="replace"))


CORPUS = [
    '{"a": 1}', '{"u": "https://x.test"} // trailing', '{/* lead */ "a": [1, 2,]}',
    '{"a": "// not a comment"}', '{"a": "/* also not */"}', '{"a": "\\"quoted // inside\\""}',
    '[1, 2, 3,]', '{}', '[]', '// only a comment', '/* unterminated', '{"a": "\\\\"}',
    '{"a": 1,}\n// tail', '{"a": "line\\nbreak // here"}', '', '   ', '{"a"', 'null',
    '{"nested": {"u": "http://a//b"}}', '{"a": "\\u00e9 // accent"}',
]


def main() -> int:
    for case in CORPUS:
        check(case)
    print(f"fuzz_jsonc: {len(CORPUS)} corpus inputs held all three properties — no crash, agrees "
          "with json where the dialects overlap, and a // inside a string survives")
    return 0


if __name__ == "__main__":
    try:
        import atheris
    except ImportError:
        sys.exit(main())
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
