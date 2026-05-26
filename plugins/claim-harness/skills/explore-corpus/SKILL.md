---
name: explore-corpus
description: Use to search the canonical claim corpus before authoring a new claim. Finds related claims, reveals open gaps, prevents duplicates, and gives the agent a reading list of worked examples.
---

# Explore the corpus

The Polymer Claims corpus is the body of machine-verifiable claims at `github.com/beldez01/polymer-claims`. Before authoring a new claim, find out what has already been said.

## Usage

Typical agent flow:

1. User asks a research question.
2. Agent calls `search_corpus(filter=...)` via the `claim-ir` MCP.
3. Agent reads the top 5–10 nearest claims (their titles + conclusions + evaluator payloads) to identify:
   - **Duplication** — has this exact claim been made? If so, cite it in `depends_on` instead of duplicating.
   - **Extensions** — has a narrower version been claimed? Declare `relations.extends: [...]`.
   - **Contradictions** — is there an existing claim that reaches the opposite conclusion on the same subject? Declare `relations.contradicts: [...]` — disputes are first-class.
   - **Open gaps** — what is plausibly claimable but not yet claimed?
4. Agent reads at least one REJECTED example too — REJECTED claims teach the implicit rules of what fails the evaluator.

## MCP tools

| Tool | Purpose | Input |
|---|---|---|
| `search_corpus` | Free-text + filter search | `{text, domain, subject_kind, outcome, evidence_class, topic, freshness_days}` |
| `query_neighbors` | Embed a draft claim and return k-nearest | `{claim_draft, k}` |
| `fetch_claim` | Full IR JSON for one claim | `{claim_id}` |
| `check_contradictions` | Return known claims that oppose the draft on the same subject | `{claim_draft}` |

## Reading a claim

When the agent fetches a claim, walk it panel-by-panel:

1. **Subject + domain** — what is this claim about?
2. **Premises** — what data sources? Which `provenance_state`? If `canonical_db`, it's reproducible today; if `local_file`, the author ran it locally.
3. **Operations** — the DAG. Which estimator? Which CV scheme? Which null model?
4. **Statistics** — pinned values. Which evidence class?
5. **Inference** — the rule the evaluator walks. The conjunct thresholds are the author's pre-registered commitment.
6. **Conclusion** — the one-sentence assertion + `outcome`.

## When no close match exists

Good. You have a novel claim. Proceed to `/author-claim`. But cite the absence — `external_assumptions` can carry an entry like `{statement: "No prior claim covers this subject at this data version", kind: "design_choice", confidence: 0.9}`.
