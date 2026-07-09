# STRATA Pharmacogenomic Licensing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn GDSC methylation-marker → drug-response associations into claims that pass the real licensing gate, populating the claims universe with computed, evidence-bearing science.

**Architecture:** All new code is umbrella-side (`src/polymer_claims/`); `grammar`/`protocol` stay pure and numpy-free; `Corpus` stays 4 collections. The STRATA mechanism scan (already lifted to `src/polymer_claims/strata/`) is an **untrusted proposer** — it ranks `(drug, marker)` candidates. Two **independent adapter legs** re-compute the association on a content-addressed SE-Contract, and only `run_cycle`/`verify_stage` confers standing. The pharmaco data is modeled in the *existing* feature×sample SE-Contract shape by prefixing feature rows `meth::<gene>` and `auc::<drug>` over the same cell-line samples, so the methyl contract machinery is reused wholesale.

**Tech Stack:** Python 3.12, pydantic v2, numpy (umbrella only), the `[strata]` extra (pandas/scipy/statsmodels/scikit-learn/lifelines/openpyxl). Design reference: `docs/superpowers/specs/2026-07-08-strata-pharmaco-licensing-design.md`.

## Global Constraints

- `grammar/` and `protocol/` stay **pure + numpy-free**; every new import of numpy/pandas/scipy lives under `src/polymer_claims/`.
- `Corpus` has **exactly 4 collections** — never add one.
- All heavy scientific deps stay behind the `[strata]` optional extra; core wheel import must succeed without it (lazy imports).
- The GDSC data and the built SE-Contract are **gitignored** — nothing real is committed.
- Licensing statistic must be **scale-invariant** (median-split / rank), not the linear `r_adj` (which is proposal-ranking only).
- The e-value comes from **one leg only** (leg A); the rank leg is a corroborating air-gap gate (`agreement_mode="both_satisfy_criterion"`). **Never** multiply per-tissue e-values.
- Within-GDSC licensing tier ceiling is **REPRODUCED**; `shared_cause_factors` MUST be populated so `independence_tier_of` cannot mint a false REPLICATED.
- Every claim's `Provenance` uses `generated_by=AGENT_GENERATED` **with a non-null `agent_id`** (construction raises otherwise).
- Non-hits and negative controls persist as **PENDING** residue, never terminal REJECT.
- The control check is an **instrument / publish-guard** — it changes no claim's status.

## Before you start (read these templates)

The framework-mechanics of licensing real data end-to-end are already solved in-repo. Read, in order:
- `src/polymer_claims/methyl_ndmp.py` — the two-leg adapter + claim-factory + `ndmp_independent_registry` template (closest analog).
- `src/polymer_claims/methyl_adapters.py` — `_load_betas` contract-read + `region_delta_beta_claim`.
- `src/polymer_claims/evidence.py` — `betting_evalue(a, b, *, threshold, comparator)`.
- `src/polymer_claims/ingest/transform.py` (`build_contract`) + `ingest/tcga_laml.py` (orchestration) — the SE-Contract builder.
- `src/polymer_claims/capabilities.py` — `CapabilityCell` + `_bindings()`.
- `src/polymer_claims/real_kernel_proof.py` — **the proven `run_cycle` licensing wiring** (materializations, `shared_cause_factors`, evidence dict). Task 6 mirrors this; read it before Task 6.

## File Structure

| Path | Responsibility |
|---|---|
| Create `src/polymer_claims/ingest/gdsc_pharmaco.py` | Build `se:gdsc_pharmaco@1` from the lifted GDSC data (`meth::<gene>` + `auc::<drug>` rows, tissue in col_data). |
| Create `src/polymer_claims/pharmaco_adapters.py` | `_load_pharmaco` contract-read, the two legs, `PHARMACO_ASSOC_CELL` usage, `marker_drug_claim`, `pharmaco_independent_registry`, `pharmaco_oracle_registry`. |
| Create `src/polymer_claims/pharmaco_evidence.py` | `pharmaco_evalue(...)` — betting e-value over the within-tissue methylation split. |
| Create `src/polymer_claims/strata_populate.py` | The batch runner: propose → pre-register → license → residue → control instrument → seed corpus. |
| Modify `src/polymer_claims/capabilities.py` | Register `PHARMACO_ASSOC_CELL` + its trust binding. |
| Modify `src/polymer_claims/cli.py` | Add the `strata-populate` subcommand (lazy, `[strata]`-gated). |
| Modify `.gitignore` | Ignore the built `gdsc_pharmaco` contract files. |
| Create `tests/pharmaco/test_*.py` | One test module per task. |

---

### Task 1: The pharmaco SE-Contract builder

**Files:**
- Create: `src/polymer_claims/ingest/gdsc_pharmaco.py`
- Test: `tests/pharmaco/test_gdsc_pharmaco_contract.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `ingest.transform.build_contract`, `contracts.load_contract`/`clear_contract_cache`, `strata.mechanism.PATHWAY_GENES`/`parse_targets`, `strata.data.gdsc`.
- Produces: `build_pharmaco_contract(betas, aucs, tissue, *, genes, drugs, out_dir) -> str` (pure-ish, testable on synthetic dicts) and `ingest_gdsc_pharmaco(data_dir=None) -> str` (orchestrator over the real lifted data). Contract uid `gdsc_pharmaco@1`; feature ids `meth::<GENE>` and `auc::<DRUG>`; col_data per sample carries `Sample_Group` (tissue) + `tissue`.

- [ ] **Step 1: Write the failing test** (synthetic 4-line contract, 2 genes, 1 drug)

```python
# tests/pharmaco/test_gdsc_pharmaco_contract.py
from polymer_claims import contracts
from polymer_claims.ingest.gdsc_pharmaco import build_pharmaco_contract

