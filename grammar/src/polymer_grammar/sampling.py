"""Sampling regime enum — pure / numpy-free: grammar + stdlib only."""
from __future__ import annotations

from enum import Enum


class SamplingRegime(str, Enum):
    IID_EXAMPLES = "iid_examples"
