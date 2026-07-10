"""Batch runner: turn pharmacogenomic mechanism-scan rows into pre-registered, licensable claims.
The pharmacogenomic engine is an untrusted proposer; standing is conferred only in Task 6's run_cycle pass."""
from __future__ import annotations

import logging
import math
import re
import sys
from pathlib import Path

from polymer_grammar import (
    Claim,
    Comparator,
    FDRLedger,
    MaterializationContext,
    Status,
    commitment_hash,
    register_test,
)
from polymer_protocol import Corpus, Layout, export_topology, run_cycle

from .capabilities import CAPABILITY_CELLS
from .contracts import load_contract
from .evidence import _terminal_node
from .pharmaco_adapters import (
    PharmacoMeanDiffAdapter,
    PharmacoRankAdapter,
    marker_drug_claim,
    pharmaco_independent_registry,
    pharmaco_oracle_registry,
)
from .pharmaco_evidence import pharmaco_evalue

log = logging.getLogger(__name__)

__all__ = [
    "ControlCheckFailed",
    "KNOWN_DRUG_CHEBI",
    "check_controls",
    "license_batch",
    "populate_universe",
    "preregister",
    "GDSC_SHARED_CAUSE_FACTORS",
    "propose_claims",
    "run_full_universe",
]

# this file: <repo>/src/polymer_claims/pharmaco_populate.py -> parents[2] == <repo>
_REPO_ROOT = Path(__file__).resolve().parents[2]

# The GDSC-shared causes: every pharmaco materialization carries these, so any later
# cross-cohort replication is gated by §E (cohorts_error_independent) rather than silently
# minting REPLICATED.
GDSC_SHARED_CAUSE_FACTORS = (
    "gdsc2-manifest", "gdsc-imputed-normalization", "hg38",
    "cell-model-passports", "scipy-statsmodels",
)

# A small curated drug -> CHEBI uri map, sufficient for the two published controls
# (MTAP->Palbociclib, MGMT->Temozolomide) plus a few other well-known GDSC compounds. Any drug
# NOT in this map still gets a claim (propose_claims never drops a drug) — it falls back to a
# synthetic "other"-ontology urn instead. A full GDSC drug->CHEBI resolver is out of scope for v1.
KNOWN_DRUG_CHEBI: dict[str, str] = {
    "Palbociclib": "http://purl.obolibrary.org/obo/CHEBI_85993",
    "Temozolomide": "http://purl.obolibrary.org/obo/CHEBI_72564",
}

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    return _SLUG_RE.sub("-", name.lower()).strip("-") or "unknown"


def propose_claims(
    res_df, *, ref: str, chebi_of: dict[str, str], agent_id: str = "pharmaco-mechanism-v1"
) -> list[Claim]:
    """One marker_drug_claim per scan row. search_cardinality = the row's n_genes_tested (falls
    back to 1). No drug is ever dropped: a drug in `chebi_of` gets a CHEBI-ontology subject term;
    any other drug falls back to the "other" ontology with a synthetic urn:pharmaco:drug:<slug> uri
    (a stable, honest stand-in — not a real ontology resolution)."""
    claims: list[Claim] = []
    n_fallback = 0
    for r in res_df.itertuples():
        drug = str(r.drug)
        uri = chebi_of.get(drug)
        if uri is None:
            ontology, uri = "other", f"urn:pharmaco:drug:{_slugify(drug)}"
            n_fallback += 1
        else:
            ontology = "CHEBI"
        n_genes = getattr(r, "n_genes_tested", 1)
        if n_genes is None or not n_genes or (isinstance(n_genes, float) and math.isnan(n_genes)):
            n_genes = 1                          # missing/0/NaN -> the honest floor of 1
        claims.append(marker_drug_claim(
            f"pgx-{r.marker}-{drug}", ref=ref, marker=str(r.marker), drug=drug,
            drug_chebi_uri=uri, drug_ontology=ontology,
            search_cardinality=int(n_genes), agent_id=agent_id))
    if n_fallback:
        log.info("propose_claims: %d row(s) used the 'other'-ontology CHEBI fallback", n_fallback)
    return claims


