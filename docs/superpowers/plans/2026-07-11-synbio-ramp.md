# Synthetic-Biology Arm Ramp — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Grow the synthetic-biology arm from 5 conjectured probe claims into a substantial, honestly-tiered sub-universe via a manifest-driven ingestion pipeline, while converging IR strain points into a fixed, deduplicated gap-log.

**Architecture:** Extraction is decoupled from construction. Reviewed JSON manifests (one per compendium chapter) are the human-in-the-loop judgment layer; a deterministic builder turns each entry into a real `Claim` through the v1.3 grammar. Every claim is `LITERATURE_EXTRACTED`/`CONJECTURED` (two-stratum rule). A mandatory `schema_fit` field per entry feeds a gap aggregator that dedups strains into canonical `GAP-N` entries. Patterns are registered (analysis-class in the pure grammar, the domain `sense_and_kill` from the umbrella). A tested-but-unlicensed expression two-leg seam scaffolds the future licensed spine.

**Tech Stack:** Python 3.12, pydantic v2, the existing grammar/protocol kernel. JSON manifests (stdlib `json` — no new dep). numpy stays umbrella-only and is not used this session.

**Spec:** `docs/superpowers/specs/2026-07-11-synbio-ramp-design.md`. Program plan: `docs/superpowers/plans/2026-07-10-synbio-claims-universe.md`.

## Global Constraints

- `grammar/` and `protocol/` stay **pure + numpy-free**; `Corpus` has **exactly 4 collections** — never add one.
- **No core-primitive change this session.** W2 is additive registry entries only; W3 *logs* gap candidates but ships no `Leaf`/`StrengthVector` change. Existing corpora (methyl/pharmaco/immuno) must validate byte-identically and their suites stay green.
- Every ingested claim is `GenerationMode.LITERATURE_EXTRACTED` → `Status.CONJECTURED`; nothing self-licenses. **No license is claimed this session** (depth deferred).
- Arm facet is the subject name **`synthetic-biology`** (not `synbio`/`wayland`). Per-claim `topic` facet carries sub-structure.
- Self-contained: regeneration reads only `data/`, never `~/Desktop/Research/` or any sibling.
- Manifests are **JSON** (no PyYAML dep). Tier-3 narrative entries are recorded `"skip": true` and never fabricated into claims.
- Test commands: umbrella `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ -q`; grammar `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -q`; targeted `uv run --project . pytest tests/synbio/ -v`.

---

## Reconciliation notes (deviations from the spec, deliberate)

- **Manifests are JSON, not YAML** (spec §3 updated): PyYAML is not a repo dep; JSON is stdlib, diffable, self-contained.
- **No standalone `synthetic_biology_universe.json` bundle** (spec W3 listed one). The merged universe (`merged-universe.json`) is the default viewer bundle and rebuilds synbio in-process via `collect_synbio()`, so a separate static bundle is redundant. The spec's "merged and rendering" exit gate is satisfied by the merged path (Task 8). Drop per YAGNI.

---

### Task 1: W1 — Pin the compendia into the repo + retarget sources

**Files:**
- Create: `data/synbio_compendia/` (copy of both compendia) + `data/synbio_compendia/SOURCE.md`
- Modify: `src/polymer_claims/synbio/sources.py`
- Test: `tests/synbio/test_sources.py`

**Interfaces:**
- Produces: `SOURCES: dict[str, ClaimSource]` with `_TREATISE` pointing at the in-repo path, extended with the five in-scope PLM chapter keys (`PLM-II` exists; add `PLM-VII` actuation, keep `PLM-VI` computing, `PLM-VIII`? — the concrete set: `PLM-II`, `PLM-III`, `PLM-VI`, `PLM-VII`, `PLM-XIII` already or newly present; add `PLM-VII` for `07-acting-cellular-effectors.md` and `PLM-VIII` for `08-delivery.md`).

- [ ] **Step 1: Copy the compendia into the repo (self-containment)**

```bash
cd /Users/zbb2/Desktop/polymer-claims
mkdir -p data/synbio_compendia
cp -R ~/Desktop/Research/topics/synthetic-biology data/synbio_compendia/synthetic-biology
cp -R ~/Desktop/Research/topics/programmable-living-medicines data/synbio_compendia/programmable-living-medicines
ls data/synbio_compendia/*/ | head
```

- [ ] **Step 2: Write `data/synbio_compendia/SOURCE.md`** recording origin + provenance:

```markdown
# Synbio compendia — pinned source

Copied 2026-07-11 from `~/Desktop/Research/topics/` for self-contained regeneration
(no sibling-directory taps). Two bodies:
- `synthetic-biology/` — technique vocabulary (12 chapters)
- `programmable-living-medicines/` — therapeutic first principles (14 chapters)

These are the reported-stratum sources for the `synthetic-biology` arm's CONJECTURED
literature claims. Referenced by `src/polymer_claims/synbio/sources.py`.
```

- [ ] **Step 3: Write the failing test** (`tests/synbio/test_sources.py` — extend it):

```python
from pathlib import Path

from polymer_claims.synbio.sources import SOURCES

_REPO = Path(__file__).resolve().parents[2]

def test_sources_resolve_in_repo():
    # every ref points at a file that exists inside the repo (no sibling taps)
    for key, src in SOURCES.items():
        p = _REPO / src.ref
        assert p.exists(), f"{key}: {src.ref} not found in-repo"

def test_in_scope_chapters_present():
    for key in ("PLM-II", "PLM-III", "PLM-VI", "PLM-VII", "PLM-VIII", "PLM-XIII"):
        assert key in SOURCES
```

- [ ] **Step 4: Run to verify it fails**

Run: `uv run --project . pytest tests/synbio/test_sources.py -v`
Expected: FAIL (refs point at `Research/...` which is not under the repo; new keys missing).

