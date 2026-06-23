"""TEST DOUBLE ONLY — DO NOT SHIP IN A PRODUCTION ADAPTER REGISTRY.

The air-gap needs two INDEPENDENTLY-OWNED adapters that agree before a license is minted.
This fixture is the independent corroborator used to validate the BioNeMo plumbing end-to-end.
Its credential MUST use a non-"NVIDIA" owner and may appear ONLY in a plumbing-validation
AdapterRegistry — NEVER in `polymer_claims.bionemo.registry`. When a real scientific wedge is
chosen, this is replaced by a real independent model (ESMFold / AlphaMissense / ...) and barred
from any certifying run. No synthetic corroboration may launder into a real claim.
"""
from __future__ import annotations

from polymer_grammar import ExecValue, MaterializationContext, OperationNode


class SyntheticCorroboratorAdapter:
    def __init__(self, *, impl: str, value: float, identity: str = "synthetic-corroborator") -> None:
        self.impl = impl
        self.value = value
        self.identity = identity

    def execute(
        self, node: OperationNode, upstream: tuple[ExecValue, ...], ctx: MaterializationContext
    ) -> ExecValue:
        if node.impl != self.impl:
            raise ValueError(f"{self.identity} cannot execute impl {node.impl!r}")
        return ExecValue(value=float(self.value))
