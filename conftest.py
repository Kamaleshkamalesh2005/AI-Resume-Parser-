"""
Root-level pytest configuration.

Ensures the ``backend/`` directory is resolved before the repository root so
that ``import app`` always resolves to ``backend/app``, not to the incomplete
root-level ``app/`` stub left over from the project restructuring.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent)
_BACKEND = str(Path(__file__).parent / "backend")

# Insert backend/ at position 0 so it is searched before the repo root.
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# Remove the repo root from sys.path (it may appear as '' or as an absolute
# path) so the incomplete root-level ``app/`` package cannot shadow
# ``backend/app/``.
_paths_to_remove = {_REPO_ROOT, "", os.getcwd()}
sys.path[:] = [p for p in sys.path if p not in _paths_to_remove]

# Ensure backend/ remains first.
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)
