"""File-in / file-out (de)serialization helpers for the v1 CLI.

The grammar/protocol models are frozen Pydantic v2, so JSON round-trip is free —
these helpers are thin wrappers that read a path and validate, or dump to a string.
"""
from __future__ import annotations

from pathlib import Path

from polymer_protocol import Corpus


def load_corpus(path: str | Path) -> Corpus:
    """Read a JSON file and validate it as a `Corpus`."""
    text = Path(path).read_text()
    return Corpus.model_validate_json(text)


def dump_corpus(corpus: Corpus) -> str:
    """Serialize a `Corpus` to a JSON string."""
    return corpus.model_dump_json()
