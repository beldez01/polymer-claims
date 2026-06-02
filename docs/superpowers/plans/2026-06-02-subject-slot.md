# Phase 7 — `Claim.subject` Slot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the polymorphic subject (what a claim is *about*) — a 10-variant `Subject` discriminated union — as an additive-optional `Claim.subject`, adapted to v1.3's frozen/hashable/extra-forbid discipline.

**Architecture:** New module `grammar/subject.py` holding `_SubjectBase`, 5 frozen sub-models, 10 variant models, and the `Subject = Annotated[Union[...], Field(discriminator="kind")]` union (mirrors `leaf.Leaf`). Built in groups; the recursive `CompositeSubject` + the union land last. `claim.py` gains one additive optional field. No `dict` fields anywhere (whole tree stays hashable).

**Tech Stack:** Python 3.12, pydantic v2 (`_Model` frozen + `extra="forbid"`), pytest, uv. Tests: `cd grammar && uv run pytest -q`; lint: `uv run ruff check src tests`.

**Spec:** `docs/superpowers/specs/2026-06-02-subject-slot-spec.md`

---

## File Structure

- Create: `grammar/src/polymer_grammar/subject.py` — `_SubjectBase`; sub-models `PhenopacketRetrieval`, `GeneOrProteinIdentifiers`, `PathwayMembers`, `CohortSourceDataset`, `CohortDefinition`; variants `GenomicRegion`, `VariantVRS`, `S4ObjectRef`, `PhenopacketRef`, `OntologyTerm`, `GeneOrProtein`, `PathwayRef`, `Cohort`, `LiteralSubject`, `CompositeSubject`; the `Subject` union.
- Create: `grammar/tests/test_subject.py`.
- Modify: `grammar/src/polymer_grammar/claim.py` — import `Subject`, add `subject: Subject | None = None`.
- Modify: `grammar/src/polymer_grammar/__init__.py` — export the public subject symbols.

Branch `phase7-subject-slot`; merge `--no-ff` to `main` at the end. Isolation guard stays green (no `polymer_formalclaim`). All module-level imports at TOP (ruff E402, no unused F401).

**Module header for `subject.py`** (Task 1 creates it with this docstring + imports):

```python
"""Polymorphic Subject — what a claim is ABOUT (spec: 2026-06-02-subject-slot-spec.md).

A discriminated union of 10 variant kinds (faithful to the v1.2 SubjectRef), mirroring the
leaf.Leaf sum-type pattern. Adapted to v1.3 discipline: frozen, extra="forbid", and NO dict
fields anywhere (lists→tuples; free-dict escapes → JSON string / tuple-of-pairs / dropped) so
the whole Subject tree is hashable for content-addressing. Imports nothing from polymer_formalclaim.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from .base import _Model
```

---

### Task 1: Scaffold + GenomicRegion + OntologyTerm

**Files:**
- Create: `grammar/src/polymer_grammar/subject.py`
- Test: `grammar/tests/test_subject.py`

- [ ] **Step 1: Write the failing test** — create `grammar/tests/test_subject.py`:

```python
import pytest
from pydantic import ValidationError

from polymer_grammar.subject import GenomicRegion, OntologyTerm


def test_genomic_region_constructs():
    r = GenomicRegion(id="r1", display="chr1:100-200", assembly="GRCh38",
                      chrom="chr1", start=100, end=200)
    assert r.kind == "genomic_region"
    assert r.strand == "."          # default
    assert r.note is None           # shared base default


def test_genomic_region_rejects_start_after_end():
    with pytest.raises(ValidationError):
        GenomicRegion(id="r", display="bad", assembly="GRCh38",
                      chrom="chr1", start=200, end=100)


def test_ontology_term_constructs():
    o = OntologyTerm(id="HP:0001250", display="Seizure", ontology="HPO",
                     ontology_release="2026-01-01", uri="http://purl.obolibrary.org/obo/HP_0001250")
    assert o.kind == "ontology_term"
    assert o.propagation == "self_only"   # default
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_subject.py -q`
Expected: FAIL (ModuleNotFoundError: No module named 'polymer_grammar.subject')

- [ ] **Step 3: Write minimal implementation** — create `grammar/src/polymer_grammar/subject.py` with the module header shown above (docstring + imports), then APPEND:

