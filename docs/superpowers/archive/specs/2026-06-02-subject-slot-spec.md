# Phase 7 — `Claim.subject` slot (polymorphic subject) — design spec

Date: 2026-06-02
Status: design (feeds `writing-plans`)
Carried-forward gap: the v1.2→v1.3 ingestion probe found `subject` homeless in 47/47 claims (the biggest fidelity hole). v1.2 had a 10-variant `SubjectRef`; v1.3 dropped it. This restores it, adapted to v1.3 discipline.
Depends on: `base._Model`; wires into `claim.Claim`.

## 0. Reading guide

Every scientific claim is *about* something — a gene, a variant, a region, a cohort, an ontology
term. v1.3 currently can't say what a claim is about. This adds a polymorphic **`Subject`** — a
discriminated union of 10 variant types (faithful to v1.2's kinds) — as an additive optional field
on `Claim`. It mirrors the existing `Leaf` sum-type pattern exactly. The one non-trivial part is
**adaptation to v1.3's frozen + hashable + `extra="forbid"` discipline**: v1.2 used `dict`/`list`
fields and an `extra="allow"` escape hatch, both of which break hashability/forbid-extras, so those
are replaced with tuples / JSON strings / dropped escape-dicts. The *kinds* are 100% faithful; the
*representation* is hardened.

## 1. Goal & scope

Add `grammar/subject.py`: `_SubjectBase` + 10 variant models + 5 sub-models + the `Subject`
discriminated union. Wire additive-optional `Claim.subject: Subject | None = None`. Frozen
`_Model`, tuples/frozensets, no `dict` fields anywhere (the whole `Subject` tree stays hashable for
content-addressing). Isolation guard holds (no `polymer_formalclaim` import). Export from `__init__`.

**Out of scope (follow-ups):** a real cohort predicate algebra (v1.2's `SetExpression` — represented
here as prose `tuple[str,...]`); making `subject` required (a later tightening phase, like
`conclusion`); a faithful re-ingest of the v1.2 corpus carrying subjects (a separate exercise once
the slot exists).

## 2. The discriminated union

```python
Subject = Annotated[
    Union[
        GenomicRegion, VariantVRS, S4ObjectRef, PhenopacketRef, OntologyTerm,
        GeneOrProtein, PathwayRef, Cohort, LiteralSubject, CompositeSubject,
    ],
    Field(discriminator="kind"),
]
```

Mirrors `leaf.Leaf`. Every variant subclasses `_SubjectBase` and adds a `kind: Literal[...]`
discriminator. `CompositeSubject` is **recursive** (`parts: tuple["Subject", ...]`) — with
`from __future__ import annotations` the forward reference resolves; call
`CompositeSubject.model_rebuild()` after `Subject` is defined if pydantic doesn't resolve it lazily
(v1.2 used the same recursive pattern successfully with `list`).

## 3. Shared base

```python
class _SubjectBase(_Model):       # frozen, extra="forbid"
    id: str
    display: str
    note: str | None = None
```

## 4. The 10 variants (fields + v1.3 adaptations + validators)

1. **GenomicRegion** — `kind="genomic_region"`, `assembly: str`, `chrom: str`, `start: int`,
   `end: int`, `strand: Literal["+", "-", "."] = "."`. *Validator:* `start <= end`.
2. **VariantVRS** — `kind="variant_vrs"`, `vrs_version: str`, `assembly: str | None = None`,
   `hgvs: str | None = None`. *Validator:* `id` starts with `ga4gh:VA.` or `ga4gh:VCL.`.
   *(Adaptation: v1.2's `canonical_allele: dict` is DROPPED — the VRS `id` + optional `hgvs`
   identify the allele; a structured allele can be a follow-up.)*
3. **S4ObjectRef** — `kind="s4_object"`, `bioc_class: str`, `bioc_version: str`, `blob_uri: str`,
   `blob_hash: str`, `projection: str | None = None`, `dims: tuple[int, ...] | None = None`.
   *(Adaptation: `dims` list→tuple.)*
4. **PhenopacketRef** — `kind="phenopacket"`, `phenopacket_version: str`,
   `retrieval: PhenopacketRetrieval`, `inline_json: str | None = None`. *Validators:*
   `retrieval.mode=="reference"` requires `retrieval.uri`; `retrieval.mode=="inline"` requires
   `inline_json`. *(Adaptation: v1.2's `inline: dict` → `inline_json: str` — a canonical JSON
   string, hashable.)*
5. **OntologyTerm** — `kind="ontology_term"`, `ontology: Literal["HPO","MONDO","GO","EFO","UBERON",
   "CL","CHEBI","PR","DOID","NCIT","SO","ECO","other"]`, `ontology_release: str` (ISO date),
   `uri: str`, `propagation: Literal["self_only","self_or_descendant","self_or_ancestor",
   "exact_match"] = "self_only"`.
6. **GeneOrProtein** — `kind="gene_or_protein"`, `identifiers: GeneOrProteinIdentifiers`,
   `entity_type: Literal["gene","protein","transcript","isoform"]`,
   `assembly_context: str | None = None`. *Validator:* `identifiers` has ≥1 of
   `hgnc`/`ensembl_gene`/`uniprot`.
7. **PathwayRef** — `kind="pathway"`, `source: Literal["Reactome","KEGG","WikiPathways","MSigDB",
   "other"]`, `source_version: str`, `members: PathwayMembers | None = None`.
8. **Cohort** — `kind="cohort"`, `definition: CohortDefinition`, `members_hash: str`.
9. **LiteralSubject** — `kind="literal"`, `prose: str`,
   `structured: tuple[tuple[str, str], ...] = ()`. *(Adaptation: v1.2's `extra="allow"` structured
   dict → an explicit frozen tuple of (key, value) string pairs.)*
10. **CompositeSubject** — `kind="composite"`, `parts: tuple[Subject, ...]` (min 2),
    `relation: Literal["co_occurrence","conditional","causal_hypothesis","temporal_sequence",
    "correlational"]`. *Validator:* `len(parts) >= 2` (via `Field(min_length=2)` on the tuple).

## 5. Sub-models (all frozen, no `dict` fields)

```python
class PhenopacketRetrieval(_Model):
    mode: Literal["reference", "inline"]
    uri: str | None = None
    hash: str | None = None

class GeneOrProteinIdentifiers(_Model):
    hgnc: str | None = None
    ensembl_gene: str | None = None
    ensembl_transcript: str | None = None
    ensembl_protein: str | None = None
    ncbi_gene: int | None = None
    uniprot: str | None = None
    refseq: str | None = None
    symbol: str | None = None

class PathwayMembers(_Model):
    retrieval: Literal["reference", "inline"] = "reference"
    uri: str | None = None
    count_hint: int | None = None
    inline: tuple[str, ...] | None = None          # v1.2 list → tuple

class CohortSourceDataset(_Model):
    name: str
    version: str | None = None
    tissue: str | None = None
    # v1.2's `extra: dict` escape hatch is DROPPED (unhashable; use note/structured elsewhere)

class CohortDefinition(_Model):
    source_dataset: CohortSourceDataset | None = None
    inclusion: tuple[str, ...] = ()                # v1.2 SetExpression predicate algebra →
    exclusion: tuple[str, ...] = ()                #   prose string predicates for now (corpus had these empty)
    cardinality: int | None = None
    random_seed: int | None = None
```

## 6. Wiring into Claim

Additive optional field, mirroring `conclusion`/`licensing`/`roles`:

```python
# claim.py
from .subject import Subject
class Claim(_Model):
    ...
    subject: Subject | None = None
```

No validator (optional). Existing claims (no `subject`) still construct — verified by a back-compat
test. Making `subject` required is deferred to a later tightening phase (same policy as
`conclusion`).

## 7. Module boundaries

- `subject.py` — `_SubjectBase`, the 5 sub-models, the 10 variant models, the `Subject` union.
  Depends only on `base._Model` + stdlib `typing`/`pydantic`. No import of `claim`/`leaf`/etc.
  (`claim.py` imports `subject`, not the reverse — no cycle.)
- `claim.py` — one new import + one new optional field.
- Export `Subject` + the 10 variant classes from `__init__.py` (sub-models stay internal unless a
  test needs them; export `GeneOrProteinIdentifiers`, `CohortDefinition`, `PhenopacketRetrieval`,
  `PathwayMembers`, `CohortSourceDataset` too, since they're needed to construct subjects).

## 8. Testing (TDD)

- Each of the 10 variants: constructs with valid data; `kind` discriminator correct.
- Validators: `genomic_region` rejects `start > end`; `variant_vrs` rejects a non-`ga4gh:` id;
  `gene_or_protein` rejects identifiers with none of hgnc/ensembl_gene/uniprot; `phenopacket`
  rejects reference-mode without `uri` and inline-mode without `inline_json`; `composite` rejects
  `< 2` parts.
- Discriminated-union dispatch: a `dict` with `kind="ontology_term"` validates into `OntologyTerm`,
  not another variant (via a `pydantic.TypeAdapter(Subject)` round-trip test).
- `composite` nests (parts containing a `gene_or_protein` + a `cohort`).
- hashability: a representative `Subject` (e.g. `GeneOrProtein`, and a nested `CompositeSubject`) is
  hashable; all models frozen + `extra="forbid"`.
- `Claim.subject`: a Claim with a `Subject` round-trips; a Claim WITHOUT `subject` still constructs
  (back-compat) and `subject is None`.
- exports resolve from `polymer_grammar`; isolation guard green.

## 9. Follow-ups (deferred)

- A real cohort predicate algebra (replace prose `inclusion`/`exclusion` tuples).
- Structured VRS `canonical_allele` (currently dropped) + structured phenopacket (currently JSON string).
- Make `subject` required (tightening phase).
- Bind `OntologyTerm`/`GeneOrProtein` identifiers to the connector/cross-domain-join machinery
  (the [[biomed ontology schema effort]]) — ontology-ID match as a cross-domain join key.
- A faithful v1.2-corpus re-ingest carrying subjects (now possible once the slot exists).
