"""Shared result and refusal contract for deterministic calculations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import DecimalException
from typing import Any

from effects import PURE


class Calculation:
    name: str
    version: str
    operation: Callable[[Mapping[str, Any]], tuple[dict[str, Any], tuple[str, ...]]]
    next_step: str
    declared = PURE  # a calculation reads only its context: no effects, same output for the same context

    def run(self, context: Mapping[str, Any]) -> Any:
        from computation_contract import request_errors  # noqa: PLC0415

        try:
            errors = request_errors(self.name, context)
            if errors:
                return self._refused(context, "contract", tuple(errors))
            output, refs = self.operation(context)
        except (ValueError, DecimalException, TypeError) as exc:
            return self._refused(context, "operation", (str(exc),))
        passed = [{"id": f"{self.name}.{step}", "state": "PASS"} for step in ("contract", "operation")]
        return self._result(context, "ok", output, passed, refs)

    def _refused(self, context: Mapping[str, Any], step: str, reasons: tuple[str, ...]) -> Any:
        failed = [{"id": f"{self.name}.{step}", "state": "FAIL", "why": "; ".join(reasons)}]
        return self._result(context, "refused", None, failed, reasons, next=self.next_step)

    def _result(
        self,
        context: Mapping[str, Any],
        status: str,
        output: Any,
        checks: list[dict],
        refs: tuple[str, ...],
        **extra: Any,
    ) -> Any:
        from microprogram import MicroResult  # noqa: PLC0415
        from receipt import build_computation_receipt  # noqa: PLC0415

        receipt = build_computation_receipt(
            program=self.name,
            version=self.version,
            inputs=context,
            outputs=output,
            status=status,
            checks=checks,
            evidence_refs=refs,
        )
        return MicroResult(self.name, self.version, status, output, evidence_refs=refs, receipt=receipt, **extra)
