"""§7 — the immuno arm's reconstruction stays STRICT-Corpus-valid (drift guard).

`data/demo/immuno_universe.json` is a hand-built viewer bundle (upper-case statuses, `dmp_count`,
a `"inf"` e-value string) that does NOT validate as a strict grammar Corpus; `collect_immuno`
reconstructs valid Claims from it. This pins that reconstruction so drift between the viewer bundle
and the grammar schema (or a regression in the collector) is caught: the reconstructed claims must
form a strict, JSON-round-trippable Corpus. Committed bundle → not data-gated.
"""
from __future__ import annotations

import json
from collections import Counter

from polymer_grammar import FDRLedger, Status

from polymer_claims.merge_universes import collect_immuno
from polymer_protocol import Corpus


def test_collect_immuno_reconstructs_a_strict_corpus_valid_arm():
    arm = collect_immuno()
    assert (arm.arm, arm.modality) == ("immuno", "methylation")
    assert len(arm.claims) == 11

    # DRIFT GUARD: the reconstructed claims + fdr tests form a STRICT valid Corpus (the whole point —
    # unique ids, referential integrity, valid leaves/statuses) and round-trip as finite JSON.
    corpus = Corpus(claims=arm.claims, fdr_ledger=FDRLedger(target_fdr=0.05, tests=arm.fdr_tests))
    json.loads(corpus.model_dump_json())  # no Infinity literal leaks

    assert Counter(c.status.value for c in arm.claims) == {"licensed": 2, "pending": 2, "rejected": 7}
    assert {c.id for c in arm.claims if c.status == Status.LICENSED} == {"mhc-ndmp", "hervk-ndmp"}

    # the non-finite MHC e-value ("inf" in the JSON — JSON has no Infinity literal) is capped to a
    # large finite sentinel so the merged bundle stays valid, parseable JSON end-to-end.
    mhc = next(t for t in arm.fdr_tests if t.claim_id == "mhc-ndmp")
    assert mhc.e_value == 1e300
    assert mhc.discovery is True
