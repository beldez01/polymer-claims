# Capability Cell + Capability Registry — Design (V1)

**Status:** Design / spec. v1.3 — **implementation-ready**. (v1.1 integrated review rounds 1–2; v1.2 round 3; v1.3 round 4.)
**Date:** 2026-06-27
**Author:** Z. Belden (with Claude)
**Roadmap item:** `2026-06-23-remaining-roadmap.md` → *Vision-derived additions* → **V1**.
**Vision:** `docs/superpowers/vision.md` (capability cell; three registries; closed-world execution).

> **Scope honesty (carry verbatim into CONTINUE/roadmap):** *V1 introduces capability description,
> discovery, and conformance reporting. Closed-world enforcement remains deferred.* Unregistered claims
> still execute and license exactly as before; conformance is advisory (unwired into the gate). V1 is
> the highest-value **non-data-blocked parallel** build — it does **not** outrank the wedge
> (H1.A2 → H2), the critical path.

---

## 1. Problem

A "capability" such as `stats::mean_diff` is **not an object** today. It is scattered across an `_IMPL`
dispatch string on `OperationNode.impl`; a domain-specific claim builder (`mean_diff_claim` /
`region_delta_beta_claim` / `n_dmps_claim`); a module-level independent `AdapterRegistry` *of
credentials*; an `OracleRegistry`; an implicit agreement rule (the `abs_tol`/`rel_tol` globals in
`evaluate._check_agreement`); a typed output (`ProducedLeafSpec`); and version strings spread across
`schema_version`, `PatternRef.version`, data `@N`, and `AdapterCredential.version`. No registered,
versioned descriptor ties these together — the precondition for the vision's closed-world execution,
clean menu expansion, and capability-registry product surface.

## 2. Goal & non-goals

**Goal (V1):** a first-class, versioned **`CapabilityCell`** descriptor + a **`CapabilityRegistry`**;
the three existing reductions registered as the first three cells; a pure plan-construction helper the
existing builders route through *only where byte-identity is proven against frozen fixtures*; and a
**conformance** API (advisory, unwired).

**Non-goals (explicit — each is a real limitation, not an omission):**

- **Closed-world enforcement** — refusing non-conformant claims at the gate. Separate later slice.
- **Version-bound claims** — see §10. V1 produces versioned *descriptors*; a `Claim`/`EvaluationPlan`
  records only `operation_impl`, never `capability_id@version`. Mapping a claim back to the cell
  version that produced it needs an externally-supplied reference (the registry-level conformance entry
  point, §8) or a future additive claim field. **V1 does not create version-bound claims.**
- **Execution wiring** — the binding is **trust-only** (credentials + oracle metadata), *not* the
  executable adapters. Adapter instances are supplied separately at runtime
  (`NodeRunner.from_seed(..., adapters=…)`, `node.py:150`). See §9.
- **Multi-node capability DAGs** — V1 is **single-operation capabilities only** (`build_evaluation_plan`
  emits exactly one `OperationNode`; conformance requires exactly one). The three reductions are all
  single-node; general DAG capabilities are deferred.
- **Per-capability agreement tolerances** (§6), **resource limits / failure semantics / pinned
  environments / migrations**, **agent-path wiring**, **N>2 independent adapters** (§5.6), and
  **oracle domain/profile-class matching** (§5.5) — all deferred.

## 3. Architecture — the grammar/umbrella split

Mirrors the existing `impl`-string (grammar) ↔ adapter-object (umbrella) split, preserving the hard
invariant that **`grammar/` and `protocol/` remain pure/numpy-free**; the impure runtime boundary is the
umbrella **node/server**, and filesystem-backed resolution (contract/probe loading) stays umbrella-side.
(Much of the umbrella — e.g. `attestation.py`, the pure parts of the builders — is itself pure.)

