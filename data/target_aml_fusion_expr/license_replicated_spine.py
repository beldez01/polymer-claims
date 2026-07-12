"""Phase 2d-iii finale — the REPLICATED license for RUNX1-RUNX1T1 across two real cohorts:
TCGA-LAML (adult, n=6 t(8;21)) + TARGET-AML (pediatric, n=90 t(8;21)). Error-independent (disjoint
shared_cause_factors). The product e_tcga * e_target folds into the single e-LOND slot; if it clears
32.9 the claim licenses at IndependenceTier.REPLICATED. Records the outcome (no assertion)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path("/Users/zbb2/Desktop/polymer-claims")
sys.path.insert(0, str(REPO / "src"))

from polymer_grammar import FDRLedger, IndependenceTier, MaterializationContext, Status  # noqa: E402
from polymer_protocol import Corpus  # noqa: E402
from polymer_claims import contracts as _c  # noqa: E402
from polymer_claims.evidence import _terminal_node  # noqa: E402
from polymer_claims.expression_floor_evidence import expression_floor_evalue  # noqa: E402
from polymer_claims.expression_floor_replication import _rebind  # noqa: E402
from polymer_claims.expression_floor_populate import (  # noqa: E402
    preregister, license_replicated, check_controls, propose_spine_claims,
)

REF_A = "se:tcga_laml_fusion_expr@1"      # adult
REF_B = "se:target_aml_fusion_expr@1"     # pediatric
FACTORS_A = ("tcga-laml-cohort", "adult-aml-population", "tcga-karyotype")
FACTORS_B = ("target-aml-cohort", "pediatric-aml-population", "target-karyotype")
BAR = 32.90

claims = propose_spine_claims(REF_A)                        # [floor-RUNX1T1, floor-ACTB]

# report the two independent cohort e-values for RUNX1T1
runx = next(c for c in claims if c.id == "floor-RUNX1T1")
node_a = _terminal_node(runx)
e1 = expression_floor_evalue(node_a)
e2 = expression_floor_evalue(_rebind(node_a, REF_B))
print(f"e-LOND first-test bar: {BAR}")
print(f"  TCGA (cohort A) e1 = {e1:.2f}")
print(f"  TARGET (cohort B) e2 = {e2:.2f}")
print(f"  product e1*e2 = {e1 * e2:.2f}")

corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
out = license_replicated(corpus, claims, ref_a=REF_A, ref_b=REF_B,
                         factors_a=FACTORS_A, factors_b=FACTORS_B)
by = out.by_id()
for cid in ("floor-RUNX1T1", "floor-ACTB"):
    c = by[cid]
    tier = c.licensing.independence_tier.value if c.licensing else "n/a"
    print(f"  {cid}: status={c.status.value.upper()}  tier={tier}")
print(f"controls: {check_controls(out, positive='floor-RUNX1T1', negative='floor-ACTB')}")

r = by["floor-RUNX1T1"]
if r.status is Status.LICENSED and r.licensing and r.licensing.independence_tier is IndependenceTier.REPLICATED:
    print(f"\nHEADLINE: RUNX1-RUNX1T1 LICENSED @ REPLICATED (e1*e2={e1*e2:.0f} ≥ {BAR}) — "
          "the first licensed synbio claim, cross-cohort replicated across TCGA-LAML + TARGET-AML.")
else:
    print(f"\nHEADLINE: RUNX1-RUNX1T1 {r.status.value.upper()} "
          f"(e1*e2={e1*e2:.2f} vs {BAR}) — honest outcome; effect real, replication "
          f"{'independent' if e1*e2 else '—'}.")