```python
class _SubjectBase(_Model):
    """Fields every subject variant carries."""
    id: str
    display: str
    note: str | None = None


class GenomicRegion(_SubjectBase):
    kind: Literal["genomic_region"] = "genomic_region"
    assembly: str
    chrom: str
    start: int
    end: int
    strand: Literal["+", "-", "."] = "."

    @model_validator(mode="after")
    def _start_le_end(self) -> "GenomicRegion":
        if self.start > self.end:
            raise ValueError(f"GenomicRegion start ({self.start}) > end ({self.end})")
        return self


class OntologyTerm(_SubjectBase):
    kind: Literal["ontology_term"] = "ontology_term"
    ontology: Literal[
        "HPO", "MONDO", "GO", "EFO", "UBERON", "CL", "CHEBI", "PR",
        "DOID", "NCIT", "SO", "ECO", "other",
    ]
    ontology_release: str
    uri: str
    propagation: Literal[
        "self_only", "self_or_descendant", "self_or_ancestor", "exact_match"
    ] = "self_only"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_subject.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/subject.py grammar/tests/test_subject.py
git commit -m "feat(grammar): subject.py scaffold + GenomicRegion + OntologyTerm variants"
```

---

### Task 2: VariantVRS + GeneOrProtein + S4ObjectRef

**Files:**
- Modify: `grammar/src/polymer_grammar/subject.py`
- Test: `grammar/tests/test_subject.py`

- [ ] **Step 1: Write the failing test** — APPEND to `grammar/tests/test_subject.py`; add `GeneOrProtein, GeneOrProteinIdentifiers, S4ObjectRef, VariantVRS` to the existing `from polymer_grammar.subject import (...)` line:

```python
def test_variant_vrs_constructs_and_validates_id():
    v = VariantVRS(id="ga4gh:VA.abc123", display="rs1 A>G", vrs_version="2.0", hgvs="NC_000001.11:g.100A>G")
    assert v.kind == "variant_vrs"
    with pytest.raises(ValidationError):
        VariantVRS(id="not-a-vrs-id", display="bad", vrs_version="2.0")


def test_gene_or_protein_requires_a_canonical_id():
    g = GeneOrProtein(
        id="HGNC:11998", display="TP53",
        identifiers=GeneOrProteinIdentifiers(hgnc="HGNC:11998", symbol="TP53"),
        entity_type="gene",
    )
    assert g.kind == "gene_or_protein"
    with pytest.raises(ValidationError):
        GeneOrProtein(
            id="x", display="no ids",
            identifiers=GeneOrProteinIdentifiers(symbol="TP53"),   # none of hgnc/ensembl_gene/uniprot
            entity_type="gene",
        )


def test_s4_object_ref_dims_is_tuple():
    s = S4ObjectRef(id="s1", display="SummarizedExperiment", bioc_class="SummarizedExperiment",
                    bioc_version="1.30", blob_uri="s3://b/x.rds", blob_hash="blake3-abc",
                    dims=(200, 50))
    assert s.kind == "s4_object"
    assert s.dims == (200, 50)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_subject.py -q`
Expected: FAIL (ImportError: cannot import name 'VariantVRS')

- [ ] **Step 3: Write minimal implementation** — APPEND to `grammar/src/polymer_grammar/subject.py`:

