# Region-Δβ via top-10k + sample-splitting — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Earn the region-Δβ reduction on real TCGA-LAML betas the honest way — select the top-10k differentially-methylated probes on a discovery sample-half, then license the Δβ betting e-value on the held-out test-half (severity / no cherry-picking).

**Architecture:** Three deterministic stages. New umbrella helpers `stratified_split` (pure), `split_contract` (writes two disjoint-sample sub-contracts, streamed), and `top_k_hypermethylated` (discovery-side Δβ ranking) — all CI-tested on synthetic fixtures. The held-out licensing reuses the existing `region_delta_beta_claim` + both legs + `evidence_map` unchanged. The real run is a gitignored local script (data on disk already), like the Phase A n-DMP earned run.

**Tech Stack:** Python 3 stdlib (+ numpy behind `[embed]` for the OLS leg, already there), pydantic models, pytest + ruff, `uv`.

## Global Constraints

- `grammar/` + `protocol/` stay pure/deterministic + numpy-free; all new impurity is umbrella-side (`src/polymer_claims/`).
- All models frozen (`extra="forbid"`); collections are tuples; no `dict`/`list` model fields. (No new models here.)
- New code is additive; existing behavior byte-identical.
- The test half MUST NEVER influence selection — `top_k_hypermethylated` reads only the discovery contract; the held-out claim runs only on the test contract. This severity invariant is the whole point.
- Determinism throughout (no RNG, no clock) so sub-contracts are content-addressable: stratified split = sort + even/odd interleave; ranking ties broken by probe id.
- Pre-registered, fixed before the test betas: split 50/50 stratified · rank by discovery Δβ (level_b − level_a) descending · k=10,000 · τ=0.10 · comparator GT · REPRODUCED tier.
- Data handling: real data + sub-contracts gitignored; the real run is local-only; CI-safe unit tests use synthetic fixtures + `monkeypatch` of `polymer_claims.contracts._DIR`.
- Tests: `uv run pytest -q` + `uv run ruff check src tests`; full gate `scripts/check-all.sh`. TDD: failing test first. Merge to `main` `--no-ff`, local-only.
- Reused unchanged: `region_delta_beta_claim`/`RegionMeanDiffAdapter` (id `methyl-meandiff-beta`)/`RegionLmCoefAdapter` (id `methyl-lm-coef`)/`methyl_independent_registry` (`methyl_adapters.py`), `evidence_map`/`betting_evalue` (`evidence.py`), `materialization_map`, `load_contract`/`clear_contract_cache`, `CANONICAL_HM450_V1`.

---

### Task 1: `stratified_split` (pure deterministic split)

**Files:**
- Create: `src/polymer_claims/split_select.py`
- Test: `tests/test_split_select.py` (create)

**Interfaces:**
- Produces: `stratified_split(sample_groups: dict[str, str]) -> tuple[list[str], list[str]]` — returns `(discovery_ids, test_ids)`, each sorted, disjoint, union = all input ids; within each group, sorted ids are assigned even-index→discovery, odd-index→test.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_split_select.py
from __future__ import annotations

from polymer_claims.split_select import stratified_split


def test_stratified_split_disjoint_covers_all_and_stratified():
    groups = {f"s{i:02d}": ("IDH_mut" if i < 4 else "WT") for i in range(12)}  # 4 IDH_mut, 8 WT
    disc, test = stratified_split(groups)
    assert set(disc).isdisjoint(test)
    assert set(disc) | set(test) == set(groups)
    # each group split ~evenly: 4 IDH_mut -> 2/2, 8 WT -> 4/4
    idh = {s for s, g in groups.items() if g == "IDH_mut"}
    assert len(idh & set(disc)) == 2 and len(idh & set(test)) == 2


def test_stratified_split_is_deterministic():
    groups = {f"s{i:02d}": ("A" if i % 3 == 0 else "B") for i in range(10)}
    assert stratified_split(groups) == stratified_split(groups)
    assert stratified_split(groups)[0] == sorted(stratified_split(groups)[0])  # sorted output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run pytest tests/test_split_select.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_claims.split_select'`.

- [ ] **Step 3: Implement**

Create `src/polymer_claims/split_select.py`:

```python
"""Discovery/test sample-splitting + top-k probe selection — the severity (anti-cherry-picking)
machinery for region-Δβ. Umbrella/impure (split_contract + top_k read/write contracts). Selection
happens ONLY on the discovery half; the held-out test half is never read during selection. Deterministic
(sort + even/odd interleave; ties by probe id) so sub-contracts are content-addressable."""
from __future__ import annotations


def stratified_split(sample_groups: dict[str, str]) -> tuple[list[str], list[str]]:
    """Deterministic stratified 50/50 split. Within each group (processed in sorted order), sorted
    sample ids are assigned even-index -> discovery, odd-index -> test. Returns (discovery, test),
    each sorted. Disjoint; union = all ids."""
    by_group: dict[str, list[str]] = {}
    for sid, grp in sample_groups.items():
        by_group.setdefault(grp, []).append(sid)
    disc: list[str] = []
    test: list[str] = []
    for grp in sorted(by_group):
        for i, sid in enumerate(sorted(by_group[grp])):
            (disc if i % 2 == 0 else test).append(sid)
    return sorted(disc), sorted(test)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_split_select.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/split_select.py tests/test_split_select.py
git commit -m "feat: stratified_split — deterministic discovery/test sample split

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `split_contract` (write two disjoint-sample sub-contracts)

**Files:**
- Modify: `src/polymer_claims/split_select.py` (add `split_contract`)
- Test: `tests/test_split_select.py` (add a round-trip test)

**Interfaces:**
- Consumes: `stratified_split` (Task 1); `build_contract` (`polymer_claims.ingest.transform`), `load_contract`/`clear_contract_cache` (`polymer_claims.contracts`).
- Produces: `split_contract(contracts_dir, *, in_stem="tcga_laml_idh", disc_stem="tcga_laml_idh_disc", test_stem="tcga_laml_idh_test", group_col="Sample_Group") -> tuple[list[str], list[str]]` — reads `{in_stem}.json` + `{in_stem}.betas.tsv` from `contracts_dir`, writes `{disc_stem}.*` and `{test_stem}.*` (same `row_data`/probes, disjoint sample columns, streamed), returns `(disc_ids, test_ids)`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_split_select.py
import json

import polymer_claims.contracts as contracts_mod
from polymer_claims.contracts import clear_contract_cache, load_contract
from polymer_claims.ingest.transform import build_contract
from polymer_claims.split_select import split_contract


def _planted_contract(tmp_path):
    # 6 samples (2 IDH_mut, 4 WT), 4 probes; cg_hi clearly hypermethylated in IDH_mut.
    sample_ids = ["s1", "s2", "s3", "s4", "s5", "s6"]
    groups = {"s1": "IDH_mut", "s2": "IDH_mut", "s3": "WT", "s4": "WT", "s5": "WT", "s6": "WT"}
    betas = {
        "cg_hi": {"s1": 0.9, "s2": 0.88, "s3": 0.1, "s4": 0.12, "s5": 0.11, "s6": 0.1},
        "cg_lo": {"s1": 0.2, "s2": 0.22, "s3": 0.2, "s4": 0.21, "s5": 0.2, "s6": 0.19},
        "cg_b":  {"s1": 0.5, "s2": 0.52, "s3": 0.5, "s4": 0.49, "s5": 0.5, "s6": 0.51},
        "cg_c":  {"s1": 0.3, "s2": 0.31, "s3": 0.3, "s4": 0.29, "s5": 0.3, "s6": 0.3},
    }
    row_meta = {p: {"chr": "chr1", "pos": 100 + i} for i, p in enumerate(betas)}
    clinical = {s: {"Age": 50, "Sex": "male"} for s in sample_ids}
    build_contract(tmp_path, uid_stem="tcga_laml_idh", betas=betas, row_meta=row_meta,
                   groups=groups, clinical=clinical, sample_ids=sample_ids)
    return sample_ids


def test_split_contract_round_trips_disjoint(tmp_path, monkeypatch):
    _planted_contract(tmp_path)
    disc_ids, test_ids = split_contract(tmp_path)
    assert set(disc_ids).isdisjoint(test_ids)

    monkeypatch.setattr(contracts_mod, "_DIR", tmp_path)
    clear_contract_cache()
    try:
        d = load_contract("se:tcga_laml_idh_disc@1")
        t = load_contract("se:tcga_laml_idh_test@1")
        # same probes, disjoint samples -> different dimnames_hash
        assert d.dimnames_hash != t.dimnames_hash
        dm = json.loads((tmp_path / "tcga_laml_idh_disc.json").read_text())
        tm = json.loads((tmp_path / "tcga_laml_idh_test.json").read_text())
        assert [r["feature_id"] for r in dm["row_data"]] == [r["feature_id"] for r in tm["row_data"]]
        assert {c["sample_id"] for c in dm["col_data"]}.isdisjoint(c["sample_id"] for c in tm["col_data"])
    finally:
        clear_contract_cache()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_split_select.py::test_split_contract_round_trips_disjoint -q`
