"""Structured cost — passed-in protocol config (like OracleRegistry), never grammar IR.

A per-claim CostVector aggregated to a single positive scalar budget-consumer by
passed-in weights (spec §3.4). The scalar feeds the value-density fill order in SELECT;
the floor keeps that division safe.
"""
from __future__ import annotations

from pydantic import Field

from .base import _Model

COST_FLOOR = 1e-6


class CostVector(_Model):
    wall_latency: float = Field(default=0.0, ge=0.0)
    capital: float = Field(default=0.0, ge=0.0)
    human_hours: float = Field(default=0.0, ge=0.0)
    failure_rate: float = Field(default=0.0, ge=0.0)
    oracle_queue_depth: float = Field(default=0.0, ge=0.0)


class CostWeights(_Model):
    wall_latency: float = 1.0
    capital: float = 1.0
    human_hours: float = 1.0
    failure_rate: float = 1.0
    oracle_queue_depth: float = 1.0


class CostModel(_Model):
    costs: tuple[tuple[str, CostVector], ...] = ()
    default: CostVector = CostVector()

    def resolve(self, claim_id: str) -> CostVector:
        for cid, cv in self.costs:
            if cid == claim_id:
                return cv
        return self.default


def aggregate_cost(vec: CostVector, weights: CostWeights) -> float:
    total = (
        vec.wall_latency * weights.wall_latency
        + vec.capital * weights.capital
        + vec.human_hours * weights.human_hours
        + vec.failure_rate * weights.failure_rate
        + vec.oracle_queue_depth * weights.oracle_queue_depth
    )
    return max(COST_FLOOR, total)