```python
class VariantVRS(_SubjectBase):
    kind: Literal["variant_vrs"] = "variant_vrs"
    vrs_version: str
    assembly: str | None = None
    hgvs: str | None = None

    @model_validator(mode="after")
    def _id_has_vrs_prefix(self) -> "VariantVRS":
        if not (self.id.startswith("ga4gh:VA.") or self.id.startswith("ga4gh:VCL.")):
            raise ValueError(
                f"VariantVRS.id must start with 'ga4gh:VA.' or 'ga4gh:VCL.', got {self.id!r}"
            )
        return self


class S4ObjectRef(_SubjectBase):
    kind: Literal["s4_object"] = "s4_object"
    bioc_class: str
    bioc_version: str
    blob_uri: str
    blob_hash: str
    projection: str | None = None
    dims: tuple[int, ...] | None = None


class GeneOrProteinIdentifiers(_Model):
    hgnc: str | None = None
    ensembl_gene: str | None = None
    ensembl_transcript: str | None = None
    ensembl_protein: str | None = None
    ncbi_gene: int | None = None
    uniprot: str | None = None
    refseq: str | None = None
    symbol: str | None = None


class GeneOrProtein(_SubjectBase):
    kind: Literal["gene_or_protein"] = "gene_or_protein"
    identifiers: GeneOrProteinIdentifiers
    entity_type: Literal["gene", "protein", "transcript", "isoform"]
    assembly_context: str | None = None

    @model_validator(mode="after")
    def _at_least_one_canonical_id(self) -> "GeneOrProtein":
        ids = self.identifiers
        if not (ids.hgnc or ids.ensembl_gene or ids.uniprot):
            raise ValueError(
                "GeneOrProtein.identifiers requires at least one of hgnc, ensembl_gene, uniprot"
            )
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_subject.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/subject.py grammar/tests/test_subject.py
git commit -m "feat(grammar): VariantVRS + GeneOrProtein + S4ObjectRef subject variants"
```

---

### Task 3: PhenopacketRef + PathwayRef

**Files:**
- Modify: `grammar/src/polymer_grammar/subject.py`
- Test: `grammar/tests/test_subject.py`

- [ ] **Step 1: Write the failing test** — APPEND; add `PathwayMembers, PathwayRef, PhenopacketRef, PhenopacketRetrieval` to the existing `from polymer_grammar.subject import (...)` line:

```python
def test_phenopacket_reference_mode_requires_uri():
    p = PhenopacketRef(
        id="pp1", display="Patient A", phenopacket_version="2.0",
        retrieval=PhenopacketRetrieval(mode="reference", uri="s3://b/pp1.json"),
    )
    assert p.kind == "phenopacket"
    with pytest.raises(ValidationError):
        PhenopacketRef(id="pp", display="bad", phenopacket_version="2.0",
                       retrieval=PhenopacketRetrieval(mode="reference"))   # no uri


def test_phenopacket_inline_mode_requires_inline_json():
    p = PhenopacketRef(
        id="pp2", display="inline", phenopacket_version="2.0",
        retrieval=PhenopacketRetrieval(mode="inline"), inline_json='{"id":"pp2"}',
    )
    assert p.inline_json == '{"id":"pp2"}'
    with pytest.raises(ValidationError):
        PhenopacketRef(id="pp", display="bad", phenopacket_version="2.0",
                       retrieval=PhenopacketRetrieval(mode="inline"))      # no inline_json


def test_pathway_ref_members_inline_is_tuple():
    pw = PathwayRef(id="R-HSA-1", display="Apoptosis", source="Reactome", source_version="88",
                    members=PathwayMembers(retrieval="inline", inline=("TP53", "BAX")))
    assert pw.kind == "pathway"
    assert pw.members.inline == ("TP53", "BAX")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_subject.py -q`
Expected: FAIL (ImportError: cannot import name 'PhenopacketRef')

- [ ] **Step 3: Write minimal implementation** — APPEND to `grammar/src/polymer_grammar/subject.py`:

```python
class PhenopacketRetrieval(_Model):
    mode: Literal["reference", "inline"]
    uri: str | None = None
    hash: str | None = None


class PhenopacketRef(_SubjectBase):
    kind: Literal["phenopacket"] = "phenopacket"
    phenopacket_version: str
    retrieval: PhenopacketRetrieval
    inline_json: str | None = None   # v1.2 inline:dict -> canonical JSON string (hashable)

    @model_validator(mode="after")
    def _retrieval_consistent(self) -> "PhenopacketRef":
        if self.retrieval.mode == "reference" and not self.retrieval.uri:
            raise ValueError("PhenopacketRef.retrieval.mode='reference' requires retrieval.uri")
        if self.retrieval.mode == "inline" and self.inline_json is None:
            raise ValueError("PhenopacketRef.retrieval.mode='inline' requires inline_json")
        return self


class PathwayMembers(_Model):
    retrieval: Literal["reference", "inline"] = "reference"
    uri: str | None = None
    count_hint: int | None = None
    inline: tuple[str, ...] | None = None   # v1.2 list -> tuple


class PathwayRef(_SubjectBase):
    kind: Literal["pathway"] = "pathway"
    source: Literal["Reactome", "KEGG", "WikiPathways", "MSigDB", "other"]
    source_version: str
    members: PathwayMembers | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_subject.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/subject.py grammar/tests/test_subject.py
git commit -m "feat(grammar): PhenopacketRef + PathwayRef subject variants"
```

