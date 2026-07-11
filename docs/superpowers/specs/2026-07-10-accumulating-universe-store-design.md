# The accumulating universe store — one atom, many links

**Date:** 2026-07-10
**Status:** Design (approved for planning). First-pass, explicitly **provisional** —
"doesn't need to be permanent." Small-scale version of `scaled-infrastructure.md`'s
Pile B corpus/graph engine, built at the size this project actually needs today.

---

## 0. One-paragraph summary

As sessions, instances, and modalities accumulate, the claims universe needs one
organizing answer, and it has one: **ONE universe.** No per-session, per-subject, or
per-modality universes. The atom is the **content-addressed claim**; everything else —
session, subject, modality, status, pattern — is a **facet**, never a physical
partition. Picking any one of those as the storage partition makes the others
second-class, so none of them is: **one atom, many links.** The store is an
append-only, content-addressed JSONL claim log (grep-able, eyeball-inspectable,
throwaway-able) as source of truth, with DuckDB SQL over that log as the facet/census
query layer. Every run **loads** the persistent `Corpus` — all four collections,
including the `fdr_ledger` — **proposes**, **content-address-dedups** against what is
already registered, **registers only the genuinely new**, **licenses**, and
**persists back**; re-running the same panel must mint zero new claims, not 696.
Append-only-plus-monotone is residualism at the store level: what is monotone is the
audit trail, not the licensed set. This turns the accumulating universe into a
**stream**, which is exactly the substrate online e-LOND was built for, and it
resolves the batch-ordering pathology hit in the SPC scale-up as an artifact of
forcing a one-shot batch onto a streaming procedure rather than a permanent tax. The
current gap is that the code is ephemeral per run — a fresh `Corpus` exported to one
topology JSON blob — and closing that gap, in this minimal form, is the entire piece
of work this spec describes.

---

## 1. Foundations alignment

| Foundation | Requirement | How this design honors it |
|---|---|---|
| Corpus / purity invariants (`GLOSSARY.md`; `epistemology.md` §7) | `Corpus` = exactly 4 collections (claims, defeat_edges, equivalences, fdr_ledger); grammar/protocol pure + numpy-free. | The store persists the **whole** `Corpus`, all 4 collections, including the `fdr_ledger` — never a partial export. All persistence/dedup/facet logic is umbrella-side; grammar/protocol untouched. |
| de Bruijn kernel (`epistemology.md` §8) | Proposers are untrusted scaffolding; nothing earns standing except by passing the kernel. | Accumulation changes nothing about *how* a claim earns standing — `run_cycle`/`verify_stage` still license. The store only changes what corpus a run loads and proposes against; content-addressing is a dedup key, never a shortcut around the gate. |
| Residualism (`residualism.md` §7, "The Claims Engine") | "What is monotone is the audit trail, not the licensed set." Un-licensed ≠ false; residue is retained, never deleted. | Append-only JSONL is the audit trail; it only grows. The licensed *set* can still be revised (defeat, drift, reinstatement) without the log itself ever losing a record — the log is monotone even where standing is not. |
| e-value / online-FDR (`epistemology.md` §7) | e-LOND controls FDR under arbitrary dependence because it rides `E[e] ≤ 1` and discount weights summing to 1; it is inherently **online** — claims arrive over time, α is a wealth process, no final-size assumption. | An accumulating universe **is** the stream e-LOND was designed for: each new claim is judged at its live ledger position, discoveries fund future budget. The batch-ordering pathology (dumping all claims at once, alphabetically, starving the front of budget) is diagnosed here as a symptom of *forcing* a stream procedure into a one-shot batch, not a defect in e-LOND itself. |
| Measurement seam (`measurement-foundation.md` §3, §6.3) | A claim's parameterization is which measurement-space dimension its plan reads; meaningfulness is checked at that seam; morphospace's occupied/empty/forbidden trichotomy needs the axes to be real first. | Modality is promoted to a first-class facet precisely because it *is* the measurement space a claim is parameterized over — the seam this foundation names is the seam this store makes queryable. The coverage census (§5) is morphospace's occupied/empty/forbidden read directly off the store's facets. |
| Compute boundary (`compute-boundary.md`) | Polymer specifies/orchestrates/witnesses/certifies; provenance roots at ingestion, not at "a file the batch found." | The store does not add hosted compute — it is a local, gitignorable/throwaway-able log plus a local SQL layer over it. Multiple Claw instances/sessions append to the same local store; nothing here crosses into hosted storage or hosted compute. |
| Scaled infrastructure (`scaled-infrastructure.md` Pile B) | The corpus/graph engine is the trust-layer piece you own and run hard: a continuously-mutating, fully-versioned knowledge graph, content-addressed, append-only history. | This *is* that engine's small-scale ancestor: append-only JSONL + DuckDB stands in for the eventual multi-TB versioned graph store, at the scale this project actually needs today. Explicitly the seed, not the final architecture. |

