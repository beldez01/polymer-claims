"""Phase 2d-ii finale — license the expression-floor spine against the REAL committed contract
se:tcga_laml_fusion_expr@1 (TCGA-LAML, n=6 t(8;21)). Records the outcome; an honest PENDING at n=6
is an acceptable result. No assertion — this is the real-data readout."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path("/Users/zbb2/Desktop/polymer-claims")
sys.path.insert(0, str(REPO / "src"))

from polymer_grammar import FDRLedger, Status  # noqa: E402
from polymer_protocol import Corpus  # noqa: E402
from polymer_claims.expression_floor_populate import (  # noqa: E402
    preregister, license_batch, check_controls, propose_spine_claims, _evidence_for,
)

REF = "se:tcga_laml_fusion_expr@1"

claims = propose_spine_claims(REF)                       # [floor-RUNX1T1, floor-ACTB]
ev = _evidence_for(claims)
corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
out = license_batch(corpus, claims, ref=REF)
by = out.by_id()

BAR = 32.90  # e-LOND first-test discovery bar (1/alpha_1, target_fdr=0.05)
print(f"e-LOND first-test bar: {BAR}")
for cid in ("floor-RUNX1T1", "floor-ACTB"):
    c = by[cid]
    print(f"  {cid}: status={c.status.value.upper()}  e={ev.get(cid, float('nan')):.2f}")
rep = check_controls(out, positive="floor-RUNX1T1", negative="floor-ACTB")
print(f"controls: {rep}")

runx1t1 = by["floor-RUNX1T1"]
if runx1t1.status is Status.LICENSED:
    print("\nHEADLINE: RUNX1-RUNX1T1 expression-floor claim LICENSED@REPRODUCED — first licensed synbio claim.")
else:
    print(f"\nHEADLINE: RUNX1-RUNX1T1 claim {runx1t1.status.value.upper()} at n=6 (unearned at this power, "
          f"NOT refuted). e={ev.get('floor-RUNX1T1', float('nan')):.2f} vs bar {BAR}.")