---

### Task 4: Cohort + LiteralSubject

**Files:**
- Modify: `grammar/src/polymer_grammar/subject.py`
- Test: `grammar/tests/test_subject.py`

- [ ] **Step 1: Write the failing test** — APPEND; add `Cohort, CohortDefinition, CohortSourceDataset, LiteralSubject` to the existing `from polymer_grammar.subject import (...)` line:

```python
def test_cohort_constructs_with_tuple_predicates():
    c = Cohort(
        id="coh1", display="TET2 cohort", members_hash="blake3-xyz",
        definition=CohortDefinition(
            source_dataset=CohortSourceDataset(name="IDAT", version="v2", tissue="blood"),
            inclusion=("age >= 18", "tissue == blood"),
            cardinality=132,
        ),
    )
    assert c.kind == "cohort"
    assert c.definition.inclusion == ("age >= 18", "tissue == blood")
    assert c.definition.exclusion == ()        # default empty tuple


def test_literal_subject_structured_is_tuple_of_pairs():
    lit = LiteralSubject(id="l1", display="ad hoc", prose="the 2026 winter cohort",
                         structured=(("season", "winter"), ("year", "2026")))
    assert lit.kind == "literal"
    assert lit.structured == (("season", "winter"), ("year", "2026"))
    bare = LiteralSubject(id="l2", display="prose only", prose="something untyped")
    assert bare.structured == ()               # default
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_subject.py -q`
Expected: FAIL (ImportError: cannot import name 'Cohort')

- [ ] **Step 3: Write minimal implementation** — APPEND to `grammar/src/polymer_grammar/subject.py`:

```python
class CohortSourceDataset(_Model):
    name: str
    version: str | None = None
    tissue: str | None = None
    # v1.2's `extra: dict` escape hatch dropped (unhashable)


class CohortDefinition(_Model):
    source_dataset: CohortSourceDataset | None = None
    inclusion: tuple[str, ...] = ()   # v1.2 SetExpression predicate algebra -> prose strings for now
    exclusion: tuple[str, ...] = ()
    cardinality: int | None = None
    random_seed: int | None = None


class Cohort(_SubjectBase):
    kind: Literal["cohort"] = "cohort"
    definition: CohortDefinition
    members_hash: str


class LiteralSubject(_SubjectBase):
    kind: Literal["literal"] = "literal"
    prose: str
    structured: tuple[tuple[str, str], ...] = ()   # v1.2 extra="allow" dict -> explicit pairs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_subject.py -q`