```
grammar/src/polymer_grammar/capability.py        (NEW — pure, numpy-free)
  CapabilityCell, ParamCodec, SubjectRequirement, OracleRequirement, DataRefKind,
  CapabilityRegistry, ConformanceResult, ConformanceReason, ConformanceWarning,
  CapabilityParamError                                          (frozen _Model descriptors + types)
  build_evaluation_plan(cell, *, params, data_ref, criterion, oracle_ref=None) -> EvaluationPlan
  validate_claim_shape(claim, cell) -> ConformanceResult        (pure; NO registration reason)
  validate_claim_conformance(claim, registry, capability_id, capability_version)
                                              -> ConformanceResult  (registry wrapper; CAN report NOT_REGISTERED)

src/polymer_claims/capabilities.py               (NEW — umbrella)
  MEAN_DIFF_CELL, REGION_DELTA_BETA_CELL, N_DMPS_CELL,  CAPABILITY_CELLS: CapabilityRegistry
  CapabilityTrustBinding(adapter_registry, oracle_registry, trust_profile)   (TRUST metadata — not executable adapters)
  bind(capability_id, capability_version="v1") -> CapabilityTrustBinding   (typed CapabilityNotFound)
  validate_trust_binding(cell, adapter_registry, oracle_registry) -> ConformanceResult
```

The cell references adapters by **identity string** and the oracle by **id** — never adapter objects —
so the descriptor stays pure. The umbrella owns the concrete credential/oracle registries and the
umbrella-side builders.

## 4. Untouched (the byte-identical guarantee)

`verify_stage`, `evaluate.verify`, `_check_agreement`, `Status`, `Corpus`, and the protocol are
**unchanged**. Existing builders keep their **exact signatures**, and produce **byte-identical output
for conformant inputs** (proven against frozen fixtures, §11) when their body delegates *plan
construction* to `build_evaluation_plan`. A builder is re-expressed **all-or-nothing** (§11) — never a
per-argument dispatch between legacy and cell paths.

**Valid-domain compatibility (NOT wholly additive).** Routing a builder through the codecs is byte-
identical for normal inputs but **fails fast** on the *noncanonical* inputs the legacy builders used to
serialize silently — an empty `region_probes`/`probes` tuple (`",".join(())==""`, rejected by the `csv`
codec) and a nonfinite `alpha` (`"nan"`/`"inf"`, rejected by the `float` codec) now raise
`CapabilityParamError`. This is a deliberate, narrow API contraction; nothing in the current suite passes
such inputs, and the full umbrella suite is the guard. Tests assert this fail-fast behavior (§11).

## 5. The descriptor types (pure, `capability.py`)

All frozen `_Model` (`extra="forbid"`); collections are tuples.

### 5.1 `CapabilityCell`

| Field | Type | Note |
|---|---|---|
| `capability_id` | `str` | Registry identity, e.g. `"stats::mean_diff"`. Nonempty. |
| `capability_version` | `str` | The cell's own version, e.g. `"v1"`. Nonempty. Distinct from `operation_impl` and claim `schema_version`. |
| `operation_impl` | `str` | The `OperationNode.impl` dispatch key. **Set explicitly** (not derived from `capability_id`) so existing keys are preserved exactly. Nonempty. |
| `title` | `str` | Human label. |
| `pattern` | `PatternRef` | The `(id, version)` pattern claims carry. |
| `subject` | `SubjectRequirement` | Subject policy (§5.3). |
| `param_schema` | `tuple[ParamCodec, ...]` | Typed param contract (§5.2). Unique `name`s. |
| `produced` | `ProducedLeafSpec` | Typed terminal output, reused verbatim from grammar. |
| `allowed_comparators` | `tuple[Comparator, ...]` | Valid `SatisfactionCriterion.comparator`s. Nonempty, unique. (No tolerances — §6.) |
| `eligible_adapter_identities` | `tuple[str, ...]` | **Eligible** adapter identities (not "all must run"). Unique. |
| `min_executing_adapters` | `int = 2` | **V1: must equal 2** (§5.6). |
| `oracle` | `OracleRequirement` | Oracle policy (§5.4). |
| `data_ref_kind` | `DataRefKind` | How `DataHandle.ref` is validated (§5.5). |
| `claim_leaf_kinds` | `tuple[Literal["quantity","categorical","existence","proposition"], ...]` | Expected `Claim.leaves` kinds, in order. Nonempty. (All three cells: `("categorical",)`.) |
| `criterion_target` | `Literal["threshold","reference_leaf","either"]` | Which `SatisfactionCriterion` target shape is valid. (All three cells: `"threshold"`.) |