def preregister(corpus: Corpus, claims: list[Claim]) -> Corpus:
    """Admit the proposed claims into the corpus (PENDING — no standing yet) and lock an e-LOND
    slot per claim (register_test/commitment_hash) BEFORE any e-value exists. Standing (LICENSED)
    is only conferred later by Task 6's run_cycle.

    Registration order is the LIST order of `claims` — i.e. STRENGTH-rank order, because
    propose_claims builds the list straight from the mechanism scan's DataFrame (sorted by level
    desc, |r_adj| desc). This is the intended use of e-LOND's front-loaded γ_t weights: test the
    most-promising hypotheses first so the strongest signals get the earliest (lowest) discovery
    bars. FDR control is order-INDEPENDENT (the γ_j sum to 1 regardless of order); only power
    changes. NOT protocol's register_hypotheses, which re-sorts claim_ids ALPHABETICALLY and would
    bury a strong-but-late-alphabet signal (e.g. MTAP→Palbociclib) behind a ~10^6 threshold. The
    locked α is honored at verify: pre-registered claims resolve via resolve_test (verify.py
    Phase D) against the α locked HERE, never re-sorted by elond_decisions."""
    admitted = corpus.model_copy(update={"claims": corpus.claims + tuple(claims)})
    ledger = admitted.fdr_ledger
    pending = {t.claim_id for t in ledger.tests if t.e_value is None and not t.retracted}
    for c in claims:
        if c.evaluation_plan is None or c.id in pending:
            continue                              # planless / already-registered -> no double-charge
        ledger = register_test(ledger, c.id, commitment_hash(c))
        pending.add(c.id)
    if ledger == admitted.fdr_ledger:
        return admitted
    return admitted.model_copy(update={"fdr_ledger": ledger})


def _evidence_for(claims: list[Claim], *, threshold: float = 0.0) -> dict[str, float]:
    """Per-claim e-value from leg A's within-tissue methylation split (ONE leg — the rank leg is
    the corroborating air-gap gate, never a factor). Skips claims whose contract read fails."""
    out: dict[str, float] = {}
    for c in claims:
        node = _terminal_node(c)
        if node is None:
            continue
        try:
            out[c.id] = pharmaco_evalue(node, threshold=threshold, comparator=Comparator.GT)
        except (FileNotFoundError, KeyError, ValueError):
            continue
    return out


def license_batch(
    corpus: Corpus, claims: list[Claim], *, ref: str, shared_cause_factors: tuple[str, ...]
) -> Corpus:
    """Confer standing on a pre-registered batch: run the two independent legs + registry + oracle
    + per-claim e-values through run_cycle against cohort `ref`. Every materialization carries
    `shared_cause_factors` (the GDSC-shared causes), so any later cross-cohort replication is gated
    by §E (cohorts_error_independent) rather than silently minting REPLICATED. Within-GDSC claims
    live in a SINGLE cohort, so a licensed claim resolves to IndependenceTier.REPRODUCED; a claim
    whose e-value never clears the e-LOND discovery bar stays PENDING (residue, not rejected).

    Mirrors the run_cycle wiring proven in real_kernel_proof.py / _ndmp_gate.run_ndmp_gate: the
    caller owns contract-root scoping (load_contract + the adapters read the active root)."""
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    try:
        dimnames_hash = load_contract(ref).dimnames_hash
    except FileNotFoundError:
        dimnames_hash = None
    factors = tuple(shared_cause_factors)
    materializations = {
        c.id: MaterializationContext(
            id=base.id, api_version=base.api_version, data_version=base.data_version,
            dimnames_hash=dimnames_hash, shared_cause_factors=factors)
        for c in claims if _terminal_node(c) is not None
    }
    result = run_cycle(
        corpus, (PharmacoMeanDiffAdapter(), PharmacoRankAdapter()), base,
        adapter_registry=pharmaco_independent_registry(),
        oracles=pharmaco_oracle_registry(),
        materializations=materializations,
        evidence=_evidence_for(claims),
        capability_registry=CAPABILITY_CELLS)
    return result.corpus


class ControlCheckFailed(RuntimeError):
    """The publish guard: a control behaved wrong (positive did not license, or negative did)."""


def check_controls(
    corpus: Corpus, *,
    positive: str = "pgx-MTAP-Palbociclib", negative: str = "pgx-MGMT-Temozolomide",
) -> dict:
    """A read-only instrument, not a gate: reports whether the known-mechanism positive control
    licensed and the known-null negative control did not — never mutates any claim's status.
    The negative condition is "not LICENSED" (robust to the null landing PENDING as a residue OR
    terminal-REJECTED via agreed refutation — either way it is not licensed)."""
    by_id = corpus.by_id()
    pos = by_id.get(positive)
    neg = by_id.get(negative)
    positive_licensed = pos is not None and pos.status == Status.LICENSED
    negative_licensed = neg is not None and neg.status == Status.LICENSED
    return {
        "ok": positive_licensed and not negative_licensed,
        "positive_licensed": positive_licensed,
        "negative_licensed": negative_licensed,
    }