- [ ] **Step 5: Retarget `sources.py`** — change `_TREATISE` and add the two new chapter sources:

```python
_TREATISE = "data/synbio_compendia/programmable-living-medicines"

SOURCES: dict[str, ClaimSource] = {
    "PLM-I": ClaimSource(ref=f"{_TREATISE}/01-first-principles-programmable-cell.md",
                         title="First Principles: The Cell as a Programmable Therapeutic"),
    "PLM-II": ClaimSource(ref=f"{_TREATISE}/02-reading-surface-antigen-sensing.md",
                          title="Reading I: Surface and Antigen Sensing"),
    "PLM-III": ClaimSource(ref=f"{_TREATISE}/03-reading-intracellular-genome-sensing.md",
                           title="Reading II: Intracellular Genome, Transcriptome, and Epigenome Sensing"),
    "PLM-VI": ClaimSource(ref=f"{_TREATISE}/06-computing-synthetic-circuits.md",
                          title="Computing: Synthetic Gene Circuits and Cellular Logic"),
    "PLM-VII": ClaimSource(ref=f"{_TREATISE}/07-acting-cellular-effectors.md",
                           title="Acting: Cellular Effectors and Payloads"),
    "PLM-VIII": ClaimSource(ref=f"{_TREATISE}/08-delivery.md",
                            title="Delivery"),
    "PLM-XIII": ClaimSource(ref=f"{_TREATISE}/13-research-agenda-open-problems.md",
                            title="A Research Agenda and the Hard Open Problems"),
}
```

- [ ] **Step 6: Run to verify it passes**

Run: `uv run --project . pytest tests/synbio/test_sources.py -v` → PASS.

- [ ] **Step 7: Confirm the compendia are committable** — they are prose docs, not gitignored data; check `git status data/synbio_compendia | head` and `git check-ignore data/synbio_compendia/synthetic-biology/_overview.md` (expect no ignore match). If ignored, note it and commit only `SOURCE.md` + the sources.py change.

- [ ] **Step 8: Commit**

```bash
git add data/synbio_compendia src/polymer_claims/synbio/sources.py tests/synbio/test_sources.py
git commit -m "feat(synbio): pin compendia into data/ for self-contained regeneration"
```

---

### Task 2: W2a — Register the analysis-class patterns in the pure grammar

**Files:**
- Modify: `grammar/src/polymer_grammar/pattern.py`
- Test: `grammar/tests/test_pattern.py`

**Interfaces:**
- Produces: `reported_quantity@v1` and `mechanistic_law@v1` registered in the module `registry`; resolvable via `get_pattern("reported_quantity", "v1")` and `get_pattern("mechanistic_law", "v1")`.

- [ ] **Step 1: Write the failing test** (append to `grammar/tests/test_pattern.py`):

```python
from polymer_grammar.pattern import get_pattern

def test_reported_quantity_pattern_registered():
    p = get_pattern("reported_quantity", "v1")
    assert p.estimand == "reported_scalar"
    assert p.excluded_applications  # >=1, pins the Newman hole

def test_mechanistic_law_pattern_registered():
    p = get_pattern("mechanistic_law", "v1")
    assert p.estimand == "qualitative_law"
    assert p.excluded_applications
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd grammar && uv run pytest tests/test_pattern.py -v`
Expected: FAIL with `KeyError: ('reported_quantity', 'v1')`.

- [ ] **Step 3: Register the two patterns** (append after the `adjusted_effect` registration in `pattern.py`):

```python
registry.register(
    Pattern(
        id="reported_quantity",
        version="v1",
        estimand="reported_scalar",
        null_model="none_reported_prior",
        scale="ratio_or_interval",
        invariance_group="admissible_unit_transform",
        intended_applications=[
            "a reported point measurement (constant, floor, derived ratio) cited from literature",
        ],
        excluded_applications=[
            "an adjusted or model-relative effect (use adjusted_effect)",
            "a recomputed statistic that passes the licensing gate (use its analysis pattern)",
        ],
    )
)

registry.register(
    Pattern(
        id="mechanistic_law",
        version="v1",
        estimand="qualitative_law",
        null_model="no_law_holds",
        scale="ordinal_relation",
        invariance_group="monotone_reparametrization",
        intended_applications=[
            "a reported mechanistic/relational principle serving as a prior or defeater",
        ],
        excluded_applications=[
            "a quantitative statistical estimand (use reported_quantity or adjusted_effect)",
        ],
    )
)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd grammar && uv run pytest tests/test_pattern.py -v` → PASS.

- [ ] **Step 5: Run the full grammar suite** — `cd grammar && uv run pytest -q`. Expected: green (additive registry entry; no existing test disturbed).

- [ ] **Step 6: Commit**

```bash
git add grammar/src/polymer_grammar/pattern.py grammar/tests/test_pattern.py
git commit -m "feat(grammar): register reported_quantity + mechanistic_law patterns"
```

---

### Task 3: W2b — Register the domain `sense_and_kill` pattern from the umbrella + re-point C1–C5

**Files:**
- Create: `src/polymer_claims/synbio/patterns.py`
- Modify: `src/polymer_claims/synbio/claims.py`
- Test: `tests/synbio/test_patterns.py`

**Interfaces:**
- Consumes: the shared singleton `registry` from `polymer_grammar.pattern`; `get_pattern`.
- Produces: importing `polymer_claims.synbio.patterns` registers `sense_and_kill@v1` (side-effect on the shared registry); exports `REPORTED_QUANTITY`, `MECHANISTIC_LAW`, `SENSE_AND_KILL` as `PatternRef`s. `claims.py` references these instead of the local placeholders.

- [ ] **Step 1: Write the failing test** (`tests/synbio/test_patterns.py`):