Expected: FAIL with `ImportError: cannot import name 'split_contract'`.

- [ ] **Step 3: Implement**

Append to `src/polymer_claims/split_select.py`:

```python
import json
from pathlib import Path


def split_contract(
    contracts_dir,
    *,
    in_stem: str = "tcga_laml_idh",
    disc_stem: str = "tcga_laml_idh_disc",
    test_stem: str = "tcga_laml_idh_test",
    group_col: str = "Sample_Group",
) -> tuple[list[str], list[str]]:
    """Split {in_stem} into two disjoint-sample sub-contracts (same probes), streamed. Returns
    (discovery_ids, test_ids)."""
    cdir = Path(contracts_dir)
    manifest = json.loads((cdir / f"{in_stem}.json").read_text())
    col_data = manifest["col_data"]
    groups = {c["sample_id"]: c[group_col] for c in col_data}
    disc_ids, test_ids = stratified_split(groups)

    sample_order = [c["sample_id"] for c in col_data]
    col_of = {sid: i + 1 for i, sid in enumerate(sample_order)}  # +1: col 0 is feature_id
    cd_by_id = {c["sample_id"]: c for c in col_data}

    for stem, ids in ((disc_stem, disc_ids), (test_stem, test_ids)):
        sel = [col_of[s] for s in ids]
        with open(cdir / f"{in_stem}.betas.tsv") as fin, open(cdir / f"{stem}.betas.tsv", "w") as fout:
            fout.write("\t".join(["feature_id", *ids]) + "\n")
            next(fin)  # skip the header
            for line in fin:
                cells = line.rstrip("\n").split("\t")
                fout.write("\t".join([cells[0], *(cells[i] for i in sel)]) + "\n")
        sub = {
            **manifest,
            "uid": f"{stem}@1",
            "dim": [len(manifest["row_data"]), len(ids)],
            "assays": [{"name": "beta", "ref": f"{stem}.betas.tsv"}],
            "col_data": [cd_by_id[s] for s in ids],
        }
        (cdir / f"{stem}.json").write_text(json.dumps(sub))
    return disc_ids, test_ids
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_split_select.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/split_select.py tests/test_split_select.py
git commit -m "feat: split_contract — write disjoint discovery/test sub-contracts (streamed)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `top_k_hypermethylated` (discovery-side selection)

**Files:**
- Modify: `src/polymer_claims/split_select.py` (add `top_k_hypermethylated`)
- Test: `tests/test_split_select.py` (add a selection test)

**Interfaces:**
- Consumes: `load_contract` (`polymer_claims.contracts`); the `_planted_contract` helper + `split_contract` (Task 2).
- Produces: `top_k_hypermethylated(ref: str, k: int, *, group_col="Sample_Group", level_a="WT", level_b="IDH_mut") -> tuple[str, ...]` — reads ONLY the named contract's betas; returns the `k` probe ids with the largest Δβ = mean(level_b) − mean(level_a), descending, ties broken by probe id.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_split_select.py
from polymer_claims.split_select import top_k_hypermethylated


def test_top_k_selects_hypermethylated_probe(tmp_path, monkeypatch):
    _planted_contract(tmp_path)
    monkeypatch.setattr(contracts_mod, "_DIR", tmp_path)
    clear_contract_cache()
    try:
        top1 = top_k_hypermethylated("se:tcga_laml_idh@1", 1, level_a="WT", level_b="IDH_mut")
        assert top1 == ("cg_hi",)  # the planted hypermethylated probe ranks first
        top2 = top_k_hypermethylated("se:tcga_laml_idh@1", 2, level_a="WT", level_b="IDH_mut")
        assert top2[0] == "cg_hi" and len(top2) == 2
        # deterministic
        assert top_k_hypermethylated("se:tcga_laml_idh@1", 3) == top_k_hypermethylated("se:tcga_laml_idh@1", 3)
    finally:
        clear_contract_cache()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_split_select.py::test_top_k_selects_hypermethylated_probe -q`
Expected: FAIL with `ImportError: cannot import name 'top_k_hypermethylated'`.

- [ ] **Step 3: Implement**

Append to `src/polymer_claims/split_select.py`:

```python
from polymer_claims.contracts import load_contract


def top_k_hypermethylated(
    ref: str,
    k: int,
    *,
    group_col: str = "Sample_Group",
    level_a: str = "WT",
    level_b: str = "IDH_mut",
) -> tuple[str, ...]:
    """Top-k probes by Δβ = mean(level_b) − mean(level_a), read ONLY from the named contract
    (the discovery half). Descending; ties broken by probe id. Deterministic."""
    se = load_contract(ref)
    betas_path = Path(se.access_methods[0].access_url)
    manifest = json.loads((betas_path.parent / f"{se.contract_uid.split('@')[0]}.json").read_text())
    group_of = {c["sample_id"]: c[group_col] for c in manifest["col_data"]}
    lines = betas_path.read_text().splitlines()
    header = lines[0].split("\t")[1:]
    a_idx = [i for i, sid in enumerate(header) if group_of[sid] == level_a]
    b_idx = [i for i, sid in enumerate(header) if group_of[sid] == level_b]
    if not a_idx or not b_idx:
        raise ValueError(f"empty group (level_a={len(a_idx)}, level_b={len(b_idx)})")
    scored: list[tuple[float, str]] = []
    for ln in lines[1:]:
        cells = ln.split("\t")
        vals = cells[1:]
        ma = sum(float(vals[i]) for i in a_idx) / len(a_idx)
        mb = sum(float(vals[i]) for i in b_idx) / len(b_idx)
        scored.append((mb - ma, cells[0]))
    scored.sort(key=lambda t: (-t[0], t[1]))  # Δβ desc, probe-id tiebreak -> deterministic
    return tuple(p for _, p in scored[:k])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_split_select.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/split_select.py tests/test_split_select.py
git commit -m "feat: top_k_hypermethylated — discovery-side Δβ probe selection

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: The local earned run (gitignored, executed locally)

**Files:**
- Create: `data/tcga_laml/run_region_split.py` (gitignored under `/data/`)

**Interfaces:**
- Consumes: `split_contract`, `top_k_hypermethylated` (Tasks 1–3); `region_delta_beta_claim`, `RegionMeanDiffAdapter`, `RegionLmCoefAdapter`, `methyl_independent_registry` (`methyl_adapters`); `evidence_map` (`evidence`); `materialization_map`; `profile_oracle_id`/`profile_oracle_registry`/`CANONICAL_HM450_V1`; `run_cycle`/`Corpus`/`FDRLedger`. Requires the real `tcga_laml_idh@1` contract already present in `src/polymer_claims/contracts/` (built earlier by `data/tcga_laml/build_contract_xena.py`).

This task is NOT a CI test — it is the real run, executed locally, like the Phase A n-DMP run. There is no failing-test-first cycle; the deliverable is the run + its reported result.

- [ ] **Step 1: Write the run script**

```python
# data/tcga_laml/run_region_split.py
"""LOCAL-ONLY earned run (gitignored). Split tcga_laml_idh -> discovery/test, select top-10k on
discovery, license region-Δβ on the held-out test half. Reports the verdict + numbers."""
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
    RegionLmCoefAdapter,
    RegionMeanDiffAdapter,
    methyl_independent_registry,
    region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_HM450_V1  # noqa: E402
from polymer_claims.split_select import split_contract, top_k_hypermethylated  # noqa: E402

K = 10_000
TAU = 0.10
BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")

print("splitting tcga_laml_idh -> discovery/test (stratified)...", flush=True)
disc_ids, test_ids = split_contract(CONTRACTS)
clear_contract_cache()
print(f"discovery n={len(disc_ids)}  test n={len(test_ids)}", flush=True)

print(f"selecting top-{K} hypermethylated probes on DISCOVERY...", flush=True)
top = top_k_hypermethylated("se:tcga_laml_idh_disc@1", K, level_a="WT", level_b="IDH_mut")
print(f"selected {len(top)} probes (held-out test never touched)", flush=True)

claim = region_delta_beta_claim(
    "tcga-laml-region-split", ref="se:tcga_laml_idh_test@1",
    region_probes=top, group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
    comparator=Comparator.GT, threshold=TAU, oracle_ref=profile_oracle_id(CANONICAL_HM450_V1),
    title="top-10k region Δβ, IDH-mut vs WT (held-out, real TCGA-LAML)",
)
corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
ev = evidence_map(corpus)
print(f"held-out test-half betting e-value (Δβ > {TAU}): {ev.get('tcga-laml-region-split')}", flush=True)
print("running the full gate on the held-out test half...", flush=True)
result = run_cycle(
    corpus, (RegionMeanDiffAdapter(), RegionLmCoefAdapter()), BASE,
    adapter_registry=methyl_independent_registry(),
    oracles=profile_oracle_registry((CANONICAL_HM450_V1, "recomputable_public")),
    materializations=materialization_map(corpus, BASE, profiles=(CANONICAL_HM450_V1,)),
    evidence=ev,
)
c = next(x for x in result.corpus.claims if x.id == "tcga-laml-region-split")
print("=" * 60, flush=True)
print(f"STATUS: {c.status}   LICENSED: {c.status is Status.LICENSED}", flush=True)
if c.licensing is not None:
    print(f"independence_tier: {c.licensing.independence_tier}", flush=True)
    if c.licensing.satisfactions:
        m = c.licensing.satisfactions[0].materialization
        print(f"content-address: dimnames={m.dimnames_hash[:20]}…  profile={(m.profile_hash or '')[:20]}…", flush=True)
