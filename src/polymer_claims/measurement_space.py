"""Measurement-space registry (B1) — one catalog, two consumers.

A measurement space is a ``(contract_uid, row_prefix)`` pair: the unit a claim's plan can point at
(e.g. ``gdsc_pharmaco@1``/``meth`` gene-body methylation vs ``gdsc_pharmaco_promoter@1``/``meth``
promoter methylation are two spaces over the same cell lines). This module is the curated catalog of
those spaces plus the measurement-theoretic metadata (Stevens scale-type + admissible-transformation
/ invariance group) that lives nowhere else in the codebase — contracts carry none of it.

Two consumers (spec 2026-07-14-measurement-space-registry-design.md):
  * the accumulating store reads it as the coverage census ("which spaces does a subject have"),
  * the re-parameterization evaluator reads it to ground an LLM's mechanistic proposal against the
    spaces that actually have data (``resolve_space`` / ``available_spaces``).

Umbrella-side only; grammar/protocol untouched; ``Corpus`` stays 4. v1 is a plain catalog — entries
are content-stable (``space_id``) so they can later be promoted to attackable meta-claims (deferred).
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from polymer_claims.contracts import load_contract, using_contract_root


class ScaleType(Enum):
    """Stevens measurement scale — the level of measurement the space's values live at."""

    RATIO = "ratio"
    INTERVAL = "interval"
    ORDINAL = "ordinal"
    NOMINAL = "nominal"


class Modality(Enum):
    """Controlled modality vocabulary for contract-backed measurement spaces.

    Unifies the ad-hoc strings hard-coded across the arm collectors
    (``methylation_genebody`` / ``methylation_promoter`` / plain ``methylation`` / ...).
    """

    METHYLATION_GENEBODY = "methylation_genebody"
    METHYLATION_PROMOTER = "methylation_promoter"
    METHYLATION_CPG = "methylation_cpg"
    EXPRESSION_TPM = "expression_tpm"
    DRUG_RESPONSE_AUC = "drug_response_auc"


@dataclass(frozen=True)
class MeasurementSpace:
    """One catalogued measurement space: a contract row-prefix + its measurement metadata."""

    contract_uid: str          # "gdsc_pharmaco@1" — no se: scheme prefix (matches SEContractRef)
    row_prefix: str            # "meth" | "auc" | "expr" | "cg"
    modality: Modality
    scale_type: ScaleType
    invariance_group: str      # admissible-transformation group (aligned w/ Pattern conventions)
    assay: str                 # the contract's assay name ("value" | "tpm" | "beta")
    units: str | None = None   # UCUM where meaningful; None for dimensionless / relative
    genome_assembly: str | None = None
    description: str = ""

    @property
    def space_id(self) -> str:
        """Stable identity ``"<contract_uid>::<row_prefix>"``."""
        return f"{self.contract_uid}::{self.row_prefix}"


# --- The v1 catalog: the real contracts on disk (spec §2.2). Extend as contracts land. ---------

_BETA_INV = "bounded_beta_normalization"          # methylation β ∈ [0,1]
_EXPR_INV = "monotone_expression_rescaling"       # matches expression_floor_patterns.py
_AUC_INV = "monotone_dose_response_rescaling"     # drug-response area-under-curve


def _expr_space(uid: str, desc: str) -> MeasurementSpace:
    return MeasurementSpace(
        contract_uid=uid, row_prefix="expr", modality=Modality.EXPRESSION_TPM,
        scale_type=ScaleType.RATIO, invariance_group=_EXPR_INV, assay="tpm",
        genome_assembly="hg38", description=desc,
    )


