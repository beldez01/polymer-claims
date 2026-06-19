# §2E REPLICATED on a Real Second Cohort — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Earn the first real §2E REPLICATED license by binding GSE86409 (SAL adult-AML HM450, IDH) as cohort B to the held-out region-Δβ claim, so the product e₁·e₂ clears the e-LOND bar (32.9).

**Architecture:** All work is local-only and gitignored under `data/sal_aml/` (no `src/` changes — the REPLICATED machinery in `src/polymer_claims/replication.py` + `node.py` already exists). A builder ingests the GSE86409 Series Matrix into a content-addressed `sal_aml_idh@1` SE-Contract; a run script reconstructs cohort-A's held-out region-Δβ claim (e₁=5.672), binds cohort B via `build_replication_inputs`, and runs the gate so the product e₁·e₂ is one e-LOND test. Correctness rests on hard inline builder asserts + the real `run_cycle` air-gap (`build_replication_inputs` itself drops cohort B if its two legs disagree or Δβ≤τ).

**Tech Stack:** Python 3 (run via `uv run python`), the existing `polymer_claims`/`polymer_grammar`/`polymer_protocol` packages, GSE86409 GEO Series Matrix.

## Global Constraints

- **No `src/` changes.** Everything under `data/sal_aml/` (the whole `/data/` tree is gitignored). Only `CONTINUE.md` (tracked) is committed.
- **τ = 0.10 fixed, K = 10_000 fixed, q (target_fdr) = 0.05.** No post-hoc tuning of any statistical knob. e-LOND first-test bar = 1/α₁ = 32.90 (γ₁=6/π²).
- **e₁ = cohort-A held-out test half (5.672), e₂ = full cohort B**, both on the top-10k region selected on cohort-A's discovery half (selection touched neither e-value's data).
- **WT means "genotyped/annotated and not an IDH hotspot," never "missing."** Contrast-matched to cohort A: IDH1/2-mut vs WT if SAL annotates both; IDH1-mut vs WT if only IDH1 (record the caveat).
- **Contract identity:** stem-named files (`sal_aml_idh.json` / `.betas.tsv`); `@1` in the manifest `uid`. `load_contract` resolves by stem. cohort B `dimnames_hash` MUST differ from cohort A.
- **Deliverable = "region-Δβ tested for replication on a real independent cohort,"** not "REPLICATED licensed." A PENDING product (e₂ too weak) is reported as-is.
- **Working dir:** `/Users/zbb2/Desktop/polymer-claims`. Branch: `feat/replicated-second-cohort`. Runs: `uv run python data/sal_aml/<script>.py`.
- **Cohort A artifacts already on disk** from the IDH-source-swap run: `tcga_laml_idh@2` contract + its `_disc`/`_test` sub-contracts under `src/polymer_claims/contracts/` (gitignored). Region-Δβ claim id = `tcga-laml-region-split`; test sub-contract ref = `se:tcga_laml_idh_test@1`.

---

### Task 1: Acquire & characterize GSE86409

**Files:**
- Create: `data/sal_aml/GSE86409_series_matrix.txt.gz` (downloaded; gitignored)
- Create: `data/sal_aml/SOURCE.txt` (pin: URL + download date + sha256 + IDH-field findings)

**Interfaces:**
- Produces: the local Series Matrix; the confirmed `!Sample_characteristics_ch1` field carrying IDH status; whether IDH2 is annotated; the IDH-mut sample count; confirmation that cohort-A's top-10k probes are present; a known IDH-mut GSM for the Task-3 control assert.

- [ ] **Step 1: Download the GEO Series Matrix and pin it**

```bash
mkdir -p data/sal_aml
URL="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE86nnn/GSE86409/matrix/GSE86409_series_matrix.txt.gz"
curl -fsSL "$URL" -o data/sal_aml/GSE86409_series_matrix.txt.gz
SHA=$(shasum -a 256 data/sal_aml/GSE86409_series_matrix.txt.gz | cut -d' ' -f1)
printf 'source: GEO GSE86409 Series Matrix\nurl: %s\nfetched: 2026-06-18\nsha256: %s\nplatform: GPL13534 (HumanMethylation450)\n' "$URL" "$SHA" > data/sal_aml/SOURCE.txt
echo "sha256=$SHA"
```
Expected: a ~tens-of-MB gz. If the FTP-mirror path 404s, fall back to the GEO query download button URL and record the actual URL in `SOURCE.txt`.

