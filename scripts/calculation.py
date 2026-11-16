"""Shared result and refusal contract for deterministic calculations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import DecimalException
from typing import Any


class Calculation:
    name: str
    version: str
    operation: Callable[[Mapping[str, Any]], tuple[dict[str, Any], tuple[str, ...]]]
    next_step: str

    def run(self, context: Mapping[str, Any]) -> Any:
        from computation_contract import request_errors  # noqa: PLC0415
        from microprogram import MicroResult  # noqa: PLC0415

        try:
            errors = request_errors(self.name, context)
            if errors:
                return MicroResult(self.name, self.version, "refused", evidence_refs=tuple(errors), next=self.next_step)
            output, refs = self.operation(context)
        except (ValueError, DecimalException, TypeError) as exc:
            return MicroResult(self.name, self.version, "refused", evidence_refs=(str(exc),), next=self.next_step)
        return MicroResult(self.name, self.version, "ok", output, evidence_refs=refs)
