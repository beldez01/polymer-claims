"""Task 5 — batch immuno methylation licensing driver over a synthetic mini-atlas.

No real data: a tiny in-tmp_path atlas (monocyte-open vs naive-T-methylated at one window)
exercises the full drive — single-pass extraction, per-locus content-addressed contract,
pre-registration in fixed panel order, and the two-independent-leg gate under one shrinking
e-LOND FDR budget. Enough per-group samples (n=11) that the native betting e-value reaches
the shallow-slot bar, so the pre-registered e-LOND slots actually RESOLVE and BITE.
"""
import gzip

from polymer_grammar import (
    FDRLedger,
    MaterializationContext,
    RejectionReason,
    Status,
    register_test,
)
from polymer_grammar.commitment import commitment_hash
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.capabilities import CAPABILITY_CELLS
from polymer_claims.evidence import evidence_map
from polymer_claims.methyl_adapters import (
    RegionHodgesLehmannAdapter,
    RegionMeanDiffAdapter,
    methyl_independent_registry,
    region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_EPICV2_V1
from polymer_claims.rip_immuno import run

# n=11 samples/group: the WSR betting e-value is a product over paired samples, so it grows with
# sample size. At this depth the strong (~0.75) region Δβ earns e ≈ 71 — comfortably above the
# slot-1 e-LOND bar (1/α₁ ≈ 33) yet below every deeper slot's bar (1/α₂ ≈ 132, 1/α₃ ≈ 296, ...).
_N = 11


def _mini_atlas(tmp_path):
    bed = tmp_path / "bed"
    bed.mkdir()

    def w(stem, beta):
        with gzip.open(bed / f"{stem}.hg38.bed.gz", "wt") as fh:
            fh.write("#chr\tstart\tend\tbeta\ttotal_cov\ttotal_meth\tn_cpgs\n")
            for pos in (100, 150, 199):
                fh.write(f"chr6\t{pos}\t{pos+1}\t{beta:.4f}\t20\t{round(beta*20)}\t1\n")

    # Real signal at chr6:100-200: naive-T methylated (~0.85+) vs monocyte open (~0.10+).
    lines = ["gsm\tfilename_stem\tcell_type\tcell_type_broad\tlineage\treplicates"]
    for i in range(_N):
        w(f"Mono{i}", 0.10 + 0.005 * i)
        w(f"T{i}", 0.85 + 0.005 * i)
        lines.append(f"GM{i}\tMono{i}\tMonocytes\tMonocyte\tMyeloid\t{i + 1}")
        lines.append(f"GT{i}\tT{i}\tT_Naive_CD4\tT_naive\tLymphoid\t{i + 1}")
    man = tmp_path / "m.tsv"
    man.write_text("\n".join(lines) + "\n")
    return bed, man


def _panel(tmp_path, rows):
    p = tmp_path / "panel.tsv"
    hdr = "locus_id\tklass\tchrom\tstart\tend\tgroup_a\tgroup_b\tcomparator\ttau\trationale\n"
    p.write_text(hdr + "".join("\t".join(map(str, r)) + "\n" for r in rows))
    return p


def test_real_signal_licenses(tmp_path):
    bed, man = _mini_atlas(tmp_path)
    panel = _panel(tmp_path, [
        ("sig", "HLA", "chr6", 100, 200, "T_naive", "Monocyte", "GT", 0.10, "real"),
    ])
    res = run(panel, bed, man, tmp_path / "contracts")
    assert res.verdicts["sig"] == "LICENSED"
    # Licensed via a GENUINE e-LOND discovery at slot 1 (not the fallback 3-way gate).
    assert res.corpus.fdr_ledger.n_discoveries == 1


def test_fdr_budget_bites_at_volume(tmp_path):
    """THE demonstration: the FDR budget bites by MULTIPLICITY, not by direction or weak effect.

    Six IDENTICAL loci over the SAME window — every one a correct-direction, real Δβ (~0.75 >> τ)
    that clears the two-leg severe test — differ ONLY in panel position, hence only in their locked
    e-LOND α. Their common e-value (~71) clears the shallow slot-1 bar (1/α₁ ≈ 33) but is below every
    deeper slot's bar (1/α₂ ≈ 132, ...). So exactly the EARLY locus licenses and the identical-effect
    LATE loci are DENIED — because α shrank, not because their effect is weaker or wrong-signed.
    """
    bed, man = _mini_atlas(tmp_path)
    rows = [(f"L{i}", "HLA", "chr6", 100, 200, "T_naive", "Monocyte", "GT", 0.10, "real")
            for i in range(6)]
    res = run(_panel(tmp_path, rows), bed, man, tmp_path / "contracts")

    led = res.corpus.fdr_ledger
    assert led.n_tests == 6
    # Exactly the EARLY (slot-1) locus licenses; every deeper-slot locus is WITHHELD.
    assert res.verdicts["L0"] == "LICENSED"
    assert all(res.verdicts[f"L{i}"] == "PENDING" for i in range(1, 6))
    assert led.n_discoveries == 1                       # genuine e-LOND resolution, not the 3-way gate

    by_slot = {t.claim_id: t for t in led.tests}
    early, late = by_slot["L0"], by_slot["L1"]
    # Same correct-direction data => IDENTICAL e-value at both slots: denial is NOT by a weaker effect.
    assert early.e_value is not None
    assert early.e_value == late.e_value
    # The budget bites purely by MULTIPLICITY: the SAME e-value clears the shallow bar, not the deep one.
    assert late.alpha_allocated < early.alpha_allocated                   # α shrank down the panel
    assert early.e_value >= 1.0 / early.alpha_allocated and early.discovery       # licenses at slot 1
    assert late.e_value < 1.0 / late.alpha_allocated and not late.discovery       # WITHHELD by α-shrink

    # The withheld loci DID clear the two-leg severe test / point τ — proven by flipping panel ORDER:
    # the SAME data placed first now licenses (via the SEVERE_TEST route), and the previously-first is
    # withheld. Effect is identical across runs; only POSITION flips the verdict — the cleanest proof
    # the budget, not the effect, decides.
    res_flip = run(_panel(tmp_path, list(reversed(rows))), bed, man, tmp_path / "contracts_flip")
    assert res_flip.verdicts["L5"] == "LICENSED"        # L5 now at slot 1
    assert res_flip.verdicts["L0"] == "PENDING"         # L0 now at slot 6
    licensed = next(c for c in res_flip.corpus.claims if c.id == "L5")
    assert licensed.licensing.route.name == "SEVERE_TEST"   # cleared the two-leg severe test / point τ


# --- Change 4: the commitment match-gate, now REACHABLE because e-values flow into VERIFY. ---
_ADAPTERS = (RegionMeanDiffAdapter(), RegionHodgesLehmannAdapter())
_CTX = MaterializationContext(id="M", api_version="v1", data_version="d1")
_POWERED = "se:epicv2_casectrl_powered@1"
_STRONG = tuple(f"cg0000000{i}" for i in range(1, 6))


def test_post_hoc_tau_change_is_rejected():
    """A τ moved AFTER pre-registration is TERMINALLY rejected via HYPOTHESIS_ALTERED.

    The driver's public `run()` is atomic (it registers and resolves the same claims in one ledger),
    so the match-gate is only reachable by driving the machinery the driver now feeds: pre-register a
    hypothesis's commitment at τ=0.10, then present the SAME claim id with τ=0.90 and let VERIFY resolve
    the pre-registered slot with a native e-value. The commitment hashes disagree, so the slot's locked
    α is NOT spent on the altered hypothesis — the claim is REJECTED (HYPOTHESIS_ALTERED), not silently
    re-licensed. This gate is inert until e-values flow (Change 1); the powered fixture is the same
    region-Δβ + betting-e-value path the driver runs, kept self-contained here.
    """
    registered = region_delta_beta_claim("c", ref=_POWERED, region_probes=_STRONG, threshold=0.10)
    ledger = register_test(FDRLedger(target_fdr=0.05), registered.id, commitment_hash(registered))

    altered = region_delta_beta_claim("c", ref=_POWERED, region_probes=_STRONG, threshold=0.90)
    assert commitment_hash(altered) != commitment_hash(registered)   # a genuine post-hoc alteration

    corpus = Corpus(claims=(altered,), fdr_ledger=ledger)
    out = run_cycle(
        corpus, _ADAPTERS, _CTX,
        adapter_registry=methyl_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        evidence=evidence_map(corpus),
        capability_registry=CAPABILITY_CELLS,
    )
    c = next(x for x in out.corpus.claims if x.id == "c")
    assert c.status == Status.REJECTED
    assert c.rejection_reason == RejectionReason.HYPOTHESIS_ALTERED
    # The pre-registered slot is NOT resolved by the altered hypothesis — its α is never spent.
    t = next(x for x in out.corpus.fdr_ledger.tests if x.claim_id == "c")
    assert t.e_value is None and not t.discovery
