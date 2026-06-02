# Phase 7 — online-FDR ledger — design spec

Date: 2026-06-01
Status: design (feeds `writing-plans`)
Requirement: unified spec §5 #4 ("corpus-level online-FDR / error-budget object as a first-class IR entity")
Depends on: nothing in the grammar beyond `base._Model` (it's a standalone corpus-level entity)

## 0. Reading guide

As the knowledge flywheel runs, it tests many hypotheses over time and licenses the ones whose
tests "pass." Without a corpus-level error budget, the false-discovery rate (FDR — the expected
fraction of licensed claims that are actually null) creeps up as the corpus grows. This module is
the **online-FDR ledger**: a first-class, immutable IR entity that records the stream of
significance tests and allocates each test a significance level `α_t` from a shrinking budget,
so that the corpus-wide FDR stays bounded by a target — *without knowing the total number of tests
in advance* (that's what "online" means). The procedure is **LOND** (Levels based On Number of
Discoveries). The grammar *computes* the allocation (a deterministic recurrence); the p-values are
supplied from outside (the evaluator/protocol). Mirrors the "grammar does the tractable math, the
protocol supplies the measurements" division used by `blame.py` and `revision.py`.

## 1. Goal & scope

Add `grammar/fdr.py`: a standalone corpus-level module — a `_gamma` discount sequence, an
`FDRTest` record, an immutable `FDRLedger` entity, a `process_test` LOND step (+ a `process_stream`
fold), and an `is_discovery` query. No new `Claim` field; no coupling to `Claim.status` (the
protocol does that wiring). Frozen `_Model`, tuples/frozensets, isolation guard holds (no
`polymer_formalclaim` import).

**Out of scope (follow-ups):** per-pattern stratified ledgers; the PPV-floor gate; the LORD++
upgrade (the `procedure` field is the pluggability seam); wiring discoveries into `Claim.status`.

## 2. The LOND procedure

LOND (Javanmard & Montanari 2018) controls FDR over an open-ended test stream under independence.

- **Discount sequence** `γ_j = (6/π²) · (1/j²)` for `j ≥ 1`. This is non-negative, monotone
  decreasing, and `Σ_{j≥1} γ_j = 1` (Basel: `Σ 1/j² = π²/6`). `math.pi` is used (deterministic;
  not `Math.random`/`Date`).
- **Allocation at step `t`** (1-based): `α_t = target_fdr · γ_t · (D_{t-1} + 1)`, where `D_{t-1}`
  is the number of discoveries strictly before test `t`.
- **Discovery rule:** test `t` is a discovery iff `p_t ≤ α_t`.
- **Budget intuition:** the level shrinks with position (`γ_t`) but grows with the number of
  discoveries so far (`D_{t-1}+1`) — each confirmed discovery "earns back" budget for later tests.
  Proportionality to `target_fdr` is what bounds corpus FDR ≤ `target_fdr` under independence.

Worked example (`target_fdr = 0.05`): `γ_1 = 6/π² ≈ 0.6079`, so `α_1 = 0.05 · 0.6079 · 1 ≈ 0.0304`.
If test 1 is a discovery, then `α_2 = 0.05 · γ_2 · 2 = 0.05 · 0.1520 · 2 ≈ 0.0152`; if test 1 is
*not* a discovery, `α_2 = 0.05 · 0.1520 · 1 ≈ 0.0076` (lower — no earned budget).

## 3. Data model

```python
class FDRTest(_Model):            # frozen, extra="forbid", hashable
    index: int                    # 1-based position in the stream
    claim_id: str
    p_value: float                # validated ∈ [0.0, 1.0]
    alpha_allocated: float        # the α_t this test was judged at
    discovery: bool               # p_value <= alpha_allocated

class FDRLedger(_Model):          # the first-class corpus IR entity
    target_fdr: float             # validated ∈ (0.0, 1.0]
    procedure: Literal["lond"] = "lond"
    tests: tuple[FDRTest, ...] = ()

    @property
    def n_tests(self) -> int: ...            # len(self.tests)
    @property
    def n_discoveries(self) -> int: ...      # sum(t.discovery for t in self.tests)
    @property
    def discoveries(self) -> frozenset[str]: # {t.claim_id for t in self.tests if t.discovery}
```

Validators: `FDRTest.p_value ∈ [0,1]`; `FDRLedger.target_fdr ∈ (0,1]`. `index` is assigned by
`process_test`, never authored ad hoc.

## 4. Operations

```python
def _gamma(j: int) -> float:
    """LOND discount γ_j = (6/π²)/j² (j ≥ 1). Σγ_j = 1, monotone decreasing."""

def process_test(ledger: FDRLedger, claim_id: str, p_value: float) -> FDRLedger:
    """One LOND step. t = n_tests+1; α_t = target_fdr·γ_t·(n_discoveries+1);
    discovery = p_value <= α_t. Returns a NEW ledger with the FDRTest appended (append-only,
    immutable). The discovery rule uses n_discoveries from the CURRENT ledger (= D_{t-1})."""

def process_stream(ledger: FDRLedger, items: Iterable[tuple[str, float]]) -> FDRLedger:
    """Fold process_test over (claim_id, p_value) pairs in order. Equivalent to iterated
    process_test (each step sees the discoveries of the prior steps)."""

def is_discovery(ledger: FDRLedger, claim_id: str) -> bool:
    """True iff some recorded test for claim_id was a discovery. Query helper the protocol
    uses to gate LICENSing; keeps the ledger decoupled from Claim."""
```

All pure functions; nothing mutates. `process_test` recomputes `n_discoveries`/`n_tests` from the
input ledger so the recurrence is self-contained and order-faithful.

## 5. Module boundaries

- `fdr.py` — `_gamma`; `FDRTest`; `FDRLedger` (+ 3 properties); `process_test`; `process_stream`;
  `is_discovery`. Depends only on `base._Model` (and stdlib `math`). Standalone — no import of
  `claim`/`defeat`/`revision`. Exported from `__init__.py`.
- No `Claim` change; `status.py` unchanged (gating LICENSE on `is_discovery` is a protocol concern).

## 6. Testing (TDD)

- `_gamma`: `γ_1 == 6/π²` (≈0.6079); strictly decreasing (`γ_1 > γ_2 > γ_3`); partial sum
  `Σ_{1..1000} γ_j` within `1e-2` of 1.0 (converges to 1).
- `process_test` first step: small `p` (< α_1) → `discovery=True`, `alpha_allocated == target·γ_1·1`,
  `index == 1`; large `p` (> α_1) → `discovery=False`.
- **budget grows with discoveries:** construct a stream where a borderline p-value that would FAIL
  at `D=0` PASSES once a prior discovery raises `D` (α_t uses `D_{t-1}+1`). Assert the discovery flips.
- `process_stream` equals iterated `process_test` (same ledger state).
- `is_discovery`: true for a discovered claim_id, false for a non-discovered or absent one.
- properties: `n_tests`, `n_discoveries`, `discoveries` correct over a mixed stream.
- validators: `p_value` outside [0,1] → ValidationError; `target_fdr` of 0 or >1 → ValidationError.
- immutability: `FDRLedger`/`FDRTest` frozen + hashable; `extra="forbid"`.
- isolation guard green.

## 7. Follow-ups (deferred)

- Per-pattern stratified ledgers (a ledger per `pattern.id`) — §4 "per-pattern empirical null".
- PPV-floor gate alongside the FDR ledger — §4 "running PPV".
- LORD++ procedure (more powerful; track per-discovery times) — the `procedure` field is the seam.
- Wiring `is_discovery` into the licensing/`Claim.status` decision — protocol-runtime concern.
- LOND controls FDR under independence; dependent p-values would need LOND-D / a discount factor —
  note, not implement.