---

## 2. Architecture

### 2.1 The atom and the "one atom, many links" through-line

The atom is the **claim**, identified by its content address. Every session,
instance, or modality that produces claims **appends** to one logical store; it does
not open a new universe, a new partition, or a new file per axis. Session, subject,
modality, and status are all queried as **facets** over that one append-only log —
never used to shard storage. This is also the clean answer to multiple concurrent
instances feeding the viewer: they all append to the one store, and the viewer
renders either the union or a faceted slice of it.

### 2.2 The store: JSONL log + DuckDB facet layer

- **Source of truth: an append-only, content-addressed JSONL claim log.**
  Grep-able and eyeball-inspectable by design; each line is one claim record, keyed
  by its content address, with modality carried on the record (see §4). Deliberately
  **throwaway-able** — this is a first-pass foundation, not a committed storage
  engine.
- **Query/facet/census layer: DuckDB SQL over the JSONL.** Satisfies "easy to search
  and inspect, and to audit its own organization" without owning a database server.
  DuckDB reads the JSONL directly; no separate ingest step duplicates the source of
  truth.
- **Alternatives weighed and set aside for v1:**
  - a directory of content-addressed files (git-friendly, dedups naturally, but
    produces a very large number of small files at any real scale);
  - an embedded SQLite/DuckDB table as the *source of truth* (best query ergonomics,
    worst grep-ability/eyeball-inspectability — loses the audit-trail legibility
    residualism asks for).

### 2.3 The persisted unit: the whole `Corpus`, including the `fdr_ledger`

The store persists the **entire** `Corpus` — all four collections (`claims`,
`defeat_edges`, `equivalences`, `fdr_ledger`) — never a subset and never a fresh
ledger. Today `populate_universe` starts a **fresh** `fdr_ledger` on every run; this
design replaces that with load → propose → dedup → register → license → persist-back,
so the ledger — and therefore the e-LOND wealth process — is itself an accumulating,
persisted object, not a per-run scratch structure.

### 2.4 The load → propose → dedup → register → license → persist-back cycle

1. **Load** the persistent `Corpus` (all 4 collections) and the JSONL log from disk.
2. **Propose** candidate claims from whatever source/session/modality is running
   (a batch runner, an agent session, a re-run of an existing panel).
3. **Content-address to dedup.** Compute each candidate's content address and check
   it against the log. Re-running the same panel — same code, same data, same
   parameterization — must **not** mint new claims; it must recognize the same atoms.
4. **Register only genuinely-new claims**, at the next live `fdr_ledger` positions
   (not a fresh ledger reset to position 0).
5. **License** via the existing gate (`run_cycle`/`verify_stage`) — unchanged;
   accumulation touches only what corpus is loaded and what is proposed against it,
   never how standing is earned.
6. **Persist back** the whole updated `Corpus` (including the advanced `fdr_ledger`)
   and append the newly-registered records to the JSONL log.

### 2.5 Append-only + monotone = residualism at the store level

The log only ever grows; nothing is deleted or overwritten. This mirrors, at the
storage layer, the discipline `residualism.md` already states for the licensed set:
"what is monotone is the audit trail, not the licensed set." A claim's *status* can
still move (PENDING → LICENSED, LICENSED → demoted by drift or defeat) — the store
does not freeze status — but the record of the claim having been proposed, tested,
and its full evidence/e-value/FDR history never disappears from the log. Demotion,
not erasure, holds at the storage layer exactly as it holds at the claim layer.

---

## 3. The FDR-stream insight

An accumulating universe **is** a stream — claims arrive over time, from different
sessions and modalities, at different moments — and that is exactly the substrate
online e-LOND was built for: each new test is judged at the current ledger position,
and early discoveries fund the budget for later ones (`epistemology.md` §7).

