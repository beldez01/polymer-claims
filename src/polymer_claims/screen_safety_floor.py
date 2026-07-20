"""B3 — expression::absence as the systematic healthy-tissue safety floor over the screen's
candidate genes.

Reuses the shipped `expression::absence` capability (two independent legs: worst-tissue max +
q99; single cohort -> IndependenceTier.REPRODUCED) against the re-paneled `gtex_healthy@1`
contract (B2), which now covers the screen oncogenes. A candidate gene is "safe" (LICENSES the
absence) iff its healthy-tissue expression stays below the ceiling in EVERY GTEx v10 tissue; a
broadly-expressed gene is vetoed by the max leg.

Verified verdicts at the screen's 13 TPM floor: SSX2 (testis-restricted) safe; ACTB/GAPDH
(housekeeping), CD79B (B-cell — the Tier-3 SNV whose WT-gene expression IS the gate), and the
broadly-expressed drivers (TP53/JAK2/PML/SS18) vetoed.

BIOLOGY CALIBRATION (team decision, NOT baked in): the veto is max-over-all-68-GTEx-tissues, so
cancer-testis antigens near the ceiling (e.g. MAGEA4: PENDING@13, safe@50) are ceiling-sensitive.
The production safety ceiling and any immune-privileged-tissue (testis) exemption is a
wet-lab/clinical call — pass `ceiling=` accordingly. Umbrella/impure; NOT re-exported from __init__.
"""
from __future__ import annotations

from polymer_grammar import Claim, FDRLedger, Status
from polymer_protocol import Corpus

from .expression_absence_adapters import expression_absence_claim
from .expression_absence_populate import license_batch, preregister

DEFAULT_REF = "se:gtex_healthy@1"
SCREEN_FLOOR_TPM = 13.0  # the screen's expression floor; the safety ceiling is a calibrated parameter

__all__ = ["DEFAULT_REF", "SCREEN_FLOOR_TPM", "propose_screen_safety_claims", "screen_safety_verdicts"]


def propose_screen_safety_claims(
    genes, *, ceiling: float = SCREEN_FLOOR_TPM, ref: str = DEFAULT_REF
) -> list[Claim]:
    """One expression::absence claim per candidate gene: 'healthy expression stays below ceiling'."""
    return [
        expression_absence_claim(f"safety-{g}", ref=ref, gene=g, ceiling=float(ceiling),
                                 search_cardinality=1)
        for g in genes
    ]


def screen_safety_verdicts(
    genes, *, ceiling: float = SCREEN_FLOOR_TPM, ref: str = DEFAULT_REF
) -> dict[str, bool]:
    """Return ``{gene: is_safe}``. ``is_safe`` == the gene LICENSES its absence (max healthy tissue
    < ceiling across both legs). Genes absent from the contract (not in GTEx v10 by symbol) resolve
    not-safe — the floor never fabricates a safe verdict for a gene it cannot read."""
    claims = propose_screen_safety_claims(genes, ceiling=ceiling, ref=ref)
    corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
    out = license_batch(corpus, claims, ref=ref).by_id()
    return {g: (out[f"safety-{g}"].status is Status.LICENSED) for g in genes}
