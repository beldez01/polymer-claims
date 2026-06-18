# IDH-Source Swap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dilution-prone GDC-MAF IDH calling (n=10) with complete cBioPortal genotyping, rebuild the real TCGA-LAML contract as `tcga_laml_idh@2`, and re-run region-Δβ at proper power.

**Architecture:** All work is a **local-only, gitignored** edit to the `data/tcga_laml/` builder + run scripts (nothing in `src/`). A new cBioPortal branch in `build_contract_xena.py` derives IDH-mut/WT labels from `laml_tcga_pub` `data_mutations.txt` over the intersection case universe, rebuilds the stem-named contract files with `uid: tcga_laml_idh@2` + provenance metadata, then `run_region_split.py` / `run_gate.py` / `two_node_demo.py` re-execute against `@2`. Correctness rests on hard inline asserts in the builder and the real `run_cycle` air-gap.

**Tech Stack:** Python 3, the existing `polymer_claims` / `polymer_grammar` / `polymer_protocol` packages (run via `uv run python`), local Xena methylation450 matrix, cBioPortal datahub flat files.

## Global Constraints

- **No `src/` changes.** Everything lives under `data/tcga_laml/` (the whole `/data/` tree is gitignored). Only `CONTINUE.md` (tracked) is committed.
- **τ = 0.10 fixed** for region-Δβ. **K = 10_000 fixed.** **α = 0.05**, n-DMP floor `k = ceil(0.05·n_probes)`. The stratified-split rule is unchanged. No post-hoc tuning of any statistical knob.
- **WT means "genotyped and not an IDH hotspot," never "missing genotype."** Cases with a beta column but no cBioPortal genotype are **dropped, not labelled WT**.
- **IDH hotspots:** IDH1 R132, IDH2 R140, IDH2 R172 (reuse existing `_IDH_HOTSPOTS` logic / residue-token parsing).
- **Contract identity:** stem-named files (`tcga_laml_idh.json` / `.betas.tsv`); `@2` lives only in the manifest `uid`. `load_contract` resolves by stem.
- **Deliverable = "region-Δβ re-run at proper power on correctly-genotyped data,"** not "region-Δβ licensed." A PENDING result at fixed τ is reported as-is.
- **Working dir:** `/Users/zbb2/Desktop/polymer-claims`. Branch: `feat/idh-source-swap`. Run scripts use `uv run python data/tcga_laml/<script>.py`.

---

### Task 1: Acquire & characterize the cBioPortal source

**Files:**
- Create: `data/tcga_laml/cbioportal/data_mutations.txt` (downloaded; gitignored)
- Create: `data/tcga_laml/cbioportal/SOURCE.txt` (records the pinned datahub commit + URL)

**Interfaces:**
- Produces: a local `data_mutations.txt` for `laml_tcga_pub`; the confirmed protein-change column name; a hand-verified list of known IDH-mut case IDs for the Task 3 control assert.

- [ ] **Step 1: Download the pinned flat file**

The cBioPortal datahub stores study flat files on GitHub. Pin a specific commit (not `master`) for reproducibility.

```bash
mkdir -p data/tcga_laml/cbioportal
# Resolve current HEAD commit of the laml_tcga_pub dir, then pin it:
COMMIT=$(curl -fsSL "https://api.github.com/repos/cBioPortal/datahub/commits?path=public/laml_tcga_pub/data_mutations.txt&per_page=1" | python3 -c "import sys,json;print(json.load(sys.stdin)[0]['sha'])")
echo "pinned datahub commit: $COMMIT"
curl -fsSL "https://media.githubusercontent.com/media/cBioPortal/datahub/$COMMIT/public/laml_tcga_pub/data_mutations.txt" -o data/tcga_laml/cbioportal/data_mutations.txt
printf 'source: cbioportal/datahub public/laml_tcga_pub/data_mutations.txt\ncommit: %s\nfetched_for: tcga_laml_idh@2\n' "$COMMIT" > data/tcga_laml/cbioportal/SOURCE.txt
```