**Descriptor invariants (model validators, #13):** nonempty `capability_id`/`capability_version`/
`operation_impl`; unique `param_schema` names; nonempty unique `allowed_comparators`; unique
`eligible_adapter_identities`; `min_executing_adapters == 2` (V1); `min_executing_adapters <=
len(eligible_adapter_identities)`; `enum` codecs require nonempty unique `choices`; non-`enum` codecs
forbid `choices`; nonempty `claim_leaf_kinds`; nonempty `title`; nonempty `eligible_adapter_identities`
entries; nonempty `ParamCodec.name`; `SubjectRequirement` self-consistency (forbidden ⇒ `kind is None`).

**Independence is NOT list membership.** `eligible_adapter_identities` only names *which* adapters may
serve the capability; whether an executing pair is genuinely independent stays decided by the protocol
trust registry (`adapters_independent`: trusted ∧ different owner ∧ different `implementation_hash`).

### 5.2 `ParamCodec` — canonical-acceptance validation (#4, resolves the v1.0 contradiction)

Operation params serialize to `tuple[tuple[str, str], ...]` — every value is already a string. A
codec defines BOTH a canonical string form and validation:

| Field | Type | Note |
|---|---|---|
| `name` | `str` | Param key. |
| `codec` | `Literal["string","int","float","csv","enum"]` | |
| `required` | `bool` | |
| `choices` | `tuple[str, ...] \| None` | Required iff `codec=="enum"`; else forbidden. |

**Validation rule = canonical acceptance:** a value `v` is valid iff **`canonicalize(v) == v`** (it is
*already* in canonical form). The helper never rewrites the value, so byte-identity is automatic for any
field that is already canonical; a legacy field that is *not* canonical is declared a `string` codec
(opaque pass-through) so its exact bytes survive.

`canonicalize` per codec:
- `string` — identity (always canonical).
- `int` — must parse as a base-10 `int` with no leading zeros / `+` sign; canonical = `str(int(v))`.
  (`"01"`, `"+1"` → not canonical → invalid under an `int` codec.)
- `float` — must parse as a **finite** float; canonical = `repr(float(v))`. **Non-finite rejected**
  (`"nan"`, `"inf"`). `"5e-2"` is not canonical (`repr(0.05)=="0.05"`) → invalid under a `float` codec.
- `csv` — comma-joined, no surrounding spaces, no empty tokens; canonical = the cleaned join.
  (`"a, b"` → not canonical → invalid under a `csv` codec.)
- `enum` — must be in `choices` (each choice is its own canonical form).

> **Per-param byte-identity check (implementation step):** for each existing param, confirm the
> builder's emitted string is already canonical for its intended codec (e.g. `str(0.05)=="0.05"` is
> canonical for `float`; `",".join(probes)` is canonical for `csv`). If any is not, that param is
> declared a `string` codec for V1. The frozen golden fixtures (§11) are the gate that decides this
> per param.

### 5.3 `SubjectRequirement` (#6)

```python
class SubjectRequirement(_Model):
    mode: Literal["forbidden", "optional", "required"]
    kind: SubjectKind | None = None   # None = any kind; SubjectKind = Literal of the 10 discriminators
    # validators: mode=="forbidden" => kind is None; kind (when set) is a real discriminator; no "" 
```