- [ ] **Step 2: Inspect the metadata header for IDH status**

```bash
gzcat data/sal_aml/GSE86409_series_matrix.txt.gz | grep -i "!Sample_characteristics_ch1" | head -40
gzcat data/sal_aml/GSE86409_series_matrix.txt.gz | grep -iE "!Sample_geo_accession" | head -1
```
Expected: one or more `!Sample_characteristics_ch1` lines; identify the one whose values look like IDH status (e.g. `idh1: mut`/`idh1: wt`, or `idh mutation: IDH1 R132H`). Record in `SOURCE.txt`: the 0-based index of the IDH characteristic line(s), the exact token format, and whether IDH2 is annotated separately. If NO IDH field exists in GEO, record that and switch to the SAL/Glass supplement (note its table id in `SOURCE.txt`) — Task 2 then reads IDH from a small hand-saved `data/sal_aml/idh_status.tsv` (`GSM<TAB>IDH_mut|WT`).

- [ ] **Step 3: Confirm the data table is betas and count IDH-mut**

```bash
# data table header (sample GSM ids) + first probe row
gzcat data/sal_aml/GSE86409_series_matrix.txt.gz | awk '/!series_matrix_table_begin/{f=1;next} /!series_matrix_table_end/{exit} f{print; n++} n>2{exit}'
# rough IDH-mut count from the identified characteristic line (adjust the grep token to Step 2's format)
gzcat data/sal_aml/GSE86409_series_matrix.txt.gz | grep -i "!Sample_characteristics_ch1" | grep -i "idh" | head -1 | tr '\t' '\n' | grep -ic "mut"
```
Expected: the table header is `"ID_REF"` + ~79 GSM ids; probe rows start `cg########` with float betas in [0,1]. The IDH-mut count should be ≥ ~12. Record the count + one IDH-mut GSM id (a column whose IDH token is "mut") in `SOURCE.txt`. If the count is < ~12, STOP and report — cohort B is underpowered for e₂ ≳ 5.8 (a cohort-choice problem, not an implementation bug).

- [ ] **Step 4: Confirm top-10k probe overlap**

```bash
# cohort-A top-10k are selected at run time, but the cohort-B probe universe must cover HM450.
# Quick proxy: count probes in cohort B, confirm cg-id space.
gzcat data/sal_aml/GSE86409_series_matrix.txt.gz | awk '/!series_matrix_table_begin/{f=1;next} /!series_matrix_table_end/{exit} f&&NR>1{c++} END{print c-1" probe rows"}'
```
Expected: ~450k probe rows (HM450). Full top-10k overlap is asserted precisely in Task 2 Step 4 once the contract is built. No commit (gitignored). Record control GSM + IDH field index in working notes for Task 2/3.

---

### Task 2: Ingest GSE86409 → `sal_aml_idh@1` contract

**Files:**
- Create: `data/sal_aml/build_contract_gse86409.py` (gitignored)

**Interfaces:**
- Consumes: `data/sal_aml/GSE86409_series_matrix.txt.gz` + the IDH field index from Task 1; `case_id` not needed (GEO uses GSM ids directly as sample ids); `load_contract`/`clear_contract_cache` from `polymer_claims.contracts`.
- Produces: on-disk `src/polymer_claims/contracts/sal_aml_idh.json` + `.betas.tsv` with `uid="sal_aml_idh@1"`, `Sample_Group` per GSM, provenance metadata.

- [ ] **Step 1: Write the builder — parse the Series Matrix**

Create `data/sal_aml/build_contract_gse86409.py`. Set `_IDH_CHAR_IDX` and `_IDH_MUT_TOKEN` from Task 1.