The batch-ordering pathology hit during the SPC scale-up (dumping 696 candidates at
once, in alphabetical order, with nothing funding the front of the queue → 0
licensed; resolved by strength-ordering the batch) is diagnosed here as an **artifact
of forcing a one-shot batch onto a streaming procedure**, not a defect in e-LOND and
not a permanent tax on this design. In a genuinely accumulating universe, that
pathology mostly dissolves on its own: claims are not required to arrive as one giant
sorted dump, so the front of the queue is not systematically starved by an arbitrary
within-batch ordering. Strength-ordering does not disappear as a concern — it becomes
a **seed-time concern**: ordering the *initial* bulk load of a new source into an
otherwise-empty or thin ledger, not a standing property of the store's steady-state
operation. (Batch-ordering finding: `[[project_polymer_spc_demo]]`.)

---

## 4. Facets

Facets are queried over the one log, never used to partition storage.

- **Provenance / session / agent** — which session/instance/agent proposed the
  claim.
- **Subject** — the biological subject the claim is about.
- **Status** — CONJECTURED / PENDING / LICENSED / REJECTED / STRUCTURAL, plus the
  e-value and FDR-ledger position that produced that status.
- **Pattern** — the registered claim pattern (e.g. `adjusted_effect@v1`).
- **Modality** — made **first-class** (see §4.1–4.3). Modality (idats→methylation
  vs. RNA-seq vs. an AlphaFold-plugin output, etc.) is the under-captured,
  highest-value facet, because it **is** the measurement space a claim is
  parameterized over — directly the seam `measurement-foundation.md` names, and the
  seam the re-parameterization evaluator (Spec 2, `2026-07-10-reparameterization-
  evaluator-design.md`) reads and revises.

### 4.1 Modality's two moments

Modality is not one fact; it has **two moments**, and keeping them apart is
load-bearing:

1. **The CHOICE** — a proposer/provenance act, **ontologically prior**. Nothing
   exists in the corpus until a proposer parameterizes it; the rational pole
   (the choice of which measurement space to read) frames the empirical pole
   (the readout itself).
2. **The REALIZED FACT** — pinned on the SE-Contract once the claim is
   materialized. This is the stable, auditable fact you query and census over.

**Design (agreed):** facet on the SE-Contract's **realized modality** — the stable,
auditable fact — and record the parameterization **CHOICE** in the claim's
**provenance**. The contract holds the *what*; provenance holds the *why-this-one*,
where the agency and its auditability actually live. This is also the ontological
ground for re-parameterization: re-parameterizing a rejected claim is a **new
provenance act** (an agent re-chooses the modality), linked to its parent by a
reinterpret edge — see Spec 2.

### 4.2 Ordinality nuances

Raw data (idats, RRBS reads, etc.) is prior even to provenance — the world exists
first. There are, in fact, **two provenances**, and separating them dissolves part of
the apparent tension between "provenance" and "modality" as facets:

- **Proposer-provenance** — which agent/session claimed this.
- **Data-provenance** — idats → minfi → β, carried on the contract.

Modality is **chosen** by proposer-provenance and **carried** by data-provenance —
so it is not really "provenance vs. modality" as two competing facets; modality is
downstream of one provenance kind and upstream of (pinned by) the other.

### 4.3 Data layer modality-partitioned, claim layer unified (Pile A / Pile B)

The **data layer is modality-partitioned** — different pipelines, adapters, and
SE-Contracts per modality (idats→β, RNA-seq, an AlphaFold API), matching
`scaled-infrastructure.md`'s Pile A (heterogeneous, orchestrated compute near
heterogeneous data). The **claim layer is unified** — one faceted log, matching Pile
B (the owned trust layer). This is read as a good sign the seam is natural: the place
where the data genuinely differs by modality (the pipeline) is exactly where it is
partitioned, and the place where it should not differ (the claim record) is exactly
where it is not.

---

## 5. Self-audit: the coverage census

A coverage census over **(subject-class × modality × status)** falls out of the
facet design for free — no new machinery, just a query over the store. **Empty
cells are the morphospace frontier** (`measurement-foundation.md` §6.3's
occupied/empty/forbidden trichotomy, read directly off the facets), and they reveal
**two distinct kinds of gap**:

- **Coverage gaps** — a subject has claims in one modality but zero in another (e.g.
  methylation claims exist for a subject, no RNA-seq claims do) — signals where to
  send an agent next.