```python
def test_sense_and_kill_registered_from_umbrella():
    import polymer_claims.synbio.patterns  # noqa: F401 — import registers the pattern
    from polymer_grammar.pattern import get_pattern
    p = get_pattern("sense_and_kill", "v1")
    assert p.excluded_applications

def test_pure_grammar_does_not_know_sense_and_kill():
    # domain pattern must NOT be written into the pure grammar source
    from pathlib import Path
    src = Path(__file__).resolve().parents[2] / "grammar/src/polymer_grammar/pattern.py"
    assert "sense_and_kill" not in src.read_text()

def test_c1_uses_registered_pattern():
    from polymer_claims.synbio.claims import mismatch_energy_claim
    c = mismatch_energy_claim()
    assert c.pattern.id == "reported_quantity" and c.pattern.version == "v1"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --project . pytest tests/synbio/test_patterns.py -v`
Expected: FAIL (`polymer_claims.synbio.patterns` missing).

- [ ] **Step 3: Create `synbio/patterns.py`** (registers the domain pattern against the shared singleton — periphery, not core):

```python
"""Domain pattern registration for the synthetic-biology arm.

`sense_and_kill` is a DOMAIN concept (synbio-specific), so per the expansion doctrine
("domain to the periphery") it is registered from the umbrella against the shared
grammar registry singleton at import — never written into the pure grammar source.
The analysis-class patterns (`reported_quantity`, `mechanistic_law`) live in the pure
grammar; we re-export their refs here so claims.py has a single import site.
"""
from __future__ import annotations

from polymer_grammar.pattern import Pattern, PatternRef, registry

REPORTED_QUANTITY = PatternRef(id="reported_quantity", version="v1")
MECHANISTIC_LAW = PatternRef(id="mechanistic_law", version="v1")
SENSE_AND_KILL = PatternRef(id="sense_and_kill", version="v1")

registry.register(
    Pattern(
        id="sense_and_kill",
        version="v1",
        estimand="design_composition",
        null_model="no_admissible_design",
        scale="categorical_composition",
        invariance_group="component_relabeling",
        intended_applications=[
            "a (reader, discrimination-topology, actuation, target) therapeutic design tuple",
        ],
        excluded_applications=[
            "surface-antigen CAR targeting with no genotype discrimination (use the antigen pattern)",
            "a bare reported quantity or mechanistic law (use reported_quantity / mechanistic_law)",
        ],
    )
)
```

- [ ] **Step 4: Re-point `claims.py` off the placeholders** — replace the local `_REPORTED_QUANTITY`/`_MECHANISTIC_LAW` definitions (lines ~29–31) with an import, and update the docstring note:

```python
from .patterns import MECHANISTIC_LAW as _MECHANISTIC_LAW
from .patterns import REPORTED_QUANTITY as _REPORTED_QUANTITY
```

(Delete the two `PatternRef(...)` placeholder assignments and the now-stale `from polymer_grammar.pattern import PatternRef` if unused. Leave the five factory bodies otherwise unchanged — they already reference `_REPORTED_QUANTITY`/`_MECHANISTIC_LAW`.)

- [ ] **Step 5: Run to verify it passes**

Run: `uv run --project . pytest tests/synbio/ -v` → PASS (patterns test + the existing C1–C5 tests still green).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/synbio/patterns.py src/polymer_claims/synbio/claims.py tests/synbio/test_patterns.py
git commit -m "feat(synbio): register sense_and_kill from umbrella; re-point C1-C5 onto registered patterns"
```

---

### Task 4: W3a — The manifest model + loader

**Files:**
- Create: `src/polymer_claims/synbio/manifest.py`
- Create: `tests/synbio/fixtures/mini_manifest.json`
- Test: `tests/synbio/test_manifest.py`

**Interfaces:**
- Produces: frozen models `SchemaFit`, `ManifestLeaf`, `ManifestEntry`; `load_manifest(path) -> list[ManifestEntry]` (parses JSON, validates each entry, raises on malformed input).

- [ ] **Step 1: Write the fixture** (`tests/synbio/fixtures/mini_manifest.json`):

```json
[
  {
    "id": "sb-plm06-toggle-leak",
    "title": "A synthetic toggle switch's OFF-state leak is ~1-5% of ON",
    "tier": 1,
    "skip": false,
    "topic": "computing",
    "leaf": {
      "kind": "quantity",
      "value": 0.03,
      "unit": null,
      "uncertainty": null,
      "measurement_basis": "DERIVED",
      "formula": "off_state_expression / on_state_expression"
    },
    "source": "PLM-VI",
    "schema_fit": {"status": "clean"}
  },
  {
    "id": "sb-plm06-narrative",
    "title": "Decoupling as a recurring design move (narrative synthesis)",
    "tier": 3,
    "skip": true,
    "topic": "computing",
    "leaf": {"kind": "quantity"},
    "source": "PLM-VI",
    "schema_fit": {"status": "clean"}
  }
]
```

- [ ] **Step 2: Write the failing test** (`tests/synbio/test_manifest.py`):

```python
from pathlib import Path
from polymer_claims.synbio.manifest import load_manifest, ManifestEntry

_FIX = Path(__file__).parent / "fixtures" / "mini_manifest.json"

def test_load_manifest_parses_entries():
    entries = load_manifest(_FIX)
    assert len(entries) == 2
    assert all(isinstance(e, ManifestEntry) for e in entries)

def test_skip_and_tier_preserved():
    entries = load_manifest(_FIX)
    by_id = {e.id: e for e in entries}
    assert by_id["sb-plm06-toggle-leak"].skip is False
    assert by_id["sb-plm06-narrative"].skip is True
    assert by_id["sb-plm06-narrative"].tier == 3

