# BioNeMo Evidence Adapter Layer — Design

**Date:** 2026-06-23
**Status:** Approved (brainstorming) → ready for implementation plan
**Scope:** Phase 1 (plumbing) of a multi-phase arc. Wedge science deferred.

---

## 1. Premise

NVIDIA's BioNeMo Agent Toolkit (launched 2026-06-23) packages NVIDIA NIM
microservices — protein folding (OpenFold, Boltz-2), docking (DiffDock),
protein design (RFdiffusion, ProteinMPNN), generative chemistry (GenMol), and
genomics — behind hosted endpoints on `build.nvidia.com`, callable with an API
key and free starting credits. No local GPU is required.

The strategic insight that drives this work:

> **BioNeMo NIMs are evidence *generators*. polymer-claims is the evidence
> *adjudicator*.** A fold confidence, a docking score, or a variant-effect
> score is exactly the kind of computational result the CES / SE-Contract layer
> is built to bind to a claim and run through the e-value / warrant-tier /
> certify path.

So the work is not "add fold tools." It is "make a BioNeMo run a first-class
evidence source that produces certifiable claims."

---

## 2. The greater vision (roadmap, kept intact)

Phase 1 below is deliberately small, but it is step one of a larger arc. The
toolkit and the 2026-06-23 NVIDIA brief expose far more than structure
prediction, and each piece has a home in this engine:

- **Genomic foundation models for variant-effect scoring** (via Parabricks +
  genomics NIMs). *This is the one that lights up.* It maps directly onto the
  Variant Adjudication Engine / AML-twin wedge that the build path flags as the
  next legible wedge claim. A variant-pathogenicity score from a genomics NIM,
  corroborated by an independent VEP (e.g. AlphaMissense), becomes a certifiable
  variant-adjudication claim. **This is the intended Phase 2 wedge.**

- **Deep Biomedical Research workflow** — literature review, protocol
  generation, pharmacovigilance. A future *generation* adapter: this can
  *propose* claims (frontier-driven) but, per the engine's guardrail, can never
  *license* them. Natural fit for the GENERATE seam, not the EXECUTE seam.

- **Nemotron (open reasoning models), NeMo RL, NemoClaw (secure agent
  blueprints), OpenShell (controlled exec env).** Reasoning and orchestration
  substrate. Relevant when the engine runs as an autonomous node that selects
  its own frontier and executes evidence runs under a controlled environment —
  later, once the evidence loop is proven.

- **Anthropic is a named BioNeMo integration partner.** Claude-Code-native
  consumption is a first-class supported path, not a workaround. The toolkit
  ships a `.claude-plugin/marketplace.json`. So the agent-facing surface (skills
  installed into Claude Code) and the runtime surface (this adapter layer inside
  polymer-claims) are complementary, both sanctioned.

The phasing:

| Phase | What | Reuses |
|-------|------|--------|
| **1 (this spec)** | Reusable BioNeMo evidence-adapter layer, proven end-to-end against a trivial cached NIM call + a fenced synthetic corroborator → one LICENSED + certified claim. | existing EXECUTE / oracle / registry seams |
| **2** | The wedge: variant-effect scoring (genomics NIM + independent VEP) → certifiable variant-adjudication claim; AML twin. | the Phase 1 layer, unchanged |
| **3** | Deep Biomedical Research as a GENERATE adapter (propose-only). | the GENERATE seam |
| **4** | Autonomous node + controlled execution (Nemotron / NemoClaw / OpenShell). | the protocol scheduler / daemons |

Phases 2–4 reuse the Phase 1 layer without modification. That is the test of
whether Phase 1 is designed right.

---

## 3. Phase 1 design

### 3.1 Goal

A reusable, well-fenced layer that turns any BioNeMo NIM run into a first-class
evidence source for the claims engine — proven end-to-end (`run_cycle` →
`LICENSED` → `certify`) against a trivial NIM call, with the scientific wedge
deferred. Hosted endpoints only; no GPU.

### 3.2 Where it lives

New sub-package `src/polymer_claims/bionemo/` in the **impure umbrella**
(alongside `llm_adapter.py`, `exec_adapters.py`). Network IO must stay out of
the pure `grammar` / `protocol` packages. New optional extra `[bionemo]` in the
umbrella `pyproject.toml`, mirroring `[llm]`. The pure packages are untouched;
this layer only *uses* their existing seams.

### 3.3 Components (each independently testable)

1. **`client.py` — NIM REST client.** Talks to hosted `build.nvidia.com` NIM
   endpoints. Knows the NIM request/response protocol (synchronous and
   202-poll patterns), auth, retries, timeouts. Knows nothing about claims.
   Two guardrails are built in:
   - **Key from macOS keychain**, env-var fallback, never a dotfile.
   - **Disk response cache** keyed by `hash(endpoint, payload)` so re-runs are
     reproducible and do not reburn free credits.

   Captures the NIM **model id / version** from each response; this becomes the
   oracle anchor and goes into the certificate.

