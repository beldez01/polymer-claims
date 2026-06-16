# `pip install polymer-claims` packaging harness — design spec

> **Status:** design / decomposition spec, 2026-06-05 (autonomous-overnight; produced at the user's request
> to "set up a plan for designing the pip install"). **NOT a build plan to execute unattended** — this
> documents the recommended layout + CLI + the decisions; the actual build/scaffold and any PyPI publish
> are gated on the user (publish is blocked anyway — see Constraints). The protocol runtime is COMPLETE
> (`7e1d5c9`), so the engine this harness wraps is done.

## Goal

A single `pip install polymer-claims` that gives a user the whole stack — the `polymer_grammar` IR + the
`polymer_protocol` runtime + a thin CLI — as the first step toward "a local node" in the federated claims
universe ([[project_polymer_claims_platform_vision]]).

## Current state

- Two independent hatchling distributions: **`polymer-grammar`** (`grammar/`, import pkg `polymer_grammar`,
  dep `pydantic`) and **`polymer-protocol`** (`protocol/`, import pkg `polymer_protocol`, dep
  `polymer-grammar` via a uv path source). Each has its own `uv` env, tests, ruff.
- One-way isolation is enforced by a test (`grammar` never imports `protocol`/`v1.2`).
- No umbrella package, no CLI, no serialization entry points. `README.md` + `LICENSE` at the root.

## Constraints (hard)

- **NO PyPI publish unattended.** The `beldez01` account is flagged — OIDC-publish workflows are suppressed;
  publishing must be done locally with a token AND only when the user explicitly says so. This spec
  therefore stops at "buildable + test-installable locally"; the publish step is a documented, user-gated
  follow-up.
- **Preserve the one-way isolation** (`grammar` imports nothing from `protocol`) in whatever layout ships.
- **Don't break the two existing dev workflows** (`cd grammar && uv run pytest`, `cd protocol && uv run
  pytest`) — the per-package envs stay.

## The layout fork (recommended: B — umbrella meta-distribution)

**A. Single bundled distribution.** One `polymer-claims` wheel vendoring BOTH import packages
(`polymer_grammar` + `polymer_protocol` + a new `polymer_claims` CLI pkg) under one `pyproject`. Pros:
one wheel, simplest user story. Cons: restructures the repo's build layout, duplicates the two existing
distributions' packaging, and risks the isolation guarantee blurring under one build.

**B. Umbrella meta-distribution (RECOMMENDED).** Keep `polymer-grammar` and `polymer-protocol` exactly as
they are (two clean, separately-versioned distributions, isolation intact). Add a THIRD thin distribution
**`polymer-claims`** at the repo root whose `pyproject` declares `dependencies = ["polymer-protocol",
"polymer-grammar"]` and ships ONLY the CLI package `polymer_claims` + the `polymer-claims` console-script
entry point. `pip install polymer-claims` pulls the other two transitively. Pros: zero disruption to the
existing packages, the isolation test stays meaningful, each layer versions independently, the umbrella is
tiny. Cons: three distributions to (eventually) publish — but they publish as a set.

**C. uv workspace.** Convert the repo to a `uv` workspace and build all three together. Pros: clean
local dev. Cons: more moving parts; workspace publish story is still per-distribution. Not worth it over B.

**Recommendation: B.** It preserves everything we've built (isolation, two-package discipline, independent
versioning) and adds the smallest possible umbrella + CLI. The "single `pip install`" user story is fully
satisfied by transitive deps.

## Proposed structure (option B)

```
polymer-claims/                      # repo root
├── pyproject.toml                   # NEW: the `polymer-claims` umbrella distribution
├── src/polymer_claims/              # NEW: the CLI import package
│   ├── __init__.py                  # re-exports the public surface (optional convenience)
│   ├── cli.py                       # argparse/typer CLI; console_scripts entry point
│   └── io.py                        # Corpus <-> JSON (de)serialization helpers
├── grammar/                         # unchanged (polymer-grammar distribution)
├── protocol/                        # unchanged (polymer-protocol distribution)
└── tests/                           # NEW: umbrella/CLI tests (test-install + CLI smoke)
```

Umbrella `pyproject.toml` sketch:

```toml
[project]
name = "polymer-claims"
version = "0.1.0"
description = "Polymer Claims — the grammar + runtime for a local knowledge-generation node."
requires-python = ">=3.12"
dependencies = ["polymer-protocol", "polymer-grammar", "pydantic>=2.6"]