Note: datahub uses git-LFS for `data_mutations.txt`; the `media.githubusercontent.com` path serves the resolved LFS blob. If it returns a tiny LFS pointer instead of TSV (first line starts with `version https://git-lfs`), fall back to the cBioPortal web API:
```bash
curl -fsSL "https://www.cbioportal.org/api/molecular-profiles/laml_tcga_pub_mutations/mutations?sampleListId=laml_tcga_pub_all&projection=DETAILED" -H "Accept: application/json" -o data/tcga_laml/cbioportal/mutations.json
```
If you fall back to JSON, record that in `SOURCE.txt` and adjust the Task 2 parser to read JSON (fields `gene.hugoGeneSymbol`, `proteinChange`, `patientId`/`sampleId`).

- [ ] **Step 2: Verify the file is real TSV and inspect the header**

Run:
```bash
head -c 200 data/tcga_laml/cbioportal/data_mutations.txt
awk -F'\t' 'NR==1{for(i=1;i<=NF;i++)print i": "$i}' data/tcga_laml/cbioportal/data_mutations.txt | grep -Ei "hugo|hgvsp|protein|barcode|sample|patient"
```
Expected: a tab-separated header. Confirm the column names for gene (`Hugo_Symbol`), protein change (`HGVSp_Short` and/or `Protein_Change`/`Amino_Acid_Change`), and sample barcode (`Tumor_Sample_Barcode`). Record which protein-change column is populated.

- [ ] **Step 3: Hand-derive the IDH-mut control set**

Run:
```bash
awk -F'\t' 'NR==1{for(i=1;i<=NF;i++){if($i=="Hugo_Symbol")g=i; if($i=="Tumor_Sample_Barcode")b=i; if($i=="HGVSp_Short")p=i}} NR>1 && ($g=="IDH1"||$g=="IDH2"){print $b"\t"$g"\t"$p}' data/tcga_laml/cbioportal/data_mutations.txt | sort -u
```
Expected: a list of IDH1/IDH2-mutated samples with their protein changes. From it, pick **3 case IDs** (12-char `TCGA-XX-XXXX`) with clear hotspots (e.g. IDH1 p.R132H/C, IDH2 p.R140Q) — these become the Task 3 control assert. Also note the total distinct IDH-hotspot case count (sanity: expect ~30-40).

- [ ] **Step 4: Commit (docs only)**

Nothing here is tracked (`/data/` is gitignored). No commit. Record the 3 control case IDs and the populated protein-change column name in your working notes for Task 2/3.

---

### Task 2: Add the cBioPortal IDH-call branch to the builder

**Files:**
- Modify: `data/tcga_laml/build_contract_xena.py`

**Interfaces:**
- Consumes: `data/tcga_laml/cbioportal/data_mutations.txt` (Task 1); existing `case_id()` from `polymer_claims.ingest.transform`; existing `_IDH_HOTSPOTS` residue logic (re-implement inline in the builder — do not import private names; the builder is local).
- Produces: in-builder values `idh_mut_cases: set[str]`, `groups: dict[str, str]` over the intersection universe, `dropped_ungenotyped: list[str]`.

- [ ] **Step 1: Add a local cBioPortal parser + IDH-hotspot helper near the top of the builder**

Insert after the existing imports (the builder already does `sys.path.insert` for `src`). This re-implements the hotspot residue test locally so the builder is self-contained:

```python
# --- cBioPortal IDH calling (local; replaces the GDC-MAF derive_groups path) ---
CBIO = DATA / "cbioportal" / "data_mutations.txt"
_IDH_HOTSPOTS = {("IDH1", "R132"), ("IDH2", "R140"), ("IDH2", "R172")}
_PROTEIN_COL = "HGVSp_Short"  # set from Task 1; switch to "Protein_Change" if that's the populated one


def _residue(hgvsp_short: str) -> str:
    aa = hgvsp_short[2:] if hgvsp_short.startswith("p.") else hgvsp_short
    if len(aa) < 2 or not aa[0].isalpha():
        return ""
    i = 1
    while i < len(aa) and aa[i].isdigit():
        i += 1
    return aa[:i]  # 'p.R132H' -> 'R132'


def _cbio_idh_mut_cases(path) -> set[str]:
    """Parse cBioPortal data_mutations.txt -> set of 12-char case ids with an IDH hotspot."""
    lines = path.read_text().splitlines()
    rows = [ln for ln in lines if ln.strip() and not ln.startswith("#")]
    header = rows[0].split("\t")
    gi = header.index("Hugo_Symbol")
    bi = header.index("Tumor_Sample_Barcode")
    pi = header.index(_PROTEIN_COL)
    mut: set[str] = set()
    for ln in rows[1:]:
        c = ln.split("\t")
        if len(c) <= max(gi, bi, pi):
            continue
        if (c[gi], _residue(c[pi])) in _IDH_HOTSPOTS:
            mut.add(case_id(c[bi]))
    return mut
```