_CATALOG: tuple[MeasurementSpace, ...] = (
    MeasurementSpace(
        contract_uid="gdsc_pharmaco@1", row_prefix="meth",
        modality=Modality.METHYLATION_GENEBODY, scale_type=ScaleType.RATIO,
        invariance_group=_BETA_INV, assay="value", genome_assembly="hg38",
        description="GDSC gene-body-averaged methylation β per gene.",
    ),
    MeasurementSpace(
        contract_uid="gdsc_pharmaco@1", row_prefix="auc",
        modality=Modality.DRUG_RESPONSE_AUC, scale_type=ScaleType.RATIO,
        invariance_group=_AUC_INV, assay="value", genome_assembly="hg38",
        description="GDSC drug-response area-under-curve per drug.",
    ),
    MeasurementSpace(
        contract_uid="gdsc_pharmaco_promoter@1", row_prefix="meth",
        modality=Modality.METHYLATION_PROMOTER, scale_type=ScaleType.RATIO,
        invariance_group=_BETA_INV, assay="value", genome_assembly="hg38",
        description="GDSC promoter-region methylation β per gene (2nd measurement space).",
    ),
    MeasurementSpace(
        contract_uid="gdsc_pharmaco_promoter@1", row_prefix="auc",
        modality=Modality.DRUG_RESPONSE_AUC, scale_type=ScaleType.RATIO,
        invariance_group=_AUC_INV, assay="value", genome_assembly="hg38",
        description="GDSC drug-response AUC (same as gene-body contract; carried for completeness).",
    ),
    _expr_space("tcga_laml_fusion_expr@1", "TCGA-LAML fusion-panel RNA-seq TPM."),
    _expr_space("target_aml_fusion_expr@1", "TARGET-AML fusion-panel RNA-seq TPM."),
    _expr_space("tcga_laml_cbf_expr@1", "TCGA-LAML CBF-fusion-panel RNA-seq TPM."),
    _expr_space("target_aml_cbf_expr@1", "TARGET-AML CBF-fusion-panel RNA-seq TPM."),
    _expr_space("gtex_healthy@1", "GTEx v10 healthy-tissue median TPM (Ch2 on-target/off-tumor "
                "safety atlas; per-tissue columns, panel built on demand via ingest.gtex_healthy)."),
    MeasurementSpace(
        contract_uid="tcga_laml_idh@2", row_prefix="cg",
        modality=Modality.METHYLATION_CPG, scale_type=ScaleType.RATIO,
        invariance_group=_BETA_INV, assay="beta", genome_assembly="hg38",
        description="TCGA-LAML HM450 per-CpG methylation β.",
    ),
)

_BY_ID: Mapping[str, MeasurementSpace] = {s.space_id: s for s in _CATALOG}


# --- Query API (spec §3) ----------------------------------------------------------------------

def all_spaces() -> tuple[MeasurementSpace, ...]:
    """The whole catalog, deterministically sorted by ``space_id``."""
    return tuple(sorted(_CATALOG, key=lambda s: s.space_id))


def get_space(space_id: str) -> MeasurementSpace | None:
    return _BY_ID.get(space_id)


def spaces_for_modality(modality: Modality) -> tuple[MeasurementSpace, ...]:
    return tuple(s for s in all_spaces() if s.modality is modality)


def spaces_for_contract(contract_uid: str) -> tuple[MeasurementSpace, ...]:
    return tuple(s for s in all_spaces() if s.contract_uid == contract_uid)


def _is_available(space: MeasurementSpace) -> bool:
    """True iff the space's contract actually resolves (manifest + betas present) under the
    current contract root — i.e. the data exists. Never raises."""
    try:
        load_contract(space.contract_uid)
    except FileNotFoundError:
        return False
    return True


def available_spaces(root=None) -> tuple[MeasurementSpace, ...]:
    """Catalog spaces whose contract resolves — the de Bruijn grounding to real data.

    ``root`` (optional) scopes contract resolution via ``using_contract_root``; unset uses the
    ambient contract root (bundled dir by default).
    """
    if root is not None:
        with using_contract_root(root):
            return tuple(s for s in all_spaces() if _is_available(s))
    return tuple(s for s in all_spaces() if _is_available(s))


def resolve_space(
    modality: Modality,
    *,
    exclude_space_id: str | None = None,
    root=None,
) -> MeasurementSpace | None:
    """The evaluator's grounding step: return one *available* space of ``modality`` (excluding
    ``exclude_space_id``), or ``None``. Never fabricates a space with no data behind it. When
    several match, returns the first by sorted ``space_id`` (deterministic)."""
    for s in available_spaces(root=root):
        if s.modality is modality and s.space_id != exclude_space_id:
            return s
    return None


def coverage() -> Mapping[tuple[Modality, ScaleType], tuple[str, ...]]:
    """Catalog grouped by ``(modality, scale_type)`` — the store's coverage census (plain report,
    no meta-claims). Mirrors ``pattern.registry.coverage()``."""
    out: dict[tuple[Modality, ScaleType], list[str]] = defaultdict(list)
    for s in all_spaces():
        out[(s.modality, s.scale_type)].append(s.space_id)
    return {k: tuple(v) for k, v in out.items()}
