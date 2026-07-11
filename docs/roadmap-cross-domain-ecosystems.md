# Cross-Domain Generalization: Verification Ecosystems Beyond Computational Biology

> **Status:** Strategic framing for the longer-term roadmap. Not an active workstream.
> The team stays focused on the computational-biology vertical for now. This document
> captures the thinking so the generalization argument is not lost.
> Companion: [actionability-and-roi.md](./actionability-and-roi.md) picks up where this doc's
> prediction-fragility takeaway leaves off, and works out where the platform's value lives.
> **Date:** 2026-06-29

## The idea in one line

Polymer's value is not "a computational-biology tool." It is auditable provenance plus
recompute-ability for statistically/computationally generated claims. Biology is the first
and most demanding vertical, but the spine is horizontal: any field that produces
computational claims a regulator, investor, reviewer, or adversary will later challenge is
a candidate.

## Why this matters: what the platform spine actually is

Walking the architecture, there is a clean seam between a domain-agnostic spine and a
(deep but thin) biology adapter.

**Portable spine — nothing about it is biological:**

- **The claim object / claim graph** — a claim is an assertion + the exact computation that
  generated it + provenance + a recompute recipe. The assertion type is irrelevant.
- **Provenance + hash parity + recompute-ability** — hashes, versions, artifacts,
  presigned-URL data flow, cross-language SHA256 parity. This is the moat and it is
  domain-independent.
- **The governance / epistemic constitution layer** — constitutional violations, epistemic
  laws, bypass auditing. Encodes "what counts as a legitimately made claim." High value
  outside biology (finance compliance, model risk, regulatory audit) and rarely built as a
  first-class system.
- **The agent loop and Tool Registry** — question → task type → tool routing → artifact wrap
  → streamed result; pluggable computational backends.
- **Artifact-first** — primary output is a data file with lineage, not prose.

**Biology-welded adapter — becomes "one backend among many" when generalized:**

- SE / SCE / MAE data contracts (genomics containers).
- The R / Bioconductor engine and the bundled methods.

Generalizing does not mean removing the typed contract. The contract is exactly why hash
parity and recompute work. The right framing is: the contract layer is pluggable, and each
vertical ships its own rigorous contract. General spine, strict per-domain contracts. General
and loose would be a worse Jupyter; general and strict has no real competitor.

## The core question: where does two-method verification come from?

Our two-parameter / two-method verification is not free. It is a privilege of Bioconductor's
unusual maturity. Bioconductor fuses **four** things in one governed place, and the fourth is
what makes cross-method verification cheap and automatic:

1. **A shared typed data contract** (SummarizedExperiment / MAE) so packages interoperate.
2. **Curated peer review** of package submissions.
3. **Version-coordinated reproducible releases** — twice a year, every package tested together
   against one R/Bioconductor version, pinned by BiocManager.
4. **Method density** — many independent implementations of the same analysis, which is the
   *only* reason "compute the claim two ways and check they agree" is possible at all.

Most other fields have these pieces, but scattered across different institutions or with one
pillar missing. Almost none fuse all four.

## Landscape: analogous ecosystems by field

| Field | Closest ecosystem | Data contract | Reference impl (verification anchor) | Curated review | Coordinated reproducible release |
|---|---|---|---|---|---|
| **Astronomy** | Astropy (coordinated + affiliated packages) | Quantity, Table, units | core astropy | Yes (affiliated-pkg vetting) | Partial |
| **Classical ML / data science** | scikit-learn + NumPy/pandas + OpenML | ndarray / DataFrame | scikit-learn | Weak | OpenML (versioned datasets/tasks/flows/runs) |
| **Quant finance** | QuantLib (+ xts/pandas) | xts/zoo, pandas time series | QuantLib (banks treat it as ground truth) | None | None (the ecosystem is a list, not a tested release) |
| **Neuroimaging** | BIDS + fMRIPrep / Nipype | BIDS standard | fMRIPrep | Community | BIDS Apps (containerized) |
| **HEP / physics** | ROOT + scikit-hep | ROOT format | ROOT (CERN) | Light | Partial |
| **Chemistry / materials** | RDKit / pymatgen + Materials Project | mol objects / pymatgen | RDKit, pymatgen | Light | Partial |
| **Cross-field overlay** | JOSS / rOpenSci / pyOpenSci | — | — | Yes (Bioconductor's review ethos generalized) | — |

## Takeaways for the roadmap

**The data contract is everywhere; the coordinated release is the rare pillar.** Almost every
field already has an "SE-equivalent" substrate (pandas, BIDS, OGC simple features, Astropy
Quantity, xts). What is scarce outside biology is pillar #4 plus pillar #3 — the version-locked,
tested-together, redundant method ecosystem that makes two-method verification automatic. The
closest non-bio analogs are **Astropy** (most holistic) and **OpenML** (most provenance-shaped;
its runs record dataset and flow versions, hyperparameters, and hardware, which is strikingly
close to our claim object).

**Two-method verification is a privilege, not a given.** In **quant finance** and in
**deep-learning AI**, that substrate does not exist off the shelf. Finance has a strong
reference implementation (QuantLib, already treated as ground truth) but no curated,
version-coordinated ecosystem — verification there is a regulatory *process* (independent model
validation, SR 11-7), i.e. you hire a second team rather than import a second package. That is
expensive and manual, which is exactly the gap a provenance-and-governance layer fills.

**The wedge for vertical #2 picks itself.** Anchor on fields that already have a reference
implementation to verify against, even if the surrounding ecosystem is thin:

- **Quant finance** → verify against QuantLib (the second "eye" already exists; the coordination
  layer does not — that is our contribution).
- **Classical ML** → verify against scikit-learn, with OpenML as a ready-made provenance/recompute
  fabric to integrate or imitate.
- **Neuroimaging** → BIDS + fMRIPrep give both a contract and a reference pipeline.

Avoid, for now, frontier deep learning and "business analytics" generally — there is no reference
anchor to verify a second computation against, so the core guarantee weakens.

**One-line summary.** In biology Polymer *rides on* Bioconductor. In finance and AI, Polymer would
have to *be* the coordination-and-verification layer those fields never built — a harder build, but
a much larger and emptier space.

## Sources

- OpenML platform — https://www.openml.org/ ; OpenML: Insights from 10 years — https://pmc.ncbi.nlm.nih.gov/articles/PMC12416095/
- Astropy affiliated packages — https://www.astropy.org/affiliated/ ; Astropy vision — https://docs.astropy.org/en/latest/development/vision.html
- QuantLib — https://www.quantlib.org/ ; The QuantLib ecosystem — https://www.implementingquantlib.com/2025/03/quantlib-ecosystem.html
- rOpenSci software review — https://github.com/ropensci/software-review ; pyOpenSci peer review — https://www.pyopensci.org/software-peer-review/about/intro.html ; JOSS partnership — https://www.pyopensci.org/software-peer-review/partners/joss.html