```python
"""LOCAL-ONLY cohort-B builder (gitignored). Ingest GSE86409 (SAL adult-AML HM450, IDH) Series Matrix
-> se:sal_aml_idh@1, the §2E REPLICATED cohort B for region-Δβ. Betas + IDH status both come from the
Series Matrix. dimnames_hash differs from cohort A by construction (different samples). No src/ changes."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

REPO = Path("/Users/zbb2/Desktop/polymer-claims")
DATA = REPO / "data" / "sal_aml"
MATRIX = DATA / "GSE86409_series_matrix.txt.gz"
CONTRACTS = REPO / "src" / "polymer_claims" / "contracts"
STEM = "sal_aml_idh"
_NA = {"", "NA", "NaN", ".", "na", "null", "null"}
_IDH_MUT_TOKEN = "mut"   # from Task 1 (substring marking an IDH-mut sample, lowercased)
_CONTROL_IDH_MUT_GSM = "GSMxxxxxxx"  # from Task 1 Step 3

sys.path.insert(0, str(REPO / "src"))


def _parse_series_matrix(path):
    """-> (gsm_ids: list[str], idh_char_lines: list[list[str]], betas: dict[probe, list[str]])."""
    gsm_ids: list[str] = []
    idh_char_lines: list[list[str]] = []
    betas: dict[str, list[str]] = {}
    in_table = False
    with gzip.open(path, "rt") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("!Sample_geo_accession"):
                gsm_ids = [c.strip('"') for c in line.split("\t")[1:]]
            elif line.startswith("!Sample_characteristics_ch1"):
                idh_char_lines.append([c.strip('"') for c in line.split("\t")[1:]])
            elif line.startswith("!series_matrix_table_begin"):
                in_table = True
            elif line.startswith("!series_matrix_table_end"):
                break
            elif in_table:
                cells = line.split("\t")
                probe = cells[0].strip('"')
                if probe == "ID_REF" or not probe.startswith("cg"):
                    continue
                betas[probe] = [c.strip('"') for c in cells[1:]]
    return gsm_ids, idh_char_lines, betas


gsm_ids, idh_char_lines, betas = _parse_series_matrix(MATRIX)
print(f"samples={len(gsm_ids)}  characteristic lines={len(idh_char_lines)}  probes(raw)={len(betas)}", flush=True)
```

- [ ] **Step 2: Derive IDH groups (contrast-matched)**

Append. Identify the IDH characteristic line(s) and mark a sample IDH_mut if any IDH characteristic value contains the mut token. (If Task 1 found NO GEO IDH field, replace this block with a read of `data/sal_aml/idh_status.tsv`.)

```python
def _is_idh_mut(values_per_line, col):
    for vals in values_per_line:
        if col < len(vals) and _IDH_MUT_TOKEN in vals[col].lower() and "wt" not in vals[col].lower():
            return True
    return False


# keep only IDH-characteristic lines (those whose text mentions idh)
idh_lines = [vals for vals in idh_char_lines if any("idh" in v.lower() for v in vals)]
assert idh_lines, "no IDH characteristic line found — fall back to idh_status.tsv (Task 1 Step 2)"
groups = {g: ("IDH_mut" if _is_idh_mut(idh_lines, i) else "WT") for i, g in enumerate(gsm_ids)}
n_idh = sum(1 for v in groups.values() if v == "IDH_mut")
n_wt = len(gsm_ids) - n_idh
print(f"IDH_mut={n_idh}  WT={n_wt}", flush=True)
```

- [ ] **Step 3: Drop NA probes, write the contract + provenance metadata**

Append. Keep probes with no NA across samples; write betas TSV (samples = GSM ids) + manifest.

```python
sel_probes = []
betas_path = CONTRACTS / f"{STEM}.betas.tsv"
CONTRACTS.mkdir(parents=True, exist_ok=True)
with open(betas_path, "w") as out:
    out.write("\t".join(["feature_id", *gsm_ids]) + "\n")
    for probe, vals in betas.items():
        if len(vals) != len(gsm_ids) or any(v.strip() in _NA for v in vals):
            continue
        out.write("\t".join([probe, *vals]) + "\n")
        sel_probes.append(probe)
print(f"probes kept={len(sel_probes)}", flush=True)

_src = (DATA / "SOURCE.txt").read_text()
_date = next((l.split("fetched:")[1].strip() for l in _src.splitlines() if l.startswith("fetched:")), "unknown")
idh_call_source = f"geo:GSE86409@{_date}"
group_digest = hashlib.sha256("\n".join(groups[g] for g in gsm_ids).encode()).hexdigest()

manifest = {
    "uid": f"{STEM}@1",
    "dim": [len(sel_probes), len(gsm_ids)],
    "assays": [{"name": "beta", "ref": f"{STEM}.betas.tsv"}],
    "col_data": [{"sample_id": g, "Sample_Group": groups[g], "Age": None, "Sex": None} for g in gsm_ids],
    "row_data": [{"feature_id": p, "chr": "", "pos": 0} for p in sel_probes],
    "metadata": {
        "genome_assembly": "hg38", "array": "HM450",
        "idh_call_source": idh_call_source, "group_digest": group_digest,
        "idh_mut_n": n_idh, "wt_n": n_wt, "cohort": "SAL/GSE86409",
    },
}
(CONTRACTS / f"{STEM}.json").write_text(json.dumps(manifest))
print(f"wrote {STEM}@1: {len(sel_probes)} probes x {len(gsm_ids)} samples", flush=True)
```

