# Polymer Claims — Scaled Infrastructure (the unicorn-scale build)

**Status:** Vision / pipedream scale. Not a roadmap — a sketch of what the
fully-realized platform's hardware and infra would actually be, so the shape is on
record. Read alongside `ARCHITECTURE_CURRENT.md` (what exists today) and the
Phase-2 North Star (`docs/superpowers/2026-06-12-phase-2-north-star.md`).

---

## The governing principle: ride, don't rebuild

The platform's own thesis decides its infra shape: **we do not own the world's
compute or the world's data — we integrate trust *over* them.** So the build
splits into two piles:

- **Pile A — what you ORCHESTRATE but never own:** the heterogeneous recomputation
  fabric, running on other people's hardware, near their data.
- **Pile B — what you OWN and run hard:** the trust machinery — ledger, graph
  engine, drift fabric, math layer, control plane.

Naive designs over-build A and under-build B. The real engineering and the real
cost are in B. At scale the platform is **infra-light on execution, infra-heavy on
trust.**

---

## The shape

```
                       ┌────────────────────────────────────────────────┐
                       │   PILE B — what you OWN (the trust layer)        │
  upstream data        │                                                  │
  sources (GEO, ENA,   │  ┌─────────────┐    ┌──────────────────────┐    │
  Refget, WorkflowHub) ─┼─▶│ DRIFT        │    │ CORPUS / GRAPH engine │   │
        │  drift events │  │ event fabric │───▶│ (claims, defeat edges,│   │
        │               │  └─────────────┘    │  equivalences, FDR     │   │
        │               │                     │  ledger; versioned)    │   │
        │               │  ┌─────────────┐    └──────────┬────────────┘    │
        │               │  │ MATH layer   │◀──────────────┘  feeds          │
        │               │  │ (sheaf gauge │                                │
        │               │  │ + embedding) │──▶ live universe (SSE / WebGPU) │
        │               │  └─────────────┘                                 │
        │               │  ┌────────────────────────────────────────┐     │
        │               │  │ TRANSPARENCY LOG (witnessed Merkle)      │     │
        │               │  └───────────────────▲────────────────────┘     │
        │               │  control plane        │ attestations + results   │
        │               │  (DRS/WES/TRS/RO-Crate)│                         │
        │               └──────────┬────────────┴──────────────────────────┘
        │                          │ dispatch  (compute-to-data)
        │                          ▼
        │               ┌────────────────────────────────────────────────┐
        │               │   PILE A — what you ORCHESTRATE, not own         │
        │               │   federated WES endpoints, each NEXT TO its data │
        │               │   ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
        └──────────────▶│   │ cloud    │  │ academic │  │ secure enclave│  │
          (watch the    │   │ HPC/GPU/ │  │ Slurm    │  │  TEE + remote │  │
           content-     │   │ FPGA     │  │ HPC      │  │  attestation  │  │
           addresses)   │   └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
                       │         │   data stays put (PHI/EGA)  │          │
                       │      [ datasets at rest inside each domain ]      │
                       └────────────────────────────────────────────────┘
```

Flow: the control plane dispatches a pinned computation to ≥2 *independent* WES
endpoints sitting next to the data; each runs in a TEE and returns a signed
attestation + result (the data never moves); the transparency log records the run;
the graph engine integrates the license; the math layer recomputes consistency and
the universe; the drift fabric watches every upstream content-address and re-opens
licenses when the world moves — re-triggering Pile A.

---

## Pile A — the recomputation fabric (orchestrate, not own)

- **A planetary mesh of execution endpoints** — GA4GH **WES** across hyperscaler
  HPC, academic Slurm clusters, national labs, and institutional enclaves. You are
  a *meta-scheduler across trust domains*, not a datacenter operator.
- **Heterogeneous accelerators, because science is heterogeneous** — CPU + large-
  memory for genomics pipelines (alignment/variant calling), GPU farms
  (H100/B200-class) for ML-derived claims and the math layer, FPGA/ASIC genomics
  accel (DRAGEN-style), MD/simulation ASICs (Anton-class) at the far edge. Routed
  to, never bought.
- **Confidential computing as the price of admission** — to recompute over
  protected cohorts (dbGaP/EGA controlled-access, PHI) *without seeing them*, and
  to prove an independent run really happened on the claimed data+code: Intel
  **TDX**, AMD **SEV-SNP**, **NVIDIA Confidential GPUs**, AWS **Nitro Enclaves**,
  ARM **CCA** — emitting **remote attestation quotes** rooted in hardware (TPMs).
  This is what the Arc-3 agent protocol means by "hardware attestation."