def test_schema_fit_required():
    entries = load_manifest(_FIX)
    assert entries[0].schema_fit.status == "clean"
```

- [ ] **Step 3: Run to verify it fails** → `uv run --project . pytest tests/synbio/test_manifest.py -v` → FAIL (module missing).

- [ ] **Step 4: Implement `synbio/manifest.py`:**

```python
"""JSON manifest schema for reported-stratum synbio claims (the reviewable judgment layer).

One manifest file per compendium chapter, a JSON list of entries. Extraction (this file's
input) is decoupled from construction (`ingest.py`); the manifest is diffable and reviewed
by a human before claims are built. `schema_fit` is mandatory — it feeds the gap ledger.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class _M(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SchemaFit(_M):
    status: str  # "clean" | "gap"
    constraint: str | None = None
    current_ir_behavior: str | None = None
    candidate_resolution: str | None = None
    expansion_class: str | None = None  # general | analysis | subject | domain
    purity_cost: str | None = None


class ManifestLeaf(_M):
    kind: str  # "quantity" | "proposition"
    # quantity
    value: float | None = None
    unit: str | None = None
    uncertainty: float | None = None
    measurement_basis: str | None = None  # "FUNDAMENTAL" | "DERIVED"
    formula: str | None = None
    context: dict | None = None  # {tissue,cell_line,assay,condition}
    # proposition
    data: str | None = None
    warrant: str | None = None
    rebuttal: str | None = None
    warrant_type: str | None = None


class ManifestEntry(_M):
    id: str
    title: str
    tier: int
    skip: bool = False
    topic: str
    leaf: ManifestLeaf
    source: str
    schema_fit: SchemaFit


def load_manifest(path: str | Path) -> list[ManifestEntry]:
    raw = json.loads(Path(path).read_text())
    return [ManifestEntry.model_validate(e) for e in raw]
```

- [ ] **Step 5: Run to verify it passes** → PASS.

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/synbio/manifest.py tests/synbio/test_manifest.py tests/synbio/fixtures/mini_manifest.json
git commit -m "feat(synbio): JSON manifest model + loader"
```

---

### Task 5: W3b — The deterministic claim builder

**Files:**
- Create: `src/polymer_claims/synbio/ingest.py`
- Test: `tests/synbio/test_ingest.py`

**Interfaces:**
- Consumes: `ManifestEntry`/`load_manifest` (Task 4); `REPORTED_QUANTITY`/`MECHANISTIC_LAW` (Task 3); `SOURCES` (Task 1); grammar `Claim`/`QuantityLeaf`/`PropositionLeaf`/`MeasurementContext`/`MeasurementBasis`/`Provenance`/`GenerationMode`/`Status`.
- Produces: `build_claim(entry: ManifestEntry) -> Claim`; `build_manifest_claims(paths: list[Path]) -> tuple[list[Claim], dict[str, str]]` (claims + `claim_id -> topic` map; skips `skip=True` and `tier==3`).

- [ ] **Step 1: Write the failing test** (`tests/synbio/test_ingest.py`):

```python
from pathlib import Path
from polymer_claims.synbio.manifest import load_manifest
from polymer_claims.synbio.ingest import build_claim, build_manifest_claims
from polymer_grammar.leaf import QuantityLeaf, MeasurementBasis
from polymer_grammar.status import Status

_FIX = Path(__file__).parent / "fixtures" / "mini_manifest.json"

def test_build_quantity_claim_is_conjectured_derived():
    entry = next(e for e in load_manifest(_FIX) if e.id == "sb-plm06-toggle-leak")
    c = build_claim(entry)
    leaf = c.leaves[0]
    assert isinstance(leaf, QuantityLeaf)
    assert leaf.measurement_basis is MeasurementBasis.DERIVED
    assert leaf.unit is None and leaf.formula
    assert c.status is Status.CONJECTURED
    assert c.pattern.id == "reported_quantity"

def test_build_manifest_claims_skips_tier3():
    claims, topics = build_manifest_claims([_FIX])
    ids = {c.id for c in claims}
    assert "sb-plm06-toggle-leak" in ids
    assert "sb-plm06-narrative" not in ids          # tier-3 / skip
    assert topics["sb-plm06-toggle-leak"] == "computing"
```

- [ ] **Step 2: Run to verify it fails** → FAIL (module missing).

- [ ] **Step 3: Implement `synbio/ingest.py`:**

```python
"""Deterministic manifest -> Claim builder. Same manifests => same claims (byte-stable).

