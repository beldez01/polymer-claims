"""Pydantic models for the Formal Claim IR (schema v1.2).

This module is the canonical definition of the IR; the published JSON-Schema
contract is generated/kept in sync at corpus/schema/formal_claim_v1.2.schema.json.
v1.2 adds:

- polymorphic `subject` slot (9 kinds + composite), discriminated on `kind`
- `domain` discriminator with per-domain legal subject kinds + context envelope
- `context` envelope (free-form dict; per-domain required keys enforced by validator)

v1.2 is additive: v1.1 fixtures continue to load (schema_version accepts both
``v1.1`` and ``v1.2``). A v1.2 claim must set `domain` and `subject`; a v1.1
claim may omit them.

Recursive types (SetExpression, InferenceExpression) use forward references
resolved via model_rebuild() at the end of the module.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "v1.2"
SCHEMA_VERSIONS_SUPPORTED = ("v1.1", "v1.2")


# ---------------------------------------------------------------------------
# Shared enums / literal types
# ---------------------------------------------------------------------------

ProvenanceState = Literal[
    # v1.1 names (kept for back-compat).
    "fly_postgres",
    "local_rds",
    "remote_url",
    "reference_genome",
    "unknown",
    # v1.2 generalizations (per MASTER_PLAN §5.4 / swarm/C §6.1):
    #   fly_postgres      → canonical_db      (any curated canonical Postgres)
    #   local_rds         → local_file        (any non-materializable local artifact)
    #   reference_genome  → reference_resource (any external reference)
    "canonical_db",
    "local_file",
    "reference_resource",
]

EvidenceClass = Literal["M", "R", "D", "S", "K", "H", "L"]

Outcome = Literal[
    "strong_positive",
    "positive",
    "qualified_positive",
    "negative",
    "fail",
]


# ---------------------------------------------------------------------------
# Shared value types
# ---------------------------------------------------------------------------


class _Model(BaseModel):
    """Project base: forbid extras so typos in fixtures fail loudly."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class LayerRef(_Model):
    """A versioned reference to a named layer.

    v1.1: adds `provenance_state` so claims citing not-yet-ingested data
    (e.g., local RDS) are explicit rather than hiding the fact in `note`.
    """

    layer: str
    version: str
    provenance_state: ProvenanceState = "unknown"
    note: str | None = None


class DataDerivedConstant(_Model):
    """A scalar that is computed at evaluation time from a named operation's output.

    Lets thresholds like `quantile(co_rate_avg, 0.75)` stay first-class —
    hashable and recomputable — instead of being embedded as opaque strings
    inside `cmp.rhs`.
    """

    kind: Literal["derived"] = "derived"
    source_operation: str
    fn: Literal["quantile", "mean", "median", "sd", "min", "max", "count"]
    col: str
    params: dict | None = None


class FeatureSet(_Model):
    """Named column subset consumed by an estimator.

    Lets dynamic sets ("all biophysics minus gc_content") be hashable and
    audit-able. `resolved` is populated by evaluate.py from the premise schema.
    """

    label: str
    select: list[str] | None = None
    exclude: list[str] | None = None
    parent: str | None = None
    resolved: list[str] | None = None


# ---------------------------------------------------------------------------
# SetExpression — recursive, discriminated on `kind`
# ---------------------------------------------------------------------------

# cmp.rhs is a union of JSON-native scalars/arrays plus DataDerivedConstant.
CmpRhs = Union[
    int,
    float,
    bool,
    str,
    list[int],
    list[float],
    list[str],
    list[bool],
    DataDerivedConstant,
]


class AndExpr(_Model):
    kind: Literal["and"] = "and"
    terms: list["SetExpression"]


class OrExpr(_Model):
    kind: Literal["or"] = "or"
    terms: list["SetExpression"]


class NotExpr(_Model):
    kind: Literal["not"] = "not"
    term: "SetExpression"


class CmpExpr(_Model):
    kind: Literal["cmp"] = "cmp"
    col: str
    op: Literal["=", "!=", "<", "<=", ">", ">=", "in", "overlaps"]
    rhs: CmpRhs


class JoinExpr(_Model):
    kind: Literal["join"] = "join"
    on: str
    other: LayerRef
    where: "SetExpression | None" = None


