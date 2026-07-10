"""Task 5 — batch immuno/ERV methylation licensing driver.

Pre-registers the whole locus panel (fixed panel order → shrinking e-LOND α slots),
extracts per-sample region betas in a single atlas pass (Task 4b), builds one
content-addressed SE-Contract per locus (Task 3), and drives each locus through the real
gate (`run_cycle`) under ONE shrinking e-LOND FDR budget with the genuinely-independent
region-Δβ leg pair (parametric group mean-difference vs Hodges–Lehmann location shift).

A locus LICENSES only when BOTH legs independently clear its pre-registered τ on the
per-locus content-addressed contract; a wrong-signed / under-powered locus stays PENDING.

Data seam: `build_contract` writes a `<locus>.json` + `<locus>.betas.tsv` SE-Contract read
by `load_contract` (the `methyl_adapters` path), NOT the CSV `load_dataset` path of
`exec_adapters.mean_diff_claim`. Resolution is scoped to `contracts_dir` via
`using_contract_root`. Umbrella/impure (atlas + contract I/O); grammar + protocol untouched.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from polymer_grammar import Comparator, FDRLedger, MaterializationContext, Status, register_test
from polymer_grammar.commitment import commitment_hash
from polymer_protocol import Corpus, run_cycle

from .analysis_profile import profile_oracle_registry
from .capabilities import CAPABILITY_CELLS
from .contracts import clear_contract_cache, using_contract_root
from .evidence import evidence_map
from .ingest.build_loyfer_contract import build_contract
from .ingest.loyfer_wgbs import extract_regions_multi
from .methyl_adapters import (
    RegionHodgesLehmannAdapter,
    RegionMeanDiffAdapter,
    methyl_independent_registry,
    region_delta_beta_claim,
)
from .panels import load_panel
from .profiles import CANONICAL_EPICV2_V1

_ADAPTERS = (RegionMeanDiffAdapter(), RegionHodgesLehmannAdapter())
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="loyfer_2023@1")

_CMP = {
    "GT": Comparator.GT, "GE": Comparator.GE,
    "LT": Comparator.LT, "LE": Comparator.LE,
    "EQ": Comparator.EQ, "NE": Comparator.NE,
}


@dataclass
class RipResult:
    verdicts: dict[str, str]  # locus_id -> "LICENSED" | "REJECTED" | "PENDING"
    corpus: object


def _verdict(status) -> str:
    """Map the three real gate outcomes distinctly (do NOT collapse REJECTED into PENDING)."""
    if status == Status.LICENSED:
        return "LICENSED"
    if status == Status.REJECTED:
        return "REJECTED"
    return "PENDING"


def run(panel_path, bed_dir, manifest, contracts_dir, *, target_fdr: float = 0.05) -> RipResult:
    """Drive the full panel through the pre-registered, FDR-budgeted licensing gate.

    Returns a `RipResult` with a `locus_id -> LICENSED|PENDING` verdict per locus and the
    settled corpus. The panel is registered in FIXED FILE ORDER so the e-LOND budget shrinks
    monotonically down the panel (test t gets α_t ∝ 1/t²): the honesty number bites at volume.
    """
    panel = load_panel(Path(panel_path))
    contracts_dir = Path(contracts_dir)
    contracts_dir.mkdir(parents=True, exist_ok=True)

    # Single-pass multi-window extraction (Task 4b): one scan per sample bed.gz, not per window.
    windows = [(loc.locus_id, loc.chrom, loc.start, loc.end) for loc in panel]
    all_rows = extract_regions_multi(Path(bed_dir), Path(manifest), windows)

    claims = []
    for loc in panel:  # FIXED panel order == pre-registered order
        rows = all_rows.get(loc.locus_id, [])
        uid = f"{loc.locus_id}@1"
        build_contract(rows, uid, contracts_dir, group_col="cell_type_broad")
        # The contract's single feature row is named for the locus (uid stem).
        # Map the panel's comparator convention (τ applies to group_a − group_b) onto the
        # region adapters, which compute level_b − level_a: set level_a=group_b, level_b=group_a.
        claims.append(region_delta_beta_claim(
            loc.locus_id,
            ref=f"se:{uid}",
            region_probes=(loc.locus_id,),
            region=(loc.chrom, loc.start, loc.end),
            group_col="cell_type_broad",
            level_a=loc.group_b,
            level_b=loc.group_a,
            comparator=_CMP[loc.comparator],
            threshold=loc.tau,
            ontology_term=loc.klass.lower(),
            title=loc.rationale,
        ))

    # Pre-registration: charge every panel test's α slot in FIXED ORDER, BEFORE any execution,
    # so the shrinking e-LOND budget is real (commit-before-data).
    ledger = FDRLedger(target_fdr=target_fdr)
    for c in claims:
        ledger = register_test(ledger, c.id, commitment_hash(c))
    corpus = Corpus(claims=tuple(claims), fdr_ledger=ledger)

    oracles = profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public"))
    registry = methyl_independent_registry()

    # Adapters resolve betas via load_contract under the scoped root; point it at contracts_dir.
    with using_contract_root(contracts_dir):
        clear_contract_cache()
        try:
            # Flywheel to a fixed point: SELECT/commit/execute/verify settle each locus; a
            # licensed claim is no longer a candidate, so re-running only re-probes the PENDING tail.
            prev = None
            for _ in range(3):
                # Recompute the native e-value map on the CURRENT corpus each pass (the corpus
                # mutates as loci settle) and feed it to the gate: this is what resolves each
                # pre-registered e-LOND slot at its LOCKED α, so the FDR budget actually bites.
                ev = evidence_map(corpus)
                corpus = run_cycle(
                    corpus, _ADAPTERS, _CTX,
                    adapter_registry=registry, oracles=oracles,
                    capability_registry=CAPABILITY_CELLS,
                    evidence=ev,
                ).corpus
                snapshot = tuple((c.id, c.status) for c in corpus.claims)
                if snapshot == prev:
                    break
                prev = snapshot
        finally:
            clear_contract_cache()

    verdicts = {c.id: _verdict(c.status) for c in corpus.claims}
    return RipResult(verdicts=verdicts, corpus=corpus)
