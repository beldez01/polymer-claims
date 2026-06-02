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


class VariantVRS(_SubjectBase):
    kind: Literal["variant_vrs"] = "variant_vrs"
    vrs_version: str
    assembly: str | None = None
    hgvs: str | None = None

    @model_validator(mode="after")
    def _id_has_vrs_prefix(self) -> "VariantVRS":
        if not (self.id.startswith("ga4gh:VA.") or self.id.startswith("ga4gh:VCL.")):
            raise ValueError(
                f"VariantVRS.id must start with 'ga4gh:VA.' or 'ga4gh:VCL.', got {self.id!r}"
            )
        return self


class S4ObjectRef(_SubjectBase):
    kind: Literal["s4_object"] = "s4_object"
    bioc_class: str
    bioc_version: str
    blob_uri: str
    blob_hash: str
    projection: str | None = None
    dims: tuple[int, ...] | None = None


class GeneOrProteinIdentifiers(_Model):
    hgnc: str | None = None
    ensembl_gene: str | None = None
    ensembl_transcript: str | None = None
    ensembl_protein: str | None = None
    ncbi_gene: int | None = None
    uniprot: str | None = None
    refseq: str | None = None
    symbol: str | None = None


class GeneOrProtein(_SubjectBase):
    kind: Literal["gene_or_protein"] = "gene_or_protein"
    identifiers: GeneOrProteinIdentifiers
    entity_type: Literal["gene", "protein", "transcript", "isoform"]
    assembly_context: str | None = None

    @model_validator(mode="after")
    def _at_least_one_canonical_id(self) -> "GeneOrProtein":
        ids = self.identifiers
        if not (ids.hgnc or ids.ensembl_gene or ids.uniprot):
            raise ValueError(
                "GeneOrProtein.identifiers requires at least one of hgnc, ensembl_gene, uniprot"
            )
        return self
