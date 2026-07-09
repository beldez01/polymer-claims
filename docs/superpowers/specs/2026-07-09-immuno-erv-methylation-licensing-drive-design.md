# Immuno / ERV Methylation Licensing Drive — Design

> **Status:** design approved 2026-07-09, pre-plan. **Scope:** one licensing drive (Approach A —
> single-cohort mining) applied to the Loyfer 2023 WGBS atlas, licensing cell-type-specific
> methylation claims at HLA and ERV/TE loci through the *existing* mean_diff air-gap.
> **Owner:** Zach. **Next:** implementation plan (writing-plans).

## 1. Goal and motivation

Grow the count of **genuinely LICENSED** nodes in the claims universe — real data through the
recompute gate, many times — in the immunogenetics / HLA / endogenous-retrovirus territory that is
the project's most interesting substrate. Today the universe has exactly **2 real blue nodes**
(TCGA-LAML n-DMP; HLA-A promoter Δβ) against 47 WITNESSED (never-gated) nodes. This drive turns the
crank on the one already-working apparatus (the `mean_diff` cell-type contrast) across a
pre-registered panel of HLA and ERV/TE loci, and in doing so produces the **first at-volume test of
the corpus honesty number `q`** — as claims accumulate, the e-LOND α budget shrinks and later claims
stop licensing. The FDR budget *biting* is the demonstration, not a bug: it is the property no eval
system has.

This is deliberately **not** a new domain to bootstrap — it is the natural expansion of the HLA-A
node that already licensed, and it even upgrades that node (the original claim stated a **T-naive**
contrast the n=3 BLUEPRINT demo could not test; the Loyfer atlas has T-Naive-CD4/CD8).

### Non-goals (explicitly deferred)
- **Correlation claims** (11 of the 47: CpG-density/dG37 vs expression) — need a correlation cell
  (two genuinely-independent correlation legs). Wave 2.
- **Enrichment claims** (8 of the 47: CoRSIV / Retro-Age fold-enrichment at TEs) — need an
  enrichment cell. Wave 3.
- **Licensed-negative path** for the FALSIFIED / designed-negative-control claims — ties to the
  neg2 backlog item ⑤ (forbidden-vs-unobserved). Not in this drive.
- **REPLICATED tier.** This drive is single-atlas → **REPRODUCED**. A second WGBS source is a later
  drive.

## 2. Data (all present on disk — confirmed 2026-07-09)

- **Loyfer 2023 methylation atlas (GSE186458)** at
  `~/Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023/bed_hg38/` — 48 samples, genome-wide per-CpG
  WGBS, **hg38**, `.bed.gz` (`chr start end beta total_cov total_meth n_cpgs`), tabix-indexed.
  Immune roster with replicates: T-CD3/CD4/CD8, CenMem/Eff/EffMem, **T-Naive-CD4/CD8**, NK,
  Monocytes, Granulocytes, B/B-Mem, tissue Macrophages (Colon/Liver/Lung). Roster + lineage labels
  in `sample_manifest.tsv` (`cell_type`, `cell_type_broad`, `lineage`, `replicates`).
- **RepeatMasker annotation** at `~/Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt` — HERV/
  ERV/LINE/Alu/LTR element coordinates. **Build must be verified hg38 before use (see §5).**
- **Prior HLA-experiment pipeline** at
  `~/Desktop/PolymerGenomicsAPI/internal/InSilico/HLA experiment/` — source of HLA locus coordinates
  and provenance logic; contains HERV/eQTL overlap code to cross-check element choices.

Real data stays **local-only / gitignored** (project convention). The atlas inputs are
**content-addressed / pinned** (mirroring the `ingest/real_kernel_pins.json` pattern) so extraction
is reproducible from a clean checkout.

## 3. Claim family and honesty discipline

**Family:** cell-type-specific methylation — the single shape the existing `mean_diff` air-gap
handles. Each claim = one (locus × contrast): "mean β at locus *L* differs between cell groups *A*
and *B* in the stated direction by more than τ."

**Two locus classes:**
1. **HLA** — class I (A/B/C) and class II (DRB1/DQ/DP) promoter/regulatory windows.
2. **ERV/HERV/LINE/LTR** — elements selected by family from `rmsk.txt`.