Expected: PASS (11 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/subject.py grammar/tests/test_subject.py
git commit -m "feat(grammar): Cohort + LiteralSubject subject variants"
```

---

### Task 5: CompositeSubject + the `Subject` discriminated union

**Files:**
- Modify: `grammar/src/polymer_grammar/subject.py`
- Test: `grammar/tests/test_subject.py`

- [ ] **Step 1: Write the failing test** — APPEND; add `CompositeSubject, Subject` to the existing `from polymer_grammar.subject import (...)` line, and add `from pydantic import TypeAdapter` to the top imports:

```python
def test_composite_nests_two_subjects():
    gene = GeneOrProtein(id="HGNC:11998", display="TP53",
                         identifiers=GeneOrProteinIdentifiers(hgnc="HGNC:11998"), entity_type="gene")
    coh = Cohort(id="coh1", display="cohort", members_hash="h",
                 definition=CohortDefinition())
    comp = CompositeSubject(id="cmp1", display="TP53 in cohort", relation="conditional",
                            parts=(gene, coh))
    assert comp.kind == "composite"
    assert len(comp.parts) == 2


def test_composite_requires_at_least_two_parts():
    gene = GeneOrProtein(id="g", display="g",
                         identifiers=GeneOrProteinIdentifiers(hgnc="HGNC:1"), entity_type="gene")
    with pytest.raises(ValidationError):
        CompositeSubject(id="c", display="bad", relation="conditional", parts=(gene,))


def test_subject_union_dispatches_on_kind():
    adapter = TypeAdapter(Subject)
    obj = adapter.validate_python(
        {"kind": "ontology_term", "id": "GO:0006915", "display": "apoptosis",
         "ontology": "GO", "ontology_release": "2026-01-01", "uri": "http://x/GO_0006915"}
    )
    assert isinstance(obj, OntologyTerm)


def test_subjects_are_hashable():
    gene = GeneOrProtein(id="g", display="g",
                         identifiers=GeneOrProteinIdentifiers(hgnc="HGNC:1"), entity_type="gene")
    comp = CompositeSubject(id="c", display="c", relation="correlational",
                            parts=(gene, gene))
    assert isinstance(hash(gene), int)
    assert isinstance(hash(comp), int)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_subject.py -q`
Expected: FAIL (ImportError: cannot import name 'CompositeSubject')

- [ ] **Step 3: Write minimal implementation** — APPEND to `grammar/src/polymer_grammar/subject.py`:

```python
class CompositeSubject(_SubjectBase):
    kind: Literal["composite"] = "composite"
    parts: tuple["Subject", ...] = Field(min_length=2)
    relation: Literal[
        "co_occurrence", "conditional", "causal_hypothesis",
        "temporal_sequence", "correlational",
    ]


Subject = Annotated[
    Union[
        GenomicRegion,
        VariantVRS,
        S4ObjectRef,
        PhenopacketRef,
        OntologyTerm,
        GeneOrProtein,
        PathwayRef,
        Cohort,
        LiteralSubject,
        CompositeSubject,
    ],
    Field(discriminator="kind"),
]

# CompositeSubject.parts references the Subject union defined above; resolve the forward ref.
CompositeSubject.model_rebuild()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_subject.py -q`
Expected: PASS (15 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/subject.py grammar/tests/test_subject.py
git commit -m "feat(grammar): CompositeSubject + Subject discriminated union"
```

---

### Task 6: Wire `Claim.subject`

**Files:**
- Modify: `grammar/src/polymer_grammar/claim.py`
- Test: `grammar/tests/test_claim_subject.py`

- [ ] **Step 1: Write the failing test** — create `grammar/tests/test_claim_subject.py`:

```python
from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import Status
from polymer_grammar.subject import GeneOrProtein, GeneOrProteinIdentifiers


def _leaf():
    return QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f")


def _claim(**kw):
    base = dict(id="c", title="c", pattern=PatternRef(id="p", version="v1"),
                leaves=(_leaf(),), status=Status.LICENSED)
    base.update(kw)
    return Claim(**base)


def test_claim_carries_a_subject():
    g = GeneOrProtein(id="HGNC:11998", display="TP53",
                      identifiers=GeneOrProteinIdentifiers(hgnc="HGNC:11998"), entity_type="gene")
    c = _claim(subject=g)
    assert c.subject is g
    assert c.subject.kind == "gene_or_protein"


def test_claim_subject_is_optional_backcompat():
    c = _claim()
    assert c.subject is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_claim_subject.py -q`
Expected: FAIL (TypeError: unexpected keyword argument 'subject', or AttributeError)

- [ ] **Step 3: Write minimal implementation** — in `grammar/src/polymer_grammar/claim.py`, add `from .subject import Subject` to the imports (with the other relative imports), and add the field to the `Claim` class body alongside `roles`:

```python
    subject: Subject | None = None
```

(Place it after the `roles: CausalRoles | None = None` line. No validator — it's additive/optional, mirroring `conclusion`/`licensing`/`roles`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_claim_subject.py -q`
Expected: PASS (2 passed). Also run `cd grammar && uv run pytest tests/test_claim.py -q` to confirm existing Claim tests still pass (back-compat).

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/claim.py grammar/tests/test_claim_subject.py
git commit -m "feat(grammar): additive optional Claim.subject field"
```

---

### Task 7: Package exports + whole-package verification

**Files:**
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_subject.py`

- [ ] **Step 1: Write the failing test** — APPEND to `grammar/tests/test_subject.py`:

```python
def test_public_api_exports():
    import polymer_grammar as pg

    for name in [
        "Subject", "GenomicRegion", "VariantVRS", "S4ObjectRef", "PhenopacketRef",
        "OntologyTerm", "GeneOrProtein", "PathwayRef", "Cohort", "LiteralSubject",
        "CompositeSubject", "GeneOrProteinIdentifiers", "CohortDefinition",
        "CohortSourceDataset", "PhenopacketRetrieval", "PathwayMembers",
    ]:
        assert hasattr(pg, name), f"{name} not exported from polymer_grammar"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_subject.py::test_public_api_exports -q`
Expected: FAIL (AssertionError: Subject not exported from polymer_grammar)

- [ ] **Step 3: Write minimal implementation** — in `grammar/src/polymer_grammar/__init__.py`, ADD a new import block after the existing ones:

```python
from .subject import (
    Cohort,
    CohortDefinition,
    CohortSourceDataset,
    CompositeSubject,
    GeneOrProtein,
    GeneOrProteinIdentifiers,
    GenomicRegion,
    LiteralSubject,
    OntologyTerm,
    PathwayMembers,
    PathwayRef,
    PhenopacketRef,
    PhenopacketRetrieval,
    S4ObjectRef,
    Subject,
    VariantVRS,
)
```

And ADD these strings to the `__all__` list (anywhere in the list):

```python
    "Cohort",
    "CohortDefinition",
    "CohortSourceDataset",
    "CompositeSubject",
    "GeneOrProtein",
    "GeneOrProteinIdentifiers",
    "GenomicRegion",
    "LiteralSubject",
    "OntologyTerm",
    "PathwayMembers",
    "PathwayRef",
    "PhenopacketRef",
    "PhenopacketRetrieval",
    "S4ObjectRef",
    "Subject",
    "VariantVRS",
```

- [ ] **Step 4: Run the whole suite + lint**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: PASS — all prior tests (160) + the new subject/claim-subject tests (18) = 178 green; ruff clean. Confirm `tests/test_isolation.py` passes (no `polymer_formalclaim` import leaked in).

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/polymer-claims
git add grammar/src/polymer_grammar/__init__.py grammar/tests/test_subject.py
git commit -m "feat(grammar): export polymorphic Subject public API"
```

---

## Final integration

- [ ] **Merge to main** (no-ff, per project rhythm):

```bash
cd ~/Desktop/polymer-claims
git checkout main
git merge --no-ff phase7-subject-slot -m "merge: polymorphic Claim.subject slot (10-variant SubjectRef port)"
cd grammar && uv run pytest -q   # verify green on the merged result
git branch -d phase7-subject-slot
```

- [ ] **Update** the Progress Log (below), `docs/superpowers/CONTINUE.md`, the root README, and memory `project_polymer_claims_knowledge_protocol`. Note this closes the biggest ingestion-fidelity gap (no `Claim.subject` slot); the vector-`Leaf` gap and a faithful subject-carrying re-ingest remain.

---

## Progress Log

_(Update after every completed task: check the box, note the commit SHA + any decisions.)_

- [x] Task 1 — scaffold + GenomicRegion + OntologyTerm — `cc57e78`
- [x] Task 2 — VariantVRS + GeneOrProtein + S4ObjectRef — `28b9ec5`
- [x] Task 3 — PhenopacketRef + PathwayRef — `ad82c46`
- [x] Task 4 — Cohort + LiteralSubject — `2d140c6`
- [x] Task 5 — CompositeSubject + Subject union (recursive, model_rebuild) — `47ad12f`
- [x] Task 6 — wire Claim.subject (additive) — `dd8426c`
- [x] Task 7 — exports + whole-package verify — `0265e4d`
- [x] Final — merged `--no-ff` to main (`eecf318`), 178 tests green + ruff clean on merged result, branch deleted. Opus final review = READY TO MERGE (hashability of all 10 variants + nested composite, TypeAdapter dispatch, every validator, and a full Claim-with-composite JSON round-trip independently verified). Docs + memory updated. Closes the biggest ingestion-fidelity gap (no Claim.subject); vector-`Leaf` gap + a faithful subject-carrying re-ingest remain.
