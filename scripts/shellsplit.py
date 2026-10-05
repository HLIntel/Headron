"""The shell-string helpers shell_verdict reads: top-level statements, pipeline stages, heredoc bodies.

Split out of agentpolicy.py at 3.50.0, which sat at the line cap when the pipeline rules moved from the
whole string to one statement. Never shlex: an unbalanced quote is exactly the input this is asked about.
"""

from __future__ import annotations

import re

# A pipeline STAGE runs in a subshell, so a construct whose purpose is to change the CURRENT shell
# loses its effect there. Only `.`/`source` in the FIRST stage is refused: `( cd x && make ) | tee`
# puts a construct in a subshell ON PURPOSE, and a guard that cannot tell those apart fires on
# correct code and gets switched off (code-quality §9).
_SOURCING = frozenset({".", "source"})
# A pipeline ending in a pure text filter makes `$?` the FILTER's status: grep exits 1 on no match
# and 0 on any match, whatever the producer did — which is how a failing command reads as a pass.
_TEXT_FILTERS = frozenset(
    {
        "head",
        "tail",
        "cat",
        "grep",
        "egrep",
        "fgrep",
        "sed",
        "awk",
        "tee",
        "wc",
        "sort",
        "uniq",
        "tr",
        "cut",
        "jq",
        "column",
        "fmt",
        "rev",
        "nl",
        "strings",
    }
)
# A VERDICT PIPED INTO A FILTER REPORTS THE FILTER (3.42.0). Measured: `atlas.py check | tail` exited 0 over
# a red check, the runtime showed exit 0, and a public-tree leak was pushed. A stage whose basename or
# argument is one of these words is a verdict; one that only READS text is not, whatever it greps for.
_VERDICT_WORDS = frozenset(
    {
        "check",
        "test",
        "tests",
        "verify",
        "lint",
        "typecheck",
        "pytest",
        "ruff",
        "mypy",
        "pyright",
        "tsc",
        "eslint",
        "shellcheck",
        "doctor",
        "gate",
        "build",
        "vitest",
        "jest",
    }
)
_READERS = _TEXT_FILTERS | frozenset({"rg", "ls", "find", "echo", "printf", "git", "gh", "diff", "pgrep", "ps"})


def _first_word(fragment: str) -> str:
    """The binary a fragment invokes, skipping leading VAR=value and `command`. Never shlex: an unbalanced quote
    is exactly the input this is asked about, and it must not raise."""
    match = re.match(r"\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*(?:command\s+)?([^\s;&|<>()]+)", fragment)
    return match.group(1).rsplit("/", 1)[-1] if match else ""


def _top_level_split(cmd: str, separator) -> list[str]:
    """Split `cmd` wherever `separator(cmd, i)` names one OUTSIDE quotes, (), {} and $(); never shlex.

    `separator` returns (width, splits): how many characters the token at i spans, and whether it
    ends a part. A token that does not split (`||` to a pipeline) is still consumed whole.
    """
    parts: list[str] = []
    buf: list[str] = []
    quote = ""
    depth = 0
    i = 0
    while i < len(cmd):
        char = cmd[i]
        if quote or char == "\\":
            width = 2 if char == "\\" and quote != "'" and i + 1 < len(cmd) else 1
            if quote and char == quote:
                quote = ""
            buf.append(cmd[i : i + width])
            i += width
            continue
        width, splits = separator(cmd, i) if depth == 0 else (0, False)
        if splits:
            parts.append("".join(buf))
            buf = []
        elif width:
            buf.append(cmd[i : i + width])
        else:
            quote = char if char in "'\"" else ""
            depth = depth + (char in "({") - (char in ")}" and depth > 0)
            buf.append(char)
            width = 1
        i += width
    parts.append("".join(buf))
    return parts


def _pipe(cmd: str, i: int) -> tuple[int, bool]:
    if cmd[i] != "|":
        return 0, False
    return (2, False) if cmd[i + 1 : i + 2] == "|" else (1, True)


def _statement_end(cmd: str, i: int) -> tuple[int, bool]:
    pair = cmd[i : i + 2]
    if pair in ("&&", "||"):
        return 2, True
    if cmd[i] in ";\n":
        return 1, True
    if cmd[i] == "&" and cmd[i - 1 : i] not in (">", "<", "|") and cmd[i + 1 : i + 2] != ">":
        return 1, True
    return (1, False) if cmd[i] == "|" else (0, False)


def pipeline_stages(cmd: str) -> list[str]:
    """Split on TOP-LEVEL `|`, leaving `||`, quoted pipes and pipes inside (), {} or $() alone.

    Returns one element when there is no pipeline, so a caller tests `len(...) > 1` instead of
    searching for a character that means four different things depending on where it sits.
    """
    return _top_level_split(cmd, _pipe)


# A HEREDOC BODY IS DATA, NOT SHELL (3.50.0). Measured over seven days of one owner's agent shells: a
# `|` or `$?` inside a heredoc written to a file was judged as the pipeline running, and the command
# was refused for text it only wrote. The body is dropped before any structural rule reads the string.
_HEREDOC = re.compile(r"(?<!<)<<-?[ \t]*(['\"]?)([A-Za-z_][\w-]*)\1[^\n]*\n.*?^[ \t]*\2[ \t]*$", re.S | re.M)


def shell_statements(cmd: str) -> list[str]:
    """The TOP-LEVEL statements of `cmd` — split on `;`, newline, `&&`, `||` and `&` — heredoc bodies
    removed. Each rule about a pipeline reads ONE statement: `$?` reports the statement before it, and a
    verdict word three statements earlier does not make a later `ls | head` a verdict."""
    stripped = _HEREDOC.sub(lambda m: m.group(0).split("\n", 1)[0], cmd)
    return [part for part in _top_level_split(stripped, _statement_end) if part.strip()]


def pipeline_refusal(statements: list[str], unpiped: bool) -> str | None:
    """The reason the first of the three pipeline shapes refuses, judged inside the statement that holds it."""
    for index, statement in enumerate(statements):
        stages = pipeline_stages(statement)
        prior = pipeline_stages(statements[index - 1]) if index else []
        reported = _first_word(prior[-1]) if len(prior) > 1 else ""
        if "$?" in statement and reported in _TEXT_FILTERS and unpiped:
            return (
                f"`$?` after a pipeline ending in `{reported}` reads {reported}'s "
                "status, not that of the command being judged: a filter that printed "
                "something exits 0 whatever it filtered. Read ${PIPESTATUS[0]}, or run "
                "the command without the filter and gate on its own code"
            )
        if len(stages) < 2:
            continue
        if _first_word(stages[0]) in _SOURCING:
            return (
                "a sourced file in a pipeline's first stage runs in a SUBSHELL: every "
                "variable it exports dies there, so the file appears to load and changes "
                "nothing. Source it on its own line, then pipe what needs it"
            )
        tail_binary = _first_word(stages[-1])
        words = {part for w in re.findall(r"[\w./-]+", stages[0]) for part in w.rsplit("/", 1)[-1].split(".")}
        if (
            tail_binary in _TEXT_FILTERS
            and _first_word(stages[0]) not in _READERS
            and words & _VERDICT_WORDS
            and unpiped
        ):
            return (
                f"a verdict piped into `{tail_binary}` exits with {tail_binary}'s code, so a "
                "red gate reports 0. Prefix `set -o pipefail;`, or run it unpiped and read "
                "the output from the log"
            )
    return None
