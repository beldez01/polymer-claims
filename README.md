# polymer-claims

Consolidated home for the Polymer Claims agent-scientist ecosystem. One repo, three subprojects:

| Subdir | What it is | Distribution |
|---|---|---|
| `formalclaim/` | The FormalClaim IR v1.2 — pydantic models, three-valued inference evaluator, materialization dispatcher, Nanopublications projection, CLI + MCP server. **Canonical source of the IR.** | PyPI: `polymer-formalclaim` (tag `formalclaim-vX.Y.Z`) |
| `corpus/` | The public claims corpus: domains, tiers, contributors, governance, JSON Schema contract, and the CI evaluator. PR-as-submission target. | GitHub PRs to `corpus/domains/**/claims/*.json` |
| `plugins/claim-harness/` | The Claude Code plugin: MCP bundle, claim-authoring skills, submission pipeline. | `/plugin marketplace add beldez01/polymer-claims` |

## Source of truth

- **Python IR:** `formalclaim/src/polymer_formalclaim/` — everything else imports it. The corpus evaluator
  consumes it via a uv path source (`corpus/evaluator/pyproject.toml`); no PyPI needed for local CI.
- **JSON Schema:** `corpus/schema/formal_claim_v1.2.schema.json` is canonical; `scripts/sync_schema.sh`
  copies it into the plugin and `scripts/sync_schema.sh --check` guards against drift.

## History

Consolidated 2026-05-26 from three now-archived repos: `beldez01/claims`,
`beldez01/polymer-formalclaim`, `beldez01/polymer-claim-marketplace`.

## Deferred

The flagship `PolymerGenomicsAPI` still vendors its own copy of the IR
(`src/polymer_genomics/formal_claims/`). Once `polymer-formalclaim` is published to PyPI, the API will
depend on the package and drop its vendored `schema/evaluate/materialize/nanopub`, keeping only its
API-specific `projection.py` + `feature_extractor.py`.

## PyPI publishing

`polymer-formalclaim` is not yet on PyPI. To publish: configure the PyPI pending Trusted Publisher
(Project `polymer-formalclaim`, Owner `beldez01`, Repository `polymer-claims`, Workflow
`publish-formalclaim.yml`), then push a `formalclaim-vX.Y.Z` tag.
