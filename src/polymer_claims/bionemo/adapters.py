from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from polymer_grammar import DataHandle, ExecValue, MaterializationContext, OperationNode

from .client import NimClient, NimRequest


class BioNeMoNIMAdapter:
    """Execution adapter: resolve a node's DataHandle to a NIM payload, call the NIM, and
    map one numeric response field to an ExecValue. Self-selects on `node.impl` and raises
    otherwise (the evaluator degrades a raise to a node error, never crashes)."""

    def __init__(
        self,
        client: NimClient,
        *,
        impl: str,
        endpoint: str,
        value_path: tuple[str, ...],
        substrate: Mapping[str, dict],
        identity: str = "bionemo-nim",
    ) -> None:
        self.client = client
        self.impl = impl
        self.endpoint = endpoint
        self.value_path = value_path
        self.substrate = substrate
        self.identity = identity

    def execute(
        self, node: OperationNode, upstream: tuple[ExecValue, ...], ctx: MaterializationContext
    ) -> ExecValue:
        if node.impl != self.impl:
            raise ValueError(f"{self.identity} cannot execute impl {node.impl!r}")
        handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
        if handle is None:
            raise ValueError(f"{self.identity} node {node.id!r} has no DataHandle input")
        payload = self.substrate.get(handle.ref)
        if payload is None:
            raise ValueError(f"{self.identity} substrate missing ref {handle.ref!r}")
        resp = self.client.call(NimRequest(endpoint=self.endpoint, payload=dict(payload)))
        cursor: Any = resp.body
        for key in self.value_path:
            cursor = cursor[key]
        return ExecValue(value=float(cursor))
