# v1.2 — frozen fallback

This directory holds the **complete v1.2 Polymer Claims ecosystem**, consolidated here and
**frozen on 2026-06-01**. It is kept **as a fallback** in case the ground-up v1.3 grammar
rebuild (`../grammar/`) proves a dead end. **Nothing here is deleted; it is paused.**

The active work is the v1.3 grammar — see the repo-root `README.md` and `../docs/superpowers/CONTINUE.md`.

## What's here

| Path | What it is |
|---|---|
| `formalclaim/` | The FormalClaim **IR v1.2** Python package (`polymer_formalclaim`) — pydantic models, 3-valued evaluator, materialization dispatcher, Nanopub projection, CLI + MCP server. |
| `corpus/` | The claims corpus — 47 primary claims (+ negatives/sidecars) across domains, plus governance, tiers, contributors, the canonical JSON Schema, and the CI evaluator. |
| `plugins/claim-harness/` | The Claude Code plugin — MCP bundle, claim-authoring skills, submission pipeline. |
| `scripts/sync_schema.sh` | Single-source-of-truth guard copying the corpus JSON Schema into the plugin. |
| `legacy-workflows/` | The 5 GitHub Actions workflows, moved out of `.github/workflows/` so they no longer auto-register (Actions were account-flagged and never ran). |
| `docs/` | v1.2-era design docs: the superseded 2026-05-29 claim-PATTERN spec + spatial map, and the 2026-05-19 FormalClaim domain-ontology note. |

## Internal wiring (preserved by the move)

All couplings are **relative within this directory**, so the ecosystem still works in place:

- `corpus/evaluator/pyproject.toml` resolves the IR via uv path source `../../formalclaim`.
- Corpus claim files reference `../../../schema/formal_claim_v1.2.schema.json` (relative).
- `scripts/sync_schema.sh` derives `ROOT` from its own location (now `v1.2/`), then reads
  `$ROOT/corpus/...` and `$ROOT/plugins/...`. Verified: `bash v1.2/scripts/sync_schema.sh --check` → "schema in sync".

The repo-root `.claude-plugin/marketplace.json` was repointed to `./v1.2/plugins/claim-harness`.

## If v1.3 fails and v1.2 is reactivated

1. Decide whether to promote `v1.2/` back to the repo root or keep it nested (update
   `marketplace.json` + any CI paths accordingly).
2. To re-enable CI, move `legacy-workflows/*.yml` back to `.github/workflows/` (and resolve the
   GitHub account flag that blocks Actions).
3. PyPI publish (deferred): configure the pending Trusted Publisher (Project `polymer-formalclaim`,
   Owner `beldez01`, Repo `polymer-claims`, Workflow `publish-formalclaim.yml`), then push a
   `formalclaim-vX.Y.Z` tag. (Account flag currently blocks OIDC publish — publish locally with a token.)

## Note on ontology — a live v1.3 concern

`docs/FormalClaim_Domain_Ontology_Note.md` lives here, but the **idea it captures (a small IR
whose biological complexity is carried by versioned, ontology-bound domain profiles) remains
load-bearing for v1.3** — it is absorbed into the unified foundations spec (`../docs/superpowers/specs/2026-05-31-unified-claim-foundations-spec.md`, §3.1 profiles and §7 functorial ontology migration). Do not treat the ontology question as frozen just because this note is.
