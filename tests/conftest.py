"""Pytest configuration."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
"""Pytest configuration for the orchestrator project."""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, "..", "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
