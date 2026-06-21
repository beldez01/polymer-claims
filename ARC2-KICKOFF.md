# Arc-2 Kickoff — Standards Skin (in-toto/SLSA attestation)

> Paste-ready brief for a fresh Claude Code instance working in THIS worktree
> (`/Users/zbb2/Desktop/polymer-claims-arc2`, branch `feat/standards-skin-attestation`).
> A sibling instance is concurrently building **arc 3** (sheaf follow-ups) in the main
> checkout `/Users/zbb2/Desktop/polymer-claims` on a different branch. Stay in YOUR worktree.

## What this project is (one line)
Polymer Claims is a compiler + runtime for science: a **recomputation gate** where an empirical
claim *earns* standing (independent re-execution + e-value criterion + defeat graph + FDR budget)
instead of asserting it. Grammar (`grammar/`) → protocol runtime (`protocol/`) → umbrella node +
CLI (`src/polymer_claims/`) → 3D viewer (`viewer/`).

## Your mission: North-Star arc 2 — the standards skin (adoption moat)
Read the strategy first:
- `docs/superpowers/2026-06-12-phase-2-north-star.md` — **§4 (pan-integrator seams, ranked)** and **§6 (sequencing: arc 2)**.
- `docs/superpowers/2026-06-16-linchpin-thesis-three-layer-arc.md` — **A1 (the "Earn-Standing" API — Sigstore/Rekor for empirical biology)**.
- `docs/superpowers/polymer-claims-canonical-spec.md` — what's built (esp. the epistemic core + content-address: `dimnames_hash`, `profile_hash`, `semantic_run_id`, the DRS-shaped SE-Contract seam).
- `ARCHITECTURE_CURRENT.md`, `GLOSSARY.md`, `docs/superpowers/CONTINUE.md` (current state).

**The thesis:** don't integrate the world's data/compute — integrate *trust over* it. Re-express our
content-address / apparatus / run model **as the standards that already exist** so we're natively a
node in the GA4GH/FAIR fabric. North-star §4 ranks the seams: DRS (#1), Workflow-Run RO-Crate + TRS
(#2), **in-toto/SLSA + Sigstore/Rekor (#3)**, WES (#4), FAIR Signposting (#5), Refget SeqCol (#6).

## Recommended FIRST slice (scope tightly — YAGNI)
**Emit a licensed run as a deterministic in-toto/SLSA-style attestation JSON**, keyed by the content
address we already compute. Concretely:
- Input: a LICENSED claim + its `Licensing` content-address (`dimnames_hash` + `profile_hash` +
  `semantic_run_id`) and the agreeing adapter/credential identities.
- Output: an in-toto statement (`subject` = the licensed output hash; `predicateType` = SLSA
  provenance-ish; `resolvedDependencies` = input DRS checksums / dimnames+profile hashes; the
  adapter air-gap pair as the "builder" witnesses). A `drs://`-shaped handle doc for the dataset is
  a natural companion.
- **Deterministic, local-file output. NO signing keys / NO network / NO Rekor in slice 1** — that's
  a later slice. Keep it a pure, content-addressed JSON shape that any third party could later sign.
- Surface it like the other exports: a CLI command (e.g. `export-attestation <corpus>`), mirroring
  `export-topology` / `export-consistency`.

This is the "safe first slice of the standards arc" CONTINUE.md flags. Confirm scope in brainstorm.

## Hard invariants (DO NOT violate — same rules the rest of the repo lives by)
- **Purity:** `grammar/` and `protocol/` stay pure/deterministic/numpy-free (no clock/random/IO).
  Any signing/IO/external-dep work is **umbrella-side** (`src/polymer_claims/`). The slice-1 JSON
  serializer is deterministic; put it umbrella-side (e.g. `src/polymer_claims/attestation.py`).
- **Zero new heavy deps if avoidable.** Use stdlib `json`/`hashlib`. Real Sigstore/Rekor/cosign is a
  later, optional slice behind its own extra — do not pull it into slice 1.
- **Additive / byte-identical when off:** new fields land `X | None = None`; existing behavior
  unchanged when the feature isn't invoked. `Corpus` stays **exactly 4 collections**.
- **Frozen models:** all models subclass `_Model` (frozen, `extra="forbid"`); collection fields are
  **tuples**, never `dict`/`list`. (`_Model` is `from .base import _Model` in protocol.)
- **TDD:** failing test first. Per-package gate: `uv run pytest -q` + `uv run ruff check src tests`.
- **Reuse, don't reinvent:** the content address already exists — `Licensing` carries
  `dimnames_hash`/`profile_hash`/`semantic_run_id`; `AnalysisProfile` is content-addressed; the
  SE-Contract is DRS-shaped (`self_uri`, `checksums`). Build the attestation FROM these.

## File boundaries (to avoid conflicts with the arc-3 instance)
- **Safe to own:** a NEW umbrella module (`src/polymer_claims/attestation.py`) + its tests; new CLI
  subcommand in `cli.py`; new exports in `src/polymer_claims/__init__.py`.
- **DO NOT touch** (arc 3 owns these): `protocol/src/polymer_protocol/sheaf.py`,
  `src/polymer_claims/sheaf_spectrum.py`, the viewer's sheaf/topology rendering, anything under the
  sheaf gauge.
- **Coordinate / keep edits minimal & append-only:** `cli.py`, `src/polymer_claims/__init__.py`,
  `CONTINUE.md`, `ARCHITECTURE_CURRENT.md`, `GLOSSARY.md`. Both instances will edit these — keep your
  additions localized and expect to resolve a small merge.
- If you need a field on `TopologyExport`, flag it — arc 3 also touches that DTO.

## Workspace setup (this worktree)
- It shares the repo's git object store but has its own working tree. Run `uv sync` (or just
  `uv run pytest -q` once, which bootstraps `.venv`) in THIS directory.
- **`scripts/check-all.sh` hardcodes `ROOT=/Users/zbb2/Desktop/polymer-claims`** — so it'll run the
  *other* checkout, not yours. Either (a) run per-package commands directly
  (`cd grammar && uv run pytest -q`, etc.), or (b) change that line to
  `ROOT="$(cd "$(dirname "$0")/.." && pwd)"` as your first commit (a genuine improvement — but it's a
  shared file, so mention it at merge).

## Process (the repo's rhythm)
1. **`superpowers:brainstorming`** → scope the first slice (2-3 questions), get the design approved,
   write the spec to `docs/superpowers/specs/2026-06-2X-standards-skin-attestation-design.md`.
2. **`superpowers:writing-plans`** → bite-sized TDD plan to
   `docs/superpowers/plans/2026-06-2X-standards-skin-attestation.md`.
3. **`superpowers:subagent-driven-development`** → implement task-by-task with reviews.
4. **Merge `--no-ff` to `main`** — but COORDINATE: only one branch merges at a time. The arc-3
   instance is the sibling; whoever merges second rebases/merges on top and resolves the shared-doc
   conflicts.

## Coordination summary
- Separate worktree, separate branch, **sequential `--no-ff` merges**.
- We don't share memory — everything you need is in the docs above.
- When you're ready to merge, check whether the arc-3 branch landed first; if so,
  `git fetch && git rebase origin/main` (or merge main in) before your `--no-ff` merge.
```