- [ ] **Step 4: Self-checks — counts, control, top-10k overlap, distinct dimnames**

Append. Recompute cohort-A's top-10k (discovery half) and assert full overlap, and assert distinct dimnames.

```python
assert 12 <= n_idh, f"IDH_mut n={n_idh} too low for e2≳5.8 — cohort underpowered"
assert groups.get(_CONTROL_IDH_MUT_GSM) == "IDH_mut", f"control {_CONTROL_IDH_MUT_GSM} not IDH_mut"

from polymer_claims.contracts import clear_contract_cache, load_contract  # noqa: E402
from polymer_claims.split_select import split_contract, top_k_hypermethylated  # noqa: E402

clear_contract_cache()
ref_b = load_contract(f"se:{STEM}@1")
dimnames_a = load_contract("se:tcga_laml_idh@2").dimnames_hash
assert ref_b.dimnames_hash != dimnames_a, "cohort B dimnames_hash equals cohort A — not a replication"

split_contract(CONTRACTS)  # (re)materialize tcga_laml_idh_disc/_test from @2
clear_contract_cache()
top = set(top_k_hypermethylated("se:tcga_laml_idh_disc@1", 10_000, level_a="WT", level_b="IDH_mut"))
missing = top - set(sel_probes)
assert not missing, f"{len(missing)} of cohort-A top-10k absent in cohort B (rebind cannot compute e2)"
print(f"self-checks passed: IDH_mut={n_idh}, dimnames distinct, top-10k overlap complete; "
      f"dimnames_b={ref_b.dimnames_hash[:24]}…", flush=True)
```

- [ ] **Step 5: Run the builder**

```bash
uv run python data/sal_aml/build_contract_gse86409.py
```
Expected: prints `IDH_mut=` (≥12), `probes kept=` (~450k minus NA), `self-checks passed`. If `top-10k absent` fires, cohort B lacks some cohort-A probes — investigate probe-id formatting before proceeding. No commit (gitignored).

---

### Task 3: REPLICATED run — bind cohort B, gate the product

**Files:**
- Create: `data/sal_aml/run_replicated.py` (gitignored)
- Create: `data/sal_aml/run_replicated_output.log` (captured)

**Interfaces:**
- Consumes: `sal_aml_idh@1` (Task 2); `tcga_laml_idh@2` + sub-contracts; `build_replication_inputs` from `polymer_claims.replication`; region adapters + `region_delta_beta_claim` from `polymer_claims.methyl_adapters`; `split_contract`/`top_k_hypermethylated` from `polymer_claims.split_select`.
- Produces: the REPLICATED verdict (LICENSED/PENDING) + e₁, e₂, product on the real cohort pair.

- [ ] **Step 1: Write the run script — reconstruct cohort-A's held-out claim**

Mirrors `data/tcga_laml/run_region_split.py` (read it first for the exact call shape), then adds binding. NOTE: confirm `run_cycle` accepts `replications=` — check the synthetic REPLICATED demo/test (grep `replications=` under `tests/` and `data/`) for the canonical signature before finalizing.