**Canonical contrasts** (defined over `cell_type_broad` / `lineage`, fixed in the panel):
myeloid vs lymphoid; monocyte vs T-naive; naive vs memory T. Each (locus × contrast) is a claim.

**Honesty discipline — non-negotiable:**
- The **full locus panel is pre-registered** through the existing `register_test` / `resolve_test`
  ledger, with a `commitment_hash` covering **every degree of freedom**: locus windows, contrasts,
  directions (comparators), thresholds τ, **and the test order** (because e-LOND's α depends on
  order). Registration happens **before any β is extracted**.
- Post-hoc edits to any of the above → terminal `HYPOTHESIS_ALTERED` at `resolve_test` (the
  match-gate). No τ-tuning, no reordering, no dropping a locus after seeing its result.
- The **e-LOND budget governs how many license.** Later claims face a shrinking α and will fail to
  license even with a real effect — this is the intended at-volume `q` demonstration.
- **Uniform pre-registered bar** τ ≈ 0.1 Δβ across the panel; comparator per the locus's stated
  direction. No per-claim threshold.
- **Tier: REPRODUCED** (single atlas), recorded honestly.

## 4. Architecture

All new code is **umbrella-side** (`src/polymer_claims/`). grammar/ and protocol/ stay pure and
numpy-free; Corpus stays exactly 4 collections. Five single-purpose units:

| Unit | Path (proposed) | Purpose | Reuse vs new |
|---|---|---|---|
| **Locus panel** | `panels/immuno_meth_v1.tsv` | Declarative, pre-registerable claim list: `locus_id, class(HLA\|TE), chrom, start, end, contrast, comparator, tau, rationale`. Authored from prior biology + `rmsk.txt` families — **never from peeking at the atlas.** | New (data) |
| **Extractor** | `ingest/loyfer_wgbs.py` | `extract(window, manifest) -> table`: tabix-query each `.bed.gz` over the window, compute **coverage-weighted mean β per sample**, emit long-format `(sample, cell_type, cell_type_broad, lineage, beta, n_cpg, coverage)`. QC-drops samples below min coverage / min n_cpg. Deterministic; no clock/random. | New (mirrors the HLA `pyBigWig→mean` pattern, here bed/tabix) |
| **Contract builder** | `ingest/build_loyfer_contract.py` | `build(table, ref) -> contract`: one extracted table → a content-addressed contract (`.betas.tsv` + `.json`, keyed by `dimnames_hash`). | New (mirrors existing `build_contract_*`) |
| **Claim builder** | (existing `exec_adapters.mean_diff_claim`) | Per locus: `mean_diff_claim(ref, group_col, group_a/b, comparator, threshold, rationale)`. | **Reused as-is** |
| **Batch driver** | `scripts/rip_immuno_meth.py` | `run(panel) -> corpus + bundle`: pre-register panel → per locus [extract → contract → claim → gate] → `resolve_test` match-gate → fold verdicts into a viewer universe bundle. | New (glue); reuses `register_test`/`resolve_test`, the gate, `make_universe_timeline.py` |

**The load-bearing design decision — the air gap must be genuinely independent.** The existing
`independent_registry()` pairs StatsPure vs StatsStdlib, which for a mean difference risks being
*two spellings of the same t-test* — a hollow AGREE check. R5.1 already solved this for the n-DMP
claim by making the two legs **algorithmically distinct** (parametric + Hodges-Lehmann/rank). This
drive **reuses that discipline**: the cell-type location shift is computed by a **parametric Δmean
leg and a rank/Hodges-Lehmann leg**, which agree on direction/magnitude only if the signal is real.
The two legs must clear the same pre-registered τ and agree in direction to satisfy AGREE.

**Data flow:**
```
panel.tsv ──(pre-register, commitment_hash)──▶ register_test
   │
   └─ per locus (in fixed panel order):
        loyfer .bed.gz ──extractor──▶ table ──contract builder──▶ contract (dimnames_hash)
             │
             └─ mean_diff_claim ──▶ GATE:  [ parametric leg ∧ rank leg AGREE ]
                                           ∧ [ beat τ ] ∧ [ grounded ] ∧ [ e-LOND discovery ]
                                                 │
                                                 ▼
                                          verdict: LICENSED | PENDING
                                                 │
                                    resolve_test (match-gate) ──▶ universe bundle ──▶ viewer
```