print(f"FDR ledger: n_tests={result.corpus.fdr_ledger.n_tests}  n_discoveries={result.corpus.fdr_ledger.n_discoveries}", flush=True)
print("=" * 60, flush=True)
```

- [ ] **Step 2: Run it locally**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run python data/tcga_laml/run_region_split.py 2>&1 | tee data/tcga_laml/region_split_output.log`
Expected: prints the split sizes, selected-probe count, the held-out betting e-value, and the gate verdict — **either** LICENSED at REPRODUCED with the content-address, **or** an honest withhold (status PENDING/REJECTED). Both are valid outcomes (low power at n=10); record whichever occurs.

- [ ] **Step 3: No commit** (the script + outputs are gitignored under `/data/`; nothing real is committed).

---

### Task 5: Document the region-Δβ status (after the local run)

**Files:**
- Modify: `docs/superpowers/CONTINUE.md`, canonical-spec §9, `ARCHITECTURE_CURRENT.md`
- Move: this spec `docs/superpowers/specs/2026-06-17-region-delta-beta-split-design.md` → `docs/superpowers/archive/specs/` (when shipped)

**Interfaces:** documentation only; gated on the Task 4 result.

- [ ] **Step 1: Record the outcome honestly**

If Task 4 LICENSED: note that **region-Δβ is earned at REPRODUCED via held-out top-10k selection** (record the test-half Δβ + e-value + split sizes), and that the severity discipline (discovery/test split) is now prototyped on real data. If it WITHHELD: note that **region-Δβ was attempted via held-out top-10k and the gate withheld at n=10 (low power)** — the system working, reported plainly. In both cases: REPLICATED stays synthetic; the split helpers (`split_select.py`) are the reusable severity machinery for the autonomous loop (Phase D §5b). Example `CONTINUE.md` addition:

```markdown
- **Region-Δβ via held-out top-10k (2026-06-17).** Selected the top-10k DMPs on a discovery half of the
  real TCGA-LAML cohort, licensed/withheld the Δβ betting e-value on the held-out test half (severity /
  no cherry-picking; `split_select.py`). Outcome: <LICENSED at REPRODUCED | honest withhold at n=10>.
  First on-real-data prototype of the autonomous-loop §5b sample-splitting discipline.
```

- [ ] **Step 2: Full gate + commit**

```bash
uv run ruff check src tests && ./scripts/check-all.sh
git add docs/ ARCHITECTURE_CURRENT.md
git commit -m "docs: region-Δβ via held-out top-10k — <earned|attempted> on real TCGA-LAML

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final integration

- [ ] Full gate: `uv run ruff check src tests && ./scripts/check-all.sh` — green (new unit tests pass; no real data needed for them).
- [ ] Merge to `main` `--no-ff` (local-only).

---

## Self-review notes (coverage against the spec)

- Spec §2 stage 1 (stratified split) → Task 1; §2 stage 1 sub-contracts → Task 2; §2 stage 2 (discovery top-k) → Task 3; §2 stage 3 (held-out licensing) → Task 4 (reuses `region_delta_beta_claim`). §3 pre-registered params → Task 4 constants (`K=10_000`, `TAU=0.10`, `Comparator.GT`) + Global Constraints. §4 new helpers + reuse → Tasks 1–3 + Task 4. §5 tests → Tasks 1–3 (CI-safe) + Task 4 (local run). §6 caveats → carried in docs (Task 5) + the run's honest-withhold handling. §7 acceptance → Tasks 1–3 (helpers + tests), Task 4 (run + report), Task 5 (docs).
- **Severity invariant** (test half never influences selection): `top_k_hypermethylated` reads only its `ref` arg (the discovery contract); Task 4 passes `se:tcga_laml_idh_disc@1` to it and `se:tcga_laml_idh_test@1` to the claim. Enforced by construction.
- **Interface check before Task 4 runs:** confirm `c.licensing.satisfactions[0].materialization` (the accessor verified earned in Phase A — `licensing.py:42`) and that `region_delta_beta_claim` accepts `region_probes` as a tuple of the 10k ids (it joins them into the node param string).
