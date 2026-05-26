"""polymer-formalclaim-mcp — stdio MCP server exposing claim-IR tools.

Registered as the `claim-ir` MCP server in the Polymer Claims harness
`.mcp.json`. Provides:

    validate_claim(claim_path)         → verdict + per-conjunct breakdown
    evaluate_claim(claim_path)         → full EvaluationResult JSON
    search_corpus(filter)              → top-K claims matching filter
    query_neighbors(draft_claim, k)    → k-nearest in embedding space
    fetch_claim(claim_id)              → full IR JSON for one claim
    check_contradictions(draft_claim)  → existing claims opposing the draft

Phase 0: implements validate/evaluate only. Search / neighbors /
contradictions require a corpus snapshot + embedding pipeline; wired in
Phase 1 once the public corpus is live.
"""

from __future__ import annotations

import sys


def main() -> int:
    # Imported lazily — the `mcp` SDK is an optional extra.
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
    except ImportError:
        print(
            "polymer-formalclaim-mcp requires the optional `mcp` extra.\n"
            "Install with: pip install 'polymer-formalclaim[mcp]'",
            file=sys.stderr,
        )
        return 1

    # MCP server scaffold. Implementation of tools lands when the evaluator
    # submodule is synced into this package — see README "Sync from monorepo".
    server = Server("polymer-formalclaim")

    @server.list_tools()  # type: ignore[misc]
    async def _list_tools() -> list:
        return []  # populated when evaluator is synced

    import anyio  # mcp already depends on anyio

    async def _run() -> None:
        async with stdio_server() as (reader, writer):
            await server.run(reader, writer, server.create_initialization_options())

    anyio.run(_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
