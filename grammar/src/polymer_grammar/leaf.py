"""L0 — the sum-typed empirical anchor (spec §3.3).

Only a Fundamental quantity (one backed by a representation theorem) may assert a
UCUM unit + meaningfulness class. Derived statistics carry their generating formula,
never a false unit. Categorical leaves carry an ontology term instead of a unit;
Existence leaves distinguish a genuine measured absence (not_detected, below
detection_limit) from a positive observation; untestedness is represented at the
status layer, not here. Proposition leaves give qualitative/mechanistic claims a
Toulmin-warrant home.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import Field, model_serializer, model_validator

from .base import _Model
from .units import Dimension


class MeasurementBasis(str, Enum):
    FUNDAMENTAL = "fundamental"
    DERIVED = "derived"
    CONVENTIONAL = "conventional"
    ORDINAL = "ordinal"
    NOMINAL = "nominal"


class MeasurementContext(_Model):
    """The context a measurement holds in — descriptive only (spec Phase-2a / GAP-2).

    Conditions interpretation (a derived statistic like ADAR ~277-fold is cell-line-specific;
    an expression TPM is tissue-specific), so two claims of the same estimand in different
    contexts are distinguishable. It carries NO value and NO unit and never enters a licensing
    criterion. All fields optional, but an all-None context is meaningless and is REJECTED at
    construction — use `context=None` on the leaf for "no context" (the single representation).
    """
    tissue: str | None = None      # e.g. "AML" / "bone marrow"
    cell_line: str | None = None   # e.g. the ADAR reporter line
    assay: str | None = None       # e.g. "RNA-seq TPM", "luciferase ratio"
    condition: str | None = None   # free-form residual (temperature, timepoint)

    @model_validator(mode="after")
    def _at_least_one_field(self) -> MeasurementContext:
        if not any((self.tissue, self.cell_line, self.assay, self.condition)):
            raise ValueError(
                "MeasurementContext must set at least one field; use context=None for no context"
            )
        return self


class QuantityLeaf(_Model):
    kind: Literal["quantity"] = "quantity"
    value: float
    unit: str | None = None
    uncertainty: float | None = None
    measurement_basis: MeasurementBasis
    formula: str | None = None
    dimension: Dimension | None = None
    context: MeasurementContext | None = None
    low: float | None = None
    high: float | None = None

    @model_serializer(mode="wrap")
    def _serialize(self, handler) -> dict:
        """Drop optional None-valued fields so a leaf without them serializes byte-identically to
        the pre-field grammar (no new key). Mirrors the additive-field pattern in capability.py."""
        data = handler(self)
        for key in ("context", "low", "high"):
            if data.get(key) is None:
                data.pop(key, None)
        return data

    @model_validator(mode="after")
    def _basis_discipline(self) -> QuantityLeaf:
        if self.measurement_basis == MeasurementBasis.FUNDAMENTAL:
            return self
        if self.unit is not None:
            raise ValueError(
                f"unit is only meaningful for FUNDAMENTAL quantities; "
                f"got unit={self.unit!r} with basis={self.measurement_basis.value}"
            )
        if self.measurement_basis == MeasurementBasis.DERIVED and not self.formula:
            raise ValueError("DERIVED quantity must carry its generating `formula`")
        return self

    @model_validator(mode="after")
    def _bound_discipline(self) -> "QuantityLeaf":
        lo, hi = self.low, self.high
        if lo is None and hi is None:
            return self
        if lo is not None and hi is not None and not lo < hi:
            raise ValueError(f"interval requires low < high; got low={lo}, high={hi}")
        if lo is not None and self.value < lo:
            raise ValueError(f"value {self.value} is below low bound {lo}")
        if hi is not None and self.value > hi:
            raise ValueError(f"value {self.value} is above high bound {hi}")
        if self.uncertainty is not None:
            raise ValueError(
                "uncertainty and explicit bounds are two spread encodings; set only one"
            )
        return self


class CategoricalLeaf(_Model):
    kind: Literal["categorical"] = "categorical"
    ontology_term: str
    assay: str | None = None


class ExistenceLeaf(_Model):
    kind: Literal["existence"] = "existence"
    state: Literal["observed", "not_detected"]
    detection_limit: float | None = None


class PropositionLeaf(_Model):
    kind: Literal["proposition"] = "proposition"
    data: str
    warrant: str
    backing: str | None = None
    qualifier: str | None = None
    rebuttal: str | None = None
    warrant_type: Literal[
        "deductive",
        "mechanistic_analogy",
        "assay_incommensurability",
        "expert_judgment",
    ] = "mechanistic_analogy"


Leaf = Annotated[
    Union[QuantityLeaf, CategoricalLeaf, ExistenceLeaf, PropositionLeaf],
    Field(discriminator="kind"),
]
