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
        from receipt import build_computation_receipt  # noqa: PLC0415

        try:
            errors = request_errors(self.name, context)
            if errors:
                receipt = build_computation_receipt(
                    program=self.name,
                    version=self.version,
                    inputs=context,
                    outputs=None,
                    status="refused",
                    verification={
                        "status": "FAIL",
                        "checks": [{"id": f"{self.name}.contract", "state": "FAIL", "why": "; ".join(errors)}],
                    },
                    evidence_refs=tuple(errors),
                )
                return MicroResult(
                    self.name,
                    self.version,
                    "refused",
                    evidence_refs=tuple(errors),
                    next=self.next_step,
                    receipt=receipt,
                )
            output, refs = self.operation(context)
        except (ValueError, DecimalException, TypeError) as exc:
            receipt = build_computation_receipt(
                program=self.name,
                version=self.version,
                inputs=context,
                outputs=None,
                status="refused",
                verification={
                    "status": "FAIL",
                    "checks": [{"id": f"{self.name}.operation", "state": "FAIL", "why": str(exc)}],
                },
                evidence_refs=(str(exc),),
            )
            return MicroResult(
                self.name, self.version, "refused", evidence_refs=(str(exc),), next=self.next_step, receipt=receipt
            )
        receipt = build_computation_receipt(
            program=self.name,
            version=self.version,
            inputs=context,
            outputs=output,
            status="ok",
            verification={
                "status": "PASS",
                "checks": [
                    {"id": f"{self.name}.contract", "state": "PASS"},
                    {"id": f"{self.name}.operation", "state": "PASS"},
                ],
            },
            evidence_refs=refs,
        )
        return MicroResult(self.name, self.version, "ok", output, evidence_refs=refs, receipt=receipt)