- [ ] **Step 2: Replace the MAF grouping block with the cBioPortal intersection grouping**

The builder currently parses MAFs (section 1) and calls `derive_groups(maf_rows, cases)` (section 2). Keep the MAF parsing lines in place but **do not use their result for grouping**. Replace the `groups = derive_groups(...)` line and the count print with:

```python
# IDH calls from cBioPortal (complete genotyping). WT = genotyped & not-hotspot, never missing.
idh_mut_cases = _cbio_idh_mut_cases(CBIO)
print(f"cBioPortal IDH-hotspot cases: {len(idh_mut_cases)}", flush=True)

genotyped = set(idh_mut_cases)  # every case appearing in data_mutations.txt is genotyped...
# ...but cases with NO mutation rows are still genotyped-WT. Build the genotyped universe from
# the full mutations file (any case appearing at all), unioned with the cohort sample list.
_all_cbio_cases = {
    case_id(ln.split("\t")[h])  # Tumor_Sample_Barcode column index resolved once below
    for ln, h in (())  # placeholder; replaced in Step 3
}
```

Stop — the genotyped universe needs the full case list from cBioPortal, not just mutated cases. Do Step 3 before running.

- [ ] **Step 3: Build the genotyped universe and the intersection grouping correctly**

Replace the placeholder from Step 2. cBioPortal `data_mutations.txt` lists only *mutated* sample rows, so "appears in the file" ≠ "genotyped, no IDH mut." The reliable genotyped universe for `laml_tcga_pub` is the study's **sample list**, fetched once:

```bash
curl -fsSL "https://www.cbioportal.org/api/sample-lists/laml_tcga_pub_sequenced/sample-ids" -H "Accept: application/json" -o data/tcga_laml/cbioportal/sequenced_samples.json
```
Record this URL in `SOURCE.txt`. Then in the builder:

```python
import json as _json
_seq = _json.loads((DATA / "cbioportal" / "sequenced_samples.json").read_text())
genotyped_cases = {case_id(s) for s in _seq}  # 12-char ids of all sequenced (genotyped) cases
print(f"cBioPortal sequenced (genotyped) cases: {len(genotyped_cases)}", flush=True)

# `cases` (from the Xena header, section 2) is the beta universe. Intersect.
beta_cases = list(cases)
universe = [c for c in beta_cases if c in genotyped_cases]
dropped_ungenotyped = [c for c in beta_cases if c not in genotyped_cases]
groups_full = {c: ("IDH_mut" if c in idh_mut_cases else "WT") for c in universe}
n_idh = sum(1 for g in groups_full.values() if g == "IDH_mut")
print(f"universe={len(universe)}  IDH_mut={n_idh}  WT={len(universe) - n_idh}  "
      f"dropped_ungenotyped={len(dropped_ungenotyped)}", flush=True)
```

Then update the downstream matrix-streaming section (section 3) to use `universe` and `groups_full` in place of `cases`/`groups`: rebind `cases = universe`, recompute `sel = [case_to_col[c] for c in universe]`, and use `groups_full` when writing `col_data`. (The matrix stream already filters columns by `sel`; pointing `sel`/`cases` at `universe` drops the ungenotyped columns automatically.)

- [ ] **Step 4: Sanity-run the grouping logic in isolation (no full matrix stream yet)**

Temporarily guard the heavy matrix-streaming section, or run a one-off:
```bash
uv run python - <<'PY'
import sys; from pathlib import Path
sys.path.insert(0, "src")
exec(open("data/tcga_laml/build_contract_xena.py").read().split("# 3. stream")[0])
PY
```
Expected: prints `IDH_mut=` in the **~30-40** range and a small `dropped_ungenotyped` count. If `IDH_mut` is ~10, the parse/column is wrong (revisit `_PROTEIN_COL`); if ~0 or ~100, the join/residue logic is wrong. Fix before proceeding. (No commit — gitignored.)

---

### Task 3: Provenance metadata, version bump, and hard self-checks

**Files:**
- Modify: `data/tcga_laml/build_contract_xena.py`