At scale, your execution footprint is deliberately thin; the bill is metered
third-party compute, not capex datacenters.

---

## Pile B — the trust layer (own and run hard)

1. **The transparency log — the crown jewel.** Append-only, tamper-evident,
   **publicly verifiable** Merkle log of every license, run, and attestation
   (Sigstore/Rekor at planetary scale), independently mirrorable and **witnessed**
   (multiple parties co-signing checkpoints, à la Certificate Transparency), so
   trust lives in the log, not in the company. Grows monotonically forever →
   *(Shipped today: a **local, single-signer, inclusion-only** log — no consistency
   proofs and no external witnesses yet. The planetary-scale, multi-party-witnessed
   version described here is the target, not the current state.)*
   geo-replicated WORM storage + the live Merkle service. (Timestamp anchoring is
   fine; a token economy is explicitly out — Goodhart.)

2. **The corpus / graph engine.** A continuously-mutating, fully-versioned
   knowledge graph at tens of millions of claims with defeat/equivalence edges and
   the FDR ledger, every state content-addressed. Needs fast defeat-reachable
   subgraph queries (bounded blast radius), **incremental** grounded-semantics
   propagation (differential-dataflow / Pregel-style), and append-only history.
   Multi-TB-RAM hot graph over a content-addressed persistent store.

3. **The drift-sensing event fabric.** A planet-scale watcher monitoring the
   content-address of *every* upstream dataset, reference, library, and apparatus
   any LICENSED claim depends on. Reverse index (content-address → dependent
   claims), Kafka-class event stream; a moved hash → drift → re-open → re-dispatch
   into Pile A. Always-on CDC integrated with thousands of sources.

4. **The math layer (sheaf + embedding).** Standing GPU compute: incremental
   **sheaf-Laplacian eigensolves** over the quantitative sub-graph (large sparse
   symmetric eigenproblems; cuSOLVER/SLEPc-class, distributed for big graphs), plus
   the **living-universe** generator (signed-Laplacian eigenmaps → Lorentz/
   hyperbolic projection → Procrustes-aligned incremental updates). Runs forever as
   the corpus mutates.

5. **AI proposer/attacker inference.** GPU inference (or large API spend) for
   frontier models that propose and adversarially attack claims at firehose scale.
   This is *untrusted scaffolding* (de Bruijn) — optimize for throughput/cost, not
   guarantees; the kernel catches its mistakes.

6. **Standards control plane + serving edge.** Highly-available DRS/WES/TRS/
   Refget/RO-Crate/in-toto/SLSA/Signposting endpoints (the "standards skin" others
   point their pipelines at), multi-tenant auth (today's local-only → federated
   gap), and a streaming/CDN edge pushing the evolving universe over SSE/WebSocket
   with client-side WebGPU rendering.

---

## The genuinely hard, "this is why it's a pipedream" problems

Not buy-more-boxes problems — open systems-research problems:

1. **Deterministic reproducibility across heterogeneous hardware.** Floating-point
   and GPU nondeterminism mean "re-run and compare" is not well-defined across
   chips and BLAS versions. Either chase bit-exactness (pin everything: Nix/Guix
   content-addressed environments, fixed BLAS, deterministic GPU modes — brutal) or
   **bake principled tolerances into the criterion** so agreement is a severe test,
   not byte-equality. This is arguably *the* core systems problem of the platform.
2. **Scheduling across trust domains.** Orchestrating compute over institutions
   that trust neither you nor each other, with data that legally cannot move, under
   cost/locality/attestation constraints. Kubernetes-meets-WES-meets-zero-trust.
3. **Attestation verification at scale.** Verifying millions of TEE quotes and
   Merkle inclusion proofs, with revocation and an auditable verification service.
4. **The economics.** Re-running a meaningful fraction of the world's computational
   science *twice* is astronomically expensive. "Ride, don't rebuild" +
   compute-to-data is the answer — and it is exactly *why* rigorous **independence**
   and **severity** matter: they decide which claims are worth the recompute spend.

---

## One line

The unicorn build is **infra-light on execution and infra-heavy on trust**: you
own a witnessed global transparency log, a versioned multi-TB knowledge-graph
engine, an always-on drift-sensing fabric, and a standing GPU math layer — and you
orchestrate the world's confidential, attested, heterogeneous compute over data
that never moves. The hardest single piece is not any box; it is making "re-run it
and check" *deterministic and severe* across all that heterogeneity.
