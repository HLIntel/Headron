#!/usr/bin/env python3
"""Characters in tracked text that a reader cannot see, or cannot tell apart.

TWO HALVES OF ONE PROBLEM, and they are opposites. `hidden_unicode_errors` refuses code points
nobody can SEE — zero-width, bidirectional control, tag characters. `confusable_command_errors`
refuses code points everybody can see and nobody can DISTINGUISH, inside the one context where the
difference decides what runs.

SPLIT OUT OF atlasgen AT 3.38.0, when adding the second one took that file to 1050 lines against a
1000-line cap. A cap is never raised to fit new code; the code moves to where it belongs, and these
two belong together.
"""
from __future__ import annotations

import re

from atlascore import rel, tracked


def hidden_unicode_errors() -> list[str]:
    """No invisible character in any tracked text file: zero-width, bidirectional control, or tag.

    WHY (2.29.0). This tree is handed to models whole. An invisible code point can carry an
    instruction a reviewer never sees (tag characters smuggle ASCII) or reorder what a reviewer sees
    against what a compiler runs (Trojan Source, CVE-2021-42574). Considered as a COMPRESSION channel
    and refused for the same reason: an encoding nobody can read is an attack surface, not a saving.
    Swept clean over every tracked text file before it was enforced.
    """
    hidden = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\U000e0000-\U000e007f]")
    errors: list[str] = []
    for path in tracked():
        if path.suffix.lower() in {".webp", ".png", ".gz", ".svg"} or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for m in hidden.finditer(line):
                errors.append(f"{rel(path)}:{number} carries invisible U+{ord(m.group()):04X} — remove it")
    return errors


# Characters that render like ASCII in a command and are not. Prose may use every one of these
# freely; a fenced command block may not.
CONFUSABLES = {
    "—": "-- (em dash)", "–": "- (en dash)", "−": "- (minus sign)",
    "‘": "' (left single quote)", "’": "' (right single quote)",
    "“": '" (left double quote)', "”": '" (right double quote)',
    " ": "a plain space (non-breaking space)",
}


def confusable_command_errors() -> list[str]:
    """A typographic character inside a COMMAND, where it renders like ASCII and is not.

    THE OPPOSITE HALF OF `hidden_unicode_errors`. That one refuses characters nobody can SEE. This
    refuses characters everybody can see and nobody can DISTINGUISH: `--change` and `—change` are
    one glyph apart on screen and a different argv entirely, and a reader who copies the second gets
    an error naming a flag that looks exactly like the one they typed.

    SCOPED TO COMMANDS, AND THAT SCOPE IS THE WHOLE DESIGN. This repository's prose is full of
    correct em dashes — this docstring included — so a tree-wide sweep would fire on hundreds of
    right answers and be switched off within a day (code-quality §9). Only fenced `bash`, `sh`,
    `shell` and `console` blocks are read, which is where a reader copies from.
    """
    errors: list[str] = []
    fence = re.compile(r"^```(bash|sh|shell|console)\s*$")
    for path in tracked():
        if path.suffix.lower() != ".md" or not path.is_file():
            continue
        inside = False
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.startswith("```"):
                inside = bool(fence.match(line)) if not inside else False
                continue
            if not inside:
                continue
            # A SHELL COMMENT IS PROSE THAT HAPPENS TO SIT IN A CODE BLOCK. The first clean sweep
            # fired on `# the latest release, READ — never typed`, which is correct English inside a
            # `#` comment and reaches no argv. A guard that fires on correct content gets switched
            # off (code-quality §9), so the comment is cut before the line is judged.
            code = line.split("#", 1)[0] if "#" in line else line
            for glyph, plain in CONFUSABLES.items():
                if glyph in code:
                    errors.append(f"{rel(path)}:{number} carries {glyph!r} inside a command block — "
                                  f"it renders like {plain.split(' (')[0]!r} and is not; a reader who "
                                  "copies this line gets an error naming a flag identical to the one "
                                  "they typed")
    return errors