SetExpression = Annotated[
    Union[AndExpr, OrExpr, NotExpr, CmpExpr, JoinExpr],
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# Premise
# ---------------------------------------------------------------------------


class Premise(_Model):
    id: str
    source: LayerRef
    predicate: SetExpression
    cardinality: int | None = None
    content_hash: str
    note: str | None = None


# ---------------------------------------------------------------------------
# Operation — discriminated on `kind`
# ---------------------------------------------------------------------------


class Agg(_Model):
    col: str
    fn: Literal["mean", "median", "sum", "count", "min", "max", "sd"]
    na_rm: bool = True


# CV schemes
class CVKFoldByChromosome(_Model):
    kind: Literal["k_fold_by_chromosome"] = "k_fold_by_chromosome"
    k: int
    seed: int


class CVKFoldRandom(_Model):
    kind: Literal["k_fold_random"] = "k_fold_random"
    k: int
    seed: int


class CVLeaveOneOut(_Model):
    kind: Literal["leave_one_out"] = "leave_one_out"


class CVStratifiedKFold(_Model):
    kind: Literal["stratified_k_fold"] = "stratified_k_fold"
    k: int
    by: str
    seed: int


CVScheme = Annotated[
    Union[CVKFoldByChromosome, CVKFoldRandom, CVLeaveOneOut, CVStratifiedKFold],
    Field(discriminator="kind"),
]


class EstimatorSpec(_Model):
    """A pinned, version-locked estimator implementation.

    `impl` uses namespace-prefixed conventions:
      - Python: "scipy.stats.spearmanr"       (implicit Python namespace)
      - Python explicit: "python::sklearn.ensemble.RandomForestClassifier"
      - R:      "R::ranger::ranger"
    """

    name: str
    impl: str
    version: str
    response: str | None = None
    features: FeatureSet | None = None
    params: dict = Field(default_factory=dict)


class NullModelSpec(_Model):
    kind: Literal["label_shuffle", "circular_shift", "parametric", "block_bootstrap"]
    n_perms: int | None = None
    seed: int | None = None
    params: dict = Field(default_factory=dict)


# Operation variants


class FilterOp(_Model):
    id: str
    kind: Literal["filter"] = "filter"
    inputs: list[str] = Field(min_length=1, max_length=1)
    predicate: SetExpression
    note: str | None = None


class ProjectOp(_Model):
    id: str
    kind: Literal["project"] = "project"
    inputs: list[str] = Field(min_length=1, max_length=1)
    cols: list[str]
    note: str | None = None


class JoinOp(_Model):
    id: str
    kind: Literal["join"] = "join"
    inputs: list[str] = Field(min_length=2, max_length=2)
    on: str
    note: str | None = None


class AggregateOp(_Model):
    id: str
    kind: Literal["aggregate"] = "aggregate"
    inputs: list[str] = Field(min_length=1, max_length=1)
    by: list[str]
    agg: list[Agg]
    note: str | None = None


class CVSplitOp(_Model):
    id: str
    kind: Literal["cv_split"] = "cv_split"
    inputs: list[str] = Field(min_length=1, max_length=1)
    scheme: CVScheme
    note: str | None = None


class EstimatorOp(_Model):
    id: str
    kind: Literal["estimator"] = "estimator"
    inputs: list[str] = Field(min_length=1)
    estimator: EstimatorSpec
    note: str | None = None


class NullModelOp(_Model):
    id: str
    kind: Literal["null_model"] = "null_model"
    inputs: list[str] = Field(min_length=1)
    spec: NullModelSpec
    note: str | None = None


class CorrectOp(_Model):
    id: str
    kind: Literal["correct"] = "correct"
    inputs: list[str] = Field(min_length=1, max_length=1)
    method: Literal["bh", "bonf", "perm", "knockoff"]
    note: str | None = None


Operation = Annotated[
    Union[
        FilterOp,
        ProjectOp,
        JoinOp,
        AggregateOp,
        CVSplitOp,
        EstimatorOp,
        NullModelOp,
        CorrectOp,
    ],
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# Statistic
# ---------------------------------------------------------------------------


class LabeledValue(_Model):
    label: str
    value: float


StatValue = Union[
    float,
    int,
    str,
    list[float],
    list[int],
    list[str],
    list[LabeledValue],
]


class Statistic(_Model):
    id: str
    produced_by: str
    name: str
    value: StatValue
    ci: tuple[float, float] | None = None
    n: int | None = None
    evidence_class: EvidenceClass
    note: str | None = None


# ---------------------------------------------------------------------------
# Inference rule — recursive, discriminated on `kind`
# ---------------------------------------------------------------------------


class StatRef(_Model):
    stat_id: str
    transform: Literal["abs", "neg", "log"] | None = None


class InferenceAnd(_Model):
    kind: Literal["and"] = "and"
    terms: list["InferenceExpression"]


class InferenceOr(_Model):
    kind: Literal["or"] = "or"
    terms: list["InferenceExpression"]


class InferenceNot(_Model):
    kind: Literal["not"] = "not"
    term: "InferenceExpression"


class InferenceCmp(_Model):
    kind: Literal["cmp"] = "cmp"
    lhs: StatRef
    op: Literal["<", "<=", "=", "!=", ">", ">="]
    rhs: Union[float, int, StatRef]


InferenceExpression = Annotated[
    Union[InferenceAnd, InferenceOr, InferenceNot, InferenceCmp],
    Field(discriminator="kind"),
]


class InferenceRule(_Model):
    expression: InferenceExpression
    justification: str
    failure_mode: str | None = None


# ---------------------------------------------------------------------------
# Conclusion
# ---------------------------------------------------------------------------


class ScopeBlock(_Model):
    layers: list[LayerRef]
    restrictions: SetExpression | None = None
    scale_note: str | None = None


class Confidence(_Model):
    type: Literal["frequentist", "bayesian", "proof"]
    value: float | None = None
    note: str | None = None


class CompositeConfidence(_Model):
    procedure: Literal[
        "bootstrap", "permutation", "bayesian_posterior", "proof_certificate"
    ]
    impl: str
    n_resamples: int | None = None
    seed: int | None = None
    interval: tuple[float, float] | None = None
    prob_inference_holds: float | None = None
    note: str | None = None


class Conclusion(_Model):
    assertion: str
    formal: SetExpression | None = None
    scope: ScopeBlock
    confidence: Confidence
    composite_confidence: CompositeConfidence | None = None
    outcome: Outcome


# ---------------------------------------------------------------------------
# External assumptions + audits
# ---------------------------------------------------------------------------


class Audit(_Model):
    auditor: str
    verdict: Literal["endorse", "contest", "revise_confidence", "defer"]
    revised_confidence: float | None = None
    rationale: str
    timestamp: str


class ExternalAssumption(_Model):
    statement: str
    kind: Literal[
        "literature", "mechanistic", "design_choice", "training_data_not_in_api"
    ]
    citation: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    audits: list[Audit] | None = None


# ---------------------------------------------------------------------------
# v1.2 additions: Domain + polymorphic SubjectRef
# ---------------------------------------------------------------------------

Domain = Literal[
    "genomic",
    "transcriptomic",
    "single_cell",
    "clinical",
    "multi_modal",
    "other",
]


class _SubjectBase(_Model):
    """Common fields every subject variant carries."""

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
            raise ValueError(
                f"GenomicRegion start ({self.start}) > end ({self.end})"
            )
        return self


class VariantVRS(_SubjectBase):
    kind: Literal["variant_vrs"] = "variant_vrs"
    vrs_version: str
    assembly: str | None = None
    hgvs: str | None = None
    canonical_allele: dict | None = None

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
    dims: list[int] | None = None


class PhenopacketRetrieval(_Model):
    mode: Literal["reference", "inline"]
    uri: str | None = None
    hash: str | None = None


class PhenopacketRef(_SubjectBase):
    kind: Literal["phenopacket"] = "phenopacket"
    phenopacket_version: str
    retrieval: PhenopacketRetrieval
    inline: dict | None = None

    @model_validator(mode="after")
    def _reference_mode_has_uri(self) -> "PhenopacketRef":
        if self.retrieval.mode == "reference" and not self.retrieval.uri:
            raise ValueError("PhenopacketRef.retrieval.mode='reference' requires uri")
        if self.retrieval.mode == "inline" and self.inline is None:
            raise ValueError("PhenopacketRef.retrieval.mode='inline' requires inline payload")
        return self


class OntologyTerm(_SubjectBase):
    kind: Literal["ontology_term"] = "ontology_term"
    ontology: Literal[
        "HPO", "MONDO", "GO", "EFO", "UBERON", "CL", "CHEBI", "PR",
        "DOID", "NCIT", "SO", "ECO", "other",
    ]
    ontology_release: str  # ISO date
    uri: str
    propagation: Literal[
        "self_only", "self_or_descendant", "self_or_ancestor", "exact_match"
    ] = "self_only"


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


class PathwayMembers(_Model):
    retrieval: Literal["reference", "inline"] = "reference"
    uri: str | None = None
    count_hint: int | None = None
    inline: list[str] | None = None


class PathwayRef(_SubjectBase):
    kind: Literal["pathway"] = "pathway"
    source: Literal["Reactome", "KEGG", "WikiPathways", "MSigDB", "other"]
    source_version: str
    members: PathwayMembers | None = None


class CohortSourceDataset(_Model):
    name: str
    version: str | None = None
    tissue: str | None = None
    extra: dict | None = None


class CohortDefinition(_Model):
    source_dataset: CohortSourceDataset | None = None
    inclusion: list["SetExpression"] = Field(default_factory=list)
    exclusion: list["SetExpression"] = Field(default_factory=list)
    cardinality: int | None = None
    random_seed: int | None = None


class Cohort(_SubjectBase):
    kind: Literal["cohort"] = "cohort"
    definition: CohortDefinition
    members_hash: str


class LiteralSubjectStructured(_Model):
    model_config = ConfigDict(extra="allow")  # intentional escape hatch


class LiteralSubject(_SubjectBase):
    kind: Literal["literal"] = "literal"
    prose: str
    structured: LiteralSubjectStructured | None = None


class CompositeSubject(_SubjectBase):
    kind: Literal["composite"] = "composite"
    parts: list["SubjectRef"] = Field(min_length=2)
    relation: Literal[
        "co_occurrence",
        "conditional",
        "causal_hypothesis",
        "temporal_sequence",
        "correlational",
    ]


SubjectRef = Annotated[
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

# Per-domain legal subject kinds (v1.2 §3.2).
_DOMAIN_LEGAL_SUBJECTS: dict[str, frozenset[str]] = {
    "genomic": frozenset(
        {"genomic_region", "variant_vrs", "gene_or_protein", "cohort", "literal"}
    ),
    "transcriptomic": frozenset(
        {"gene_or_protein", "s4_object", "cohort", "pathway", "literal"}
    ),
    "single_cell": frozenset(
        {"s4_object", "cohort", "gene_or_protein", "ontology_term", "literal"}
    ),
    "clinical": frozenset(
        {"phenopacket", "ontology_term", "cohort", "literal"}
    ),
    "multi_modal": frozenset({"composite"}),
    "other": frozenset(
        {"literal", "gene_or_protein", "pathway", "ontology_term"}
    ),
}


# ---------------------------------------------------------------------------
# Root: FormalClaim
# ---------------------------------------------------------------------------


class FormalClaim(_Model):
    # JSON-Schema pointer (optional, used by editors)
    schema_ref: str | None = Field(default=None, alias="$schema")

    # Default stays at "v1.1" until all 47 fixtures are migrated; v1.2 is
    # opt-in by explicitly setting `schema_version="v1.2"`, which then enforces
    # the `domain` + `subject` requirement below.
    schema_version: Literal["v1.1", "v1.2"] = "v1.1"

    id: str
    exp_number: int | None = None
    title: str
    posted_at: str
    api_version: str
    data_version: str
    version: str

    # v1.2 additions — required when schema_version == "v1.2", optional on v1.1.
    domain: Domain | None = None
    subject: SubjectRef | None = None
    context: dict | None = None

    premises: list[Premise]
    operations: list[Operation]
    statistics: list[Statistic]
    inference: InferenceRule
    conclusion: Conclusion

    depends_on: list[str] = Field(default_factory=list)
    external_assumptions: list[ExternalAssumption] = Field(default_factory=list)
    notebook: str | None = None

    @model_validator(mode="after")
    def _v12_requires_subject_and_domain(self) -> "FormalClaim":
        if self.schema_version == "v1.2":
            if self.domain is None:
                raise ValueError(
                    "schema_version='v1.2' requires a `domain` discriminator"
                )
            if self.subject is None:
                raise ValueError(
                    "schema_version='v1.2' requires a `subject` reference"
                )
        return self

    @model_validator(mode="after")
    def _domain_subject_compat(self) -> "FormalClaim":
        if self.domain is not None and self.subject is not None:
            legal = _DOMAIN_LEGAL_SUBJECTS.get(self.domain, frozenset())
            # subject.kind is the discriminator; pydantic guarantees it exists.
            kind = self.subject.kind  # type: ignore[union-attr]
            if kind not in legal:
                raise ValueError(
                    f"domain={self.domain!r} does not permit subject.kind={kind!r}; "
                    f"legal kinds: {sorted(legal)}"
                )
        return self


# ---------------------------------------------------------------------------
# Resolve forward refs
# ---------------------------------------------------------------------------

AndExpr.model_rebuild()
OrExpr.model_rebuild()
NotExpr.model_rebuild()
JoinExpr.model_rebuild()
InferenceAnd.model_rebuild()
InferenceOr.model_rebuild()
InferenceNot.model_rebuild()
Premise.model_rebuild()
FilterOp.model_rebuild()
ProjectOp.model_rebuild()
AggregateOp.model_rebuild()
CVSplitOp.model_rebuild()
EstimatorOp.model_rebuild()
NullModelOp.model_rebuild()
Conclusion.model_rebuild()
# v1.2 subject-slot forward refs
CohortDefinition.model_rebuild()
Cohort.model_rebuild()
CompositeSubject.model_rebuild()
FormalClaim.model_rebuild()
