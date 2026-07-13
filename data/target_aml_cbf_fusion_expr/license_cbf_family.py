"""Phase 2e finale — license the CBF 2x2 fusion-marker family across TCGA-LAML + TARGET-AML (replicated).
Records tier/status/e-values for A/B/C/D + the ACTB control. No assertion — the real-data readout."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path("/Users/zbb2/Desktop/polymer-claims")
sys.path.insert(0, str(REPO / "src"))

from polymer_grammar import FDRLedger, IndependenceTier, Status  # noqa: E402
from polymer_protocol import Corpus  # noqa: E402
from polymer_claims import contracts as _c  # noqa: E402
from polymer_claims.evidence import _terminal_node  # noqa: E402
from polymer_claims.expression_floor_evidence import expression_floor_evalue  # noqa: E402
from polymer_claims.expression_floor_replication import _rebind  # noqa: E402
from polymer_claims.expression_floor_populate import (  # noqa: E402
    preregister, license_replicated, check_controls, propose_cbf_family_claims,
)

REF_A = "se:tcga_laml_cbf_expr@1"
REF_B = "se:target_aml_cbf_expr@1"
FACTORS_A = ("tcga-laml-cohort", "adult-aml-population", "tcga-karyotype")
FACTORS_B = ("target-aml-cohort", "pediatric-aml-population", "target-karyotype")

claims = propose_cbf_family_claims(REF_A)
print("e-values (TCGA e1, TARGET e2, product) — e-LOND bars are front-loaded (32.9, 131, 296, 526, 800):")
for c in claims:
    node = _terminal_node(c)
    e1 = expression_floor_evalue(node)
    e2 = expression_floor_evalue(_rebind(node, REF_B))
    print(f"  {c.id:32s} e1={e1:10.2f}  e2={e2:12.2f}  product={e1 * e2:.2e}")

corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
out = license_replicated(corpus, claims, ref_a=REF_A, ref_b=REF_B, factors_a=FACTORS_A, factors_b=FACTORS_B)
by = out.by_id()
print("\nresults:")
licensed = 0
for c in claims:
    x = by[c.id]
    tier = x.licensing.independence_tier.value if x.licensing else "n/a"
    print(f"  {c.id:32s} status={x.status.value.upper():9s} tier={tier}")
    if x.status is Status.LICENSED and x.licensing and x.licensing.independence_tier is IndependenceTier.REPLICATED:
        licensed += 1
print(f"controls: {check_controls(out, positive='floor-MN1-inv16-vs-other', negative='floor-ACTB-inv16-vs-other')}")
print(f"\nHEADLINE: {licensed} of 4 CBF family claims LICENSED @ REPLICATED across TCGA-LAML + TARGET-AML "
      "(RUNX1T1/t(8;21) + MN1/inv(16), each vs other and vs the other fusion). ACTB control held.")