[project.scripts]
polymer-claims = "polymer_claims.cli:main"

[tool.uv.sources]
polymer-grammar = { path = "grammar", editable = true }
polymer-protocol = { path = "protocol", editable = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/polymer_claims"]
```

(For a real publish, the `[tool.uv.sources]` path overrides are dropped so the deps resolve from PyPI; keep
them for local dev/test-install.)

## CLI surface (thin wrapper over the COMPLETE runtime)

The CLI is a thin shell over what's already built — `run_cycle`, `next_action`, and the grammar validators.
Minimal v1 commands:

- `polymer-claims version` — print the three component versions.
- `polymer-claims validate <claim.json>` — load a claim through `Claim.model_validate`; report valid / the
  validation error. (Exercises the grammar.)
- `polymer-claims run-cycle <corpus.json> [--out <path>]` — deserialize a `Corpus`, run ONE `run_cycle`
  (reference adapters), serialize the resulting corpus + a short summary (counts by status, frontier).
- `polymer-claims loop <corpus.json> --budget <N> [--out <path>]` — drive the #5d budget-governed loop:
  repeatedly `next_action` → execute the recommended pass → thread state, until `None` or the budget
  exhausts; print the action trace + final corpus. **This is the headline command — it runs the whole
  flywheel as a local node.**

`io.py` handles `Corpus` (de)serialization via Pydantic (`model_dump_json` / `model_validate_json`) — the
models are already frozen Pydantic v2, so round-trip is free. The CLI injects the two deterministic
reference adapters (`IdentityAdapter`, `ReferenceAdapter`) by default; real adapters/oracles/red-teamers are
a later `--plugin` surface (out of scope for v1).

## Versioning

- Each distribution keeps its own `version` (grammar/protocol/claims). The umbrella's version is the
  user-facing release number; it pins compatible component ranges (e.g. `polymer-protocol>=0.1,<0.2`).
- Document the grammar's "foundational vs surface" policy (unified spec §7) in the umbrella README so users
  understand what a minor bump can change.

## Test / acceptance (local only — NO publish)

- `uv build` in each of the three dirs produces wheels without error.
- A throwaway venv `pip install`s the locally-built `polymer-claims` wheel (+ the two component wheels) and:
  - `polymer-claims version` prints all three versions;
  - `polymer-claims validate` accepts a valid claim JSON and rejects a malformed one;
  - `polymer-claims loop <small-corpus> --budget 100` runs to completion and licenses ≥1 claim
    (the runtime smoke, end-to-end, through the installed package).
- The isolation test still passes (the umbrella doesn't let grammar import protocol).
- ruff clean on `src/polymer_claims`.

## Decomposition into buildable tasks (when the user greenlights)

1. **Umbrella + CLI scaffold** — `pyproject.toml`, `src/polymer_claims/{__init__,cli,io}.py`, the
   `console_scripts` entry, `version`/`validate` commands + tests.
2. **`run-cycle` + `loop` commands** — `io.py` Corpus (de)serialization + the two runtime commands wired to
   `run_cycle`/`next_action` with reference adapters; CLI smoke tests.
3. **Local build + test-install harness** — a script that `uv build`s all three and `pip install`s into a
   throwaway venv and runs the CLI smoke (no publish).
4. **(USER-GATED) publish** — drop the path sources, build final wheels, publish locally with a token. NOT
   automated; explicitly the user's call.

## Out of scope (v1)

- Real (network/R/scipy) adapters, oracle registries, injected LLM red-teamers behind a `--plugin` surface.
- Any federated/networking layer (the "federated universe" is the platform-vision arc, built separately).
- PyPI publish / CI (flagged account).
- A persistent on-disk corpus store (v1 is file-in / file-out JSON).