**Interfaces:**
- Consumes: `universe`, `groups_full`, `idh_mut_cases`, `dropped_ungenotyped` (Task 2); the pinned commit from `SOURCE.txt`; the 3 control case IDs (Task 1).
- Produces: an on-disk `tcga_laml_idh.json` with `uid: tcga_laml_idh@2` + provenance metadata; `tcga_laml_idh.betas.tsv`.

- [ ] **Step 1: Add the control + count asserts before the manifest write**

Insert right after the grouping block (Task 2 Step 3). Replace the three IDs with the ones from Task 1 Step 3:

```python
import hashlib

_CONTROL_IDH_MUT = {"TCGA-AB-XXXX", "TCGA-AB-YYYY", "TCGA-AB-ZZZZ"}  # from Task 1 Step 3
missing = {c for c in _CONTROL_IDH_MUT if groups_full.get(c) != "IDH_mut"}
assert not missing, f"known IDH-mut controls not called IDH_mut: {sorted(missing)}"
assert 20 <= n_idh <= 50, f"IDH_mut count {n_idh} outside sane band [20,50] — swap likely failed"
assert n_idh + (len(universe) - n_idh) == len(universe)  # universe accounting (drops excluded)
print(f"self-checks passed: {len(_CONTROL_IDH_MUT)} controls OK, IDH_mut={n_idh} in band", flush=True)
```

- [ ] **Step 2: Read the pinned commit and compute the group digest**

Insert before building the manifest dict:

```python
_src_txt = (DATA / "cbioportal" / "SOURCE.txt").read_text()
_commit = next((l.split("commit:")[1].strip() for l in _src_txt.splitlines() if l.startswith("commit:")), "unknown")
idh_call_source = f"cbioportal:laml_tcga_pub@{_commit}"
# digest over the ordered Sample_Group vector (cases in `universe` order)
_group_vec = "\n".join(groups_full[c] for c in universe).encode()
group_digest = hashlib.sha256(_group_vec).hexdigest()
```

- [ ] **Step 3: Bump uid to @2 and extend metadata in the manifest write**

The builder currently writes (section 4) a `manifest` dict with `"uid": f"{STEM}@1"`. Change the `uid` and `metadata`:

```python
manifest = {
    "uid": f"{STEM}@2",
    "dim": [len(row_feature_ids), len(universe)],
    "assays": [{"name": "beta", "ref": f"{STEM}.betas.tsv"}],
    "col_data": [{"sample_id": c, "Sample_Group": groups_full[c], "Age": None, "Sex": None} for c in universe],
    "row_data": [{"feature_id": p, "chr": "", "pos": 0} for p in row_feature_ids],
    "metadata": {
        "genome_assembly": "hg38", "array": "HM450",
        "idh_call_source": idh_call_source,
        "group_digest": group_digest,
        "idh_mut_n": n_idh, "wt_n": len(universe) - n_idh,
        "dropped_ungenotyped_n": len(dropped_ungenotyped),
    },
}
```

- [ ] **Step 4: Run the full builder and verify the loader round-trip**

Run:
```bash
uv run python data/tcga_laml/build_contract_xena.py
```
Expected output includes: `IDH_mut=` ~30-40; `self-checks passed`; `probes kept=...`; and the final `load_contract OK: dimnames_hash=...`. Add/confirm the builder's closing round-trip block asserts `@2`:
```python
ref = load_contract(f"se:{STEM}@2")
assert ref.contract_uid == f"{STEM}@2", ref.contract_uid
print(f"load_contract OK: uid={ref.contract_uid} dimnames_hash={ref.dimnames_hash[:24]}…  size={ref.size}", flush=True)
```
Re-run if you added the assert. Expected: passes, prints `uid=tcga_laml_idh@2`.

- [ ] **Step 5: Commit (docs only)**

Builder is gitignored — no commit. Capture the printed counts (IDH_mut, WT, dropped, dimnames_hash) into your notes for the CONTINUE update (Task 7).

---

### Task 4: Re-run region-Δβ at proper power (headline)

**Files:**
- Modify: `data/tcga_laml/run_region_split.py`
- Create: `data/tcga_laml/region_split_output_at2.log` (captured run log)

**Interfaces:**
- Consumes: the `@2` contract (Task 3); `split_contract`, `top_k_hypermethylated` from `polymer_claims.split_select` (unchanged).
- Produces: the held-out region-Δβ verdict (LICENSED or PENDING) + betting e-value on `@2`.

- [ ] **Step 1: Point the run script refs at @2**