- **IR gaps** — a facet you *want* to slice by but structurally cannot, because the
  claim IR does not capture it — signals a representation gap, not a data gap.

The design keeps this a **plain census/report** first and deliberately resists
materializing reflexive meta-claims (claims-about-the-census) until later — a
scope discipline, not an oversight.

---

## 6. Components to build

All umbrella-side; grammar/protocol untouched; `Corpus` stays exactly 4 collections.

1. **The append-only JSONL claim record schema** — one line per claim, content-
   addressed, with modality carried on the SE-Contract portion of the record and
   provenance (including the modality-choice act) carried on the provenance portion.
2. **`populate_universe` → append, not export.** Replace "fresh `Corpus`, one
   exported topology blob" with "load persistent `Corpus` + JSONL, propose,
   content-address-dedup, register only new, license, persist back."
3. **The DuckDB facet/query layer** over the JSONL — the census query (§5) and
   general faceted lookups (by session, subject, modality, status, pattern).
4. **Viewer wiring** — point the viewer at the store with facet filters, so it
   renders the union or a faceted slice, not a single run's export.

**Cheapest high-value first move:** define the JSONL claim record (modality on the
contract) → make `populate_universe` append to it instead of exporting a fresh blob
→ one census query → point the viewer at the store with facet filters.

---

## 7. Testing strategy

Behavior, not implementation.

- **Dedup on re-run.** Re-running the same source/panel against a populated store
  mints zero new claims; re-running against an empty store mints the expected count.
  This is the single highest-value regression test — it is the concrete form of "not
  696 new claims."
- **Whole-`Corpus` persistence.** A round-trip (persist → reload) preserves all 4
  collections, in particular the `fdr_ledger`'s live position — a load that silently
  resets the ledger to a fresh state is the regression this design exists to prevent.
- **Facet queries.** The coverage census over (subject-class × modality × status)
  correctly reports empty cells for a store constructed with a known coverage gap
  and a known IR gap (a facet intentionally absent from the record schema).
- **Modality's two moments.** A claim's realized modality (on the contract) and its
  parameterization choice (in provenance) are independently queryable and can be
  asserted to agree in the common case; a synthetic fixture where they would
  disagree (a re-parameterized claim) is reserved for Spec 2's tests, not this one.
- **Stream vs. batch FDR behavior.** A synthetic accumulation scenario (claims
  arriving in several small waves rather than one sorted dump) does not reproduce
  the batch-ordering pathology, contrasted with a fixture that forces a one-shot
  alphabetical batch and does reproduce it — pinning the diagnosis in §3 as a
  regression, not just a narrative claim.
- **Append-only / no erasure.** No operation in the runner ever removes a line from
  the JSONL log, including on claim demotion or defeat.

---

## 8. Open questions / deferred

- **Unified provenance object vs. two records.** Whether proposer-provenance and
  data-provenance should be one unified provenance object with internal links, or
  two distinct records the claim points at, is left open — the "one document vs.
  faceted" question recurring one level deeper. The likely answer is "one atom, many
  links" again, fractally, but this is not settled here.
- **Store format at scale.** JSONL + DuckDB is explicitly a first-pass, throwaway-
  able foundation, sized for what this project needs *now*. At the scale
  `scaled-infrastructure.md` describes (tens of millions of claims, incremental
  grounded-semantics propagation, multi-TB-RAM hot graph), this store is the seed
  that gets replaced, not extended in place — when and into what is explicitly
  deferred.
- **This is the small-scale version of scaled-infra's corpus/graph engine.** Stated
  once for the record: this design is provisional by intent, not by neglect — "it
  doesn't need to be permanent."

---

## See also

- `[[project_polymer_universe_organization]]` — the source memory this spec renders.
- `docs/superpowers/specs/2026-07-10-reparameterization-evaluator-design.md` — Spec
  2; shares the measurement-space registry and treats re-parameterization as a
  provenance operation over this store.
- `[[project_polymer_spc_demo]]` — the batch-ordering finding referenced in §3.
- `[[project_polymer_claims_knowledge_protocol]]`, `[[feedback_flag_engine_gaps]]`.
- `docs/superpowers/foundations/measurement-foundation.md` §3, §6.3 — the
  parameterization seam and the morphospace trichotomy.
- `docs/superpowers/foundations/scaled-infrastructure.md` — Pile A/B and the
  full-scale corpus/graph engine this design seeds.
