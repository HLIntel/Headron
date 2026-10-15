"""Calendar-claim validation, separate from CLI routing and contract orchestration."""

import re

from atlascore import atlas, rel, tracked


def dated_claim_errors() -> tuple[list[str], int, int]:
    """Every calendar date in a tracked text file, and the size of the sweep that found none.

    A DATE STAMPS WHEN SOMEONE TYPED; A VERSION STAMPS WHICH TREE THE CLAIM WAS TRUE OF. Only the
    second can be re-checked, and only the second survives being read a year later. So a calendar
    date may not appear in a tracked text file at all, with exactly two ways through: it is part of
    a URL, or it is an external project's own version that happens to be date shaped (MCP versions
    its specification that way), declared once in atlas.yaml.

    EXTRACTED BECAUSE THE RATCHET FIRED for the fourth time, on the line that wired the agent
    controls into check(). The cap falls with each split; raising it to fit the function it
    measures would make the ratchet a record of whatever happened last.
    """
    errors: list[str] = []
    external = {str(v) for v in (atlas().get("external_versions") or {}).values()}
    pattern = re.compile(r"\d{4}-\d{2}-\d{2}")
    suffixes = {".md", ".yaml", ".yml", ".json", ".py", ".toml", ".txt"}
    scanned = 0
    for path in tracked():
        if path.suffix.lower() not in suffixes or path.is_symlink() or not path.exists():
            continue
        scanned += 1
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for token in line.split():
                found = pattern.search(token)
                if not found or token.startswith(("http://", "https://")) or found.group(0) in external:
                    continue
                errors.append(
                    f"calendar date in {rel(path)}:{number} ({found.group(0)}) — stamp the claim with the "
                    "contract version it was measured at, or declare the date as an external project's "
                    "version in atlas.yaml/external_versions"
                )
    return errors, scanned, len(external)