def test_build_pharmaco_contract_roundtrips(tmp_path):
    lines = ["L1", "L2", "L3", "L4"]
    betas = {"CDKN2A": dict(zip(lines, [0.1, 0.2, 0.8, 0.9])),
             "MTAP":   dict(zip(lines, [0.15, 0.25, 0.75, 0.85]))}
    aucs = {"Palbociclib": dict(zip(lines, [0.95, 0.90, 0.55, 0.50]))}
    tissue = {"L1": "skin", "L2": "skin", "L3": "lung", "L4": "lung"}
    uid = build_pharmaco_contract(betas, aucs, tissue,
                                  genes=["CDKN2A", "MTAP"], drugs=["Palbociclib"],
                                  out_dir=tmp_path)
    assert uid == "gdsc_pharmaco@1"
    contracts.clear_contract_cache()
    # feature rows are prefixed; tissue rides col_data as Sample_Group
    manifest_p = tmp_path / "gdsc_pharmaco.json"
    text = manifest_p.read_text()
    assert "meth::CDKN2A" in text and "auc::Palbociclib" in text
    assert '"Sample_Group": "skin"' in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/pharmaco/test_gdsc_pharmaco_contract.py -v`
Expected: FAIL — `ModuleNotFoundError: ...gdsc_pharmaco`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/polymer_claims/ingest/gdsc_pharmaco.py
"""Build se:gdsc_pharmaco@1 — GDSC methylation + drug-response in one content-addressed
SE-Contract. Reuses the feature x sample contract shape: feature ids are prefixed
'meth::<GENE>' (methylation beta) and 'auc::<DRUG>' (drug-response AUC) over the same
cell-line samples; per-line tissue rides col_data (Sample_Group). Gitignored; built on demand.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


def build_pharmaco_contract(
    betas: dict[str, dict[str, str | float]],
    aucs: dict[str, dict[str, str | float]],
    tissue: dict[str, str],
    *,
    genes: list[str],
    drugs: list[str],
    out_dir,
    uid_stem: str = "gdsc_pharmaco",
) -> str:
    """Write the manifest JSON + values TSV load_contract reads. Samples = union of lines with
    a tissue; features = meth::<gene> then auc::<drug> (sorted within each block). Missing
    values -> 'nan' (adapters drop them)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    samples = sorted(tissue)
    feat_rows = [f"meth::{g}" for g in sorted(genes)] + [f"auc::{d}" for d in sorted(drugs)]

    def _val(prefix_map, key, sid):
        v = prefix_map.get(key, {}).get(sid)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "nan"
        return f"{float(v):.6f}"

    manifest = {
        "uid": f"{uid_stem}@1",
        "dim": [len(feat_rows), len(samples)],
        "assays": [{"name": "value", "ref": f"{uid_stem}.betas.tsv"}],
        "col_data": [{"sample_id": s, "Sample_Group": tissue[s], "tissue": tissue[s]} for s in samples],
        "row_data": [{"feature_id": f, "chr": "", "pos": 0} for f in feat_rows],
        "metadata": {"source": "GDSC2", "kind": "pharmaco"},
    }
    (out_dir / f"{uid_stem}.json").write_text(json.dumps(manifest, indent=2))

    lines = ["\t".join(["feature_id", *samples])]
    for g in sorted(genes):
        lines.append("\t".join([f"meth::{g}", *(_val(betas, g, s) for s in samples)]))
    for d in sorted(drugs):
        lines.append("\t".join([f"auc::{d}", *(_val(aucs, d, s) for s in samples)]))
    (out_dir / f"{uid_stem}.betas.tsv").write_text("\n".join(lines) + "\n")
    return f"{uid_stem}@1"


def ingest_gdsc_pharmaco(data_dir: str | None = None) -> str:
    """Load the lifted GDSC data, restrict to the mechanism-gene union + all drugs, and build the
    contract into the package contracts/ dir (gitignored). Returns a one-line summary."""
    from polymer_claims import contracts as _contracts
    from polymer_claims.strata.data import gdsc
    from polymer_claims.strata.mechanism import PATHWAY_GENES, TARGET_ALIAS, parse_targets

    meth = gdsc.load_gdsc_methylation()            # lines x genes
    drug = gdsc.load_gdsc_drug_response()          # long: COSMIC_ID, drug_name, auc
    ann = gdsc.load_gdsc_annotations()             # index COSMIC_ID -> tissue
    valid = set(meth.columns)
    gene_union = sorted({g for genes in PATHWAY_GENES.values() for g in genes if g in valid}
                        | set(TARGET_ALIAS.values()) & valid)
    drugs = sorted(drug["drug_name"].unique().tolist())
    lines = [str(x) for x in meth.index]
    tissue = {s: str(ann["tissue"].get(s, "unknown")) for s in lines if s in ann.index}
    betas = {g: {s: float(meth.loc[s, g]) for s in tissue if s in meth.index} for g in gene_union}
    aucs: dict[str, dict[str, float]] = {}
    for d, sub in drug.groupby("drug_name"):
        aucs[str(d)] = {str(r.COSMIC_ID): float(r.auc) for r in sub.itertuples() if str(r.COSMIC_ID) in tissue}
    uid = build_pharmaco_contract(betas, aucs, tissue, genes=gene_union, drugs=drugs,
                                  out_dir=Path(_contracts.__file__).parent)
    _contracts.clear_contract_cache()
    ref = _contracts.load_contract(f"se:{uid}")
    return f"ingested {uid}: {ref.dimnames_hash[:16]}… ({len(tissue)} lines, {len(gene_union)} genes, {len(drugs)} drugs)"
```

Add `from pathlib import Path` usage note: `ingest_gdsc_pharmaco` references `Path`; it is already imported at module top.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/pharmaco/test_gdsc_pharmaco_contract.py -v`
Expected: PASS.

- [ ] **Step 5: Gitignore the built contract**

Add to `.gitignore` under the pharmaco block:
```
src/polymer_claims/contracts/gdsc_pharmaco.json
src/polymer_claims/contracts/gdsc_pharmaco.betas.tsv
```

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/ingest/gdsc_pharmaco.py tests/pharmaco/test_gdsc_pharmaco_contract.py .gitignore
git commit -m "feat(pharmaco): SE-Contract builder for GDSC methylation + drug-response"
```

---

### Task 2: The two independent recompute legs

**Files:**
- Create: `src/polymer_claims/pharmaco_adapters.py` (legs + read helper only in this task)
- Test: `tests/pharmaco/test_pharmaco_adapters.py`

**Interfaces:**
- Consumes: `methyl_adapters._load_betas` (the contract read), `polymer_grammar.ExecValue`/`OperationNode`.
- Produces:
  - `_pharmaco_split(node) -> tuple[list[float], list[float]]` — returns (high-meth-group AUCs, low-meth-group AUCs), median-split **within each tissue** on the marker's methylation, pooled across tissues. Reads params `marker`, `drug`.
  - `class PharmacoMeanDiffAdapter` (`identity="pharmaco-meandiff"`) — leg A; `execute` returns `ExecValue(mean(low) - mean(high))` (positive = high-meth more sensitive).
  - `class PharmacoRankAdapter` (`identity="pharmaco-rank"`) — leg B; `execute` returns the Hodges–Lehmann location shift of (low − high) pairwise diffs.
- Direction convention: value > 0 ⇔ high-methylation lines are more sensitive (lower AUC).

- [ ] **Step 1: Write the failing test**

