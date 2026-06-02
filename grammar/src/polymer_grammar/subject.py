"""Polymorphic Subject — what a claim is ABOUT (spec: 2026-06-02-subject-slot-spec.md).

A discriminated union of 10 variant kinds (faithful to the v1.2 SubjectRef), mirroring the
leaf.Leaf sum-type pattern. Adapted to v1.3 discipline: frozen, extra="forbid", and NO dict
fields anywhere (lists→tuples; free-dict escapes → JSON string / tuple-of-pairs / dropped) so
the whole Subject tree is hashable for content-addressing. Imports nothing from polymer_formalclaim.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

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


class PhenopacketRetrieval(_Model):
    mode: Literal["reference", "inline"]
    uri: str | None = None
    hash: str | None = None


class PhenopacketRef(_SubjectBase):
    kind: Literal["phenopacket"] = "phenopacket"
    phenopacket_version: str
    retrieval: PhenopacketRetrieval
    inline_json: str | None = None   # v1.2 inline:dict -> canonical JSON string (hashable)

    @model_validator(mode="after")
    def _retrieval_consistent(self) -> "PhenopacketRef":
        if self.retrieval.mode == "reference" and not self.retrieval.uri:
            raise ValueError("PhenopacketRef.retrieval.mode='reference' requires retrieval.uri")
        if self.retrieval.mode == "inline" and self.inline_json is None:
            raise ValueError("PhenopacketRef.retrieval.mode='inline' requires inline_json")
        return self


class PathwayMembers(_Model):
    retrieval: Literal["reference", "inline"] = "reference"
    uri: str | None = None
    count_hint: int | None = None
    inline: tuple[str, ...] | None = None   # v1.2 list -> tuple


class PathwayRef(_SubjectBase):
    kind: Literal["pathway"] = "pathway"
    source: Literal["Reactome", "KEGG", "WikiPathways", "MSigDB", "other"]
    source_version: str
    members: PathwayMembers | None = None


class CohortSourceDataset(_Model):
    name: str
    version: str | None = None
    tissue: str | None = None
    # v1.2's `extra: dict` escape hatch dropped (unhashable)


class CohortDefinition(_Model):
    source_dataset: CohortSourceDataset | None = None
    inclusion: tuple[str, ...] = ()   # v1.2 SetExpression predicate algebra -> prose strings for now
    exclusion: tuple[str, ...] = ()
    cardinality: int | None = None
    random_seed: int | None = None


class Cohort(_SubjectBase):
    kind: Literal["cohort"] = "cohort"
    definition: CohortDefinition
    members_hash: str


class LiteralSubject(_SubjectBase):
    kind: Literal["literal"] = "literal"
    prose: str
    structured: tuple[tuple[str, str], ...] = ()   # v1.2 extra="allow" dict -> explicit pairs


class CompositeSubject(_SubjectBase):
    kind: Literal["composite"] = "composite"
    parts: tuple["Subject", ...] = Field(min_length=2)
    relation: Literal[
        "co_occurrence", "conditional", "causal_hypothesis",
        "temporal_sequence", "correlational",
    ]


Subject = Annotated[
    Union[
        GenomicRegion,
        VariantVRS,
        S4ObjectRef,
        PhenopacketRef,
        OntologyTerm,
        GeneOrProtein,
        PathwayRef,
        Cohort,
        LiteralSubject,
        CompositeSubject,
    ],
    Field(discriminator="kind"),
]

# CompositeSubject.parts references the Subject union defined above; resolve the forward ref.
CompositeSubject.model_rebuild()
