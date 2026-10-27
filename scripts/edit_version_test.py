#!/usr/bin/env python3
"""Planted case: the edit MCP route negotiates its revision like the read route, never echoing the client's."""

from __future__ import annotations


def edit_version_case(module) -> None:
    """headron_edit echoed any protocolVersion a client named: the defect headron_mcp fixed at 3.9.2, sighted again."""
    import headron_edit
    import headron_mcp

    declared = str(headron_mcp.atlas()["external_versions"]["mcp_specification"])

    def answer(ask: dict) -> object:
        reply = headron_edit.handle(ask)
        if reply is None:
            raise SystemExit("FAIL headron_edit read an initialize request as a notification")
        return reply["result"]["protocolVersion"]

    ask = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "no-such-revision"}}
    unknown = answer(ask)
    ask["params"]["protocolVersion"] = declared
    known = answer(ask)
    if (unknown, known) != (declared, declared):
        raise SystemExit(
            f"FAIL headron_edit answered an unknown revision with {unknown!r}, the declared one with {known!r}"
        )
    module.CASES.append(
        (
            "the edit MCP route answers an unknown revision with the declared one",
            "a second MCP server that echoed whatever revision a client named",
        )
    )
    print("  ok    headron-edit: an unknown MCP revision gets the declared one, not an echo")


def run(module) -> None:
    edit_version_case(module)