```python
# tests/pharmaco/test_pharmaco_adapters.py
from polymer_grammar import DataHandle, OperationNode
from polymer_claims import contracts
from polymer_claims.ingest.gdsc_pharmaco import build_pharmaco_contract
from polymer_claims.pharmaco_adapters import PharmacoMeanDiffAdapter, PharmacoRankAdapter

def _node(ref, marker, drug):
    return OperationNode(id="n", impl="pharmaco::assoc",
                         inputs=(DataHandle(ref=ref),),
                         params=(("marker", marker), ("drug", drug)))

def _contract(tmp_path):
    lines = [f"L{i}" for i in range(8)]
    # high-meth (L4..L7) are sensitive (low AUC); low-meth (L0..L3) resistant (high AUC)
    betas = {"CDKN2A": {l: (0.1 if i < 4 else 0.9) for i, l in enumerate(lines)}}
    aucs = {"Palbociclib": {l: (0.95 if i < 4 else 0.55) for i, l in enumerate(lines)}}
    tissue = {l: ("skin" if i < 4 else "lung") for i, l in enumerate(lines)}
    # split within tissue: give each tissue both hi and lo meth so the within-tissue split is real
    betas["CDKN2A"] = {l: (0.1 if i % 2 == 0 else 0.9) for i, l in enumerate(lines)}
    aucs["Palbociclib"] = {l: (0.95 if i % 2 == 0 else 0.55) for i, l in enumerate(lines)}
    return build_pharmaco_contract(betas, aucs, tissue, genes=["CDKN2A"],
                                   drugs=["Palbociclib"], out_dir=tmp_path)

def test_both_legs_positive_on_planted_sensitivity(tmp_path, monkeypatch):
    monkeypatch.setenv("STRATA_DATA_ROOT", str(tmp_path))  # not used; contract read is by path
    ref = "se:" + _contract(tmp_path)
    contracts.clear_contract_cache()
    monkeypatch.setattr(contracts, "_CONTRACT_DIR", tmp_path, raising=False)
    node = _node(ref, "CDKN2A", "Palbociclib")
    a = PharmacoMeanDiffAdapter().execute(node, (), None).value
    b = PharmacoRankAdapter().execute(node, (), None).value
    assert a > 0 and b > 0   # high-meth lines are more sensitive
```