`SubjectKind = Literal["genomic_region","ontology_term","variant_vrs","s4_object","gene_or_protein",
"phenopacket","pathway","cohort","literal","composite"]` — the grammar's `Subject.kind` discriminators
(`subject.py`), not Python class names.

Uses the **serialized discriminator** (`Subject.kind`: `"genomic_region"`, `"ontology_term"`, …), not
the Python class name. Conformance: `forbidden` ⇒ claim must have no subject; `optional` ⇒ subject may
be absent, and if present its `kind` must match `kind` (when set); `required` ⇒ subject present and
`kind`-matching (when set). Cells: mean_diff = `forbidden`; region_delta_beta = **`required`**, `kind="genomic_region"` — the
apparatus domain requires it (`methyl_adapters.py:143`); the builder's `with_subject=False` path exists
only to probe the out-of-domain precondition, so its golden fixture stays byte-identical but
**deliberately fails conformance** with `SUBJECT_REQUIRED_MISSING`. n_dmps = `required`,
`kind="genomic_region"`.

### 5.4 `OracleRequirement`

```python
class OracleRequirement(_Model):
    default_oracle_id: str | None = None
    required: bool = False
```

Minimal: builders accept alternate/unknown oracle refs, so the cell expresses *default + required*, not
a mandatory id. Domain/profile-class matching deferred (the `OracleRegistry`'s `ApplicabilityDomain`
governs domain at gate time).

### 5.5 `DataRefKind` (#5)

```python
class DataRefKind(str, Enum):
    OPAQUE = "opaque"            # any nonempty string (e.g. "dose_response"); no structure asserted
    SE_CONTRACT = "se_contract"  # anchored:  ^se:[^:@\s]+@[0-9]+$   (name: no colon/at/whitespace; version: digits)
```

`validate_claim_shape` checks the claim's `DataHandle.ref` against this matcher. Cells: mean_diff =
`OPAQUE`; region_delta_beta and n_dmps = `SE_CONTRACT`. `uri`/`drs` are future additions.

### 5.6 Adapter cardinality (#7)

`min_executing_adapters` is fixed at **2** in V1 (validator-enforced). The protocol predicate finds one
trusted independent *pair*; an arbitrary independent subset of size N>2 is undefined there. N>2 (with a
defined pairwise-independent-subset algorithm) is deferred.

### 5.7 `CapabilityRegistry`

```python
class CapabilityRegistry(_Model):
    cells: tuple[CapabilityCell, ...] = ()
    def resolve(self, capability_id: str, capability_version: str) -> CapabilityCell | None
    @property
    def is_empty(self) -> bool
    # validator: (capability_id, capability_version) pairs unique
```

## 6. Agreement tolerances — omitted (no duplicate truth)

`verify` uses module-global `_ABS_TOL`/`_REL_TOL`. Per-cell tolerances `verify` does not read would be a
second, silently-drifting source of truth for a verification-affecting value. V1 **omits** tolerances;
the cell keeps `allowed_comparators` (a declared constraint genuinely checkable against
`criterion.comparator`). Per-capability tolerances become real only if `verify` is changed to read them.

## 7. Plan construction — `build_evaluation_plan` (pure)

```python
def build_evaluation_plan(
    cell, *, params: dict[str, str], data_ref: str,
    criterion: SatisfactionCriterion, oracle_ref: str | None = None,
) -> EvaluationPlan
```

- `params` are **already-resolved canonical strings** (the caller did any IO, e.g. probe resolution).
- Validates: every required param present, no unknown keys, each value passes its codec by **canonical
  acceptance** (§5.2); `criterion.comparator ∈ allowed_comparators`; `data_ref` matches
  `cell.data_ref_kind`. Violations → raise `CapabilityParamError` (fail-fast; misuse is a programming
  error).