```python
"""LOCAL-ONLY §2E REPLICATED run (gitignored). Reconstruct cohort-A's held-out region-Δβ claim
(e1=5.672), bind cohort B (GSE86409) via build_replication_inputs, gate the product e1*e2 as one
e-LOND test. Reports the verdict + e1/e2/product."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path("/Users/zbb2/Desktop/polymer-claims")
CONTRACTS = REPO / "src" / "polymer_claims" / "contracts"
sys.path.insert(0, str(REPO / "src"))

from polymer_grammar import Comparator, FDRLedger, MaterializationContext, Status  # noqa: E402
from polymer_protocol import Corpus, run_cycle  # noqa: E402

from polymer_claims.analysis_profile import profile_oracle_id, profile_oracle_registry  # noqa: E402
from polymer_claims.contracts import clear_contract_cache  # noqa: E402
from polymer_claims.evidence import evidence_map  # noqa: E402
from polymer_claims.materialization import materialization_map  # noqa: E402
from polymer_claims.methyl_adapters import (  # noqa: E402
    RegionLmCoefAdapter, RegionMeanDiffAdapter, methyl_independent_registry, region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_HM450_V1  # noqa: E402
from polymer_claims.replication import build_replication_inputs  # noqa: E402
from polymer_claims.split_select import split_contract, top_k_hypermethylated  # noqa: E402

K, TAU = 10_000, 0.10
BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")
CID, REF_B = "tcga-laml-region-split", "se:sal_aml_idh@1"

split_contract(CONTRACTS)
clear_contract_cache()
top = top_k_hypermethylated("se:tcga_laml_idh_disc@1", K, level_a="WT", level_b="IDH_mut")
claim = region_delta_beta_claim(
    CID, ref="se:tcga_laml_idh_test@1", region_probes=top,
    group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
    comparator=Comparator.GT, threshold=TAU, oracle_ref=profile_oracle_id(CANONICAL_HM450_V1),
    title="top-10k region Δβ, IDH-mut vs WT — REPLICATED (TCGA-LAML × SAL/GSE86409)",
)
corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
e1 = evidence_map(corpus).get(CID)
print(f"cohort-A held-out e1 = {e1}", flush=True)
```

- [ ] **Step 2: Bind cohort B and run the gate**

Append.

```python
repl = build_replication_inputs(corpus, BASE, bindings={CID: REF_B})
e_product = repl.evidence.get(CID)
replicated = CID in repl.replications
e2 = (e_product / e1) if (e_product and e1) else None
print(f"cohort-B replication emitted: {replicated}", flush=True)
print(f"cohort-B e2 = {e2}", flush=True)
print(f"product e1*e2 = {e_product}  (e-LOND bar = 32.90)", flush=True)

result = run_cycle(
    corpus, (RegionMeanDiffAdapter(), RegionLmCoefAdapter()), BASE,
    adapter_registry=methyl_independent_registry(),
    oracles=profile_oracle_registry((CANONICAL_HM450_V1, "recomputable_public")),
    materializations=materialization_map(corpus, BASE, profiles=(CANONICAL_HM450_V1,)),
    replications=repl.replications, evidence=repl.evidence,
)
c = next(x for x in result.corpus.claims if x.id == CID)
print("=" * 64, flush=True)
print(f"STATUS: {c.status}   LICENSED: {c.status is Status.LICENSED}", flush=True)
if c.licensing is not None:
    print(f"independence_tier: {c.licensing.independence_tier}", flush=True)
    print(f"satisfactions: {len(c.licensing.satisfactions)} (expect 2 for REPLICATED)", flush=True)
led = result.corpus.fdr_ledger
print(f"FDR ledger: n_tests={led.n_tests}  n_discoveries={led.n_discoveries}", flush=True)
print("=" * 64, flush=True)
```

- [ ] **Step 3: Run and capture the log**

```bash
uv run python data/sal_aml/run_replicated.py 2>&1 | tee data/sal_aml/run_replicated_output.log
```
Expected: `cohort-B replication emitted: True`; e₂ printed; `product e1*e2`; STATUS. If `replicated=False`, cohort B failed the air-gap (legs disagree) or Δβ≤τ — read the e₂ line; investigate cohort B betas/groups. Record verdict honestly: REPLICATED if product > 32.9, else PENDING (do NOT tune τ/K/q).

- [ ] **Step 4: Commit (docs only)** — gitignored; no commit. Note e₁, e₂, product, status for Task 4.

---

### Task 4: Update CONTINUE.md + memory (the only tracked commit)

**Files:**
- Modify: `docs/superpowers/CONTINUE.md`
- Modify: memory `project_polymer_claims_knowledge_protocol` + `INDEX.md`

**Interfaces:**
- Consumes: e₁/e₂/product + verdict from Task 3.

- [ ] **Step 1: Update Standing caveats in CONTINUE.md**