## 5. Error handling and edge cases

Two pre-flight gates (silent corruption if wrong):
- **Genome build match.** Assert `rmsk.txt` is **hg38** before trusting any TE window. A build
  mismatch silently mis-locates every ERV/TE window and still "licenses" garbage. Hard fail if not
  hg38.
- **Pre-registered test order.** e-LOND α depends on order → order is fixed inside `commitment_hash`
  at registration, never chosen after results.

Explicit (never silent) handling:
- **Sparse/zero coverage** (HLA CD4-T demo had n_CpG 9–15): QC-drop a sample below min coverage /
  min n_cpg; if a group drops below min replicates the locus resolves **PENDING (unpowered)** — not
  skipped, not licensed. Honest ledger consequence: a pre-registered but unpowerable locus still
  consumed its α slot, so **do not pad the panel with unpowerable loci** — power-check windows
  against the atlas's CpG coverage *before* committing the panel (a coverage pre-check is allowed;
  it reads coverage, not effect).
- **Air-gap disagreement**: legs disagree (direction or beyond tolerance) → PENDING
  (adapter-disagreement). The check working, not an error.
- **Deterministic extraction**: coverage-weighted mean reproducible from pinned Loyfer files; the
  contract `dimnames_hash` is stable across re-runs.

## 6. Testing (behavior-first; extractor built first, TDD)

- **Anchor test (load-bearing):** re-extract the HLA-A promoter window
  (chr6:29,940,000–29,944,000, GRCh38) from the Loyfer atlas; assert the new bed/tabix extractor
  reproduces the monocyte-open / T-methylated **direction** and a Δβ in the ballpark of the prior
  **0.59**. Independent-second-route check: the new pipeline must agree with the old bigWig
  extraction on the one window already trusted.
- **Air-gap teeth:** a constructed case where two-spelling t-tests both agree but the
  parametric + rank legs correctly diverge — proving AGREE is not decorative; plus a real-signal
  case where they agree.
- **Match-gate:** mutate τ (or order) after registration → terminal `HYPOTHESIS_ALTERED`.
- **FDR-at-volume:** a panel seeded with by-construction null loci → e-LOND rejects them at the
  expected rate, so the `q` demonstration is itself asserted.
- **Extractor units:** coverage-weighted mean correctness on a tiny synthetic `.bed` fixture;
  QC-drop behavior; empty window → unpowered.
- **End-to-end smoke:** a 2–3 locus mini-panel runs the full driver → corpus with expected verdicts
  + a loadable viewer universe bundle.

## 7. Build order (for the implementation plan)

1. **Extractor + anchor test** — `ingest/loyfer_wgbs.py`, pinned atlas inputs, HLA-A anchor green.
2. **Genuinely-independent leg pair** — parametric Δmean + rank/Hodges-Lehmann legs for the
   cell-type contrast (reuse R5.1 pattern), with the air-gap-teeth test.
3. **Contract builder** — `ingest/build_loyfer_contract.py`, content-address parity test.
4. **Panel v1 + coverage pre-check** — author HLA + ERV/TE loci from prior biology + `rmsk.txt`;
   power-check windows against atlas coverage; freeze order.
5. **Batch driver + pre-registration wiring** — `scripts/rip_immuno_meth.py`; match-gate test;
   FDR-at-volume test; end-to-end smoke.
6. **Universe bundle emission** — fold verdicts into a viewer bundle; visual confirm the new blue
   nodes render.

## 8. Success criteria

- The universe goes from 2 → **many** real LICENSED immuno/ERV nodes, each with a recorded
  content-address (`dimnames_hash` / `profile_hash` / `semantic_run_id`), REPRODUCED tier.
- The already-licensed HLA-A node is **upgraded** to the proper T-naive contrast at real power.
- The e-LOND budget **visibly bites** at volume (later claims PENDING as α shrinks) — the first
  at-volume `q` demonstration, asserted by the FDR-at-volume test.
- Pre-registration is enforced end-to-end (a post-hoc τ/order change terminally rejects).
- grammar/protocol untouched (pure, numpy-free); Corpus stays 4; full suite green.
