"""Content-addressed BenchmarkArtifact, label-free BenchmarkAdapter Protocol,
and deterministic fixture predictors for the V2.0 evidence-licensed capability.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, field_validator

from polymer_grammar import SamplingRegime

from ._hashing import canonical_sha256
from .benchmark_evidence import PredictionVector

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# BenchmarkExample — immutable unit of evidence (carries label for content-addressing)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkExample:
    """A single labelled example.  Label is included for content-addressing; adapters
    receive the full tuple but MUST NOT read ``.label`` when producing predictions."""

    example_id: str
    features: tuple[tuple[str, str], ...]
    label: str


# ---------------------------------------------------------------------------
# BenchmarkArtifact — frozen pydantic model with validators
# ---------------------------------------------------------------------------


class BenchmarkArtifact(BaseModel, frozen=True):
    """Content-addressed benchmark dataset.

    ``ref`` = ``"bench:sha256:<hex>"`` — matches DataRefKind.BENCHMARK.
    """

    examples: tuple[BenchmarkExample, ...]
    target_population: str
    sampling_regime: SamplingRegime
    version: str
    sampling_seed: int
    dgp_digest: str

    # ------------------------------------------------------------------
    # Field validators
    # ------------------------------------------------------------------

    @field_validator("target_population", "version")
    @classmethod
    def _nonempty_str(cls, v: str, info) -> str:
        if not v.strip():
            raise ValueError(f"{info.field_name} must be non-empty")
        return v

    @field_validator("dgp_digest")
    @classmethod
    def _sha256_shaped(cls, v: str) -> str:
        if not _SHA256_RE.match(v):
            raise ValueError(
                f"dgp_digest must be 'sha256:<64 hex chars>', got {v!r}"
            )
        return v

    @field_validator("examples")
    @classmethod
    def _validate_examples(
        cls, examples: tuple[BenchmarkExample, ...]
    ) -> tuple[BenchmarkExample, ...]:
        seen_ids: set[str] = set()
        for ex in examples:
            if not ex.label:
                raise ValueError(
                    f"BenchmarkExample label must be non-empty; example_id={ex.example_id!r} has empty label"
                )
            if ex.example_id in seen_ids:
                raise ValueError(
                    f"Duplicate example_id in examples: {ex.example_id!r}"
                )
            seen_ids.add(ex.example_id)
        return examples

    # ------------------------------------------------------------------
    # Content-address properties
    # ------------------------------------------------------------------

    @property
    def content_hash(self) -> str:
        """``sha256:<hex>`` over the canonical JSON of ``model_dump(mode='json')``."""
        return canonical_sha256(self.model_dump(mode="json"))

    @property
    def ref(self) -> str:
        """``bench:sha256:<hex>`` — matches DataRefKind.BENCHMARK."""
        return "bench:" + self.content_hash


# ---------------------------------------------------------------------------
# BenchmarkAdapter — typing.Protocol (label-free predict)
# ---------------------------------------------------------------------------


@runtime_checkable
class BenchmarkAdapter(Protocol):
    """Protocol for benchmark adapters.  ``predict`` receives BenchmarkExamples
    but MUST derive predictions only from ``example_id`` and ``features`` —
    never from ``label``."""

    identity: str
    config: dict

    def predict(
        self,
        examples: tuple[BenchmarkExample, ...],
    ) -> PredictionVector:
        ...


# ---------------------------------------------------------------------------
# Fixture adapters — deterministic, seeded independently of labels
# ---------------------------------------------------------------------------

_FIXTURE_CLASSES = ("pos", "neg", "unk")


class FixtureModelAdapter:
    """Deterministic fixture model adapter.  Predictions derived from feature
    values and example_id only — never from labels."""

    def __init__(self, identity: str = "fixture-model", config: dict | None = None) -> None:
        self.identity = identity
        self.config: dict = config if config is not None else {}

    def predict(
        self,
        examples: tuple[BenchmarkExample, ...],
    ) -> PredictionVector:
        preds: list[tuple[str, str]] = []
        for ex in examples:
            # Hash of id + features → deterministic class selection, label-free
            feature_str = ":".join(f"{k}={v}" for k, v in ex.features)
            raw = hashlib.sha256(
                f"fixture-model:{ex.example_id}:{feature_str}".encode()
            ).digest()
            cls = _FIXTURE_CLASSES[raw[0] % len(_FIXTURE_CLASSES)]
            preds.append((ex.example_id, cls))
        return PredictionVector(tuple(preds))


class FixtureBaselineAdapter:
    """Deterministic fixture baseline adapter.  Always predicts the majority
    class derived from example_id hash — never from labels."""

    def __init__(self, identity: str = "fixture-baseline", config: dict | None = None) -> None:
        self.identity = identity
        self.config: dict = config if config is not None else {}

    def predict(
        self,
        examples: tuple[BenchmarkExample, ...],
    ) -> PredictionVector:
        preds: list[tuple[str, str]] = []
        for ex in examples:
            raw = hashlib.sha256(
                f"fixture-baseline:{ex.example_id}".encode()
            ).digest()
            # Use only first two classes for a simple baseline
            cls = ("neg", "pos")[raw[0] % 2]
            preds.append((ex.example_id, cls))
        return PredictionVector(tuple(preds))
