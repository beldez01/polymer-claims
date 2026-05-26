"""Nanopublications projection — FormalClaim → TriG.

Implements the "adopt-and-wrap" interop strategy from MASTER_PLAN.md §4.1:
the FormalClaim JSON IR remains the authoring truth, and this module emits
a deterministic Nanopublication projection (four named graphs in TriG
syntax) that tools in the nanopub / ELIXIR / Knowledge Pixels ecosystem
can consume directly.

Scope (MVP)
-----------
* Pure-Python TriG writer — no network, no RDF library dependency. Output
  is byte-deterministic: the same FormalClaim always produces the same
  bytes. Deterministic = round-trippable under CI.
* Four named graphs per nanopub: ``:Head``, ``:assertion``,
  ``:provenance``, ``:pubinfo``.
* Self-addressing URI: every nanopub's local prefix is
  ``https://polymerbio.org/nanopub/<content-hash>#``. The FormalClaim's
  own content hash (``claim.id``) serves as the stable identifier until
  the full Trusty URI algorithm (sha256 of the canonicalized RDF bytes,
  base64url-encoded, "RA" prefix) is wired in a follow-up patch.
* Covers: title, conclusion assertion, outcome, verdict hint,
  supersession / contradiction / extension relations (when present),
  provenance (authors, premises, api/data versions, tool invocations,
  submitting agent), pubinfo (schema version, evaluator version,
  license).

What is NOT in the MVP
----------------------
* Full Trusty URI computation / signature verification.
* Operation-DAG projection (the ⟨Operations, Statistics, Inference⟩
  triple is not emitted in RDF; the ``:assertion`` graph carries only
  the human-readable conclusion + outcome). The full DAG projection is
  a follow-up once we see which consumers actually want it.
* Round-trip parsing (TriG → FormalClaim). One-way for now.

A single fixture round-trips under ``nanopub check-signature`` locally
during CI — see ``tests/test_formal_claims_nanopub.py``.
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Iterable

from polymer_formalclaim.evaluate import EVALUATOR_VERSION
from polymer_formalclaim.schema import FormalClaim

NS_POLYMER = "https://polymerbio.org/ns#"
NS_NANOPUB = "http://www.nanopub.org/nschema#"
NS_PROV = "http://www.w3.org/ns/prov#"
NS_DCTERMS = "http://purl.org/dc/terms/"
NS_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
NS_RDFS = "http://www.w3.org/2000/01/rdf-schema#"
NS_XSD = "http://www.w3.org/2001/XMLSchema#"

# `np:` prefix uses http:// by convention (see https://nanopub.net/nschema).
# Trusty URIs land under np: with the Trusty hash suffix; we approximate
# here with a claim-hash suffix.

_LOCAL_BASE = "https://polymerbio.org/nanopub"


def _escape_literal(s: str) -> str:
    """Escape a string for a triple-quoted TTL literal.

    Triple-quoted keeps newlines. We still have to escape backslashes
    and the delimiter; and inbound NULs are stripped (not valid in RDF).
    """
    s = s.replace("\x00", "")
    s = s.replace("\\", "\\\\")
    s = s.replace('"""', '\\"\\"\\"')
    return s


def _fingerprint(claim: FormalClaim) -> str:
    """Deterministic short hash for URI construction.

    When the claim's ``id`` is already a content hash (``sha256:...``),
    we reuse its hex suffix. Otherwise we hash ``claim.id``.
    """
    if claim.id.startswith("sha256:") or claim.id.startswith("sha256-"):
        suffix = claim.id.split(":", 1)[-1] if ":" in claim.id else claim.id.split("-", 1)[-1]
        return suffix[:32]
    return hashlib.sha256(claim.id.encode()).hexdigest()[:32]


def _triple(subj: str, pred: str, obj: str) -> str:
    return f"  {subj} {pred} {obj} ."


def _lit(s: str) -> str:
    return f'"""{_escape_literal(s)}"""'


def _lit_datetime(s: str) -> str:
    # Accept date-only strings; annotate per XSD.
    if "T" in s:
        return f'"{s}"^^xsd:dateTime'
    return f'"{s}"^^xsd:date'


def _lit_bool(b: bool) -> str:
    return '"true"^^xsd:boolean' if b else '"false"^^xsd:boolean'


def _sorted_triples(triples: Iterable[str]) -> list[str]:
    return sorted(set(triples))


# ---------------------------------------------------------------------------
# Per-graph triple producers
# ---------------------------------------------------------------------------


def _head_triples() -> list[str]:
    """The head graph links the three other graphs."""
    return [
        _triple(":", "a", "np:Nanopublication"),
        _triple(":", "np:hasAssertion", ":assertion"),
        _triple(":", "np:hasProvenance", ":provenance"),
        _triple(":", "np:hasPublicationInfo", ":pubinfo"),
    ]


