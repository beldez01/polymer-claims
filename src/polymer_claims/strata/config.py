"""Data-root config for the lifted STRATA pharmacogenomic engine.

Defaults to the gitignored ``data/pharmaco/`` tree at the polymer-claims repo
root; override with the ``STRATA_DATA_ROOT`` env var. Unlike the original Hack
config this has **no import-time side effects** (it does not create directories).
"""

from __future__ import annotations

import os
from pathlib import Path

# this file: <repo>/src/polymer_claims/strata/config.py  ->  parents[3] == <repo>
_REPO_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = Path(os.environ.get("STRATA_DATA_ROOT", _REPO_ROOT / "data" / "pharmaco"))

RANDOM_STATE = 0
N_TOP_FEATURES = 2000