In `run_region_split.py`, the parent ref read by `split_contract` is by stem (`in_stem="tcga_laml_idh"`) — unchanged. Update only the explicit `@1` ref strings used for the sub-contracts and claim so logs/provenance read `@2`-derived. Change:
- `top_k_hypermethylated("se:tcga_laml_idh_disc@1", ...)` → keep `@1` only if `split_contract` still writes `_disc@1`. **Confirm:** `split_contract` hardcodes `f"{stem}@1"` for sub-contracts, so the disc/test refs stay `@1`. Leave them. The parent provenance (`idh_call_source`, `group_digest`) propagates via `**manifest` into the sub-contracts automatically.

No code change may be required here — verify by reading the script. The behavioral change comes entirely from the rebuilt `tcga_laml_idh.json` on disk. **Do not change K or TAU.**

- [ ] **Step 2: Run region-Δβ and capture the log**

Run:
```bash
uv run python data/tcga_laml/run_region_split.py | tee data/tcga_laml/region_split_output_at2.log
```
Expected: prints discovery/test n (now ~15-20 IDH-mut per half vs ~5 before), selected 10000 probes, the held-out betting e-value, and `STATUS: ... LICENSED: True|False`.

- [ ] **Step 3: Record the verdict honestly**

Read `STATUS` from the log. If `LICENSED: True` — region-Δβ is **earned** at proper power. If `LICENSED: False` (PENDING) — record the e-value; **do not change τ**. Either outcome is the deliverable. Note the numbers for Task 7.

- [ ] **Step 4: Commit (docs only)**

Gitignored — no commit.

---

### Task 5: Evaluate n-DMP on @2 (demo plumbing only)

**Files:**
- Modify: `data/tcga_laml/run_gate.py`
- Create: `data/tcga_laml/gate_output_at2.log`

**Interfaces:**
- Consumes: the `@2` contract; `n_dmps_claim` + adapters from `polymer_claims.methyl_ndmp` (unchanged).
- Produces: n-DMP status on `@2` so both demo nodes share one contract version.

- [ ] **Step 1: Point the run script ref at @2**

In `run_gate.py`, change `REF = "se:tcga_laml_idh@1"` → `REF = "se:tcga_laml_idh@2"`. Leave `ALPHA = 0.05` and `k = ceil(0.05·n_probes)` unchanged.

- [ ] **Step 2: Run the n-DMP gate and capture the log**

Run:
```bash
uv run python data/tcga_laml/run_gate.py | tee data/tcga_laml/gate_output_at2.log
```
Expected: `STATUS: ... LICENSED: True`, `independence_tier: reproduced`, content-address line showing the `@2`-derived dimnames, FDR ledger summary. (n-DMP should still license; non-diluted it should be at least as strong.)

- [ ] **Step 3: Commit (docs only)**

Gitignored — no commit. Note the status for Task 7.

---

### Task 6: Refresh the two-node viewer demo on @2

**Files:**
- Modify: `data/tcga_laml/two_node_demo.py`
- Create: `data/tcga_laml/two_node_demo_output_at2.log`

**Interfaces:**
- Consumes: the `@2` contract; the region-Δβ + n-DMP outcomes (Tasks 4-5).
- Produces: a refreshed two-node topology (n-DMP ↔ region-Δβ) both on `@2` for the viewer.

- [ ] **Step 1: Point all contract refs in the demo at @2**

In `two_node_demo.py`, update any `se:tcga_laml_idh@1` / `@1` parent refs to `@2` (sub-contract `_disc@1`/`_test@1` stay as `split_contract` emits them). Read the script first; change only the parent-contract refs. Do not change τ/K/α.

- [ ] **Step 2: Run the demo and capture the log + viewer payload**

Run:
```bash
uv run python data/tcga_laml/two_node_demo.py | tee data/tcga_laml/two_node_demo_output_at2.log
```
Expected: both nodes emitted on `@2`; region-Δβ node reflects the Task 4 verdict; n-DMP node LICENSED. If the demo writes a viewer JSON payload, confirm it regenerated.

- [ ] **Step 3: Spot-check in the viewer (optional)**

If desired, run the viewer per `docs/spectral-layout-how-to-use.md` and confirm the two-node topology renders with the `@2` outcomes and correct `independence_tier`.

- [ ] **Step 4: Commit (docs only)**

Gitignored — no commit.

---

