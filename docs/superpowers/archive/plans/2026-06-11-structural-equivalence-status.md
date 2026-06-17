# M1 — Structural Equivalence Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `canonicalize` from minting `LICENSED` structural-equivalence edges that passed no evidential test; give them an honest `Status.STRUCTURAL` ("true by construction").

**Architecture:** Additive grammar enum member + a Claim-side fence validator + a one-line broadening of `equivalence_class`'s back-compat membership gate, then a one-line change in the protocol `canonicalize` stage to mint the new status. No new `Corpus` collection, no new fields, no protocol public-API change. Grammar one-way isolation preserved; viewer/topology contract untouched (`STRUCTURAL` never appears as a node status).

**Tech Stack:** Python 3, Pydantic v2 (frozen models), pytest, uv (per-package projects), ruff.

**Spec:** `docs/superpowers/archive/specs/2026-06-11-structural-equivalence-status.md`
**Branch:** `feat/m1-structural-equivalence-status` (off the current `docs/credibility-arc-roadmap` HEAD, so it carries the roadmap + spec + this plan).

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `grammar/src/polymer_grammar/status.py` | The shared `Status` enum | Add `STRUCTURAL` member |
| `grammar/src/polymer_grammar/claim.py` | `Claim` model + validators | Add a validator fencing `STRUCTURAL` out of `Claim` |
| `grammar/src/polymer_grammar/equivalence.py` | `EquivalenceClaim` + `equivalence_class` membership | Broaden the back-compat IN gate to `{LICENSED, STRUCTURAL}`; update docstring |
| `grammar/tests/test_status.py` | enum value coverage | Update the exhaustive value-set assertion |
| `grammar/tests/test_equivalence.py` | equivalence model + membership | Add STRUCTURAL-as-IN and CONJECTURED-not-IN tests |
| `grammar/tests/test_claim.py` | Claim validation | Add the STRUCTURAL-rejected test |
| `protocol/src/polymer_protocol/canonicalize.py` | structural-key collapse stage | Mint `Status.STRUCTURAL` instead of `LICENSED` (line ~78) |
| `protocol/tests/test_canonicalize.py` | canonicalize behavior | Update the minted-status assertion; assert no LICENSED equivalence is minted |

`protocol/tests/test_cycle.py` needs **no change** — verified it asserts nothing about equivalence status (its `Status.LICENSED` uses are all on claims). Task 5 confirms it stays green.

---

## Task 0: Create the implementation branch

- [ ] **Step 1: Branch off the current HEAD**

Run:
```bash
cd /Users/zbb2/Desktop/polymer-claims
git checkout -b feat/m1-structural-equivalence-status
git log --oneline -1
```
Expected: a new branch whose HEAD is the M1 spec commit (`design(m1): structural equivalence…`).

---

## Task 1: Grammar — add `Status.STRUCTURAL`

**Files:**
- Modify: `grammar/src/polymer_grammar/status.py`
- Test: `grammar/tests/test_status.py`, `grammar/tests/test_equivalence.py`

- [ ] **Step 1: Update the exhaustive status-set test and add an EquivalenceClaim-accepts test**

In `grammar/tests/test_status.py`, replace the body of `test_status_values` so the expected set includes `"structural"`:

```python
def test_status_values():
    assert Status.LICENSED.value == "licensed"
    assert Status.STRUCTURAL.value == "structural"
    assert {s.value for s in Status} == {
        "conjectured",
        "exploratory",
        "pending",
        "licensed",
        "rejected",
        "structural",
    }
```

In `grammar/tests/test_equivalence.py`, add (the `_eq` helper already defaults `status=Status.LICENSED`; override it):

```python
def test_equivalence_accepts_structural_status():
    eq = _eq(status=Status.STRUCTURAL)
    assert eq.status == Status.STRUCTURAL
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd grammar && uv run pytest tests/test_status.py::test_status_values tests/test_equivalence.py::test_equivalence_accepts_structural_status -q
```
Expected: FAIL — `AttributeError: STRUCTURAL` (the enum member does not exist yet).

- [ ] **Step 3: Add the enum member**

In `grammar/src/polymer_grammar/status.py`, add `STRUCTURAL` to the `Status` enum (after `REJECTED`):

```python
class Status(str, Enum):
    CONJECTURED = "conjectured"
    EXPLORATORY = "exploratory"
    PENDING = "pending"
    LICENSED = "licensed"
    REJECTED = "rejected"
    STRUCTURAL = "structural"   # true by construction (e.g. a structural-key equivalence);
                                # NOT an evidential license. Valid only on EquivalenceClaim.
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd grammar && uv run pytest tests/test_status.py tests/test_equivalence.py -q
```
Expected: PASS (all tests in both files).

- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/status.py grammar/tests/test_status.py grammar/tests/test_equivalence.py
git commit -m "feat(grammar): add Status.STRUCTURAL (true-by-construction, equivalence-only)"
```

---

## Task 2: Grammar — fence `STRUCTURAL` out of `Claim`

**Files:**
- Modify: `grammar/src/polymer_grammar/claim.py`
- Test: `grammar/tests/test_claim.py`

- [ ] **Step 1: Write the failing test**

In `grammar/tests/test_claim.py`, add (uses the same minimal-Claim shape already used elsewhere in the suite):

```python
def test_claim_rejects_structural_status():
    from polymer_grammar import CategoricalLeaf, PatternRef

    with pytest.raises(ValidationError, match="STRUCTURAL is valid only on an EquivalenceClaim"):
        Claim(
            id="c",
            title="c",
            pattern=PatternRef(id="adjusted_effect", version="v1"),
            leaves=(CategoricalLeaf(ontology_term="t"),),
            status=Status.STRUCTURAL,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd grammar && uv run pytest tests/test_claim.py::test_claim_rejects_structural_status -q
```
Expected: FAIL — no `ValidationError` is raised (the Claim is currently accepted with any status).

- [ ] **Step 3: Add the fence validator**

In `grammar/src/polymer_grammar/claim.py`, add a third `model_validator` after `_licensing_only_when_licensed` (around line 65):

```python
    @model_validator(mode="after")
    def _structural_only_on_equivalence(self) -> "Claim":
        if self.status == Status.STRUCTURAL:
            raise ValueError(
                "status=STRUCTURAL is valid only on an EquivalenceClaim "
                "(a Claim is never true by construction); got a Claim"
            )
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd grammar && uv run pytest tests/test_claim.py -q
```
Expected: PASS (the new test plus all existing `test_claim.py` tests).

- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/claim.py grammar/tests/test_claim.py
git commit -m "feat(grammar): fence Status.STRUCTURAL out of Claim (equivalence-only)"
```

---

## Task 3: Grammar — `equivalence_class` counts `STRUCTURAL` as IN

**Files:**
- Modify: `grammar/src/polymer_grammar/equivalence.py`
- Test: `grammar/tests/test_equivalence.py`

- [ ] **Step 1: Write the failing tests**

In `grammar/tests/test_equivalence.py`, add:

```python
def test_structural_edge_counts_as_in_back_compat():
    # back-compat path (grounded_in not supplied): a STRUCTURAL edge merges its endpoints.
    eq = _eq(status=Status.STRUCTURAL)
    assert are_equivalent(eq.left, eq.right, [eq])
    assert equivalence_class(eq.left, [eq]) == frozenset({eq.left, eq.right})


def test_conjectured_edge_does_not_count_as_in():
    # a mere conjecture must NOT merge endpoints in the back-compat path.
    eq = _eq(status=Status.CONJECTURED)
    assert not are_equivalent(eq.left, eq.right, [eq])
```

- [ ] **Step 2: Run tests to verify the STRUCTURAL one fails**

Run:
```bash
cd grammar && uv run pytest tests/test_equivalence.py::test_structural_edge_counts_as_in_back_compat tests/test_equivalence.py::test_conjectured_edge_does_not_count_as_in -q
```
Expected: `test_structural_edge_counts_as_in_back_compat` FAILS (gate is still `== LICENSED`, so the STRUCTURAL edge is not counted); `test_conjectured_edge_does_not_count_as_in` PASSES already.

- [ ] **Step 3: Broaden the membership gate**

In `grammar/src/polymer_grammar/equivalence.py`, change the back-compat branch of the `counts` expression in `equivalence_class` (currently lines ~64–68):

```python
        counts = (
            eq.id in grounded_in
            if grounded_in is not None
            else eq.status in (Status.LICENSED, Status.STRUCTURAL)
        )
```

Update the function docstring sentence to name both IN statuses:

```python
    """Connected component of `handle` over symmetric equivalence edges.

    An edge counts as "IN" when, if `grounded_in` is supplied, its claim id is a member
    of that grounded extension (the real L3 membership); otherwise (back-compat) when its
    status is LICENSED or STRUCTURAL (a structural-key identity is IN by construction).
    """
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd grammar && uv run pytest tests/test_equivalence.py -q
```
Expected: PASS (both new tests plus all existing).

- [ ] **Step 5: Commit**

```bash
git add grammar/src/polymer_grammar/equivalence.py grammar/tests/test_equivalence.py
git commit -m "feat(grammar): equivalence_class counts STRUCTURAL edges as IN (back-compat)"
```

---

## Task 4: Protocol — `canonicalize` mints `STRUCTURAL`

**Files:**
- Modify: `protocol/src/polymer_protocol/canonicalize.py`
- Test: `protocol/tests/test_canonicalize.py`

- [ ] **Step 1: Update the minted-status assertion (the failing test)**

In `protocol/tests/test_canonicalize.py`, in `test_structurally_identical_claims_become_one_equivalence_class`, change line 18 and its comment, and add a no-LICENSED assertion:

```python
    assert eq.status == Status.STRUCTURAL
    # they are now in one equivalence class (back-compat STRUCTURAL gating)
    assert are_equivalent("a", "b", out.equivalences)
    # canonicalize must never mint a LICENSED equivalence (no evidential test was run)
    assert all(e.status != Status.LICENSED for e in out.equivalences)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd protocol && uv run pytest tests/test_canonicalize.py::test_structurally_identical_claims_become_one_equivalence_class -q
```
Expected: FAIL — `eq.status` is still `Status.LICENSED`.

- [ ] **Step 3: Mint the new status**

In `protocol/src/polymer_protocol/canonicalize.py`, in the `EquivalenceClaim(...)` constructor (around line 78), change the status line:

```python
                    status=Status.STRUCTURAL,
```

(Leave `id`, `left`, `right`, `severity=1.0`, and `note="structural-key collapse"` unchanged. `Status` is already imported in this module.)

- [ ] **Step 4: Run the canonicalize tests to verify they pass**

Run:
```bash
cd protocol && uv run pytest tests/test_canonicalize.py -q
```
Expected: PASS — all canonicalize tests, including the idempotency and conclusion-collapse tests that rely on `are_equivalent` (which now counts STRUCTURAL).

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/canonicalize.py protocol/tests/test_canonicalize.py
git commit -m "feat(protocol): canonicalize mints Status.STRUCTURAL, not LICENSED (M1)"
```

---

## Task 5: Full-suite + lint + isolation + viewer verification

**Files:** none (verification only).

- [ ] **Step 1: Run the grammar suite + lint**

Run:
```bash
cd grammar && uv run pytest -q && uv run ruff check src tests
```
Expected: all green; ruff clean. (Includes the isolation guard `tests/test_isolation.py`.)

- [ ] **Step 2: Run the protocol suite + lint**

Run:
```bash
cd protocol && uv run pytest -q && uv run ruff check src tests
```
Expected: all green (notably `tests/test_cycle.py` unchanged and passing); ruff clean.

- [ ] **Step 3: Run the umbrella suite**

Run:
```bash
cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ -q
```
Expected: all green (no umbrella code touched; this confirms no transitive break).

- [ ] **Step 4: Run the full local CI substitute**

Run:
```bash
cd /Users/zbb2/Desktop/polymer-claims && bash scripts/check-all.sh
```
Expected: `ALL GREEN` (umbrella + grammar + protocol pytest/ruff + isolation + viewer typecheck/build). The viewer step confirms the topology contract is unaffected.

- [ ] **Step 5: Update the continuity log + roadmap, then commit**

Mark M1 done in the credibility-arc roadmap (`docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md` — add a `✅ DONE` note to the 1a section) and add a dated entry to `docs/superpowers/CONTINUE.md` recording: the new `Status.STRUCTURAL`, the Claim fence, the gate broadening, the canonicalize change, and the final green test counts.

```bash
git add docs/superpowers/CONTINUE.md docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md
git commit -m "docs(m1): structural-equivalence status done — CONTINUE + roadmap"
```

---

## Self-Review

**Spec coverage:**
- §Design 1 (new `Status.STRUCTURAL`) → Task 1. ✓
- §Design 2 (fence out of `Claim`) → Task 2. ✓
- §Design 3 (broaden `equivalence_class` gate) → Task 3. ✓
- §Design 4 (mint in `canonicalize`) → Task 4. ✓
- §Design 5 (tests: Claim-rejected, equivalence-accepts, STRUCTURAL-as-IN, CONJECTURED-not-IN, canonicalize mints STRUCTURAL, no LICENSED minted) → Tasks 1–4. ✓
- §Deliberate non-changes (viewer/topology/Corpus untouched; `test_cycle.py` unchanged) → verified in File Structure note + Task 5 step 4. ✓
- §Acceptance (all four bullets) → Task 5. ✓

**Placeholder scan:** none — every step has the exact code/command and expected result.

**Type consistency:** `Status.STRUCTURAL` used identically across all tasks; validator method `_structural_only_on_equivalence`; the error string `"STRUCTURAL is valid only on an EquivalenceClaim"` is matched in the Task 2 test and raised in the Task 2 validator. `_eq(...)`/`make_claim(...)`/`make_plan(...)` helpers used as they exist in their respective suites.