- Oracle: `oracle_ref` if given else `cell.oracle.default_oracle_id`; if `cell.oracle.required` and the
  result is `None` → `CapabilityParamError`.
- **Strings are preserved, not rewritten** (canonical by precondition) and emitted **ordered per
  `param_schema`**.
- Builds a **single** `OperationNode(id="n0", impl=cell.operation_impl,
  inputs=(DataHandle(ref=data_ref),), params=<schema-ordered>, produces=cell.produced,
  oracle_ref=<resolved>)` → `ComputeGraph(nodes=(node,), terminal="n0")` → `EvaluationPlan(graph,
  criterion)`.

**Not a claim builder.** Domain builders keep all claim-level + IO concerns: `n_dmps_claim` resolves
probes via `_all_probe_ids` (filesystem IO) then passes the csv-string; `region_delta_beta_claim`
constructs its `GenomicRegion` (and supports a deliberately absent subject); `mean_diff_claim`
constructs its provenance. Each wraps the returned plan.

## 8. Conformance — separated checks (#3, #7)

Declared capacity vs observed execution are kept distinct.

1. **`validate_claim_shape(claim, cell) -> ConformanceResult`** (pure). The caller supplies the cell, so
   this **cannot and does not** report registration. Checks everything the cell declares:
   **graph shape** — exactly one `OperationNode`, `graph.terminal` equal to its id (`"n0"`), exactly one
   input that is a `DataHandle` (no `NodeRef`) (`GRAPH_SHAPE_MISMATCH` otherwise); `operation_impl`;
   `pattern`; `produced`; **params** — required present, none unknown, **no duplicate keys**
   (`PARAM_DUPLICATE`; params are iterated as the raw `tuple`, never `dict()`-collapsed), each
   codec-canonical (`PARAM_MALFORMED`); **`claim_leaf_kinds`** match `Claim.leaves` in count + kind
   (`LEAF_SHAPE_MISMATCH`); **`criterion_target`** — the criterion uses the declared target shape
   (`threshold` vs `reference_leaf_index`) (`CRITERION_TARGET_MISMATCH`); `comparator ∈
   allowed_comparators`; subject policy; `data_ref_kind`; oracle policy (`required` ⇒ `oracle_ref`
   present).
2. **`validate_claim_conformance(claim, registry, capability_id, capability_version)`** (pure registry
   wrapper). Resolves the cell → `CAPABILITY_NOT_REGISTERED` if absent, else delegates to
   `validate_claim_shape`. **The capability ref is supplied externally** because the claim does not
   carry one (the §10 limitation). This is the *only* entry point that can return
   `CAPABILITY_NOT_REGISTERED`.
