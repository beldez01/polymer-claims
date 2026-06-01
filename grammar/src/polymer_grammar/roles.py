"""Typed causal role slots (spec §1; unified spec §3.1).

A claim's variables are tagged with their causal role. The adjustment set is DERIVED
from the roles (= the confounders), never authored: you adjust for confounders, never
for mediators (blocks the effect — the Table-2 fallacy) or colliders (opens a spurious
path). Pearl's causal-hierarchy discipline in minimal form. Roles bind plain variable
names; ontology-backed subjects are a separate later concern.
"""
from __future__ import annotations

from enum import Enum

from pydantic import model_validator

from .base import _Model


class Role(str, Enum):
    PREDICTOR = "predictor"
    OUTCOME = "outcome"
    CONFOUNDER = "confounder"
    MEDIATOR = "mediator"
    COLLIDER = "collider"
    INSTRUMENT = "instrument"


class CausalRoles(_Model):
    predictor: str
    outcome: str
    confounders: tuple[str, ...] = ()
    mediators: tuple[str, ...] = ()
    colliders: tuple[str, ...] = ()
    instruments: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _predictor_outcome_distinct(self) -> "CausalRoles":
        if self.predictor == self.outcome:
            raise ValueError("predictor and outcome must be distinct variables")
        return self

    @model_validator(mode="after")
    def _each_variable_has_one_role(self) -> "CausalRoles":
        assignments = [self.predictor, self.outcome, *self.confounders,
                       *self.mediators, *self.colliders, *self.instruments]
        seen: set[str] = set()
        dupes: set[str] = set()
        for v in assignments:
            if v in seen:
                dupes.add(v)
            seen.add(v)
        if dupes:
            raise ValueError(
                f"each variable may hold at most one causal role; "
                f"multiply-assigned: {sorted(dupes)}"
            )
        return self

    @property
    def adjustment_set(self) -> frozenset[str]:
        """Derived minimal sufficient adjustment set = the confounders. Mediators,
        colliders, and instruments are excluded by construction (no authoring path)."""
        return frozenset(self.confounders)