Edit the region-Δβ Standing-caveat bullet: record the REPLICATED attempt — cohort B = `geo:GSE86409` (SAL adult AML), IDH-mut N=<n>, e₂=<v>, product=<e1*e2>, verdict=<REPLICATED LICENSED | PENDING>. If LICENSED: note REPLICATED is now *earned* (no longer synthetic-only) and state the honest independence scope (different consortium/lab/pipeline; North Star §E common-cause DAG still future). If PENDING: record the product value and that τ/K/q were not tuned.

- [ ] **Step 2: Update the NEXT menu**

If LICENSED: move region-Δβ to "REPLICATED earned"; surface next frontiers (real HM450 manifest / sex-chrom QC; Phase D integrity ledger; North Star §E DAG). If PENDING: note cohort B's power and the next diagnostic (a larger/3rd cohort).

- [ ] **Step 3: Update recently-shipped + date**

Add: "§2E REPLICATED on a real 2nd cohort — TCGA-LAML × SAL/GSE86409; region-Δβ product e1*e2=<v> (<verdict>) (2026-06-18)."

- [ ] **Step 4: Update memory**

Prepend a dated entry to `project_polymer_claims_knowledge_protocol` (the REPLICATED outcome + cohort-B source + honest independence scope); refresh the `INDEX.md` hook.

- [ ] **Step 5: Commit the docs**

