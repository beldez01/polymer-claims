"""evidence_executor.py — EvidenceExecutor Protocol, EvidenceExecution (state validator),
ExecutionFailure, and EvidenceRuntime.

Part of the V2.0 evidence-licensed capability pathway (spec §5).
Pure + numpy-free; imports grammar but NOT polymer_claims.
"""
from __future__ import annotations

import dataclasses
import math
import typing
from typing import Literal

from pydantic import model_validator

from polymer_grammar.capability import CapabilityRegistry
from polymer_grammar.evidence_policy import EvidencePolicyRegistry
from polymer_grammar.executor_credential import ExecutorDescriptorRegistry, ExecutorTrustRegistry
from polymer_grammar.licensing import SatisfactionVerdict
from polymer_grammar.verification_policy import EvidenceLicensingInfo

from .base import _Model
from .corpus import ExecRecord

__all__ = [
    "ExecutionFailure",
    "EvidenceExecution",
    "EvidenceExecutor",
    "EvidenceRuntime",
]


# ---------------------------------------------------------------------------
# ExecutionFailure
# ---------------------------------------------------------------------------


class ExecutionFailure(_Model):
    """Structured reason a single evidence-execution was rejected or errored.

    ``stage`` distinguishes pre-dispatch rejection (validator/policy checks before the
    executor runs) from execution failures (the executor raised or returned an error).
    """

    reason: Literal[
        "empty",
        "malformed",
        "duplicate",
        "missing",
        "order_mismatch",
        "nonfinite_prediction",
        "out_of_support",
        "predictor_error",
        "policy_mismatch",
        "credential_mismatch",
        "digest_mismatch",
        "untrusted_executor",
    ]
    stage: Literal["pre_dispatch", "execution"]
    detail: str = ""


# ---------------------------------------------------------------------------
# EvidenceExecution (state validator)
# ---------------------------------------------------------------------------


class EvidenceExecution(_Model):
    """The outcome of a single evidence-computation run.

    Exactly one of two mutually-exclusive states:

    SUCCESS (``failure_reason is None``):
        * ``e_value`` is present, not NaN, and >= 0 (+inf is permitted).
        * ``licensing_info`` is present.
        * ``record.evaluation.satisfaction`` is None (not yet licensed).
        * ``record.evaluation.results`` has exactly one result whose verdict is
          UNDETERMINED (the executor produces raw e-values, not satisfaction).
        * ``record.claim_id`` matches ``licensing_info.evidence_provenance.claim_id``.

    FAILURE (``failure_reason is not None``):
        * ``e_value`` and ``licensing_info`` are both None.
        * ``record.evaluation.results`` has exactly one result with
          ``status == "error"`` and ``terminal.value is None``.
    """

    record: ExecRecord
    e_value: float | None = None
    licensing_info: EvidenceLicensingInfo | None = None
    failure_reason: ExecutionFailure | None = None

    @model_validator(mode="after")
    def _validate_state(self) -> "EvidenceExecution":
        results = self.record.evaluation.results

        if self.failure_reason is None:
            # ── SUCCESS path ──────────────────────────────────────────────
            errors: list[str] = []

            if self.e_value is None:
                errors.append("e_value must be set on a successful execution")
            elif math.isnan(self.e_value):
                errors.append("e_value must not be NaN")
            elif self.e_value < 0:
                errors.append(f"e_value must be >= 0, got {self.e_value}")

            if self.licensing_info is None:
                errors.append("licensing_info must be set on a successful execution")

            if self.record.evaluation.satisfaction is not None:
                errors.append(
                    "record.evaluation.satisfaction must be None in a pre-licensing "
                    "EvidenceExecution (satisfaction is minted by the licensing layer)"
                )

            if len(results) != 1:
                errors.append(
                    f"record.evaluation.results must have exactly one result on success; "
                    f"got {len(results)}"
                )
            elif results[0].verdict != SatisfactionVerdict.UNDETERMINED:
                errors.append(
                    f"result verdict must be UNDETERMINED on a raw evidence execution; "
                    f"got {results[0].verdict!r}"
                )

            if self.licensing_info is not None and self.e_value is not None:
                prov_id = self.licensing_info.evidence_provenance.claim_id
                if self.record.claim_id != prov_id:
                    errors.append(
                        f"record.claim_id ({self.record.claim_id!r}) does not match "
                        f"licensing_info.evidence_provenance.claim_id ({prov_id!r})"
                    )

            if errors:
                raise ValueError("; ".join(errors))

        else:
            # ── FAILURE path ──────────────────────────────────────────────
            errors = []

            if self.e_value is not None:
                errors.append("e_value must be None when failure_reason is set")

            if self.licensing_info is not None:
                errors.append("licensing_info must be None when failure_reason is set")

            if len(results) != 1:
                errors.append(
                    f"record.evaluation.results must have exactly one result on failure; "
                    f"got {len(results)}"
                )
            else:
                result = results[0]
                if result.status != "error":
                    errors.append(
                        f"result status must be 'error' on a failed execution; "
                        f"got {result.status!r}"
                    )
                if result.terminal.value is not None:
                    errors.append(
                        f"result terminal.value must be None on a failed execution; "
                        f"got {result.terminal.value!r}"
                    )

            if errors:
                raise ValueError("; ".join(errors))

        return self


# ---------------------------------------------------------------------------
# EvidenceExecutor (Protocol)
# ---------------------------------------------------------------------------


@typing.runtime_checkable
class EvidenceExecutor(typing.Protocol):
    """Structural protocol for an executor that produces e-value evidence."""

    def credential(self) -> str:
        """Return a stable, registry-registered credential string for this executor."""
        ...

    def execute(
        self,
        claim: typing.Any,
        cell: typing.Any,
        policy: typing.Any,
        ctx: typing.Any,
        fdr_test: typing.Any,
    ) -> EvidenceExecution:
        """Run the evidence computation and return a complete EvidenceExecution."""
        ...


# ---------------------------------------------------------------------------
# EvidenceRuntime (plain frozen dataclass — holds the executor callable)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class EvidenceRuntime:
    """Protocol-level runtime bundle wiring the registries to a concrete executor.

    A plain frozen dataclass (not a _Model) so it can carry the executor callable,
    which is not JSON-serialisable.
    """

    capability_registry: CapabilityRegistry
    evidence_policy_registry: EvidencePolicyRegistry
    executor_descriptor_registry: ExecutorDescriptorRegistry
    executor_trust_registry: ExecutorTrustRegistry
    executor: EvidenceExecutor