Every claim is reported-stratum: LITERATURE_EXTRACTED / CONJECTURED. Nothing here licenses.
"""
from __future__ import annotations

from pathlib import Path

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import (
    MeasurementBasis,
    MeasurementContext,
    PropositionLeaf,
    QuantityLeaf,
)
from polymer_grammar.provenance import GenerationMode, Provenance
from polymer_grammar.status import Status

from .manifest import ManifestEntry, load_manifest
from .patterns import MECHANISTIC_LAW, REPORTED_QUANTITY
from .sources import SOURCES


def _provenance(source_key: str) -> Provenance:
    src = SOURCES[source_key]
    return Provenance(
        generated_by=GenerationMode.LITERATURE_EXTRACTED,
        method=src.ref,
        version=src.title,
        search_cardinality=1,
    )


def _context(raw: dict | None) -> MeasurementContext | None:
    if not raw or not any(raw.get(k) for k in ("tissue", "cell_line", "assay", "condition")):
        return None
    return MeasurementContext(
        tissue=raw.get("tissue"),
        cell_line=raw.get("cell_line"),
        assay=raw.get("assay"),
        condition=raw.get("condition"),
    )


def build_claim(entry: ManifestEntry) -> Claim:
    leaf_spec = entry.leaf
    if leaf_spec.kind == "quantity":
        leaf: object = QuantityLeaf(
            value=leaf_spec.value,
            unit=leaf_spec.unit,
            uncertainty=leaf_spec.uncertainty,
            measurement_basis=MeasurementBasis[leaf_spec.measurement_basis],
            formula=leaf_spec.formula,
            context=_context(leaf_spec.context),
        )
        pattern = REPORTED_QUANTITY
    elif leaf_spec.kind == "proposition":
        leaf = PropositionLeaf(
            data=leaf_spec.data,
            warrant=leaf_spec.warrant,
            rebuttal=leaf_spec.rebuttal,
            warrant_type=leaf_spec.warrant_type or "mechanistic_analogy",
        )
        pattern = MECHANISTIC_LAW
    else:
        raise ValueError(f"{entry.id}: unknown leaf kind {leaf_spec.kind!r}")
    return Claim(
        id=entry.id,
        title=entry.title,
        pattern=pattern,
        leaves=(leaf,),
        status=Status.CONJECTURED,
        provenance=_provenance(entry.source),
    )


def build_manifest_claims(paths: list[Path]) -> tuple[list[Claim], dict[str, str]]:
    claims: list[Claim] = []
    topics: dict[str, str] = {}
    for path in paths:
        for entry in load_manifest(path):
            if entry.skip or entry.tier >= 3:
                continue
            claims.append(build_claim(entry))
            topics[entry.id] = entry.topic
    return claims, topics
```

- [ ] **Step 4: Run to verify it passes** → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/synbio/ingest.py tests/synbio/test_ingest.py
git commit -m "feat(synbio): deterministic manifest->Claim builder"
```

---

### Task 6: W3c — The gap-ledger aggregator (the "fixed list")

**Files:**
- Create: `src/polymer_claims/synbio/gap_ledger.py`
- Test: `tests/synbio/test_gap_ledger.py`

**Interfaces:**
- Consumes: `ManifestEntry` (Task 4).
- Produces: `GapRecord` (frozen: `id`, `constraint`, `current_ir_behavior`, `candidate_resolution`, `expansion_class`, `purity_cost`); `aggregate_gaps(entries, start_index=5) -> list[GapRecord]` — collects `schema_fit.status == "gap"` entries, dedups by normalized `(expansion_class, constraint)`, assigns canonical `GAP-N` ids from `start_index`.

- [ ] **Step 1: Write the failing test** (`tests/synbio/test_gap_ledger.py`):

```python
from polymer_claims.synbio.manifest import ManifestEntry
from polymer_claims.synbio.gap_ledger import aggregate_gaps

def _entry(id, status, constraint=None, cls=None):
    return ManifestEntry.model_validate({
        "id": id, "title": id, "tier": 1, "topic": "computing",
        "leaf": {"kind": "quantity"}, "source": "PLM-VI",
        "schema_fit": {"status": status, "constraint": constraint,
                       "expansion_class": cls, "current_ir_behavior": "x",
                       "candidate_resolution": "y", "purity_cost": "z"},
    })

def test_gaps_deduped_and_numbered_from_5():
    entries = [
        _entry("a", "clean"),
        _entry("b", "gap", "no half-life field", "general"),
        _entry("c", "gap", "no half-life field", "general"),   # dup of b
        _entry("d", "gap", "no ontology slot for chassis", "subject"),
    ]
    gaps = aggregate_gaps(entries, start_index=5)
    assert [g.id for g in gaps] == ["GAP-5", "GAP-6"]           # deduped to 2
    assert gaps[0].constraint == "no half-life field"
```

- [ ] **Step 2: Run to verify it fails** → FAIL (module missing).

- [ ] **Step 3: Implement `synbio/gap_ledger.py`:**

```python
"""Aggregate manifest schema_fit gaps into the fixed, deduplicated gap list (GAP-N).

