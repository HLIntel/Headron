#!/usr/bin/env python3
"""yaml_prose_is_quoted: prose inside a YAML flow collection is quoted, so a comma cannot silently split it.

WHY (3.28.0). This break was made THREE times in one session, by the agent writing the rules. An
unquoted multi-word value inside `[...]` or `{...}` is a plain scalar, and a plain scalar ends at the
first comma or `: ` — so adding a clause to a sentence turns ONE declared item into TWO, and the file
still parses. A roster silently grows an item nobody wrote; `example_coverage — the tool budget` was
found in this tree reading as one ratchet across a line wrap.

The LOUD shape needs no rule: a `: ` in a block scalar is a parse error, and the parse-first check
already refuses it. Only the flow-context split is silent, so only it is guarded here.

Measured before the rule shipped (scripts/yamlshape.py --sweep): a rule firing on any unquoted prose
value anywhere flagged 434 of 2660 inline values and was REFUSED as unshippable — a guard that fires
on correct content gets switched off. Narrowed to flow context it flagged 45, and those 45 were
QUOTED rather than exempted, each verified by loading the file before and after and comparing the
parsed data. The rule ships against a clean tree.
"""
from __future__ import annotations

import sys
from functools import lru_cache

import yaml
from atlascore import ROOT, tracked
from yaml import FlowMappingEndToken, FlowMappingStartToken, FlowSequenceEndToken, FlowSequenceStartToken, ScalarToken

PROSE_WORDS = 3   # a two-word plain item (`go vet`, `read only`) is idiom, not a sentence


@lru_cache(maxsize=None)
def flow_prose(text: str) -> tuple:
    """Every plain (unquoted) scalar inside a flow collection that reads as prose, with its line.

    The tokenizer is the identity here, never a regular expression over the line: `{steps: [[go, vet]]}`
    is correctly quoted flow and a regex reading commas cannot tell it from a split sentence. Measured
    on this tree, the regex form reported 168 where the tokenizer reports 45.

    CONTENT-KEYED, like `atlascore.parsed_python`, and for the same reason: this runs once per
    planted case and a name-keyed cache would answer from before the plant. Keyed on the TEXT, a
    plant changes the key. MEASURED at 3.38.0: 0.225 s to 0.001 s unchanged, 0.139 s when atlas.yaml
    moved — ~22 s off a suite.
    """
    found: list[tuple[int, str]] = []
    depth = 0
    for token in yaml.scan(text):
        if isinstance(token, (FlowSequenceStartToken, FlowMappingStartToken)):
            depth += 1
        elif isinstance(token, (FlowSequenceEndToken, FlowMappingEndToken)):
            depth -= 1
        elif isinstance(token, ScalarToken) and depth > 0 and token.style is None \
                and len(token.value.split()) >= PROSE_WORDS:
            found.append((token.start_mark.line + 1, token.value))
    return found


def yaml_shape_errors() -> list[str]:
    """yaml_prose_is_quoted — an unquoted sentence inside a YAML flow collection is refused.

    A file this cannot SCAN is reported, never skipped: a shape check that silently passes on the one
    file it could not read is the blind spot it exists to close.
    """
    errors: list[str] = []
    scanned = 0
    for path in tracked():
        rel = str(path)
        if not rel.endswith((".yaml", ".yml")):
            continue
        scanned += 1
        try:
            text = (ROOT / rel).read_text(encoding="utf-8")
            items = flow_prose(text)
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            errors.append(f"{rel}: cannot be scanned for YAML shape ({type(exc).__name__}); "
                          f"a shape check that skips a file it could not read proves nothing")
            continue
        errors += [
            f"{rel}:{line}: unquoted prose inside a flow collection — {value[:60]!r}. Quote it: a "
            f"plain scalar ends at the first comma, so adding a clause splits one item into two and "
            f"the file still parses."
            for line, value in items
        ]
    if not scanned:
        errors.append("yaml_prose_is_quoted scanned no YAML file at all — the roster has stopped "
                      "describing the tree, and an empty clean pass prints like a real one")
    return errors


def main() -> int:
    """`--sweep` prints the coverage beside the refusal count: 0 of 0 and 0 of many print the same 0."""
    errors = yaml_shape_errors()
    scanned = sum(1 for path in tracked() if str(path).endswith((".yaml", ".yml")))
    for line in errors:
        print(f"- {line}")
    print(f"{len(errors)} findings over {scanned} tracked YAML files")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
