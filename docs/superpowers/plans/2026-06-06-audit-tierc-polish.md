# Audit Tier-C Polish — Plan

> Small, additive polish of the remaining cheap audit items (no substantial refactoring). LOCAL ONLY.
> Source: `/Users/zbb2/Desktop/polymer-claims-audit.md`. Branch `feat/audit-tierc-polish`.

**Skipped (policy):** #13–15 (v1.2 evaluator semantics) — v1.2 is frozen-legacy, already bannered; un-freezing is out of scope.

**Verify:** `bash scripts/check-all.sh` must reach ALL GREEN. ABSOLUTE paths.

## Item 1 — #10 contract hardening (protocol DTO + viewer mirror + drift test)
- `protocol/topology.py`: module const `CONTRACT_VERSION = "1.0"`; add `contract_version: str = CONTRACT_VERSION` to `TopologyExport`; add a `@model_validator(mode="after")` on `TopologyNode` requiring `len(strength) == len(AXES)` (6) when present (the audit's "enforce exact length/order" — order is already guaranteed by the `AXES`-ordered export).
- `protocol/timeline.py`: add `contract_version: str` to `TopologyTimeline` (import the const from topology).
- `viewer/src/lib/topology.ts` + `timeline.ts`: add `contract_version: string` to the mirrored interfaces; keep the `StrengthVector` 6-tuple doc.
- Regenerate `viewer/public/sample-topology.json` + `sample-timeline.json` so the committed fixtures carry the field.
- **Drift test** (umbrella `tests/test_viewer_contract.py`): load both committed viewer fixtures, validate via `TopologyExport`/`TopologyTimeline`, assert JSON round-trip — guards protocol↔fixture drift.

## Item 2 — #4-light run_cycle output revalidation guard
- `protocol/tests/`: a test asserting `Corpus.model_validate(res.corpus.model_dump()) == res.corpus` after `run_cycle` across licensing / rejection / generation scenarios — catches any `model_copy(update=)` that yields an invalid corpus.

## Item 3 — #12-light protocol public-API sectioning
- `protocol/__init__.py`: reorganize the `__all__` (and the import block if clean) into COMMENTED sections — `# stable contracts`, `# runtime`, `# adapters / generation`, `# daemons`, `# topology/timeline`, `# experimental/internal`. NO moves of code, NO renames — comments only, signalling intent (the no-refactor version of the audit's facade idea).

## Item 4 — #17 packaging metadata
- All three `pyproject.toml` (root/grammar/protocol): add `readme`, `license`, `authors`, `keywords`, `classifiers`, `[project.urls]`. Add dependency BOUNDS: umbrella `polymer-grammar>=0.1,<0.2`/`polymer-protocol>=0.1,<0.2`; protocol `polymer-grammar>=0.1,<0.2`. (uv path-sources still override for local dev; bounds apply at publish.) Keep versions at 0.1.0.

**After:** check-all ALL GREEN; finish branch (merge local no-ff, no push); CONTINUE.md + memory note.