2. **`adapters.py` — `BioNeMoNIMAdapter`.** Implements the existing `Adapter`
   protocol (`identity`, `execute(node, upstream, ctx) -> ExecValue`). Reads
   the input `DataHandle`, calls the client, maps one response field to a
   `Leaf` / `ExecValue`. One concrete subclass for the validation capability.

3. **`oracle.py` — `bionemo_oracle_registry()`.** Emits an `OracleDossier` per
   NIM. **Tiers are set conservatively.** A pure-compute NIM with no wet-lab
   anchor for the subject gets `UNVALIDATED` or `INDIRECT`, never `ANCHORED`.
   The tier *caps* claim strength, so honesty here is load-bearing; each tier
   choice is documented with its justification.

4. **`registry.py` — adapter credentials.**
   `AdapterCredential(identity, owner="NVIDIA", implementation_hash=<bytecode-derived>, version, trusted=True)`.

5. **`apparatus.py` — NIM apparatus record.** A small, bespoke frozen record
   capturing endpoint + model id / version + payload schema → a content hash.
   **Note:** the existing `AnalysisProfile` is methylation-specific (required
   fields like `array_type`, `norm_package`, `design_formula`) and is *not*
   reused here. Instead the apparatus hash feeds the generic
   `MaterializationContext` provenance fields (`profile_hash`,
   `semantic_run_id`, `shared_cause_factors`), so the certificate still records
   exactly which NIM version produced the evidence — without forcing a
   methylation schema onto a protein/genomics run.

### 3.4 The air-gap, handled honestly

A license requires **two independently-owned adapters that agree** (different
`owner` *and* different `implementation_hash`; both registered and trusted).
A lone BioNeMo run can never self-license — by design.

For plumbing-only validation, the second adapter is a clearly-labeled
**`SyntheticCorroboratorAdapter`** (different owner, different impl hash) that
lives under `tests/fixtures/` and is registered **only** in the
plumbing-validation corpus — **never** the production registry. When the Phase 2
wedge is chosen, it is replaced by a real independent model (ESMFold /
AlphaMissense / etc.) and barred from any certifying run.

**Fence (non-negotiable):** no synthetic corroboration may ever launder into a
real scientific claim. The synthetic adapter is a test double, scoped to
plumbing validation only.

### 3.5 Data flow

```
Claim with EvaluationPlan DAG
  → OperationNode(oracle_ref="bionemo-<cap>@v1") over a DataHandle
  → run_cycle EXECUTE:
        BioNeMoNIMAdapter.execute()        → ExecValue (leaf)
        SyntheticCorroboratorAdapter.execute() → ExecValue (leaf)
  → VERIFY: both resolve in AdapterRegistry, trusted,
            different owner, different impl hash → 2× SATISFIED → Satisfaction
  → OracleRegistry tier caps strength axes
  → e-LOND budget check
  → LICENSED
  → certify → certificate embeds NIM model version + content addresses
```

### 3.6 Error handling

NIM failure (timeout / 5xx / malformed) → adapter raises → it produces no
`SATISFIED` → claim stays `PENDING`. Never a false license. Cache-miss with no
key → explicit error. All network is confined to the node layer; pure packages
stay deterministic.

### 3.7 Worked example + verification

- `examples/bionemo_plumbing/` — a corpus JSON + `run.py` that produces **one
  LICENSED claim** from a real (cached) NIM call + the synthetic corroborator,
  then certifies it via the existing `certify` path.

- **Tests** (matching the repo's offline, deterministic, 1200-test bar):
  - unit: client (mocked HTTP), adapter response→leaf mapping, oracle tier
    capping, independence gate (NVIDIA-vs-synthetic passes; NVIDIA-vs-NVIDIA
    held `PENDING`).
  - integration: one **cassette-backed** test (recorded NIM response) so CI
    stays offline.
  - one **opt-in live smoke test** gated behind an env flag + real key that hits
    `build.nvidia.com` exactly once.

### 3.8 Out of scope (Phase 1)

Variant-effect / fold / dock science; new subject kinds; new SE-Contract data
seams; self-hosting NIMs; the GENERATE-adapter and autonomous-node phases. All
deferred — and all reuse this layer unchanged.

---

## 4. Module boundaries (isolation check)

| Module | Knows about | Does NOT know about | Independently testable |
|--------|-------------|---------------------|------------------------|
| `client.py` | HTTP, NIM protocol, auth, caching | claims, grammar | yes (mock HTTP) |
| `adapters.py` | NIM response → `ExecValue`, grammar types | HTTP details | yes (mock client) |
| `oracle.py` | validation tiers (pure data) | network, claims runtime | yes |
| `registry.py` | credentials (pure data) | network | yes |
| `apparatus.py` | apparatus → content hash, MaterializationContext provenance | network, methylation schema | yes |

Each unit answers: what it does, how to use it, what it depends on — and can be
changed without breaking consumers.

---

## 5. Open questions deferred to the plan

- Exact NIM endpoint chosen for the trivial plumbing call (smallest, cheapest,
  most stable response shape).
- Cassette format (custom JSON vs an existing recorder library already in the
  repo's deps).
- Whether `[bionemo]` pulls a small HTTP client dep or reuses one already
  present.