```bash
git add docs/superpowers/CONTINUE.md
git commit -m "$(cat <<'EOF'
docs: §2E REPLICATED on a real 2nd cohort — TCGA-LAML × SAL/GSE86409

Bound GSE86409 (SAL adult-AML HM450, IDH) as cohort B to the held-out region-Δβ
claim. Product e1*e2 (5.672*<e2>) as one e-LOND test vs the 32.9 bar -> <verdict>.
First earned REPLICATED (if licensed); honest independence scope recorded.
Local-only run artifacts under data/sal_aml/ (gitignored).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: Finish the branch** — use `superpowers:finishing-a-development-branch`.

---

## Self-Review

**1. Spec coverage:**
- §2 cohort-B decision (GSE86409) → Task 1. ✓
- §3 ingestion (Series Matrix → `sal_aml_idh@1`, contrast-matched groups, provenance) → Task 2. ✓
- §4 REPLICATED run (reconstruct e₁, bind cohort B, product gate, report) → Task 3. ✓
- §5 self-checks (IDH-mut band, top-10k overlap, control, distinct dimnames, air-gap) → Task 2 Step 4 + Task 3 Step 2/3. ✓
- §6 docs/memory → Task 4. ✓
- Severity bookkeeping (selection on A-discovery; e₁=A-test, e₂=B-full) → Global Constraints + Task 3. ✓

**2. Placeholder scan:** `_IDH_MUT_TOKEN`, `_IDH_CHAR_IDX`/IDH-field index, `_CONTROL_IDH_MUT_GSM`, and the Series-Matrix URL are resolved in Task 1 and substituted in Task 2 — flagged inline, not silent TODOs. The IDH-from-supplement fallback is a real Task-1 branch. No "add error handling"-style placeholders.

**3. Type consistency:** `groups` (dict[gsm,str]), `sel_probes` (list), `n_idh`/`n_wt` (int), `group_digest`/`idh_call_source` (str) consistent Task 2→3. Run script: `repl.evidence`/`repl.replications` match `ReplicationInputs` fields in `replication.py`; `build_replication_inputs(corpus, base_ctx, *, bindings)` signature matches; `e_product = repl.evidence[CID]`, `e2 = e_product/e1`. Manifest keys match the spec §3 + the loader.

**Note for the implementer:** Task 1 is a real characterization gate — the IDH characteristic field and IDH-mut count are unknown until the Series Matrix is inspected. If GEO carries no per-sample IDH field, switch to the supplement-derived `idh_status.tsv` (Task 1 Step 2) before Task 2. And confirm `run_cycle(..., replications=...)` against the existing synthetic REPLICATED caller before running Task 3.

---

## Implementation status (2026-06-18→19)

- **Task 1 — DONE + BLOCKED finding.** GSE86409 betas downloaded (419,415 HM450 probes, [0,1]; sha256 `3e308c82…`), but GEO carries **no per-sample IDH** (only AML/stage/tissue/sex). A full GEO hunt confirmed **no open HM450 adult-AML cohort exposes machine-readable IDH** (it's in paper supplements / dbGaP phs001657; the GEO series carrying `idh1:`/`idh2:` — GSE146173, GSE98350 — are RNA/seq). The series-matrix join key is `!Sample_title` = `eAML-NGS-*` (or GSM).
- **Tasks 2–3 — STAGED (gitignored), awaiting one real input.** `data/sal_aml/build_contract_gse86409.py` (reads a user-supplied `data/sal_aml/idh_status.tsv` keyed by `eAML-NGS`/GSM, classifies IDH labels, **drops unlabeled samples — no WT dilution**, builds `sal_aml_idh@1`, runs the self-checks) and `data/sal_aml/run_replicated.py` (binds cohort B, gates the product vs 32.9) are written and `py_compile`-clean. **Resume = drop `idh_status.tsv` → run both.** No genotype fabrication.

## Completeness & Validity Audit

This arc is **local-only / gitignored** (no `src/` change), so its test surface is **builder hard-asserts + the `run_cycle` air-gap + acceptance criteria** (not pytest). Every spec requirement maps to an executable check:

| Spec requirement | Task / file | Executable check (the "test") |
|---|---|---|
| §2 cohort B = independent adult-AML HM450 w/ IDH | T1 | platform grep `GPL13534`; series-title adult-AML; IDH labels present (via `idh_status.tsv`) |
| §3 WT = annotated-not-hotspot, never missing | T2 builder | unlabeled samples DROPPED (`dropped_unlabeled_n`), never defaulted WT — code path + printed count |
| §3 contrast-matched (IDH1/2 hotspot → IDH_mut) | T2 builder | `_classify_idh` aborts on unclassifiable token (no silent mislabel) |
| §3 distinct dimnames_hash (a real replication) | T2 builder | hard assert `ref_b.dimnames_hash != cohort-A` |
| §4/§5 top-10k probe overlap complete | T2 builder | hard assert `top - set(sel_probes) == ∅` (else rebind can't compute e₂) |
| §3 IDH-mut N powered (≥12) | T2 builder | hard assert `n_idh >= 12` |
| §4 product gate e₁·e₂ vs 32.9 | T3 run | `run_replicated.py` prints e₁, e₂, product, STATUS, `independence_tier` |
| §4 cohort-B air-gap (legs agree ∧ Δβ>τ) | machinery | `build_replication_inputs` DROPS cohort B if the two region legs disagree or Δβ≤τ (`replication.py:89-94`) — silent inflation is impossible |
| §1 τ/K/q fixed (no tuning) | Global Constraints | hard-coded `K=10_000, TAU=0.10`, `target_fdr=0.05` in `run_replicated.py` |
| machinery validated | pre-flight | `run_cycle(..., replications=)` confirmed at `cycle.py:60`; canonical caller `tests/test_2e_tiered_independence_e2e.py` |

**Validity arguments:**
1. **Severity on both legs.** The top-10k is selected on cohort-A's *discovery* half only ⇒ e₁ (cohort-A test half) and e₂ (all of cohort B) are each valid severe e-values on data unused for selection; their product is the §2E REPLICATED test (one e-LOND slot).
2. **No silent license.** Two independent region legs must agree on *each* cohort (air-gap), and cohort B must independently clear τ, before any e₂ is emitted — a mis-ingested cohort B fails closed (drops out), it cannot inflate the product.
3. **No dilution reintroduced.** Drop-not-default mirrors the cohort-A IDH-source fix; an unlabeled GSE86409 sample is excluded, never silently labeled WT.
4. **Honest outcome.** Deliverable is "tested for replication," not "REPLICATED licensed" — a product < 32.9 is reported PENDING with τ/K/q untouched.

**Gap analysis (explicit, not silent):**
- **Hard-blocked on real IDH labels.** The only missing input is `idh_status.tsv` (SAL PMID 28366934 / dbGaP phs001657) — user-supplied; not fabricable. Until then the arc is *built but not earned* (region-Δβ stays PENDING).
- **Independence is cohort/lab/pipeline-level**, content-addressed only as `dimnames_hash ≠`; the formal common-cause-DAG bar (North Star §E) is **not** cleared and the caveat must say so (Task 4 Step 1).
- **No pytest coverage** (gitignored data) — the air-gap + builder asserts are the substitute; a `skip-if-absent` local e2e test mirroring `test_2e_tiered_independence_e2e.py` could be added once `sal_aml_idh@1` exists (future, optional).