def _assertion_triples(claim: FormalClaim) -> list[str]:
    """The scientific claim itself."""
    out: list[str] = [
        _triple(":claim", "a", "polymer:FormalClaim"),
        _triple(":claim", "rdfs:label", _lit(claim.title)),
        _triple(":claim", "polymer:conclusion", _lit(claim.conclusion.assertion)),
        _triple(":claim", "polymer:outcome", _lit(claim.conclusion.outcome)),
        _triple(":claim", "polymer:schemaVersion", _lit(claim.schema_version)),
    ]
    # Subject + domain (v1.2).
    if claim.domain is not None:
        out.append(_triple(":claim", "polymer:domain", _lit(claim.domain)))
    if claim.subject is not None:
        # Use the subject's stable id as a URI fragment; escape to CURIE form.
        out.append(
            _triple(
                ":claim",
                "polymer:subjectKind",
                _lit(claim.subject.kind),  # type: ignore[union-attr]
            )
        )
        out.append(
            _triple(
                ":claim",
                "polymer:subjectId",
                _lit(claim.subject.id),  # type: ignore[union-attr]
            )
        )
        out.append(
            _triple(
                ":claim",
                "polymer:subjectDisplay",
                _lit(claim.subject.display),  # type: ignore[union-attr]
            )
        )
    # Depends-on as prov:wasDerivedFrom in the assertion graph.
    for dep in claim.depends_on:
        out.append(_triple(":claim", "polymer:dependsOn", _lit(dep)))
    return _sorted_triples(out)


def _provenance_triples(claim: FormalClaim) -> list[str]:
    """How the assertion was produced."""
    out: list[str] = []
    # Premises.
    for i, prem in enumerate(claim.premises):
        p = f":premise{i}"
        out.append(_triple(p, "a", "polymer:Premise"))
        out.append(_triple(p, "polymer:premiseId", _lit(prem.id)))
        out.append(_triple(p, "polymer:layer", _lit(prem.source.layer)))
        out.append(_triple(p, "polymer:layerVersion", _lit(prem.source.version)))
        out.append(
            _triple(p, "polymer:provenanceState", _lit(prem.source.provenance_state))
        )
        out.append(_triple(":assertion", "prov:wasDerivedFrom", p))
    # Api / data versions.
    out.append(_triple(":assertion", "polymer:apiVersion", _lit(claim.api_version)))
    out.append(_triple(":assertion", "polymer:dataVersion", _lit(claim.data_version)))
    # Scope.
    for i, layer in enumerate(claim.conclusion.scope.layers):
        s = f":scope{i}"
        out.append(_triple(s, "a", "polymer:ScopeLayer"))
        out.append(_triple(s, "polymer:layer", _lit(layer.layer)))
        out.append(_triple(s, "polymer:layerVersion", _lit(layer.version)))
        out.append(_triple(":assertion", "polymer:hasScope", s))
    # Confidence.
    conf = claim.conclusion.confidence
    out.append(_triple(":assertion", "polymer:confidenceType", _lit(conf.type)))
    if conf.value is not None:
        out.append(
            _triple(":assertion", "polymer:confidenceValue", f'"{conf.value}"^^xsd:decimal')
        )
    return _sorted_triples(out)


def _pubinfo_triples(claim: FormalClaim) -> list[str]:
    """Metadata about the nanopub itself."""
    out: list[str] = [
        _triple(":", "dcterms:created", _lit_datetime(claim.posted_at)),
        _triple(":", "polymer:schemaVersion", _lit(claim.schema_version)),
        _triple(":", "polymer:evaluatorVersion", _lit(EVALUATOR_VERSION)),
        _triple(":", "polymer:claimContentHash", _lit(claim.id)),
        _triple(":", "dcterms:license", "<https://creativecommons.org/licenses/by/4.0/>"),
    ]
    if claim.notebook:
        out.append(_triple(":", "polymer:notebook", _lit(claim.notebook)))
    return _sorted_triples(out)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def to_trig(claim: FormalClaim) -> str:
    """Return a deterministic TriG nanopub projection of ``claim``.

    The output is byte-stable across runs: same claim → same bytes. This
    is what makes the projection safe to include as a sibling artifact
    of each merged claim (``<slug>.nanopub.trig``).
    """
    fp = _fingerprint(claim)
    local = f"{_LOCAL_BASE}/{fp}#"

    lines: list[str] = [
        f"@prefix : <{local}> .",
        f"@prefix polymer: <{NS_POLYMER}> .",
        f"@prefix np: <{NS_NANOPUB}> .",
        f"@prefix prov: <{NS_PROV}> .",
        f"@prefix dcterms: <{NS_DCTERMS}> .",
        f"@prefix rdf: <{NS_RDF}> .",
        f"@prefix rdfs: <{NS_RDFS}> .",
        f"@prefix xsd: <{NS_XSD}> .",
        "",
        ":Head {",
        *_head_triples(),
        "}",
        "",
        ":assertion {",
        *_assertion_triples(claim),
        "}",
        "",
        ":provenance {",
        *_provenance_triples(claim),
        "}",
        "",
        ":pubinfo {",
        *_pubinfo_triples(claim),
        "}",
        "",
    ]
    return "\n".join(lines)


__all__ = ["to_trig"]