def populate_universe(
    res_df, *, ref: str, chebi_of: dict[str, str], shared_cause_factors: tuple[str, ...],
    require_controls: bool = True, agent_id: str = "pharmaco-mechanism-v1",
) -> Corpus:
    """End-to-end: propose -> preregister -> license_batch -> check_controls (the publish guard).
    Raises ControlCheckFailed if require_controls and the control instrument reports not-ok."""
    claims = propose_claims(res_df, ref=ref, chebi_of=chebi_of, agent_id=agent_id)
    corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
    corpus = license_batch(corpus, claims, ref=ref, shared_cause_factors=shared_cause_factors)
    report = check_controls(corpus)
    if require_controls and not report["ok"]:
        raise ControlCheckFailed(f"control instrument failed: {report}")
    return corpus


def _evalue_of(corpus: Corpus, claim_id: str) -> float | None:
    """The claim's resolved e-value from the fdr_ledger, or None if never registered/resolved."""
    for t in reversed(corpus.fdr_ledger.tests):
        if t.claim_id == claim_id:
            return t.e_value
    return None


def run_full_universe(
    *, require_controls: bool = False, agent_id: str = "pharmaco-mechanism-v1",
    out_path: "str | Path | None" = None,
) -> Corpus:
    """The volume path for the Monday demo: rebuild the contract with full mechanism-gene
    coverage, run `all_mechanism_markers` (every apt (drug, gene) row, not just the single best
    per drug -> ~2,000 candidates), propose+license a claim for EVERY row (no drug dropped —
    `KNOWN_DRUG_CHEBI` resolves the curated few, every other drug gets an "other"-ontology
    fallback), print a stderr summary (total/LICENSED/PENDING/REJECTED + the top-15 LICENSED
    claims by e-value), and save the exported topology under data/pharmaco/ (gitignored) so a
    viewer step can consume it later. Returns the populated Corpus."""
    from .ingest.gdsc_pharmaco import ingest_gdsc_pharmaco
    from .pharmaco.mechanism import all_mechanism_markers, load_inputs

    summary = ingest_gdsc_pharmaco()
    print(f"ingest: {summary}", file=sys.stderr)
    ref = "se:gdsc_pharmaco@1"

    res = all_mechanism_markers(*load_inputs())
    n_drugs = res["drug"].nunique() if len(res) else 0
    print(f"mechanism scan (full volume path): {len(res)} candidate marker/drug row(s) "
          f"across {n_drugs} drug(s)", file=sys.stderr)

    corpus = populate_universe(
        res, ref=ref, chebi_of=dict(KNOWN_DRUG_CHEBI), shared_cause_factors=GDSC_SHARED_CAUSE_FACTORS,
        require_controls=require_controls, agent_id=agent_id)

    licensed = [c for c in corpus.claims if c.status == Status.LICENSED]
    pending = [c for c in corpus.claims if c.status == Status.PENDING]
    rejected = [c for c in corpus.claims if c.status == Status.REJECTED]
    print(f"universe: {len(corpus.claims)} total claims "
          f"({len(licensed)} LICENSED / {len(pending)} PENDING / {len(rejected)} REJECTED)",
          file=sys.stderr)

    ranked = sorted(
        ((c.id, _evalue_of(corpus, c.id)) for c in licensed),
        key=lambda x: (x[1] is None, -(x[1] if x[1] is not None else 0.0)),
    )
    print(f"top {min(15, len(ranked))} LICENSED claims by e-value:", file=sys.stderr)
    for cid, e in ranked[:15]:
        print(f"  {cid}: e={e}", file=sys.stderr)

    resolved_out = Path(out_path) if out_path else (
        _REPO_ROOT / "data" / "pharmaco" / "gdsc_pharmaco_universe_topology.json")
    resolved_out.parent.mkdir(parents=True, exist_ok=True)
    topo = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
    resolved_out.write_text(topo.model_dump_json(indent=2))
    print(f"topology exported: {resolved_out}", file=sys.stderr)

    return corpus