> Note: `contracts.load_contract` resolves the contract from the package `contracts/` dir. For the test, either build into that dir via `ingest_gdsc_pharmaco`-style placement, or (simpler) build into `tmp_path` and point the contract loader at it. Read `src/polymer_claims/contracts/__init__.py` for the exact resolution knob (`_CONTRACT_DIR` or `load_contract`'s search path) and adjust the monkeypatch to match the real attribute name.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/pharmaco/test_pharmaco_adapters.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

```python
# src/polymer_claims/pharmaco_adapters.py  (Task 2 portion)
"""Two INDEPENDENT legs recompute a marker->drug association over the pharmaco SE-Contract.
Leg A (mean difference of within-tissue-split AUCs; feeds the e-value) vs leg B (Hodges-Lehmann
location shift; corroborating air-gap gate). Median-split on the marker's methylation is done
WITHIN each tissue (tissue-adjusted) and is monotone-invariant (the measurement-seam requirement).
Umbrella/impure. NOT re-exported from __init__ (base import stays numpy-free)."""
from __future__ import annotations

import numpy as np
from polymer_grammar import ExecValue, OperationNode

from .methyl_adapters import _load_betas

_IMPL = "pharmaco::assoc"


def _pharmaco_split(node: OperationNode) -> tuple[list[float], list[float]]:
    """(high-meth AUCs, low-meth AUCs), median-split within each tissue on marker methylation,
    pooled across tissues. Drops lines missing either value. Raises on empty groups."""
    beta, sample_ids, tissue_of, p = _load_betas(node)   # tissue_of = col_data[group_col]
    marker_row, drug_row = f"meth::{p['marker']}", f"auc::{p['drug']}"
    if marker_row not in beta or drug_row not in beta:
        raise KeyError(f"missing {marker_row!r} or {drug_row!r} in contract")
    meth, auc = beta[marker_row], beta[drug_row]
    hi: list[float] = []
    lo: list[float] = []
    # group lines by tissue
    by_tissue: dict[str, list[str]] = {}
    for s in sample_ids:
        m, a = meth.get(s), auc.get(s)
        if m is None or a is None or np.isnan(m) or np.isnan(a):
            continue
        by_tissue.setdefault(tissue_of[s], []).append(s)
    for _, members in by_tissue.items():
        if len(members) < 2:
            continue
        med = float(np.median([meth[s] for s in members]))
        for s in members:
            (hi if meth[s] > med else lo).append(auc[s])
    if not hi or not lo:
        raise ValueError("empty methylation split group")
    return hi, lo


class PharmacoMeanDiffAdapter:
    """Independent leg A — mean(low-meth AUC) - mean(high-meth AUC). Positive => high-meth
    lines are more sensitive (lower AUC). Feeds the e-value."""

    identity = "pharmaco-meandiff"

    def execute(self, node, upstream, ctx) -> ExecValue:
        hi, lo = _pharmaco_split(node)
        return ExecValue(value=(sum(lo) / len(lo)) - (sum(hi) / len(hi)))


class PharmacoRankAdapter:
    """Independent leg B — Hodges-Lehmann location shift: median of all pairwise (lo_j - hi_i).
    Rank-family, robust to AUC tails; a genuinely different estimator from leg A. Corroborating
    air-gap gate (CapabilityCell.agreement_mode='both_satisfy_criterion'), never feeds the e-value."""

    identity = "pharmaco-rank"

    def execute(self, node, upstream, ctx) -> ExecValue:
        hi, lo = _pharmaco_split(node)
        h = np.asarray(hi, dtype=float)
        lo_arr = np.asarray(lo, dtype=float)
        pairwise = (lo_arr[:, None] - h[None, :]).ravel()
        return ExecValue(value=float(np.median(pairwise)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/pharmaco/test_pharmaco_adapters.py -v`
Expected: PASS (both leg values positive).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/pharmaco_adapters.py tests/pharmaco/test_pharmaco_adapters.py
git commit -m "feat(pharmaco): two independent recompute legs (mean-diff + Hodges-Lehmann)"
```

---

### Task 3: The marker→drug betting e-value

**Files:**
- Create: `src/polymer_claims/pharmaco_evidence.py`
- Test: `tests/pharmaco/test_pharmaco_evidence.py`

**Interfaces:**
- Consumes: `evidence.betting_evalue`, `pharmaco_adapters._pharmaco_split`, `polymer_grammar.Comparator`.
- Produces: `pharmaco_evalue(node, *, threshold: float, comparator=Comparator.GT) -> float` — betting e-value that high-meth lines are more sensitive by more than `threshold`. Uses **leg A's split only**.

- [ ] **Step 1: Write the failing test**

```python
# tests/pharmaco/test_pharmaco_evidence.py
from polymer_grammar import Comparator, DataHandle, OperationNode
from polymer_claims.ingest.gdsc_pharmaco import build_pharmaco_contract
from polymer_claims import contracts
from polymer_claims.pharmaco_evidence import pharmaco_evalue

def _node(ref): return OperationNode(id="n", impl="pharmaco::assoc",
    inputs=(DataHandle(ref=ref),), params=(("marker", "G"), ("drug", "D")))

def test_evalue_high_on_signal_low_on_null(tmp_path, monkeypatch):
    lines = [f"L{i}" for i in range(40)]
    # planted signal: even lines low-meth/resistant, odd lines high-meth/sensitive, both tissues
    betas = {"G": {l: (0.1 if i % 2 == 0 else 0.9) for i, l in enumerate(lines)}}
    aucs_sig = {"D": {l: (0.9 if i % 2 == 0 else 0.4) for i, l in enumerate(lines)}}
    aucs_null = {"D": {l: 0.7 for l in lines}}
    tissue = {l: ("a" if i < 20 else "b") for i, l in enumerate(lines)}
    monkeypatch.setattr(contracts, "_CONTRACT_DIR", tmp_path, raising=False)
    ref_sig = "se:" + build_pharmaco_contract(betas, aucs_sig, tissue, genes=["G"], drugs=["D"], out_dir=tmp_path)
    contracts.clear_contract_cache()
    e_sig = pharmaco_evalue(_node(ref_sig), threshold=0.0, comparator=Comparator.GT)
    ref_null = "se:" + build_pharmaco_contract(betas, aucs_null, tissue, genes=["G"], drugs=["D"], out_dir=tmp_path, uid_stem="gdsc_pharmaco")  # overwrite
    contracts.clear_contract_cache()
    e_null = pharmaco_evalue(_node(ref_null), threshold=0.0, comparator=Comparator.GT)
    assert e_sig > 2.0        # accrues capital against the null
    assert e_null < 1.5       # no license-worthy evidence
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/pharmaco/test_pharmaco_evidence.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

```python
# src/polymer_claims/pharmaco_evidence.py
"""The native e-value for a marker->drug association: a Waudby-Smith & Ramdas betting e-value
(evidence.betting_evalue) over leg A's within-tissue methylation split of the drug AUCs. Tests the
severe null that high-meth lines are NOT more sensitive by more than `threshold`. One leg only —
the rank leg is a corroborating gate, never a factor in the e-value (mirrors n-DMP)."""
from __future__ import annotations

from polymer_grammar import Comparator, OperationNode

from .evidence import betting_evalue
from .pharmaco_adapters import _pharmaco_split


def pharmaco_evalue(node: OperationNode, *, threshold: float, comparator: Comparator = Comparator.GT) -> float:
    """betting_evalue tests mu_b - mu_a > threshold. a = high-meth AUCs, b = low-meth AUCs, so
    a positive shift (low-meth AUC higher) = high-meth more sensitive. Bounded [0,1] AUCs."""
    hi, lo = _pharmaco_split(node)
    return betting_evalue(hi, lo, threshold=threshold, comparator=comparator)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/pharmaco/test_pharmaco_evidence.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/pharmaco_evidence.py tests/pharmaco/test_pharmaco_evidence.py
git commit -m "feat(pharmaco): marker->drug betting e-value (single leg, within-tissue split)"
```

---

### Task 4: Capability cell, oracle, registry, and the claim factory

**Files:**
- Modify: `src/polymer_claims/capabilities.py` (add `PHARMACO_ASSOC_CELL` to `CAPABILITY_CELLS` and a binding in `_bindings()`)
- Modify: `src/polymer_claims/pharmaco_adapters.py` (add factory + registries)
- Test: `tests/pharmaco/test_pharmaco_claim.py`

**Interfaces:**
- Consumes: `polymer_grammar.capability.CapabilityCell`/`build_evaluation_plan`/`SubjectRequirement`/`OracleRequirement`/`ParamCodec`/`DataRefKind`, `polymer_grammar` subject/leaf/provenance types, `polymer_protocol.{AdapterRegistry,AdapterCredential,OracleRegistry}`, `polymer_grammar.oracle.{OracleDossier,ApplicabilityDomain,ValidationTier}`, `adapter_identity.implementation_hash_for_adapter`.
- Produces:
  - `PHARMACO_ASSOC_CELL` (capability `pharmaco::assoc@v1`, `agreement_mode="both_satisfy_criterion"`, subject required kind `composite`, eligible adapters `("pharmaco-meandiff","pharmaco-rank")`, `data_ref_kind=SE_CONTRACT`).
  - `pharmaco_independent_registry() -> AdapterRegistry`.
  - `pharmaco_oracle_id() -> str` and `pharmaco_oracle_registry() -> OracleRegistry` (a BENCHMARKED apparatus whose `ApplicabilityDomain.subject_kinds=("composite",)` admits the gene/drug subject).
  - `marker_drug_claim(claim_id, *, ref, marker, drug, drug_chebi_uri, tissue_adjusted=True, threshold=0.0, comparator=Comparator.GT, search_cardinality, agent_id="strata-mechanism-v1", prior_cohorts=(), strength=None) -> Claim`. **No `r_adj` parameter — STRATA's statistic never enters the claim.**

- [ ] **Step 1: Write the failing test**

```python
# tests/pharmaco/test_pharmaco_claim.py
from polymer_grammar import Status
from polymer_claims.pharmaco_adapters import marker_drug_claim, pharmaco_oracle_registry
from polymer_claims.capabilities import CAPABILITY_CELLS, bind

def test_cell_registered_and_binding_resolves():
    assert CAPABILITY_CELLS.resolve("pharmaco::assoc", "v1") is not None
    b = bind("pharmaco::assoc", "v1")           # must not raise
    assert b.trust_profile

def test_marker_drug_claim_shape():
    c = marker_drug_claim(
        "pgx-CDKN2A-Palbociclib", ref="se:gdsc_pharmaco@1", marker="CDKN2A",
        drug="Palbociclib", drug_chebi_uri="http://purl.obolibrary.org/obo/CHEBI_85993",
        search_cardinality=8)
    assert c.status == Status.PENDING
    assert c.pattern.id == "adjusted_effect"
    assert c.subject.kind == "composite" and len(c.subject.parts) == 2
    assert c.leaves[0].kind == "categorical"     # Polymer-native; no STRATA r_adj in the claim
    assert c.provenance.generated_by.value == "agent_generated"
    assert c.provenance.agent_id == "strata-mechanism-v1"
    # composite subject is admitted by the apparatus domain
    dom = pharmaco_oracle_registry().dossiers[0].applicability_domain
    assert "composite" in dom.subject_kinds
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/pharmaco/test_pharmaco_claim.py -v`
Expected: FAIL — `marker_drug_claim`/cell not defined.

- [ ] **Step 3a: Register the cell + binding in `capabilities.py`**

After `N_DMPS_CELL` (mirror its constructor; note `claim_leaf_kinds` now includes `"quantity"`):
```python
PHARMACO_ASSOC_CELL = CapabilityCell(
    capability_id="pharmaco::assoc", capability_version="v1", operation_impl="pharmaco::assoc",
    title="marker->drug tissue-adjusted association", pattern=_PATTERN,
    subject=SubjectRequirement(mode="required", kind="composite"),
    param_schema=(_STR(name="marker", codec="string"), _STR(name="drug", codec="string")),
    produced=_Q, allowed_comparators=_ALL_CMP,
    eligible_adapter_identities=("pharmaco-meandiff", "pharmaco-rank"),
    oracle=OracleRequirement(default_oracle_id="gdsc_pharmaco_apparatus", required=True),
    data_ref_kind=DataRefKind.SE_CONTRACT, claim_leaf_kinds=("categorical",),
    criterion_target="threshold", agreement_mode="both_satisfy_criterion",
)
```
Add `PHARMACO_ASSOC_CELL` to the `CAPABILITY_CELLS = CapabilityRegistry(cells=(...))` tuple. In `_bindings()`, add:
```python
from .pharmaco_adapters import pharmaco_independent_registry, pharmaco_oracle_registry
...
("pharmaco::assoc", "v1"): CapabilityTrustBinding(
    adapter_registry=pharmaco_independent_registry(),
    oracle_registry=pharmaco_oracle_registry(),
    trust_profile="gdsc-pharmaco-recomputable-public"),
```

- [ ] **Step 3b: Add the factory + registries to `pharmaco_adapters.py`**

```python
# appended to src/polymer_claims/pharmaco_adapters.py
from polymer_grammar import (
    CategoricalLeaf, Claim, Comparator, CompositeSubject, GeneOrProtein,
    OntologyTerm, PatternRef, PendingReason,
    SatisfactionCriterion, Status, StrengthVector,
)
from polymer_grammar.subject import GeneOrProteinIdentifiers
from polymer_grammar.provenance import GenerationMode, Provenance
from polymer_protocol import AdapterCredential, AdapterRegistry, OracleRegistry
from polymer_grammar.oracle import ApplicabilityDomain, OracleDossier, ValidationTier

from .adapter_identity import implementation_hash_for_adapter

_PHARMACO_ORACLE_ID = "gdsc_pharmaco_apparatus"


def pharmaco_oracle_id() -> str:
    return _PHARMACO_ORACLE_ID


def pharmaco_oracle_registry() -> OracleRegistry:
    """BENCHMARKED GDSC apparatus admitting the composite gene/drug subject."""
    return OracleRegistry(dossiers=(OracleDossier(
        oracle_id=_PHARMACO_ORACLE_ID, validation_tier=ValidationTier.BENCHMARKED,
        applicability_domain=ApplicabilityDomain(subject_kinds=("composite",)),
        anchor="gdsc-pharmaco-v1"),))


def pharmaco_independent_registry() -> AdapterRegistry:
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="pharmaco-meandiff", owner="owner-meandiff",
                          implementation_hash=implementation_hash_for_adapter(PharmacoMeanDiffAdapter)),
        AdapterCredential(identity="pharmaco-rank", owner="owner-rank",
                          implementation_hash=implementation_hash_for_adapter(PharmacoRankAdapter)),
    ))


def marker_drug_claim(
    claim_id: str, *, ref: str, marker: str, drug: str, drug_chebi_uri: str,
    threshold: float = 0.0, comparator: Comparator = Comparator.GT,
    search_cardinality: int, agent_id: str = "strata-mechanism-v1",
    prior_cohorts: tuple[str, ...] = (), preregistration_hash: str | None = None,
    strength: StrengthVector | None = None,
) -> Claim:
    """PENDING adjusted-association claim: gene-G methylation is associated (tissue-adjusted) with
    drug-D response. Pattern adjusted_effect@v1 (association, NOT a causal edge). CategoricalLeaf
    per shipped Polymer practice; the computed ΔAUC lives in the verify result — STRATA's r_adj
    never enters the claim. Composite (gene, CHEBI drug) subject. AGENT_GENERATED."""
    from .capabilities import PHARMACO_ASSOC_CELL
    from polymer_grammar.capability import build_evaluation_plan

    plan = build_evaluation_plan(
        PHARMACO_ASSOC_CELL, params={"marker": marker, "drug": drug}, data_ref=ref,
        criterion=SatisfactionCriterion(comparator=comparator, threshold=float(threshold)),
        oracle_ref=_PHARMACO_ORACLE_ID)
    subject = CompositeSubject(
        id=f"{marker}~{drug}", display=f"{marker} methylation ~ {drug} response", relation="correlational",
        parts=(
            GeneOrProtein(id=f"HGNC:{marker}", display=marker, entity_type="gene",
                          identifiers=GeneOrProteinIdentifiers(hgnc=marker, symbol=marker)),
            OntologyTerm(id=f"CHEBI:{drug}", display=drug, ontology="CHEBI",
                         ontology_release="unknown", uri=drug_chebi_uri),
        ))
    return Claim(
        id=claim_id, title=f"{marker} methylation ~ {drug} sensitivity (tissue-adjusted)",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="pharmacogenomic_association"),),
        status=Status.PENDING, pending_reason=PendingReason.UNTESTED, strength=strength,
        subject=subject, evaluation_plan=plan,
        provenance=Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id=agent_id,
                              search_cardinality=int(search_cardinality),
                              preregistration_hash=preregistration_hash, prior_cohorts=prior_cohorts,
                              rationale=f"mechanism-anchored proposal: {marker} in {drug}'s target/pathway"))
```

> If `CompositeSubject`/`CategoricalLeaf`/`OntologyTerm`/`GeneOrProtein` are not re-exported from the `polymer_grammar` top-level, import them from `polymer_grammar.subject` / `polymer_grammar.leaf`. Verify against `grammar/src/polymer_grammar/__init__.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/pharmaco/test_pharmaco_claim.py -v`
Expected: PASS (cell registered, binding resolves, claim shape correct, composite in domain).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/capabilities.py src/polymer_claims/pharmaco_adapters.py tests/pharmaco/test_pharmaco_claim.py
git commit -m "feat(pharmaco): capability cell, apparatus oracle, registry, and claim factory"
```

---

### Task 5: The batch runner core — propose, pre-register, residue

**Files:**
- Create: `src/polymer_claims/strata_populate.py` (proposal + pre-registration + residue; licensing wired in Task 6)
- Test: `tests/pharmaco/test_strata_populate.py`

**Interfaces:**
- Consumes: `strata.mechanism.rank_mechanism_opportunities`/`load_inputs`, `pharmaco_adapters.marker_drug_claim`, `grammar.fdr.{register_test}`, `grammar.commitment.commitment_hash`.
- Produces:
  - `propose_claims(res_df, *, ref, chebi_of, agent_id="strata-mechanism-v1") -> list[Claim]` — one `marker_drug_claim` per mechanism-scan row, `search_cardinality` = that drug's tested-gene count.
  - `preregister(corpus, claims) -> Corpus` — locks an e-LOND slot per claim via `register_test(ledger, claim.id, commitment_hash(claim))` **before** any e-value.
  - A CHEBI lookup shim `chebi_of: dict[str, str]` (drug → CHEBI uri); unknown drugs are skipped with a logged count (no silent drop).

- [ ] **Step 1: Write the failing test** (synthetic scan rows; no network)

```python
# tests/pharmaco/test_strata_populate.py
import pandas as pd
from polymer_claims.strata_populate import propose_claims

def test_propose_sets_search_cardinality_and_skips_unknown_chebi(caplog):
    res = pd.DataFrame([
        {"drug": "Palbociclib", "marker": "MTAP", "r_adj": -0.20, "level": "L3", "n_genes_tested": 8},
        {"drug": "MysteryDrug", "marker": "FOO", "r_adj": -0.15, "level": "L2", "n_genes_tested": 3},
    ])
    chebi = {"Palbociclib": "http://purl.obolibrary.org/obo/CHEBI_85993"}
    claims = propose_claims(res, ref="se:gdsc_pharmaco@1", chebi_of=chebi)
    assert len(claims) == 1                       # MysteryDrug skipped (no CHEBI)
    assert claims[0].provenance.search_cardinality == 8
```

> `rank_mechanism_opportunities` (Task from the lift) returns columns `drug, pathway, marker, level, r_adj, rho_pooled, p_adj, retained, within_sig, n_tissues`. Add the per-drug tested-gene count as `n_genes_tested` in `propose_claims` by re-deriving `len(genes)` from `mechanism.PATHWAY_GENES`/`parse_targets`, OR extend `rank_mechanism_opportunities` to emit it. The honest `search_cardinality` is the count of genes actually evaluated for that drug.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/pharmaco/test_strata_populate.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

```python
# src/polymer_claims/strata_populate.py  (Task 5 portion)
"""Batch runner: turn STRATA mechanism-scan rows into pre-registered, licensable claims.
STRATA is an untrusted proposer; standing is conferred only in Task 6's run_cycle pass."""
from __future__ import annotations

import logging

from polymer_grammar.commitment import commitment_hash
from polymer_grammar.fdr import register_test

from .pharmaco_adapters import marker_drug_claim

log = logging.getLogger(__name__)


def propose_claims(res_df, *, ref, chebi_of, agent_id="strata-mechanism-v1"):
    """One marker_drug_claim per scan row whose drug has a CHEBI uri. search_cardinality =
    the row's n_genes_tested (falls back to 1). Skipped-for-no-CHEBI count is logged, not silent."""
    claims, skipped = [], 0
    for r in res_df.itertuples():
        uri = chebi_of.get(str(r.drug))
        if uri is None:
            skipped += 1
            continue
        claims.append(marker_drug_claim(
            f"pgx-{r.marker}-{r.drug}", ref=ref, marker=str(r.marker), drug=str(r.drug),
            drug_chebi_uri=uri,
            search_cardinality=int(getattr(r, "n_genes_tested", 1) or 1), agent_id=agent_id))
    if skipped:
        log.warning("propose_claims: skipped %d rows lacking a CHEBI uri", skipped)
    return claims


def preregister(corpus, claims):
    """Lock an e-LOND slot per claim (commitment_hash over the plan) BEFORE any e-value.
    Mirrors protocol/register.py usage; returns the corpus with a charged fdr_ledger."""
    ledger = corpus.fdr_ledger
    for c in claims:
        ledger = register_test(ledger, c.id, commitment_hash(c))
    return corpus.model_copy(update={"fdr_ledger": ledger})
```

> Read `protocol/src/polymer_protocol/register.py` and `grammar/src/polymer_grammar/fdr.py::register_test` to confirm the `Corpus.fdr_ledger` field name and whether a higher-level `register_hypotheses` helper should be used instead of hand-charging. Prefer the existing helper if present.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/pharmaco/test_strata_populate.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/strata_populate.py tests/pharmaco/test_strata_populate.py
git commit -m "feat(pharmaco): batch proposal + pre-registration (untrusted proposer)"
```

---

### Task 6: License the batch — run_cycle wiring, REPRODUCED tier, residue

**Files:**
- Modify: `src/polymer_claims/strata_populate.py` (add `license_batch`)
- Test: `tests/pharmaco/test_strata_license.py`

**Interfaces:**
- Consumes: `protocol.run_cycle`, `pharmaco_adapters.{pharmaco_independent_registry, pharmaco_oracle_registry, PharmacoMeanDiffAdapter, PharmacoRankAdapter}`, `pharmaco_evidence.pharmaco_evalue`, `capabilities.CAPABILITY_CELLS`.
- Produces: `license_batch(corpus, claims, *, ref, shared_cause_factors) -> Corpus` — runs the two legs + registry + per-claim evidence through `run_cycle`, populates `shared_cause_factors` on every materialization so the §E gate fires (within-GDSC ⇒ REPRODUCED), and leaves non-satisfying claims PENDING.

**Read first:** `src/polymer_claims/real_kernel_proof.py` — it licenses the real n-DMP claim end-to-end via `run_cycle`. Mirror its `materializations`/`evidence`/`adapter_registry`/`oracles` wiring; substitute the pharmaco cell, adapters, registry, oracle, and the `pharmaco_evalue` evidence map.

- [ ] **Step 1: Write the failing test** (on a synthetic contract with a planted positive control and a planted null)

```python
# tests/pharmaco/test_strata_license.py — behavior: planted signal licenses at REPRODUCED; null stays PENDING
from polymer_grammar import Status
from polymer_grammar.licensing import IndependenceTier
# ... build a synthetic gdsc_pharmaco contract with two markers/drugs (one strong, one null),
#     propose + preregister + license_batch, then assert:
def test_signal_licenses_reproduced_null_pending(...):
    licensed = [c for c in out.claims if c.status == Status.LICENSED]
    pending  = [c for c in out.claims if c.status == Status.PENDING]
    assert any(c.id == "pgx-G1-D1" for c in licensed)      # planted signal
    assert any(c.id == "pgx-G2-D2" for c in pending)       # planted null = residue, not rejected
    sat = licensed[0].licensing.satisfactions[0]           # exact accessor per grammar/licensing.py
    assert sat.independence_tier == IndependenceTier.REPRODUCED
```

> Fill the `...` by mirroring the synthetic-contract construction in Tasks 2–3 and the `run_cycle` call in `real_kernel_proof.py`. Confirm the `Satisfaction`/`independence_tier` accessor names against `grammar/src/polymer_grammar/licensing.py` before finalizing the asserts.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/pharmaco/test_strata_license.py -v`
Expected: FAIL — `license_batch` not defined.

- [ ] **Step 3: Write minimal implementation** (mirror `real_kernel_proof.py`)

```python
# appended to src/polymer_claims/strata_populate.py
from .pharmaco_adapters import (
    PharmacoMeanDiffAdapter, PharmacoRankAdapter,
    pharmaco_independent_registry, pharmaco_oracle_registry,
)
from .pharmaco_evidence import pharmaco_evalue


def _evidence_for(claims, *, threshold=0.0):
    """Per-claim e-value from leg A's split (single leg). Skips claims whose contract read fails."""
    from .evidence import _terminal_node
    from polymer_grammar import Comparator
    out = {}
    for c in claims:
        node = _terminal_node(c)
        if node is None:
            continue
        try:
            out[c.id] = pharmaco_evalue(node, threshold=threshold, comparator=Comparator.GT)
        except (FileNotFoundError, KeyError, ValueError):
            continue
    return out


def license_batch(corpus, claims, *, ref, shared_cause_factors):
    """Run the two legs + registry + evidence through run_cycle. shared_cause_factors is populated
    on every materialization (GDSC manifest/normalization/reference/library/panel) so the §E gate
    fires and within-GDSC tiers resolve to REPRODUCED — never a laundered REPLICATED. Mirror the
    run_cycle invocation in real_kernel_proof.py for the exact materialization/ctx wiring."""
    adapters = (PharmacoMeanDiffAdapter(), PharmacoRankAdapter())
    evidence = _evidence_for(claims)
    # NOTE: assemble `materializations` with shared_cause_factors exactly as real_kernel_proof.py
    # does, then:
    result = run_cycle(  # noqa: F821 — import run_cycle from polymer_protocol at module top
        corpus, adapters, ctx,                       # ctx per real_kernel_proof.py
        adapter_registry=pharmaco_independent_registry(),
        oracles=pharmaco_oracle_registry(),
        evidence=evidence,
        materializations=materializations,           # carries shared_cause_factors
        capability_registry=CAPABILITY_CELLS,        # from .capabilities
    )
    return result.corpus
```

> This task's exact `ctx` + `materializations` construction is copied from `real_kernel_proof.py`. Add `from polymer_protocol import run_cycle` and `from .capabilities import CAPABILITY_CELLS` at module top. The `shared_cause_factors` tuple must list the GDSC-shared causes: `("gdsc2-manifest", "gdsc-imputed-normalization", "hg38", "cell-model-passports", "scipy-statsmodels")`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/pharmaco/test_strata_license.py -v`
Expected: PASS — signal LICENSED @ REPRODUCED; null PENDING.

- [ ] **Step 5: Add the tier-trap regression test**

```python
def test_empty_shared_cause_never_mints_replicated(...):
    # same as above but with shared_cause_factors=() ; assert the tier is NOT REPLICATED
    # (documents that empty factors are forbidden — see licensing.py:182-183 fallback).
    assert sat.independence_tier != IndependenceTier.REPLICATED
```

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/strata_populate.py tests/pharmaco/test_strata_license.py
git commit -m "feat(pharmaco): license the batch via run_cycle at REPRODUCED tier (no laundered REPLICATED)"
```

---

### Task 7: The control instrument + publish guard

**Files:**
- Modify: `src/polymer_claims/strata_populate.py` (add `check_controls` + `populate_universe`)
- Test: `tests/pharmaco/test_pharmaco_controls.py`

**Interfaces:**
- Produces:
  - `check_controls(corpus) -> dict` — reports whether `pgx-MTAP-Palbociclib` is LICENSED and `pgx-MGMT-Temozolomide` is not-LICENSED; returns `{"ok": bool, "positive_licensed": bool, "negative_licensed": bool}`. Changes **no** claim status.
  - `populate_universe(res_df, *, ref, chebi_of, shared_cause_factors, require_controls=True) -> Corpus` — end-to-end propose → preregister → license_batch → `check_controls`; raises `ControlCheckFailed` if `require_controls` and `not ok`. This is the publish guard.

- [ ] **Step 1: Write the failing test**

```python
# tests/pharmaco/test_pharmaco_controls.py
import pytest
from polymer_claims.strata_populate import check_controls, ControlCheckFailed, populate_universe

def test_publish_guard_raises_when_positive_control_fails(monkeypatch, ...):
    # build a corpus where the positive control did NOT license
    with pytest.raises(ControlCheckFailed):
        populate_universe(res_df, ref=ref, chebi_of=chebi,
                          shared_cause_factors=(...,), require_controls=True)

def test_check_controls_changes_no_status(...):
    before = {c.id: c.status for c in corpus.claims}
    check_controls(corpus)
    after = {c.id: c.status for c in corpus.claims}
    assert before == after     # instrument, not a gate
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/pharmaco/test_pharmaco_controls.py -v`
Expected: FAIL — names not defined.

- [ ] **Step 3: Write minimal implementation**

```python
# appended to src/polymer_claims/strata_populate.py
from polymer_grammar import Status


class ControlCheckFailed(RuntimeError):
    """The publish guard: a control behaved wrong (positive did not license, or negative did)."""


def check_controls(corpus, *, positive="pgx-MTAP-Palbociclib", negative="pgx-MGMT-Temozolomide"):
    by_id = {c.id: c for c in corpus.claims}
    pos = by_id.get(positive)
    neg = by_id.get(negative)
    positive_licensed = pos is not None and pos.status == Status.LICENSED
    negative_licensed = neg is not None and neg.status == Status.LICENSED
    return {"ok": positive_licensed and not negative_licensed,
            "positive_licensed": positive_licensed, "negative_licensed": negative_licensed}


def populate_universe(res_df, *, ref, chebi_of, shared_cause_factors, require_controls=True,
                      agent_id="strata-mechanism-v1"):
    from polymer_protocol.corpus import Corpus  # empty seed corpus
    corpus = Corpus()  # or the project's canonical empty-corpus constructor
    claims = propose_claims(res_df, ref=ref, chebi_of=chebi_of, agent_id=agent_id)
    corpus = corpus.model_copy(update={"claims": corpus.claims + tuple(claims)})
    corpus = preregister(corpus, claims)
    corpus = license_batch(corpus, claims, ref=ref, shared_cause_factors=shared_cause_factors)
    report = check_controls(corpus)
    if require_controls and not report["ok"]:
        raise ControlCheckFailed(f"control instrument failed: {report}")
    return corpus
```

> Confirm the canonical empty-`Corpus` constructor and how claims are injected into a corpus (there may be a helper like `seed_corpus`/`with_claims`). Read `protocol/src/polymer_protocol/corpus.py` and `src/polymer_claims/seed.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/pharmaco/test_pharmaco_controls.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/strata_populate.py tests/pharmaco/test_pharmaco_controls.py
git commit -m "feat(pharmaco): control instrument + publish guard (changes no claim status)"
```

---

### Task 8: CLI wiring + the real-data control-recovery integration test

**Files:**
- Modify: `src/polymer_claims/cli.py` (add `strata-populate`)
- Test: `tests/pharmaco/test_strata_cli.py` (help/smoke) and `tests/pharmaco/test_real_controls_slow.py` (data-gated)

**Interfaces:**
- Produces: CLI `polymer-claims strata-populate [--data-dir PATH] [--no-require-controls]` → ingests the contract (if absent), builds the drug→CHEBI map, runs `populate_universe`, prints a machine-clean JSON summary to stdout. Lazy imports so core import is clean without `[strata]`.

- [ ] **Step 1: Write the failing CLI smoke test**

```python
# tests/pharmaco/test_strata_cli.py
import subprocess, sys
def test_strata_populate_in_help():
    out = subprocess.run([sys.executable, "-m", "polymer_claims.cli", "--help"],
                         capture_output=True, text=True)
    assert "strata-populate" in out.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/pharmaco/test_strata_cli.py -v`
Expected: FAIL — subcommand absent.

- [ ] **Step 3: Add the subcommand to `cli.py`**

Mirror the existing `verify-kernel`/`ingest` subcommand registration (parser at the `verify-kernel` block). Add a `strata-populate` subparser and a `_cmd_strata_populate(args)` that lazy-imports `strata_populate.populate_universe` + `ingest.gdsc_pharmaco.ingest_gdsc_pharmaco`, emits summaries to **stderr** and the JSON result to **stdout** (machine-clean convention — see the Tier-A audit note in `ARCHITECTURE_CURRENT.md`). Missing `[strata]` extra → stderr hint + exit 1 (mirror `run-cycle --llm`).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/pharmaco/test_strata_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Add the data-gated real-control integration test**

```python
# tests/pharmaco/test_real_controls_slow.py
import os, pytest
pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.expanduser(
        os.environ.get("STRATA_DATA_ROOT", "")) + "/gdsc/methylation_imputed.csv.gz")
    and not os.path.exists(
        __import__("polymer_claims.strata.config", fromlist=["DATA_DIR"]).DATA_DIR / "gdsc/methylation_imputed.csv.gz"),
    reason="real GDSC data not present (gitignored)")