Dedup by normalized (expansion_class, constraint) so the same strain recorded on many
manifest entries collapses to one canonical, numbered entry. Numbering continues from the
existing gap-log (GAP-1..4 already used), default start_index=5.
"""
from __future__ import annotations

from dataclasses import dataclass

from .manifest import ManifestEntry


@dataclass(frozen=True)
class GapRecord:
    id: str
    constraint: str
    current_ir_behavior: str | None
    candidate_resolution: str | None
    expansion_class: str | None
    purity_cost: str | None


def _key(sf) -> tuple[str, str]:
    return ((sf.expansion_class or "").strip().lower(),
            (sf.constraint or "").strip().lower())


def aggregate_gaps(entries: list[ManifestEntry], start_index: int = 5) -> list[GapRecord]:
    seen: dict[tuple[str, str], GapRecord] = {}
    n = start_index
    for e in entries:
        sf = e.schema_fit
        if sf.status != "gap":
            continue
        k = _key(sf)
        if k in seen:
            continue
        seen[k] = GapRecord(
            id=f"GAP-{n}",
            constraint=sf.constraint or "",
            current_ir_behavior=sf.current_ir_behavior,
            candidate_resolution=sf.candidate_resolution,
            expansion_class=sf.expansion_class,
            purity_cost=sf.purity_cost,
        )
        n += 1
    return list(seen.values())
```

- [ ] **Step 4: Run to verify it passes** → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/synbio/gap_ledger.py tests/synbio/test_gap_ledger.py
git commit -m "feat(synbio): gap-ledger aggregator (dedup schema_fit -> canonical GAP-N)"
```

---

### Task 7: W3d — Draft + review the manifests for the five in-scope chapters (the ramp content)

**Files:**
- Create: `data/synbio_compendia/manifests/plm-02-sensing.json`, `plm-03-sensing.json`, `plm-06-computing.json`, `plm-07-actuation.json`, `plm-08-delivery.json`
- Test: `tests/synbio/test_manifests_build.py`

**Interfaces:**
- Consumes: `build_manifest_claims` (Task 5), `aggregate_gaps` (Task 6), `SOURCES` keys (Task 1).
- Produces: reviewed manifest files whose non-skipped entries all build and validate through the grammar.

**Process (this is the human-in-the-loop judgment task — content, not just code):**

- [ ] **Step 1: Extract claims per chapter.** For each in-scope chapter (`02`, `03`, `06`, `07`, `08` under `data/synbio_compendia/programmable-living-medicines/`), read it and record every **Tier-1** (quantitative floor/constant → `quantity`) and **Tier-2** (mechanistic law/design principle → `proposition`) claim as a manifest entry. Record Tier-3 narrative as `"tier": 3, "skip": true`. **Do not fabricate** a claim to hit a count — capture the genuine yield (expect ~5–15 buildable/chapter). Each entry MUST carry a `schema_fit`: `clean` if it mapped without strain, else a classified `gap` record (this is the highest-value field — where the IR strained). A representative entry:

```json
{
  "id": "sb-plm02-affinity-discrimination-window",
  "title": "Antigen-density discrimination window for a CAR is ~10x (tumor vs normal)",
  "tier": 1,
  "skip": false,
  "topic": "sensing",
  "leaf": {
    "kind": "quantity",
    "value": 10.0,
    "unit": null,
    "uncertainty": null,
    "measurement_basis": "DERIVED",
    "formula": "antigen_density_tumor / antigen_density_normal_threshold"
  },
  "source": "PLM-II",
  "schema_fit": {
    "status": "gap",
    "constraint": "the value is a required-ratio threshold, not a measured point; the IR cannot mark a QuantityLeaf as a design floor vs an observation",
    "current_ir_behavior": "stored as a DERIVED quantity with no floor/observation distinction",
    "candidate_resolution": "an optional quantity_role enum (observation|floor|threshold) on QuantityLeaf",
    "expansion_class": "general",
    "purity_cost": "core Leaf field; additive+optional; byte-identity proof required (deferred, logged only)"
  }
}
```

- [ ] **Step 2: Write the failing test** (`tests/synbio/test_manifests_build.py`) — asserts the real manifests all build:

```python
from pathlib import Path
from polymer_claims.synbio.ingest import build_manifest_claims
from polymer_grammar.status import Status

_MANIFESTS = sorted((Path(__file__).resolve().parents[2]
                     / "data/synbio_compendia/manifests").glob("*.json"))

def test_all_manifest_claims_build_and_are_conjectured():
    assert _MANIFESTS, "no manifests found"
    claims, topics = build_manifest_claims(_MANIFESTS)
    assert len(claims) >= 20                     # a real ramp beyond the 5 probe claims
    assert all(c.status is Status.CONJECTURED for c in claims)
    assert all(cid in topics for cid in (c.id for c in claims))

def test_manifest_ids_unique():
    claims, _ = build_manifest_claims(_MANIFESTS)
    ids = [c.id for c in claims]
    assert len(ids) == len(set(ids))
```

- [ ] **Step 3: Run to verify it fails** → FAIL (no manifests yet / <20 claims).

- [ ] **Step 4: Author the five manifest files** from Step 1's extraction until the test passes. Fix any build error by correcting the manifest (e.g. a DERIVED leaf missing its `formula`) — the builder raising IS the grammar enforcing discipline.

- [ ] **Step 5: Run to verify it passes** → `uv run --project . pytest tests/synbio/test_manifests_build.py -v` → PASS.

- [ ] **Step 6: HUMAN REVIEW GATE.** Print the yield (`build_manifest_claims` count, by-topic and by-tier breakdown, and `aggregate_gaps` output) and present the manifests to the operator for review — especially the `schema_fit` annotations. Incorporate feedback before committing.

- [ ] **Step 7: Commit**

```bash
git add data/synbio_compendia/manifests tests/synbio/test_manifests_build.py
git commit -m "feat(synbio): ingest reviewed claims for 5 PLM read/compute/act chapters"
```

---

### Task 8: W3e — Wire `collect_synbio` from manifests + thread the topic facet into the merged universe

**Files:**
- Modify: `src/polymer_claims/synbio/ingest.py` (add `collect_all_synbio_claims`)
- Modify: `src/polymer_claims/merge_universes.py` (`ArmFacet`, `ArmSource`, `merge_universes`, `collect_synbio`)
- Modify: `viewer/scripts/make_merged_universe.py`
- Test: `tests/test_merge_universes.py` (extend), `tests/synbio/test_collect.py`

**Interfaces:**
- Consumes: `build_manifest_claims` (Task 5); `build_all` (existing probe factories, `synbio/probe.py`).
- Produces: `collect_all_synbio_claims() -> tuple[list[Claim], dict[str, str]]` (the 5 probe claims + all manifest claims, with a merged topic map); `ArmFacet.topic: str | None`; `ArmSource.topics: dict[str, str]`; `collect_synbio()` returns `arm="synthetic-biology"` with topics populated.

- [ ] **Step 1: Write the failing tests.**

`tests/synbio/test_collect.py`:

```python
def test_collect_all_includes_probe_and_manifest_claims():
    from polymer_claims.synbio.ingest import collect_all_synbio_claims
    claims, topics = collect_all_synbio_claims()
    ids = {c.id for c in claims}
    assert "synbio-c1-mismatch-energy" in ids            # probe claim
    assert len(claims) >= 25                             # 5 probe + >=20 manifest
    assert all(c.id in topics for c in claims)
```

Extend `tests/test_merge_universes.py`:

```python
def test_synbio_arm_named_by_subject_with_topic_facet():
    from polymer_claims.merge_universes import collect_synbio, merge_universes
    src = collect_synbio()
    assert src.arm == "synthetic-biology"
    merged, facets = merge_universes([src])
    assert any(f.arm == "synthetic-biology" for f in facets.values())
    assert any(f.topic for f in facets.values())         # topic facet populated
```

- [ ] **Step 2: Run to verify they fail** → FAIL (`collect_all_synbio_claims` missing; `arm=="synbio"`; no `topic`).

- [ ] **Step 3: Add `collect_all_synbio_claims` to `ingest.py`:**

```python
def collect_all_synbio_claims() -> tuple[list[Claim], dict[str, str]]:
    """The 5 probe factory claims + every non-skipped manifest claim, with a topic map.
    Probe claims get a static topic; manifest claims carry their own."""
    from .probe import build_all

    _PROBE_TOPICS = {
        "synbio-c1-mismatch-energy": "sensing",
        "synbio-c2-adar-dynamic-range": "sensing",
        "synbio-c3-car-threshold": "sensing",
        "synbio-c4-endosomal-escape": "delivery",
        "synbio-c5-affinity-discrimination-law": "sensing",
    }
    manifest_dir = Path(__file__).resolve().parents[3] / "data/synbio_compendia/manifests"
    paths = sorted(manifest_dir.glob("*.json"))
    m_claims, m_topics = build_manifest_claims(paths)

    claims = list(build_all()) + m_claims
    topics = {**_PROBE_TOPICS, **m_topics}
    return claims, topics
```

- [ ] **Step 4: Thread `topic` through `merge_universes.py`.** Add `topic: str | None = None` to `ArmFacet`; add `topics: dict[str, str] = field(default_factory=dict)` to `ArmSource` (import `field` from dataclasses); in `merge_universes`, set the facet with topic:

```python
facets[c.id] = ArmFacet(arm=src.arm, modality=src.modality, topic=src.topics.get(c.id))
```

Rewrite `collect_synbio`:

```python
def collect_synbio() -> ArmSource:
    """Facet: arm="synthetic-biology", modality="literature" (reported CONJECTURED claims),
    per-claim topic facet (sensing/computing/writing/delivery/actuation/...)."""
    from .synbio.ingest import collect_all_synbio_claims

    claims, topics = collect_all_synbio_claims()
    return ArmSource(arm="synthetic-biology", modality="literature",
                     claims=tuple(claims), topics=topics)
```

- [ ] **Step 5: Tag `topic` in `make_merged_universe.py`** — in the node-tagging loop add `node["topic"] = facet.topic` (and `node["topic"] = None` in the untagged branch).

- [ ] **Step 6: Update any test asserting the old arm string** — `grep -rn '"synbio"' tests/ | grep -i arm` and update expectations from `synbio` → `synthetic-biology` (the merge unit tests). Run `uv run --project . pytest tests/test_merge_universes.py tests/synbio/ -v` → PASS.

- [ ] **Step 7: Regenerate the merged universe and eyeball the counts** (no real license expected; synbio grew):

```bash
uv run --project . python viewer/scripts/make_merged_universe.py 2>&1 | tail -6
```

Expected stderr: `by arm` shows `synthetic-biology: <25+>` and pharmaco/immuno/polymergenomics unchanged; all synbio claims CONJECTURED.

- [ ] **Step 8: Commit**

```bash
git add src/polymer_claims/synbio/ingest.py src/polymer_claims/merge_universes.py viewer/scripts/make_merged_universe.py viewer/public/merged-universe.json tests/
git commit -m "feat(synbio): rename arm to synthetic-biology, ingest manifest claims into merged universe with topic facet"
```

---

### Task 9: W4 — Expression two-leg spine seam (tested, unlicensed; data gate documented)

**Files:**
- Create: `src/polymer_claims/synbio/spine.py`
- Test: `tests/synbio/test_spine_seam.py`

**Interfaces:**
- Produces: `expression_floor_claim(gene, tissue, floor_tpm) -> Claim` (a CONJECTURED claim shape carrying `MeasurementContext(tissue=…, assay="RNA-seq TPM")`); `two_leg_floor_agreement(tpm_leg_a, tpm_leg_b, floor) -> bool` (both legs must agree the value clears the floor). **No `run_cycle`, no license.**

- [ ] **Step 1: Write the failing test** (`tests/synbio/test_spine_seam.py`):

```python
from polymer_claims.synbio.spine import expression_floor_claim, two_leg_floor_agreement
from polymer_grammar.leaf import QuantityLeaf
from polymer_grammar.status import Status

def test_expression_floor_claim_shape_conjectured_with_context():
    c = expression_floor_claim("RUNX1T1", tissue="AML", floor_tpm=13.0)
    leaf = c.leaves[0]
    assert isinstance(leaf, QuantityLeaf)
    assert leaf.context is not None and leaf.context.tissue == "AML"
    assert leaf.context.assay == "RNA-seq TPM"
    assert c.status is Status.CONJECTURED       # scaffold only — no license this session

def test_two_leg_agreement_requires_both():
    assert two_leg_floor_agreement(20.0, 18.0, floor=13.0) is True
    assert two_leg_floor_agreement(20.0, 5.0, floor=13.0) is False   # leg B disagrees
    assert two_leg_floor_agreement(2.0, 3.0, floor=13.0) is False    # both below
```

- [ ] **Step 2: Run to verify it fails** → FAIL (module missing).

- [ ] **Step 3: Implement `synbio/spine.py`:**

```python
"""Expression two-leg spine SEAM (Phase 2d foundation) — the machinery for a future LICENSED
synbio claim, exercised on synthetic values only. NO real data is pinned this session and
`run_cycle` is NOT invoked, so NOTHING here licenses (status stays CONJECTURED).

