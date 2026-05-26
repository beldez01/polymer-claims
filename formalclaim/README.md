# polymer-formalclaim

FormalClaim IR v1.2 — pydantic models, three-valued inference evaluator, operation-DAG materialization dispatcher, Nanopublications projection, and a stdio MCP server. Standalone distribution of what lives inside the PolymerGenomicsAPI monorepo at `src/polymer_genomics/formal_claims/`.

## Install

```bash
pip install polymer-formalclaim
# or (harness pattern):
uvx --from 'polymer-formalclaim>=0.2.0' polymer-formalclaim validate <claim.json>
```

Optional `mcp` extra for the stdio server:

```bash
pip install 'polymer-formalclaim[mcp]'
```

## CLI

```bash
polymer-formalclaim validate <claim.json>            # inference verdict
polymer-formalclaim validate --fail-on-pending <x>   # non-zero exit on PENDING
polymer-formalclaim refresh-corpus --pointer ./corpus/pointer.json
```

## MCP server

Registered in the Polymer Claims harness `.mcp.json` as `claim-ir`:

```json
{
  "mcpServers": {
    "claim-ir": {
      "command": "uvx",
      "args": ["--from", "polymer-formalclaim>=0.2.0", "polymer-formalclaim-mcp"]
    }
  }
}
```

## Release flow

This package is the **canonical source** of the FormalClaim IR — it lives in the `formalclaim/` subdir of
the [`beldez01/polymer-claims`](https://github.com/beldez01/polymer-claims) monorepo and is published to
PyPI from there:

1. Push a `formalclaim-v<semver>` tag.
2. `.github/workflows/publish-formalclaim.yml` fires (path-filtered to `formalclaim/**`).
3. `uv build` → wheel + sdist.
4. `pypa/gh-action-pypi-publish` with PyPI **Trusted Publishing** (OIDC, no API token stored).

Trusted publisher must be configured at `https://pypi.org/manage/account/publishing/` (pending publisher
until the first release) with:

- **PyPI Project name:** `polymer-formalclaim`
- **Repository owner:** `beldez01`
- **Repository name:** `polymer-claims`
- **Workflow filename:** `publish-formalclaim.yml`
- **Environment name:** (leave empty, or restrict to a `release` env)

## License

MIT. See `LICENSE`.

Claims authored using this library are licensed by the corpus they're submitted to — the
[`beldez01/polymer-claims`](https://github.com/beldez01/polymer-claims) corpus uses CC-BY-4.0.
