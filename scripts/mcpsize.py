#!/usr/bin/env python3
"""Measure an MCP `tools/list` dump against the declared per-server token band.

WHY THIS EXISTS. `python scripts/contextcost.py` prints
"mcp tool schemas: NOT MEASURED here — pass a tools/list dump as the first argument"
because this repository cannot spawn a consumer's servers: the roster is theirs, the
credentials are theirs, and a probe that reaches out would make a measurement depend
on a network. This script is the other half of that split: the caller drives
`tools/list` once per server, saves `{server: [tools...]}` as JSON, and this reports
each server's schema cost against the band `atlas.yaml/context_policy` declares.

IT SHARES THE INSTRUMENTS, NOT JUST THE IDEA. Token math uses `contextcost.tokens`
(the ONE bytes-to-tokens estimate) and the report reuses `mcp_schema_tax` and
`mcp_tax_errors`, so this and `contextcost.py` can never disagree on what a server
costs or whether it is over the band.

EXIT CODE IS THE VERDICT: 0 when every server is inside the band, 1 when a server
exceeds it (the finding is printed), 2 when the dump cannot be read or is
misshapen. Refuse rather than invent: a dump that is not {server: [tools...]} is an
error, never an empty measurement.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from contextcost import mcp_schema_tax, mcp_tax_errors


def load_dump(path: Path) -> dict[str, list]:
    """Read the dump and shape-check it. Raises ValueError on anything misshapen."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"no such file: {path}") from None
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path} as JSON: {exc}") from None
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{path} must be a non-empty JSON object of {{server: [tools...]}}")
    for server, tools in raw.items():
        if not isinstance(server, str) or not isinstance(tools, list):
            raise ValueError(
                f"{path}: {server!r} must map to a list of tool schemas, "
                f"got {type(tools).__name__}"
            )
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcpsize.py",
        description=(
            "Report each MCP server's tools/list schema cost against the declared "
            "per-server token band. Complements `python scripts/contextcost.py`, which "
            "cannot measure schemas it cannot reach: drive tools/list yourself, save "
            "{server: [tools...]} as JSON, and measure it here."
        ),
    )
    parser.add_argument("dump", type=Path, help="JSON file: {server: [tool schemas...]}")
    parser.add_argument(
        "--cap",
        type=int,
        default=None,
        help="tokens per server; defaults to atlas.yaml/context_policy/mcp_server_tokens",
    )
    args = parser.parse_args(argv)

    try:
        tool_lists = load_dump(args.dump)
    except ValueError as exc:
        print(f"mcpsize: {exc}", file=sys.stderr)
        return 2

    tax = mcp_schema_tax(tool_lists)
    print(
        f"mcp tool schemas: {tax['servers']} server(s), {tax['bytes']} B (~{tax['tokens']} tok) "
        f"handed over on EVERY request; worst = {tax['worst']}"
    )
    for name, row in sorted(tax["per_server"].items(), key=lambda kv: -kv[1]["tokens"]):
        print(f"  {row['bytes']:>7} B  ~{row['tokens']:>6} tok  {row['tools']:>3} tools  {name}")

    errors = mcp_tax_errors(tool_lists, cap_tokens=args.cap)
    for error in errors:
        print(f"- {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