DATA GATE (next session): pin real AML fusion-expression RNA-seq into data/ (Option A:
TCGA-LAML RNA-seq TPM from UCSC Xena -> "RUNX1-RUNX1T1 clears the ~13 TPM floor in AML";
Option B, self-contained: BLUEPRINT hematopoietic RSEM -> "RUNX1T1/ETO silent in normal
blood"). Then two independent estimators feed `two_leg_floor_agreement` through the
SE-Contract seam + the two-leg AdapterRegistry, and run_cycle mints the license.
"""
from __future__ import annotations

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import (
    MeasurementBasis,
    MeasurementContext,
    QuantityLeaf,
)
from polymer_grammar.provenance import GenerationMode, Provenance
from polymer_grammar.status import Status

from .patterns import REPORTED_QUANTITY


def expression_floor_claim(gene: str, tissue: str, floor_tpm: float) -> Claim:
    return Claim(
        id=f"synbio-spine-{gene.lower()}-{tissue.lower()}-tpm-floor",
        title=f"{gene} clears the ~{floor_tpm:g} TPM expression floor in {tissue}",
        pattern=REPORTED_QUANTITY,
        leaves=(
            QuantityLeaf(
                value=floor_tpm,
                unit=None,
                uncertainty=None,
                measurement_basis=MeasurementBasis.DERIVED,
                formula="gene_tpm >= floor_tpm",
                context=MeasurementContext(tissue=tissue, assay="RNA-seq TPM"),
            ),
        ),
        status=Status.CONJECTURED,  # scaffold: no recompute, no license
        provenance=Provenance(
            generated_by=GenerationMode.LITERATURE_EXTRACTED,
            method="synbio.spine (seam scaffold — data-gated)",
            version="v0",
            search_cardinality=1,
        ),
    )


def two_leg_floor_agreement(tpm_leg_a: float, tpm_leg_b: float, floor: float) -> bool:
    """Both independent legs must agree the value clears the floor (the two-leg gate's
    agreement predicate). Exercised on synthetic values; the real legs arrive with data."""
    return tpm_leg_a >= floor and tpm_leg_b >= floor
```

- [ ] **Step 4: Run to verify it passes** → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/synbio/spine.py tests/synbio/test_spine_seam.py
git commit -m "feat(synbio): expression two-leg spine seam (tested, unlicensed; data gate documented)"
```

---

### Task 10: Finalize — gap-log, full suite, continuity

**Files:**
- Modify: `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`
- Modify: `docs/superpowers/CONTINUE.md`
- Create/Modify: memory (per the memory protocol)

- [ ] **Step 1: Append the new canonical gaps.** Run the aggregator over the real manifests and append each `GAP-N` (from `aggregate_gaps`) to the gap-log under a new `## Ramp gaps (2026-07-11, GAP-5+)` section, each with constraint / current IR behavior / candidate resolution / expansion_class / purity_cost. State the yield verdict (how many distinct new gaps, by class). Note explicitly that none were resolved this session (core-primitive changes deferred, byte-identity-gated).

```bash
uv run --project . python -c "
from pathlib import Path
from polymer_claims.synbio.ingest import build_manifest_claims  # noqa
from polymer_claims.synbio.manifest import load_manifest
from polymer_claims.synbio.gap_ledger import aggregate_gaps
d = Path('data/synbio_compendia/manifests')
entries = [e for p in sorted(d.glob('*.json')) for e in load_manifest(p)]
for g in aggregate_gaps(entries):
    print(g.id, '|', g.expansion_class, '|', g.constraint)
"
```

- [ ] **Step 2: Run the full gate** — `bash scripts/check-all.sh` (or, if the viewer font-fetch step blocks offline, at minimum the three pytest suites + ruff). Expected: umbrella + grammar + protocol green; ruff clean. Record the counts.

- [ ] **Step 3: Update `CONTINUE.md`** — new session-close block: synbio arm renamed `synthetic-biology`, grown from 5 → N claims (all CONJECTURED) via manifest ingestion, gap-log extended to GAP-M, spine seam scaffolded (license deferred on the data gate), compendia pinned into `data/`. Update the merged-universe node/arm counts.

- [ ] **Step 4: Update memory** — a `project` memory recording the ramp state + the deferred data gate + the naming decision; link related memories.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md docs/superpowers/CONTINUE.md
git commit -m "docs(synbio): ramp close — gap-log GAP-5+, CONTINUE + memory update"
```

---

## Self-review (run against the spec)

- **W1 self-containment** → Task 1 (pin compendia, retarget sources, in-repo-resolution test). ✔
- **W2 patterns** → Task 2 (grammar analysis-class) + Task 3 (umbrella domain `sense_and_kill`, re-point C1–C5, pure-core-clean test). ✔
- **W3 ingestion + gap-log** → Tasks 4 (manifest), 5 (builder), 6 (gap aggregator = the fixed list), 7 (content + review gate), 8 (merged universe + topic facet). ✔
- **W4 spine scaffold, license deferred** → Task 9 (seam tested on synthetic values, no `run_cycle`, data gate documented). ✔
- **Gap-log as first-class deliverable** → Task 6 (aggregator) + Task 7 Step 1 (mandatory schema_fit) + Task 10 Step 1 (canonical GAP-N appended). ✔
- **Invariants** (Global Constraints): no core change (Tasks 2–3 additive; gaps logged not patched in Task 10); all CONJECTURED (Tasks 5, 9); Corpus stays 4 (merge unchanged, Task 8); self-contained (Task 1). ✔
- **Type consistency:** `build_manifest_claims -> (claims, topics)` used identically in Tasks 5/8; `ArmFacet.topic` / `ArmSource.topics` defined in Task 8 and consumed in `make_merged_universe`; `REPORTED_QUANTITY`/`MECHANISTIC_LAW` defined in Task 3, imported in Tasks 5/9. ✔