### Task 7: Update CONTINUE.md + memory (the only tracked commit)

**Files:**
- Modify: `docs/superpowers/CONTINUE.md`
- Modify: memory `project_polymer_claims_knowledge_protocol` (+ `INDEX.md` pointer if new)

**Interfaces:**
- Consumes: the recorded counts + verdicts from Tasks 3-6.

- [ ] **Step 1: Update the Standing caveats block in CONTINUE.md**

In the `## Current state` → Standing caveats bullet about n-DMP/region-Δβ, replace the "IDH-mut n=10" + "region-Δβ WITHHELD (power-limited)" language with the `@2` reality: IDH source now `cbioportal:laml_tcga_pub@<commit>`, IDH-mut n=<actual>, region-Δβ outcome=<LICENSED|PENDING with e-value>, dropped_ungenotyped=<n>. Keep it honest about what's earned vs pending.

- [ ] **Step 2: Update the ▶ NEXT menu**

Move the region-Δβ item out of "power-limited WITHHELD." If LICENSED: mark region-Δβ earned at proper power, and surface the next frontier (2nd real cohort → §2E REPLICATED). If still PENDING: record that power was addressed and the result held PENDING at fixed τ (a real finding), and note the next diagnostic.

- [ ] **Step 3: Update the recently-shipped line + date**

Add a "Recently shipped" entry: "IDH-source swap — cBioPortal genotyping → tcga_laml_idh@2; region-Δβ re-run at proper power (<verdict>) (2026-06-18)." Update the `Current state` date.

- [ ] **Step 4: Update memory**

Update `project_polymer_claims_knowledge_protocol` (in the memory dir) with the IDH-source swap + region-Δβ `@2` outcome (absolute date 2026-06-18). Add/refresh the `INDEX.md` pointer if needed.

- [ ] **Step 5: Commit the docs**

```bash
git add docs/superpowers/CONTINUE.md
git commit -m "$(cat <<'EOF'
docs: IDH-source swap shipped — cBioPortal genotyping → tcga_laml_idh@2

region-Δβ re-run at proper power on correctly-genotyped real TCGA-LAML data
(IDH-mut n raised from 10 to ~30-40; WT no longer a missing-data dustbin).
Verdict + numbers in CONTINUE Standing caveats. Local-only run artifacts under
data/tcga_laml/ (gitignored).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: Finish the branch**

Use `superpowers:finishing-a-development-branch` to decide merge (`--no-ff`, local-only per project rhythm) vs leaving the branch for review.

---

## Self-Review

**1. Spec coverage:**
- §2 source decision → Task 1 (download/pin cBioPortal `laml_tcga_pub`). ✓
- §3 builder branch / data flow → Task 2. ✓
- §4 intersection universe + drop-not-default WT → Task 2 Steps 2-3 + Global Constraints. ✓
- §5 `@2` uid + `idh_call_source` + `group_digest` + counts; sub-contract propagation → Task 3 + Task 4 Step 1 note. ✓
- §6 re-runs with fixed knobs (region-Δβ headline, n-DMP demo plumbing, two-node refresh) → Tasks 4, 5, 6. ✓
- §7 builder self-checks (controls, count band, universe accounting, loader round-trip) + air-gap → Task 3 Step 1/4, Tasks 4-5 runs. ✓
- §8 CONTINUE + memory → Task 7. ✓

**2. Placeholder scan:** Control case IDs (`TCGA-AB-XXXX`) and `_PROTEIN_COL` are intentionally resolved in Task 1 and substituted in Task 3 — flagged inline, not silent TODOs. Datahub commit is resolved at runtime (Task 1 Step 1). No "add error handling"-style placeholders.

**3. Type consistency:** `idh_mut_cases` (set), `groups_full` (dict), `universe` (list), `dropped_ungenotyped` (list), `group_digest`/`idh_call_source` (str) used consistently Tasks 2→3. Manifest `uid`/`metadata` keys match the spec §5 exactly. `load_contract("se:tcga_laml_idh@2").contract_uid` matches the loader's `manifest["uid"]` mapping confirmed in `src/polymer_claims/contracts/__init__.py`.

**Note for the implementer:** Task 1 has a real branch — if `data_mutations.txt` arrives as a git-LFS pointer, fall back to the cBioPortal JSON API and adjust the Task 2 parser fields accordingly. Resolve this in Task 1 before touching Task 2.
