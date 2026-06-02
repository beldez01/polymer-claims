"""Polymorphic Subject — what a claim is ABOUT (spec: 2026-06-02-subject-slot-spec.md).

A discriminated union of 10 variant kinds (faithful to the v1.2 SubjectRef), mirroring the
leaf.Leaf sum-type pattern. Adapted to v1.3 discipline: frozen, extra="forbid", and NO dict
fields anywhere (lists→tuples; free-dict escapes → JSON string / tuple-of-pairs / dropped) so
the whole Subject tree is hashable for content-addressing. Imports nothing from polymer_formalclaim.
"""
from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from .base import _Model


class _SubjectBase(_Model):
    """Fields every subject variant carries."""
    id: str
    display: str
    note: str | None = None


class GenomicRegion(_SubjectBase):
    kind: Literal["genomic_region"] = "genomic_region"
    assembly: str
    chrom: str
    start: int
    end: int
    strand: Literal["+", "-", "."] = "."

    @model_validator(mode="after")
    def _start_le_end(self) -> "GenomicRegion":
        if self.start > self.end:
            raise ValueError(f"GenomicRegion start ({self.start}) > end ({self.end})")
        return self


class OntologyTerm(_SubjectBase):
    kind: Literal["ontology_term"] = "ontology_term"
    ontology: Literal[
        "HPO", "MONDO", "GO", "EFO", "UBERON", "CL", "CHEBI", "PR",
        "DOID", "NCIT", "SO", "ECO", "other",
    ]
    ontology_release: str
    uri: str
    propagation: Literal[
        "self_only", "self_or_descendant", "self_or_ancestor", "exact_match"
    ] = "self_only"