def test_real_positive_control_licenses_negative_does_not():
    from polymer_claims.ingest.gdsc_pharmaco import ingest_gdsc_pharmaco
    from polymer_claims.strata.mechanism import load_inputs, rank_mechanism_opportunities
    from polymer_claims.strata_populate import populate_universe, check_controls
    ingest_gdsc_pharmaco()
    res = rank_mechanism_opportunities(*load_inputs())
    # ... build chebi_of for the controls, run populate_universe(require_controls=False),
    #     then assert check_controls(corpus)["ok"] is True.
```

> This test is slow (loads the full matrix + reads the 21M xlsx) and data-gated; it must be excluded from core CI (mark `slow`, run only under the `[strata]` extra). It is the end-to-end proof that MTAP→Palbociclib licenses and MGMT→Temozolomide does not on real data.

- [ ] **Step 6: Run the full local suite**

Run: `uv run ruff check src/polymer_claims/ tests/pharmaco/ && scripts/check-all.sh`
Expected: ruff clean; grammar/protocol/umbrella suites green; core import works without `[strata]`.

- [ ] **Step 7: Commit**

```bash
git add src/polymer_claims/cli.py tests/pharmaco/test_strata_cli.py tests/pharmaco/test_real_controls_slow.py
git commit -m "feat(pharmaco): strata-populate CLI + data-gated real-control integration test"
```

---

## Self-Review

**Spec coverage:** entry path (Tasks 4–6 license through the real gate), boundary (all umbrella, Task 1 gitignored contract), scope full-panel (Tasks 5–8), STRATA-as-proposer (Task 5), two legs / single-leg e-value (Tasks 2–3, 6), REPRODUCED ceiling + shared_cause_factors + tier-trap (Task 6), pattern/subject/leaf/provenance corrections (Task 4), residue-as-PENDING (Tasks 6–7), controls-as-instrument (Task 7), pre-registration (Task 5), ingestion provenance / SE-Contract (Task 1), CLI + real-data proof (Task 8). The attested-log air-gap (spec §7) and earned-strength (§11) are explicitly deferred in the spec and are **not** tasked here — noted as follow-ups below.

**Deferred (in spec, not in this plan):** the in-toto/SLSA attested-log emission + witness air-gap; earned oracle-capped strength; stage-2 PRISM/CTRP REPLICATED; the independence-breadth logging (② backlog). Each is its own later plan.

**Placeholder note:** Tasks 6–8 intentionally reference in-repo templates (`real_kernel_proof.py`, `licensing.py`, `corpus.py`, `cli.py`) for framework-mechanics that must be copied exactly rather than guessed — the `run_cycle` materialization/ctx wiring, the `Satisfaction.independence_tier` accessor, the empty-corpus constructor, and the CLI subcommand registration. Read those files before implementing the flagged steps; do not invent their signatures.