3. **`validate_trust_binding(cell, adapter_registry, oracle_registry) -> ConformanceResult`** (umbrella).
   Passes iff a **trusted, mutually-independent pair** exists among `eligible_adapter_identities` that
   are present+credentialed (via `adapters_independent`). Eligible identities that are missing from the
   registry or untrusted are **warnings (diagnostics), not failures** (#8) — a capability with one
   bad-plus-two-good eligible adapters still binds. Oracle rule (#9): if `oracle.required` and
   `default_oracle_id` is set, the default **must resolve** in `oracle_registry` (else
   `BINDING_ORACLE_MISSING`, fatal); if `required` **without** a default, static satisfiability is
   **unknown** (warning, not fatal); if not required, ok.
4. **Runtime adapter verification** — the **existing** gate, unchanged: where the adapters that
   *actually executed* are checked. The claim never carries adapter identities (they appear only in
   `EvaluationResult`), which is exactly why 1–3 cannot be collapsed.

```python
class ConformanceResult(_Model):
    reasons: tuple[ConformanceReason, ...] = ()   # FATAL
    warnings: tuple[ConformanceWarning, ...] = ()
    detail: str = ""
    @computed_field      # serialized (machine-readable) yet DERIVED — never separately stored
    @property
    def ok(self) -> bool:
        return not self.reasons
```

`ConformanceReason` (fatal): `CAPABILITY_NOT_REGISTERED` (wrapper only), `OPERATION_IMPL_MISMATCH`,
`PATTERN_MISMATCH`, `GRAPH_SHAPE_MISMATCH`, `PARAM_MISSING`, `PARAM_UNKNOWN`, `PARAM_DUPLICATE`,
`PARAM_MALFORMED`, `OUTPUT_TYPE_MISMATCH`, `LEAF_SHAPE_MISMATCH`, `COMPARATOR_NOT_ALLOWED`,
`CRITERION_TARGET_MISMATCH`, `SUBJECT_FORBIDDEN_PRESENT`, `SUBJECT_REQUIRED_MISSING`,
`SUBJECT_KIND_MISMATCH`, `DATA_REF_KIND_MISMATCH`, `ORACLE_REQUIRED_MISSING`, `BINDING_NO_INDEPENDENT_PAIR`,
`BINDING_ORACLE_MISSING`.
`ConformanceWarning`: `BINDING_ADAPTER_UNTRUSTED`, `BINDING_ADAPTER_MISSING`,
`BINDING_ORACLE_SATISFIABILITY_UNKNOWN`.

## 9. Umbrella binding & registry (`capabilities.py`)

- `MEAN_DIFF_CELL`, `REGION_DELTA_BETA_CELL`, `N_DMPS_CELL` instantiated with real `operation_impl`,
  param codecs, subject/oracle/data-ref policy, eligible identities, `produced`. → `CAPABILITY_CELLS`.
- **`CapabilityTrustBinding`** (renamed from `CapabilityBinding`, #1) `= {adapter_registry:
  AdapterRegistry, oracle_registry: OracleRegistry, trust_profile: str}` — **trust + oracle metadata
  only, NOT executable adapters.** The `trust_profile` label makes the operator-selected trust policy
  **visible and honest** (it is a default bundled binding, not a per-dataset guarantee);
  `trust_profile` must be nonempty. Executable adapter instances remain supplied separately at runtime
  (`node.py:150`); wiring them through a capability is a later (execution) slice.
- **Per-cell oracle registries (correctness — the registries are NOT interchangeable):**
  - **mean_diff** → `apparatus_oracle_registry()` (the `dose_response_apparatus` dossier, BENCHMARKED);
    `trust_profile = "bundled-dose-response-apparatus"`.
  - **region_delta_beta / n_dmps** → `profile_oracle_registry((CANONICAL_EPICV2_V1, substrate))`
    (`analysis_profile.py:134`), **not** `apparatus_oracle_registry()` (which lacks the profile oracle).
    The **substrate** sets the validation tier (`recomputable_public`→BENCHMARKED, etc.).
    `trust_profile = "bundled-recomputable-public"`.
  - **Honesty caveat (must be in the spec + binding):** the tier in a bundled binding applies to the
    **bundled fixture substrate only** — it is *not* a claim that every dataset run through the
    capability earns that tier. A different dataset requires re-binding with its own
    `(profile, substrate)`; the conservative fallback is an `unvalidated` substrate binding.
- `bind(capability_id, capability_version="v1") -> CapabilityTrustBinding`: lookup by
  `(capability_id, capability_version)`; unknown → typed `CapabilityNotFound` (never `KeyError`). V1:
  exactly one binding per `(id, version)`; multiple versions of one `capability_id` may coexist and all
  remain resolvable (no implicit "latest"); deprecation + runtime/environment identity are noted future
  seams, not built.

## 10. Limitation — versioned descriptors, not version-bound claims (#2)

A `Claim`/`EvaluationPlan`/`OperationNode` records only `operation_impl`, never `capability_id@version`.
Therefore: two cell versions can share an `operation_impl`; one claim may conform to multiple versions;
the system cannot determine which version generated a claim; and a future closed-world gate cannot
resolve the intended cell from the claim alone. This is acceptable for an advisory catalog and is why
`validate_claim_conformance` takes the capability ref externally. **Deferred requirement:** a
claim-to-capability binding — an additive `EvaluationPlan`/`Claim` field (e.g. `capability_ref:
str|None`) or a content-addressed association — tracked for the enforcement slice.

## 11. Testing — frozen baselines, per-builder, all-or-nothing (#10, #11, #12)

- **Frozen pre-refactor golden fixtures (#10).** *Before* touching any builder, capture each builder's
  per-variant canonical `model_dump_json()` **and** `ComputeGraph` content-hash into committed fixture
  files. Re-expressed builders are tested against these **frozen** fixtures — never against the helper
  they now call (which would prove nothing).
- **Per-builder variant matrices (#12)** — only applicable variants:
  - **mean_diff:** default; custom comparator+threshold; alternate oracle; rationale/provenance present;
    custom title/ontology/strength. *(no subject — forbidden.)*
  - **region_delta_beta:** default; custom comparator+threshold; alternate oracle; **missing subject**;
    custom region; custom title/ontology/strength.
  - **n_dmps:** default **incl. default probe resolution (IO path)**; **explicit probe subset**; custom
    comparator+threshold (`k`); alternate oracle; custom region; strength. *(no ontology customization.)*
- **All-or-nothing re-expression (#11).** Every applicable variant of a builder matches its frozen
  fixtures, or that **entire builder stays unchanged** in V1. No argument-based dispatch between a legacy
  and a cell path inside a builder. Per-builder matrices include each builder's legacy comparators
  **incl. `EQ` and `NE`**, so a comparator-specific regression can't escape the byte-identity guard.
- **Valid-domain fail-fast (#1, §4).** `build_evaluation_plan` rejects an empty `csv` param (`""`) and a
  nonfinite `float` param (`"nan"`/`"inf"`) with `CapabilityParamError` — the narrow, documented behavior
  change vs. the legacy builders, asserted directly.
- **Descriptor invariant tests (#13)** — each validator in §5.1 (nonempty ids/title/identity-entries/
  `ParamCodec.name`; unique params/comparators/identities; `min==2`; `min<=len(eligible)`; enum⇒choices;
  non-enum⇒no choices); `SubjectRequirement` (forbidden+non-None `kind` rejected; unknown discriminator
  rejected; empty `kind` rejected); registry duplicate `(id, version)`.
- **Conformance tests** — positive (each cell's built claim passes `validate_claim_shape`); negative per
  fatal reason: unknown/extra/**duplicate** (`(("alpha","0.05"),("alpha","0.01"))` → `PARAM_DUPLICATE`)/
  malformed param (`"01"`/`"5e-2"`/`"nan"`/`"a, b"` → `PARAM_MALFORMED`); **missing region subject** —
  the `with_subject=False` claim is byte-identical to its fixture **and** fails with
  `SUBJECT_REQUIRED_MISSING`; **wrong leaf count/kind** (`LEAF_SHAPE_MISMATCH`); **reference-leaf
  criterion** rejected (`CRITERION_TARGET_MISMATCH`); wrong pattern/output/subject-kind/comparator;
  single-node / terminal / input-shape violations (`GRAPH_SHAPE_MISMATCH`); **malformed SE-contract refs**
  — extra `@`, whitespace, missing name, non-digit version (`DATA_REF_KIND_MISMATCH`).
  `validate_claim_conformance` returns `CAPABILITY_NOT_REGISTERED` for an unknown `(id, version)`.
- **Binding tests** — trusted independent pair → ok; an extra untrusted/missing eligible identity →
  `ok` with the corresponding **warning** (not a failure); no independent pair → `BINDING_NO_INDEPENDENT_PAIR`;
  oracle required+default-present → ok; required+default-absent-in-registry → `BINDING_ORACLE_MISSING`;
  required+no-default → ok with `BINDING_ORACLE_SATISFIABILITY_UNKNOWN`; **per-cell oracle registry** —
  a methyl cell bound to `apparatus_oracle_registry()` (lacks the profile oracle) → `BINDING_ORACLE_MISSING`,
  and to its `profile_oracle_registry((CANONICAL_EPICV2_V1, substrate))` → ok; each binding carries a
  non-empty `trust_profile` label.
- **`bind` tests** — resolves each cell; unknown `(id, version)` → `CapabilityNotFound`.
- **Purity** — `capability.py` imports nothing umbrella/numpy (grammar isolation guard + numpy-free
  assertion); the pure functions run with no IO/clock/random.

## 12. File-by-file change list

- **NEW** `grammar/src/polymer_grammar/capability.py` — descriptors + `build_evaluation_plan` +
  `validate_claim_shape` + `validate_claim_conformance` + result/error types. Pure.
- **EDIT** `grammar/src/polymer_grammar/__init__.py` — export public names.
- **NEW** `src/polymer_claims/capabilities.py` — the three cells, `CAPABILITY_CELLS`,
  `CapabilityTrustBinding`, `bind`, `validate_trust_binding`, `CapabilityNotFound`.
- **EDIT** `src/polymer_claims/{exec_adapters,methyl_adapters,methyl_ndmp}.py` — builders delegate plan
  construction to `build_evaluation_plan` **only if the whole builder's frozen-fixture matrix passes**;
  signatures unchanged.
- **NEW fixtures** under `tests/` (frozen golden JSON + hashes, committed before refactor).
- **NEW tests** under `grammar/tests/` (pure descriptors + helpers + conformance) and `tests/` (binding,
  byte-identity matrix).
- *(Deferred from V1 core)* a read-only `polymer-claims capabilities` CLI listing the registry — nice
  product surface, but dropped from the minimal slice; pull in as a fast follow.

## 13. Acceptance criteria

1. `CapabilityCell`/`ParamCodec`/`SubjectRequirement`/`OracleRequirement`/`DataRefKind`/
   `CapabilityRegistry` exist, pure, numpy-free, exported, with all §5.1 validators.
2. The three reductions are registered cells; `bind` resolves each to its correctly scoped,
   nonempty-labeled trust binding (mean difference → apparatus registry; methylation cells → profile
   oracle registry); unknown → `CapabilityNotFound`.
3. Frozen golden fixtures are captured **before** refactor; every re-expressed builder matches them for
   **all** its applicable variants, or the builder is left unchanged (and that is recorded).
4. `validate_claim_shape` checks every declared field and never returns `CAPABILITY_NOT_REGISTERED`;
   `validate_claim_conformance` is the only source of that reason; `validate_trust_binding` separates
   fatal reasons from warnings per §8. None of the three raise.
5. The full negative/binding/invariant test list passes.
6. `verify`/gate/`Status`/`Corpus`/protocol unchanged; `export-*` and all existing suites byte-identical
   for conformant inputs (valid-domain compatibility — noncanonical empty-csv / nonfinite-float params
   now fail fast, a documented narrow behavior change — tested in §11).
7. `check-all.sh` green; ruff clean.
8. The §2 limitations (no enforcement, no version-bound claims, trust-only binding, single-node only)
   are stated in the spec and echoed in CONTINUE/roadmap.

## 14. Resolved decisions (formerly open questions)

- **Numeric canonical forms — RESOLVED: keep canonical acceptance.** `"01"`/`"5e-2"`/`"nan"` are
  rejected under int/float codecs; any non-canonical legacy field is declared a `string` codec. Chosen
  over parse-only acceptance because it is deterministic and already has a safe string fallback.
- **`capabilities` CLI — RESOLVED: deferred from V1 core.** V1 has enough surface; add the CLI once the
  descriptor + conformance behavior have stabilized.
