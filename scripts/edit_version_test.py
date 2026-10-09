#!/usr/bin/env python3
"""Planted case: the edit MCP route negotiates its revision like the read route, never echoing the client's."""

from __future__ import annotations


def edit_version_case(module) -> None:
    """thea_edit echoed any protocolVersion a client named: the defect thea_mcp fixed at 3.9.2, sighted again."""
    import thea_edit
    import thea_mcp

    declared = str(thea_mcp.atlas()["external_versions"]["mcp_specification"])

    def answer(ask: dict) -> object:
        reply = thea_edit.handle(ask)
        if reply is None:
            raise SystemExit("FAIL thea_edit read an initialize request as a notification")
        return reply["result"]["protocolVersion"]

    ask = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "no-such-revision"}}
    unknown = answer(ask)
    ask["params"]["protocolVersion"] = declared
    known = answer(ask)
    if (unknown, known) != (declared, declared):
        raise SystemExit(
            f"FAIL thea_edit answered an unknown revision with {unknown!r}, the declared one with {known!r}"
        )
    module.CASES.append(
        (
            "the edit MCP route answers an unknown revision with the declared one",
            "a second MCP server that echoed whatever revision a client named",
        )
    )
    print("  ok    thea-edit: an unknown MCP revision gets the declared one, not an echo")


def run(module) -> None:
    edit_version_case(module)
