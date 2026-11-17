"""Offline local Markdown link and anchor checks."""

from __future__ import annotations

import re
from pathlib import Path

from atlascore import HTML_LINK_RE, LINK_RE, ROOT, anchor_error, link_target, rel, text_of, tracked


def _outside_fences(content: str) -> str:
    """Ignore Markdown code fences when interpreting links."""
    lines, fence = [], None
    source_lines = content.splitlines(keepends=True)
    for index, line in enumerate(source_lines):
        marker = re.match(r"^ {0,3}(?:(?:[-+*]|\d{1,9}[.)])[ \t]+)?(`{3,}|~{3,})", line)
        if marker and fence is None:
            lines.append("\n\n")
            fence = marker.group(1)
        elif (
            marker
            and fence
            and marker.group(1)[0] == fence[0]
            and len(marker.group(1)) >= len(fence)
            and not line[marker.end() :].strip()
        ):
            fence = None
            lines.append("\n\n")
        elif fence is None:
            item = re.match(r"^ {0,3}(?:[-+*]|\d{1,9}[.)])[ \t]+", line)
            block = re.match(r"^ {0,3}(?:#{1,6}(?:[ \t]|$)|>|(?:[-*_][ \t]*){3,}$)", line)
            setext = index + 1 < len(source_lines) and re.match(r"^ {0,3}(?:=+|-+)[ \t]*$", source_lines[index + 1])
            if block or item or setext:
                lines.append("\n\n")
            lines.append(line)
            if block or setext:
                lines.append("\n\n")
    text = "".join(lines)
    markers = list(re.finditer(r"`+", text))
    spans, opening = [], None
    for marker in markers:
        if opening is not None and re.search(r"\n[ \t]*\n", text[opening.end() : marker.start()]):
            opening = None
        if opening is None:
            before = text[: marker.start()]
            if (len(before) - len(before.rstrip("\\"))) % 2:
                continue
            opening = marker
        elif len(marker.group()) == len(opening.group()):
            spans.append((opening.start(), marker.end()))
            opening = None
    for start, end in reversed(spans):
        text = text[:start] + text[end:]
    return text


def link_errors(sources: list[Path] | None = None, root: Path = ROOT) -> tuple[list[str], dict[str, list[str]], int]:
    """Every local Markdown and HTML link resolves; also returns who links to what, and how many were read."""
    errors: list[str] = []
    inbound: dict[str, list[str]] = {}
    links_checked = 0
    for source in tracked() if sources is None else sources:
        if source.suffix.lower() != ".md" or source.is_symlink():
            continue
        if not source.is_file():
            errors.append(f"missing markdown: {rel(source, root)}")
            continue
        try:
            content = text_of(source)
        except UnicodeDecodeError:
            errors.append(f"non-UTF-8 markdown: {rel(source, root)}")
            continue
        content = _outside_fences(content)
        for match in list(LINK_RE.finditer(content)) + list(HTML_LINK_RE.finditer(content)):
            raw = (match.group(1) if match.re is HTML_LINK_RE else (match.group(1) or match.group(2))) or ""
            try:
                target = link_target(source, raw, root)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if missing_anchor := anchor_error(source, raw, root):
                errors.append(missing_anchor)
            if target is None:
                continue
            links_checked += 1
            key = rel(target, root)
            inbound.setdefault(key, []).append(rel(source, root))
            if target.is_dir():  # a link to a directory reaches its README
                inbound.setdefault(key + "/README.md", []).append(rel(source, root))
            if not target.exists():
                errors.append(f"broken local link: {rel(source, root)} -> {raw}")
    return errors, inbound, links_checked
