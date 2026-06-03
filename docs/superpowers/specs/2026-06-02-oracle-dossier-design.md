# Oracle Dossier — Protocol Runtime Sub-project #2

> Design spec. Status: **approved** (brainstorm 2026-06-02). Second sub-project of the
> protocol runtime. Implements unified-spec §5 #2 / daemon D2's *grammar object + VERIFY
> enforcement*: every oracle that grounds a claim carries a credibility dossier, and a
> claim's **empirical strength is capped by its weakest oracle's validation tier**. Binds
> the `OperationNode.oracle_ref` slot Phase 8 left unbound. Spans a new grammar module
> (`oracle.py`) + a thin protocol enforcement (`oracle.py` + `verify_stage`).

## 0. Context — where this sits

The v1.3 grammar is complete (8 layer-phases). The protocol runtime is decomposed into 5
sub-projects; **#1 (Corpus + the assessment spine) is merged** (`run_cycle` over a frozen
`Corpus` through seven pure stages; EXECUTE reuses the air-gapped `verify()`). This is **#2**:
the oracle credibility-qualification object (D2). It makes "execution sets the posterior"
conditional on a *validated* execution backend — without it, a claim grounded by an
unvalidated or misapplied oracle can carry full strength, which the spec forecloses ("no
unvalidated oracle certifying truth"). Deep design source: the keystone protocol doc's D2
section + unified spec §4/§5 #2.

## 1. Success criterion

A claim's `evaluation_plan` references zero or more oracles via `OperationNode.oracle_ref`.
Given a registry of `OracleDossier`s (passed into `run_cycle` like `adapters`/`ctx`, **not**
persisted in the `Corpus`), when a claim earns LICENSED in `verify_stage`, its **empirical
strength axes are capped by the ceiling of the weakest oracle it depends on**. An oracle that
is unresolved (no dossier) **or** used outside its qualified applicability domain counts as
effective `UNVALIDATED` (empirical ceiling 0.0). The cap is a pure `meet` with a tier ceiling;
there is **no new status, no new `PendingReason`, no binary license gate** — the tier does all
its work through strength, which is the grammar's universal currency.

- **Sensitivity:** the dossier represents validation tier + bounded applicability domain +
  propagated uncertainty (representable), and the cap genuinely bites (a weak/misapplied
  oracle yields zero empirical strength → the claim is epistemically inert: it loses every
  defeat contest and dominates nothing).
- **Specificity:** oracle-validation and claim-*novelty* are orthogonal — a **novel** claim on
  a **validated** oracle licenses at full strength. The gate never tests for literature
  precedent. Pure-builtin claims (no `oracle_ref`) are wholly unaffected (every existing spine
  test passes unchanged).

## 2. Design principles

- **The tier is about the *apparatus*, not the *claim*.** `ValidationTier` measures how the
  oracle (API endpoint / R routine / assay) was validated against an external anchor — never
  whether the claim's content agrees with the literature. Concordance-with-literature is a
  *strength signal* (it lifts `world_contact`/`evidence_against_null`), handled on the strength
  vector elsewhere, **not** a license precondition here.
- **Cap, don't bar.** The whole mechanism is one pure function: tier → empirical-axis ceiling,
  applied via `StrengthVector.meet`. Unvalidated/out-of-domain → ceiling 0.0 → LICENSED label
  but zero empirical weight. No hidden scalar, no status gate — consistent with the Pareto
  strength philosophy.
- **Empirical axes only.** The ceiling bounds `magnitude`, `uncertainty`,
  `evidence_against_null`, `world_contact` (what the *data* can support). It leaves `severity`
  and `explanatory_virtue` at 1.0 (test-design / theory quality, set by argument, not
  apparatus).
- **Weakest oracle wins.** A claim grounded by several oracles is only as strong as its
  weakest one (a chain's empirical reliability is bounded by its least-validated link).
- **Grammar = mechanism, protocol = policy** (mirrors `governance`/`safety_gate`). Grammar
  `oracle.py` ships the IR + pure helpers; protocol `oracle.py` ships the registry + the policy
  (unresolved → `UNVALIDATED`; out-of-domain → `UNVALIDATED`; cap at the LICENSED seam).
- **One-way isolation preserved**; `Corpus` stays at exactly four collections (the registry is
  passed-in environment config, like `adapters`).
- TDD; grammar tests `cd grammar && uv run pytest -q`, protocol tests `cd protocol && uv run
  pytest -q`; `uv run ruff check src tests` in both.

## 3. Package & layout

```
polymer-claims/
  grammar/src/polymer_grammar/
    oracle.py                 # NEW — ValidationTier, ApplicabilityDomain, OracleDossier + pure helpers
    __init__.py               # MODIFY — export the oracle surface
  grammar/tests/
    test_oracle.py            # NEW
  protocol/src/polymer_protocol/
    oracle.py                 # NEW — OracleRegistry + oracle_cap policy
    verify.py                 # MODIFY — verify_stage gains `oracles`; caps strength on LICENSED
    cycle.py                  # MODIFY — run_cycle gains `oracles`, threads it to verify_stage
    __init__.py               # MODIFY — export OracleRegistry/oracle_cap + re-export grammar oracle types
  protocol/tests/
    test_oracle.py            # NEW
    test_verify.py            # MODIFY — cap-on-LICENSED cases
    test_cycle.py             # MODIFY — run_cycle-with-registry case
```

**No change to any existing grammar field.** `OperationNode.oracle_ref` already exists (Phase
8). `claim.py`, `status.py`, `operations.py` are untouched. The grammar delta is a single new
additive module + its exports.

## 4. The dossier IR (`grammar/oracle.py`)

```python
class ValidationTier(str, Enum):
    UNVALIDATED = "unvalidated"            # no dossier / unresolved / out-of-domain
    INDIRECT = "indirect"                  # checked against literature-reported / heuristic values
    BENCHMARKED = "benchmarked"            # against a computational ground-truth set
    ANCHORED = "anchored"                  # against a direct wet-lab/clinical anchor, bounded domain
    GOLD = "gold"                          # gold-standard, broadly validated

# str-Enum (JSON-faithful, grammar convention) -> explicit rank for ordering, mirroring
# revision._STATUS_TIER.
_TIER_RANK = {ValidationTier.UNVALIDATED: 0, ValidationTier.INDIRECT: 1,
              ValidationTier.BENCHMARKED: 2, ValidationTier.ANCHORED: 3, ValidationTier.GOLD: 4}

# Empirical (apparatus-bounded) strength axes the ceiling caps. severity + explanatory_virtue
# are theory/test-design axes -> never capped by the oracle.
_EMPIRICAL_AXES = ("magnitude", "uncertainty", "evidence_against_null", "world_contact")

# v1 ceiling ladder on the empirical axes (monotone; endpoints pinned at 0.0 and 1.0; tunable).
_TIER_CEILING = {ValidationTier.UNVALIDATED: 0.0, ValidationTier.INDIRECT: 0.4,
                 ValidationTier.BENCHMARKED: 0.6, ValidationTier.ANCHORED: 0.85,
                 ValidationTier.GOLD: 1.0}


class ApplicabilityDomain(_Model):
    subject_kinds: tuple[str, ...] = ()    # Subject discriminator kinds qualified for; () = unbounded
    predicates: tuple[str, ...] = ()       # prose qualifications for human audit (NOT machine-checked)


class OracleDossier(_Model):
    oracle_id: str = Field(min_length=1)   # matches OperationNode.oracle_ref
    validation_tier: ValidationTier
    applicability_domain: ApplicabilityDomain = ApplicabilityDomain()
    anchor: str | None = None              # what external anchor it was validated against (prose)
    relative_uncertainty: float | None = Field(default=None, ge=0.0)  # representable; propagation deferred
```

## 5. Pure helpers (`grammar/oracle.py`)

```python
def tier_ceiling(tier: ValidationTier) -> StrengthVector:
    """The per-axis strength ceiling a tier imposes: the empirical axes carry the tier's
    ceiling value; the theory axes (severity, explanatory_virtue) stay at 1.0 (uncapped)."""
    c = _TIER_CEILING[tier]
    return StrengthVector(**{ax: (c if ax in _EMPIRICAL_AXES else 1.0) for ax in AXES})


def cap_strength(strength: StrengthVector | None, tier: ValidationTier) -> StrengthVector | None:
    """`strength` meet the tier ceiling (componentwise min) — caps only the empirical axes
    (theory-axis ceilings are 1.0). None in -> None out (nothing to cap)."""
    if strength is None:
        return None
    return strength.meet(tier_ceiling(tier))


def in_domain(domain: ApplicabilityDomain, subject: Subject | None) -> bool:
    """Is `subject` within the oracle's qualified domain? Unbounded domain (no subject_kinds)
    -> always True. A bounded domain qualifies only its listed Subject kinds; a claim with no
    subject can't be confirmed in a bounded domain -> False (conservative)."""
    if not domain.subject_kinds:
        return True
    if subject is None:
        return False
    return subject.kind in domain.subject_kinds


def referenced_oracle_ids(plan: EvaluationPlan) -> frozenset[str]:
    """The set of oracle_refs the plan's operation nodes name (None refs excluded)."""
    return frozenset(n.oracle_ref for n in plan.graph.nodes if n.oracle_ref is not None)


def weakest_tier(tiers: Iterable[ValidationTier]) -> ValidationTier:
    """The lowest-rank tier (a chain is only as strong as its weakest oracle). Empty ->
    GOLD: the no-constraint identity (GOLD's ceiling is all-1.0, so capping by it is a no-op),
    so callers that pass no tiers get no cap."""
    ts = list(tiers)
    if not ts:
        return ValidationTier.GOLD
    return min(ts, key=lambda t: _TIER_RANK[t])
```

Exports added to `grammar/__init__.py`: `ValidationTier`, `ApplicabilityDomain`,
`OracleDossier`, `tier_ceiling`, `cap_strength`, `in_domain`, `referenced_oracle_ids`,
`weakest_tier`.

## 6. The protocol policy (`protocol/oracle.py` + `verify_stage`)

```python
class OracleRegistry(_Model):
    """Execution-environment knowledge of oracle validation — passed into run_cycle like
    adapters, NEVER persisted in the Corpus."""
    dossiers: tuple[OracleDossier, ...] = ()

    @model_validator(mode="after")
    def _unique_ids(self) -> "OracleRegistry":
        ids = [d.oracle_id for d in self.dossiers]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"OracleRegistry oracle_ids must be unique; duplicates: {dupes}")
        return self

    def resolve(self, oracle_id: str) -> OracleDossier | None:
        return {d.oracle_id: d for d in self.dossiers}.get(oracle_id)


def _effective_tier(registry: OracleRegistry, oracle_id: str, subject) -> ValidationTier:
    """Resolution POLICY: an unresolved ref OR an oracle used outside its qualified domain
    counts as UNVALIDATED (its validation doesn't apply to this claim)."""
    d = registry.resolve(oracle_id)
    if d is None:
        return ValidationTier.UNVALIDATED
    if not in_domain(d.applicability_domain, subject):
        return ValidationTier.UNVALIDATED
    return d.validation_tier


def oracle_cap(claim: Claim, registry: OracleRegistry) -> StrengthVector | None:
    """The strength to write for `claim` after its weakest oracle's ceiling. Returns the
    (possibly unchanged) strength; None when there is no strength to cap. Pure-builtin claims
    (no oracle_ref) and claims with no plan get their strength back unchanged."""
    if claim.strength is None:
        return None
    if claim.evaluation_plan is None:
        return claim.strength
    refs = referenced_oracle_ids(claim.evaluation_plan)
    if not refs:
        return claim.strength
    tiers = [_effective_tier(registry, r, claim.subject) for r in refs]
    return cap_strength(claim.strength, weakest_tier(tiers))
```

`verify_stage` gains an `oracles: OracleRegistry | None = None` parameter. Only the **LICENSED
branch** changes: when minting LICENSED, also write the capped strength.

```python
def verify_stage(corpus, scaffolding, exec_records, oracles=None) -> Corpus:
    registry = oracles or OracleRegistry()
    ...
        if ev.satisfaction is not None and c.id in in_ext and c.provenance is not None:
            licensing = Licensing(route=SEVERE_TEST, satisfactions=(ev.satisfaction,),
                                  rival_set_closure=OPEN_ACKNOWLEDGED)
            new_claims.append(_with_status(
                c, status=Status.LICENSED, licensing=licensing, pending_reason=None,
                strength=oracle_cap(c, registry),   # <-- the only new line; None leaves strength None
            ))
        # REJECTED / PENDING branches unchanged
```

`run_cycle(corpus, adapters, ctx, oracles=None)` threads `oracles` straight to `verify_stage`;
no other stage needs it. Default `None` normalizes to an **empty** registry — so the guarantee
is **always-on**: a claim that references an oracle (`oracle_ref` set) with no resolvable
dossier is `UNVALIDATED` (empirical strength capped to 0) **whether or not a registry was
passed**. Back-compat holds for **builtin-only** claims (no `oracle_ref` — the entire existing
suite): they reference no oracle, so `oracle_cap` returns their strength unchanged regardless of
the registry. The guarantee cannot be silently disabled by omitting the argument.

Exports added to `protocol/__init__.py`: `OracleRegistry`, `oracle_cap`, plus re-exports of the
grammar oracle types (`OracleDossier`, `ValidationTier`, `ApplicabilityDomain`) for caller
convenience (mirrors the `Adapter`/`MaterializationContext` re-exports a `run_cycle` caller
needs).

## 7. Within-cycle interaction (intended, documented)

The cap is applied **after** the LICENSED membership decision (which uses the head
`scaffolding.grounded_extension`, computed over *uncapped* strengths) and **before** INTEGRATE.
Two consequences, both intended:

- **The cap flows into INTEGRATE's contests this cycle.** `restore_consistency`'s entrenchment
  reads `evidence_against_null` (capped) + `severity` (uncapped), and `effective_defeats` reads
  all six axes — so a claim grounded by a weak oracle has lower entrenchment and resists fewer
  attacks *in the same cycle*. This is exactly the spec's "oracle-strength multiplier" that lets
  a decisive high-tier result lawfully overturn a tower of cheap correlations.
- **A freshly-capped LICENSED claim may re-surface on the next frontier** under its corrected
  (lower) strength — the cap revealed it is weaker than it looked, so it re-enters scrutiny.
  Benign (re-scrutiny, not a status error). The fuller "cap upstream of REPRESENT so the
  extension is computed over capped strengths throughout" is a deferred refinement that belongs
  with #3's strength/posterior work.

## 8. Scope fence — explicitly OUT (deferred)

- **Dossiers-as-first-class-claims** — the long game (a dossier is itself a claim "measurement
  M validly instruments concept C"; oracle-construction as a generative target). *User-flagged
  to track.* The passed-in registry is the v1; promotion to claims is a later sub-project.
- **Uncertainty *propagation*** into executed leaves as error bars — `relative_uncertainty` is
  representable in the dossier now, but feeding it into `ExecValue`/leaf uncertainty at EXECUTE
  is later (touches the runtime, not VERIFY).
- **SPOT planted-error probes + verifier-authority degradation + the standing D2 daemon** — the
  runtime that re-validates oracles and degrades verifier authority on rising miss rate (→ #5).
- **Per-axis (vs uniform) empirical ceilings**, and **fine-grained domain matching** (value
  ranges / specific genes beyond Subject-kind): v1 caps the four empirical axes uniformly and
  matches domains at Subject-kind granularity; finer control via the prose `predicates` (human
  audit) for now.
- **Capping non-LICENSED claims' strength** — v1 caps at the LICENSED seam only.
- **Validating `subject_kinds` against the real Subject discriminator set** — left as free
  strings (a typo'd kind simply never matches → conservative out-of-domain).

## 9. Testing

**Grammar `test_oracle.py`:** tier ordering (`weakest_tier` picks min-rank; single; empty →
GOLD); `tier_ceiling` (empirical axes carry the ceiling, severity/explanatory_virtue = 1.0;
monotone across tiers; GOLD = all-1.0); `cap_strength` (caps empirical axes only; None → None;
cap by GOLD = unchanged; cap by UNVALIDATED → empirical axes 0, theory axes untouched);
`in_domain` (unbounded → True incl. None subject; bounded+matching kind → True; bounded+wrong
kind → False; bounded+None subject → False); `referenced_oracle_ids` (collects non-None refs;
empty when all None).

**Protocol `test_oracle.py`:** `OracleRegistry` (resolve hit/miss; dup-id rejected);
`oracle_cap` — builtin-only claim (no refs) → strength unchanged; GOLD oracle → unchanged;
UNVALIDATED/unresolved oracle → empirical axes 0; out-of-domain oracle → treated UNVALIDATED;
weakest-of-two (GOLD + INDIRECT → INDIRECT ceiling); strengthless claim (None) → None.

**`test_verify.py` (extend):** a claim whose plan node carries `oracle_ref` (impl still
`builtin::const`, so the reference adapters execute it) + a registry → LICENSED with capped
strength; same claim, `oracles=None` → strength unchanged (back-compat); out-of-domain oracle →
LICENSED but empirical strength 0.

**`test_cycle.py` (extend):** `run_cycle(corpus, adapters, ctx, oracles=registry)` caps a
licensed oracle-grounded claim's strength; the existing no-registry tests still pass.

## 10. Connections

- Binds `OperationNode.oracle_ref` (Phase 8's deliberately-unbound slot) to a real dossier and
  a real consequence (the strength ceiling).
- Reuses L0 `StrengthVector.meet` (Pareto algebra), L2 `Licensing` (the cap rides the LICENSED
  mint), and the Phase-8 `EvaluationPlan`/`OperationNode` operations IR.
- The capped strength feeds L3 `defeat`/`effective_defeats` + L4 `revision` entrenchment in the
  same `run_cycle` — the oracle tier becomes a live input to the corpus's self-correction.
- Emits no new corpus state; the registry is execution config. The path toward the federated
  claims universe ([[project_polymer_claims_platform_vision]]) where each node ships validated
  oracle dossiers with its claims.
